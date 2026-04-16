"""OCR evaluation metrics: CER, WER, Field-F1, ANLS, KVRR.

All metrics expect pre-normalized strings (see normalize() in datasets.py).
See METHODOLOGY.md §1 for scientific rationale behind each metric.
"""
import re
import unicodedata
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

def normalize(text: str, *, fold_case: bool = False, fold_diacritics: bool = False) -> str:
    """Standard pre-comparison normalization pipeline (METHODOLOGY.md §2)."""
    text = unicodedata.normalize("NFC", text)
    text = "".join(c for c in text if unicodedata.category(c) not in ("Cf",))  # remove format chars
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\xa0\u2009\u200a]+", " ", text).strip()
    if fold_diacritics:
        text = "".join(
            c for c in unicodedata.normalize("NFD", text)
            if unicodedata.category(c) != "Mn"
        )
    if fold_case:
        text = text.casefold()
    return text


def _edit_distance(a: str, b: str) -> int:
    """Wagner-Fischer Levenshtein distance, O(min(m,n)) space."""
    m, n = len(a), len(b)
    if m < n:
        a, b, m, n = b, a, n, m
    prev = list(range(n + 1))
    for i, ca in enumerate(a, 1):
        curr = [i] + [0] * n
        for j, cb in enumerate(b, 1):
            curr[j] = (
                prev[j - 1] if ca == cb
                else 1 + min(prev[j], curr[j - 1], prev[j - 1])
            )
        prev = curr
    return prev[n]


# ---------------------------------------------------------------------------
# CER / WER
# ---------------------------------------------------------------------------

def cer(reference: str, hypothesis: str) -> float:
    """Character Error Rate. Returns 0.0 when both strings are empty."""
    if not reference:
        return 0.0 if not hypothesis else float("inf")
    return _edit_distance(reference, hypothesis) / len(reference)


def wer(reference: str, hypothesis: str) -> float:
    """Word Error Rate. Tokenizes on whitespace (punctuation attached)."""
    def _tokens(s: str) -> list[str]:
        return s.split()

    ref_t, hyp_t = _tokens(reference), _tokens(hypothesis)
    if not ref_t:
        return 0.0 if not hyp_t else float("inf")
    return _edit_distance(ref_t, hyp_t) / len(ref_t)  # type: ignore[arg-type]


def cer_no_diacritic(reference: str, hypothesis: str) -> float:
    """Secondary metric: CER after stripping diacritics (METHODOLOGY.md §1.2)."""
    return cer(
        normalize(reference, fold_diacritics=True),
        normalize(hypothesis, fold_diacritics=True),
    )


# ---------------------------------------------------------------------------
# ANLS (DocVQA standard, METHODOLOGY.md §1.6)
# ---------------------------------------------------------------------------

def _ned(pred: str, gt: str) -> float:
    denom = max(len(pred), len(gt))
    return 0.0 if denom == 0 else _edit_distance(pred, gt) / denom


def anls_score(pred: str, ground_truths: list[str], threshold: float = 0.5) -> float:
    """ANLS for a single prediction against one or more ground truths."""
    if not ground_truths:
        return 0.0
    best_nls = max(1.0 - _ned(pred, gt) for gt in ground_truths)
    return best_nls if best_nls >= threshold else 0.0


def anls(predictions: list[str], ground_truths: list[list[str]], threshold: float = 0.5) -> float:
    """Mean ANLS over a list of predictions."""
    if not predictions:
        return 0.0
    return sum(
        anls_score(p, g, threshold)
        for p, g in zip(predictions, ground_truths)
    ) / len(predictions)


# ---------------------------------------------------------------------------
# Field-level F1 (METHODOLOGY.md §1.5)
# ---------------------------------------------------------------------------

def _token_f1(pred: str, ref: str) -> float:
    """Token-level F1 for a single field value."""
    p_tokens = set(pred.split())
    r_tokens = set(ref.split())
    if not p_tokens and not r_tokens:
        return 1.0
    if not p_tokens or not r_tokens:
        return 0.0
    tp = len(p_tokens & r_tokens)
    precision = tp / len(p_tokens)
    recall = tp / len(r_tokens)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def field_f1(
    predicted_fields: dict[str, str],
    reference_fields: dict[str, str],
    *,
    numeric_fields: set[str] | None = None,
) -> dict[str, float]:
    """
    Per-field F1. For numeric fields (CPF, dates, IDs), uses exact match
    after digit-only normalization. For text fields uses token-level F1.

    Returns a dict mapping field_name → f1_score, plus 'macro_f1'.
    """
    numeric_fields = numeric_fields or set()
    scores: dict[str, float] = {}
    for fname, ref_val in reference_fields.items():
        pred_val = predicted_fields.get(fname, "")
        if fname in numeric_fields:
            ref_n = re.sub(r"\D", "", normalize(ref_val))
            pred_n = re.sub(r"\D", "", normalize(pred_val))
            scores[fname] = 1.0 if ref_n == pred_n else 0.0
        else:
            scores[fname] = _token_f1(normalize(pred_val), normalize(ref_val))
    scores["macro_f1"] = sum(scores.values()) / len(scores) if scores else 0.0
    return scores


# ---------------------------------------------------------------------------
# KVRR — Key-Value Recovery Rate (METHODOLOGY.md §1.5)
# ---------------------------------------------------------------------------

def kvrr(
    predictions: list[dict[str, str]],
    references: list[dict[str, str]],
    *,
    numeric_fields: set[str] | None = None,
) -> float:
    """
    Fraction of documents where ALL mandatory fields are correctly extracted
    (METHODOLOGY.md §1.2 KVRR). Strict binary metric per document.
    """
    if not predictions:
        return 0.0
    correct = 0
    for pred, ref in zip(predictions, references):
        f1s = field_f1(pred, ref, numeric_fields=numeric_fields)
        # All non-macro fields must be 1.0 (exact/full-token match)
        all_correct = all(
            v == 1.0 for k, v in f1s.items() if k != "macro_f1"
        )
        if all_correct:
            correct += 1
    return correct / len(predictions)


# ---------------------------------------------------------------------------
# Bootstrap CI (METHODOLOGY.md §3.1)
# ---------------------------------------------------------------------------

def bootstrap_ci(
    values: list[float],
    B: int = 10_000,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[float, float]:
    """95% percentile bootstrap CI on the mean of `values` (numpy-vectorized)."""
    import numpy as np
    n = len(values)
    rng = np.random.default_rng(seed)
    arr = np.asarray(values, dtype=np.float64)
    idx = rng.integers(0, n, size=(B, n))
    means = arr[idx].mean(axis=1)
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return float(lo), float(hi)


# ---------------------------------------------------------------------------
# Aggregated result container
# ---------------------------------------------------------------------------

@dataclass
class DocumentResult:
    """Per-document OCR evaluation result."""
    doc_id: str
    engine: str
    quality_tier: str      # clean | degraded | synthetic
    doc_type: str          # free_text | form | table | mixed
    cer: float
    wer: float
    cer_no_diac: float
    latency_s: float
    field_f1: dict[str, float] = field(default_factory=dict)   # empty for non-form docs
    anls_score: float = 0.0
    # Optional reference/hypothesis storage for T5 (error analysis).
    # Underscore prefix matches the key names read by report._char_substitutions.
    _ref: str = ""
    _hyp: str = ""


@dataclass
class EngineAggregate:
    """Aggregated metrics across all documents for one engine."""
    engine: str
    n_docs: int
    mean_cer: float
    ci_cer: tuple[float, float]
    mean_wer: float
    ci_wer: tuple[float, float]
    mean_cer_no_diac: float
    macro_field_f1: float
    mean_anls: float
    mean_latency_s: float
    # Stratified: (quality_tier, doc_type) → mean_cer
    stratified_cer: dict[str, float] = field(default_factory=dict)

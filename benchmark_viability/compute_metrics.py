"""Step 3: Compute multiple CER variants to isolate format vs content divergence.

Three CER variants:
  1. CER_raw     — standard CER against concatenated GT (what benchmark already measures)
  2. CER_sorted  — CER after sorting both ref and hyp tokens alphabetically
                   (removes ordering/layout penalty, keeps content penalty)
  3. CER_content — CER using only answer-labeled GT items vs hypothesis,
                   after token-level normalization (isolates content accuracy)

If VLMs improve dramatically from CER_raw → CER_sorted while classicals don't,
the finding is: "CER penalizes structured reading, not content errors."
"""
import re
import unicodedata
from dataclasses import dataclass

from collect_results import DocResult


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def _sorted_tokens(text: str) -> str:
    return " ".join(sorted(_normalize(text).split()))


def _edit_distance(a: str, b: str) -> int:
    m, n = len(a), len(b)
    if m < n:
        a, b, m, n = b, a, n, m
    prev = list(range(n + 1))
    for i, ca in enumerate(a, 1):
        curr = [i] + [0] * n
        for j, cb in enumerate(b, 1):
            curr[j] = prev[j - 1] if ca == cb else 1 + min(prev[j], curr[j - 1], prev[j - 1])
        prev = curr
    return prev[n]


def cer(ref: str, hyp: str) -> float:
    if not ref:
        return 0.0 if not hyp else float("inf")
    return _edit_distance(ref, hyp) / len(ref)


def token_f1(ref: str, hyp: str) -> float:
    ref_tokens = set(_normalize(ref).split())
    hyp_tokens = set(_normalize(hyp).split())
    if not ref_tokens:
        return 1.0 if not hyp_tokens else 0.0
    tp = len(ref_tokens & hyp_tokens)
    if tp == 0:
        return 0.0
    prec = tp / len(hyp_tokens) if hyp_tokens else 0.0
    rec = tp / len(ref_tokens)
    return 2 * prec * rec / (prec + rec)


@dataclass
class MetricResult:
    doc_id: str
    engine: str
    cer_raw: float
    cer_sorted: float
    cer_normalized: float
    token_f1: float
    ref_len: int
    hyp_len: int


def compute_all(result: DocResult, answers_text: str = "") -> MetricResult:
    ref = result.ref_text
    hyp = result.hyp_text

    cer_raw = result.cer
    cer_sorted_val = cer(_sorted_tokens(ref), _sorted_tokens(hyp))
    cer_norm = cer(_normalize(ref), _normalize(hyp))
    tf1 = token_f1(ref, hyp)

    return MetricResult(
        doc_id=result.doc_id,
        engine=result.engine,
        cer_raw=cer_raw,
        cer_sorted=cer_sorted_val,
        cer_normalized=cer_norm,
        token_f1=tf1,
        ref_len=len(ref),
        hyp_len=len(hyp),
    )

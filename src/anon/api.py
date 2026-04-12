"""
Python API for AnonShield — callable from web workers and the web backend.

Provides:
  - anonymize_file(): run anonymization programmatically
  - get_supported_entities(): real entity list from Presidio + custom recognizers

Usage:
    from src.anon.api import anonymize_file

    result = anonymize_file(
        input_path="/tmp/report.pdf",
        output_dir="/tmp/out/",
        strategy="regex",
        lang="pt",
        entities=["CPF", "EMAIL_ADDRESS"],
        custom_patterns=[{"entity_type": "BANK_ACCOUNT", "pattern": r"\\d{5}-\\d", "score": 0.9}],
        secret_key="my-secret",
    )
    # result = {"entity_count": 12, "entity_counts": {"CPF": 5, "EMAIL_ADDRESS": 7}}
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def anonymize_file(
    input_path: str | Path,
    output_dir: str | Path,
    strategy: str = "filtered",
    lang: str = "en",
    entities: list[str] | None = None,
    preserve_entities: list[str] | None = None,
    allow_list: list[str] | None = None,
    custom_patterns: list[dict] | None = None,
    slug_length: int = 8,
    ocr_engine: str = "tesseract",
    transformer_model: str = "Davlan/xlm-roberta-base-ner-hrl",
    secret_key: str = "",
    use_db: bool = False,
) -> dict[str, Any]:
    """Anonymize a single file and write output to output_dir.

    Returns dict with entity_count and entity_counts breakdown.
    CLI (anon.py) remains the primary interface; this is for programmatic use only.
    """
    from src.anon.config import ENTITY_MAPPING, Global
    from src.anon.engine import AnonymizationOrchestrator, load_custom_recognizers
    from src.anon.entity_detector import EntityDetector
    from src.anon.hash_generator import HashGenerator
    from src.anon.cache_manager import CacheManager
    from src.anon.database import DatabaseContext
    from src.anon.processors import ProcessorRegistry
    from src.anon.model_registry import get_entity_mapping
    from src.anon.ocr.factory import get_ocr_engine

    if secret_key:
        os.environ["ANON_SECRET_KEY"] = secret_key

    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- supported entities ---
    supported_upper = {s.upper() for s in get_supported_entities(strategy, lang=lang)}

    # Entity selection / preservation
    if entities:
        valid = {e.upper() for e in entities if e.upper() in supported_upper}
        entities_to_preserve = list(Global.NON_PII_ENTITIES | (supported_upper - valid))
    else:
        requested_preserve = {e.upper() for e in (preserve_entities or []) if e.upper() in supported_upper}
        entities_to_preserve = list(Global.NON_PII_ENTITIES) + list(requested_preserve)

    allow_list = [t.strip() for t in (allow_list or []) if t.strip()]

    # --- DB context ---
    db_context = None
    if use_db:
        db_context = DatabaseContext(mode="in-memory", db_dir=None)
        db_context.initialize()

    # --- Entity detector ---
    entity_mapping = get_entity_mapping(transformer_model) if transformer_model else dict(ENTITY_MAPPING)
    custom_recognizers = load_custom_recognizers([lang], regex_priority=False)
    compiled_patterns: list[dict] = []
    for recognizer in custom_recognizers:
        etype = recognizer.supported_entities[0]
        if etype in entities_to_preserve:
            continue
        for pattern in recognizer.patterns:
            try:
                compiled_patterns.append({
                    "label": etype,
                    "regex": re.compile(pattern.regex, flags=re.DOTALL | re.IGNORECASE),
                    "score": pattern.score,
                })
            except re.error:
                pass

    # Custom inline patterns
    for p in (custom_patterns or []):
        etype = p.get("entity_type", "CUSTOM")
        if etype in entities_to_preserve:
            continue
        try:
            flags_val = re.IGNORECASE
            if p.get("flags", "").upper() == "IGNORECASE":
                flags_val = re.IGNORECASE
            compiled_patterns.append({
                "label": etype,
                "regex": re.compile(p["pattern"], flags=flags_val),
                "score": float(p.get("score", 0.85)),
            })
        except (re.error, KeyError):
            logger.warning("Skipping invalid custom pattern: %s", p)

    entity_detector = EntityDetector(
        compiled_patterns=compiled_patterns,
        entities_to_preserve=set(entities_to_preserve),
        allow_list=set(allow_list),
        entity_mapping=entity_mapping,
    )

    cache_manager = CacheManager(use_cache=False, max_cache_size=0)
    hash_generator = HashGenerator()
    ocr_eng = get_ocr_engine(ocr_engine)

    orchestrator = AnonymizationOrchestrator(
        lang=lang,
        db_context=db_context,
        allow_list=allow_list,
        entities_to_preserve=entities_to_preserve,
        slug_length=slug_length,
        strategy_name=strategy,
        cache_manager=cache_manager,
        hash_generator=hash_generator,
        entity_detector=entity_detector,
        transformer_model=transformer_model,
    )

    processor = ProcessorRegistry.get_processor(
        str(input_path),
        orchestrator,
        output_dir=str(output_dir),
        ocr_engine=ocr_eng,
        overwrite=True,
    )
    if processor is None:
        raise ValueError(f"No processor available for file type: {input_path.suffix}")

    processor.process()

    return {
        "entity_count": orchestrator.total_entities_processed,
        "entity_counts": dict(orchestrator.entity_counts),
    }


# ── Entity discovery ───────────────────────────────────────────────────────────

_ENTITY_CACHE: dict[str, list[str]] = {}


def get_supported_entities(strategy: str = "filtered", lang: str = "en") -> list[str]:
    """Return the real entity types supported by the engine for the given strategy/lang.

    Results are cached per (strategy, lang) key so the first call (slow) is
    the only one that loads the NLP engine.
    """
    cache_key = f"{strategy}:{lang}"
    if cache_key in _ENTITY_CACHE:
        return _ENTITY_CACHE[cache_key]

    from src.anon.engine import load_custom_recognizers

    # Custom regex recognizers are always available
    custom = [r.supported_entities[0] for r in load_custom_recognizers([lang])]

    if strategy == "regex":
        # Regex-only: only custom recognizers, no Presidio NLP
        result = sorted(set(custom))
    else:
        # NER strategies: Presidio built-ins + custom recognizers
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_analyzer.nlp_engine import NlpEngineProvider

            provider = NlpEngineProvider(
                nlp_configuration={
                    "nlp_engine_name": "spacy",
                    "models": [{"lang_code": lang, "model_name": _spacy_model(lang)}],
                }
            )
            nlp_engine = provider.create_engine()
            ae = AnalyzerEngine(nlp_engine=nlp_engine)
            for r in load_custom_recognizers([lang]):
                ae.registry.add_recognizer(r)
            presidio_entities = ae.get_supported_entities(language=lang)
            result = sorted(set(list(presidio_entities) + custom))
        except Exception as exc:
            logger.warning("Could not load Presidio for entity list (%s) — using custom only", exc)
            result = sorted(set(custom))

    _ENTITY_CACHE[cache_key] = result
    return result


def _spacy_model(lang: str) -> str:
    _MODELS = {
        "en": "en_core_web_lg",
        "pt": "pt_core_news_lg",
        "es": "es_core_news_lg",
        "fr": "fr_core_news_lg",
        "de": "de_core_news_lg",
        "it": "it_core_news_lg",
        "nl": "nl_core_news_lg",
    }
    return _MODELS.get(lang, "en_core_web_lg")


def preview_structured_file(path: str | Path, max_rows: int = 5) -> dict:
    """Analyze a structured file (CSV, XLSX, JSON, JSONL) and return fields + samples.

    Returns:
        {
            "type": "csv" | "xlsx" | "json" | "jsonl",
            "fields": [{"name": "email", "sample_values": ["a@b.com", ...]}],
            "row_count": 1000,
        }
    """
    import json
    import csv

    path = Path(path)
    ext = path.suffix.lower().lstrip(".")

    def _truncate(v: object) -> str:
        s = str(v) if v is not None else ""
        return s[:80] + "…" if len(s) > 80 else s

    if ext == "csv":
        rows: list[dict] = []
        with path.open(encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                rows.append(row)
        if not rows:
            return {"type": "csv", "fields": [], "row_count": 0}
        fields = [
            {"name": k, "sample_values": [_truncate(r.get(k)) for r in rows]}
            for k in rows[0]
        ]
        return {"type": "csv", "fields": fields, "row_count": None}

    if ext in ("xls", "xlsx"):
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        rows_raw = list(ws.iter_rows(values_only=True))
        if len(rows_raw) < 2:
            return {"type": "xlsx", "fields": [], "row_count": 0}
        headers = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(rows_raw[0])]
        data_rows = rows_raw[1: 1 + max_rows]
        fields = [
            {"name": h, "sample_values": [_truncate(r[i]) for r in data_rows if i < len(r)]}
            for i, h in enumerate(headers)
        ]
        return {"type": "xlsx", "fields": fields, "row_count": len(rows_raw) - 1}

    if ext in ("json", "jsonl"):
        with path.open(encoding="utf-8", errors="replace") as f:
            first_char = f.read(1)
            f.seek(0)
            if ext == "jsonl" or first_char == "{":
                # JSONL or single object per line
                records = []
                for i, line in enumerate(f):
                    if i >= max_rows:
                        break
                    line = line.strip()
                    if line:
                        try:
                            records.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
            else:
                data = json.load(f)
                if isinstance(data, list):
                    records = data[:max_rows]
                else:
                    return {"type": "json", "fields": [], "row_count": 1}

        if not records or not isinstance(records[0], dict):
            return {"type": ext, "fields": [], "row_count": len(records)}

        all_keys: list[str] = []
        for r in records:
            for k in r:
                if k not in all_keys:
                    all_keys.append(k)

        fields = [
            {"name": k, "sample_values": [_truncate(r.get(k)) for r in records]}
            for k in all_keys
        ]
        return {"type": ext, "fields": fields, "row_count": None}

    return {"type": ext, "fields": [], "row_count": None}

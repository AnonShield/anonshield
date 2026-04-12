"""
Python API for AnonShield — callable from web workers without going through anon.py CLI.

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
    from src.anon.db import DatabaseContext
    from src.anon.processors import ProcessorRegistry
    from src.anon.model_registry import get_entity_mapping
    from src.anon.ocr.factory import get_ocr_engine

    if secret_key:
        os.environ["ANON_SECRET_KEY"] = secret_key

    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- supported entities ---
    from src.anon.engine import get_supported_entities
    supported_upper = {s.upper() for s in get_supported_entities(strategy, transformer_model)}

    # Entity selection / preservation
    if entities:
        valid = {e.upper() for e in entities if e.upper() in supported_upper}
        entities_to_preserve = list(Global.NON_PII_ENTITIES | (supported_upper - valid))
    else:
        requested_preserve = {e.upper() for e in (preserve_entities or []) if e.upper() in supported_upper}
        entities_to_preserve = list(Global.NON_PII_ENTITIES) + list(requested_preserve)

    allow_list = [t.strip() for t in (allow_list or []) if t.strip()]

    # --- DB context ---
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

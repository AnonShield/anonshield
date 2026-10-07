"""
Global run configuration loader.

Allows persisting all CLI settings in a YAML (or JSON) file.
CLI arguments always win over config file values.

Usage:
    config = load_run_config("anon_config.yaml")
    args = merge_with_args(config, args)
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

@dataclass
class RunConfig:
    """Mirrors the most important CLI options as typed fields."""
    lang: str = "en"
    strategy: str = "filtered"
    transformer_model: str = ""
    slug_length: int | None = None
    ocr_engine: str = "tesseract"
    entities: list[str] = field(default_factory=list)
    preserve_entities: list[str] = field(default_factory=list)
    allow_list: list[str] = field(default_factory=list)
    custom_patterns: list[dict] | str = field(default_factory=list)
    word_list: str | None = None
    anonymization_config: dict | str | None = None
    db_mode: str | None = None
    log_level: str | None = None
    regex_priority: bool | None = None
    min_word_length: int | None = None
    skip_numeric: bool | None = None
    use_cache: bool | None = None
    max_cache_size: int | None = None
    batch_size: str | None = None
    overwrite: bool | None = None
    output_dir: str | None = None
    custom_models: list[dict] = field(default_factory=list)
    ner_score_threshold: float | None = None
    ner_aggregation_strategy: str | None = None


def load_run_config(path: str) -> RunConfig:
    """Load a YAML or JSON run config file and return a RunConfig instance."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    raw: dict[str, Any]
    if p.suffix in (".yaml", ".yml"):
        import yaml  # PyYAML is a core dependency
        with p.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    elif p.suffix == ".json":
        with p.open(encoding="utf-8") as f:
            raw = json.load(f)
    else:
        raise ValueError(f"Unsupported config format: {p.suffix}. Use .yaml or .json")

    if not isinstance(raw, dict):
        raise ValueError("Run config must be a YAML or JSON object.")

    cfg = RunConfig()
    field_names = {f.name for f in fields(RunConfig)}
    for key, val in raw.items():
        if key in field_names:
            if key in {"word_list", "anonymization_config", "custom_patterns"} and isinstance(val, str):
                val = str((p.parent / val).resolve())
            setattr(cfg, key, val)
        else:
            logger.warning("Unknown config key '%s'; ignored", key)
    logger.info("Loaded run config from '%s'", path)
    return cfg


def merge_with_args(config: RunConfig, args, explicit_args: set[str] | None = None) -> None:
    """Apply profile settings except destinations explicitly supplied on the CLI."""
    explicit_args = explicit_args or set()
    list_fields = {"entities", "preserve_entities", "allow_list"}

    mappings = {
        "strategy": "anonymization_strategy",
        "entities": "entities",
        "preserve_entities": "preserve_entities",
        "allow_list": "allow_list",
        "slug_length": "slug_length",
        "lang": "lang",
        "output_dir": "output_dir",
        "ocr_engine": "ocr_engine",
        "word_list": "word_list",
        "custom_patterns": "custom_patterns",
        "anonymization_config": "anonymization_config",
        "transformer_model": "transformer_model",
        "db_mode": "db_mode",
        "log_level": "log_level",
        "regex_priority": "regex_priority",
        "min_word_length": "min_word_length",
        "skip_numeric": "skip_numeric",
        "use_cache": "use_cache",
        "max_cache_size": "max_cache_size",
        "batch_size": "batch_size",
        "overwrite": "overwrite",
        "ner_score_threshold": "ner_score_threshold",
        "ner_aggregation_strategy": "ner_aggregation_strategy",
    }

    for cfg_key, arg_key in mappings.items():
        if arg_key in explicit_args:
            continue
        cfg_val = getattr(config, cfg_key, None)
        if cfg_val is None:
            continue
        current = getattr(args, arg_key, _SENTINEL)
        if current is _SENTINEL:
            continue
        if cfg_key in list_fields and isinstance(cfg_val, list):
            cfg_val = ",".join(str(v) for v in cfg_val)
        if cfg_key == "transformer_model" and not cfg_val:
            continue
        if cfg_key == "custom_patterns":
            continue
        setattr(args, arg_key, cfg_val)

    # custom_patterns is handled separately, returned as list of dicts
    # anon.py will call _load_custom_patterns_from_config() after merge


_SENTINEL = object()

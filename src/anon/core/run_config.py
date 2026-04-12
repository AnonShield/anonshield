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

# Mapping from config file key → argparse dest attribute
# Only the keys that differ from argparse dest names need an entry.
_KEY_TO_ARG = {
    "strategy": "anonymization_strategy",
    "preserve_entities": "preserve_entities",
    "allow_list": "allow_list",
    "slug_length": "slug_length",
    "lang": "lang",
    "output_dir": "output_dir",
    "ocr_engine": "ocr_engine",
    "ocr_preprocess": "ocr_preprocess",
    "ocr_preprocess_preset": "ocr_preprocess_preset",
    "entities": "entities",
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
}


@dataclass
class RunConfig:
    """Mirrors the most important CLI options as typed fields."""
    lang: str = "en"
    strategy: str = "filtered"
    transformer_model: str = ""
    slug_length: int | None = None
    ocr_engine: str = "tesseract"
    ocr_preprocess: list[str] = field(default_factory=list)
    ocr_preprocess_preset: str = "none"
    entities: list[str] = field(default_factory=list)
    preserve_entities: list[str] = field(default_factory=list)
    allow_list: list[str] = field(default_factory=list)
    custom_patterns: list[dict] = field(default_factory=list)
    word_list: str | None = None
    anonymization_config: str | None = None
    db_mode: str | None = None
    log_level: str | None = None
    regex_priority: bool | None = None
    min_word_length: int | None = None
    skip_numeric: bool | None = None
    use_cache: bool | None = None
    max_cache_size: int | None = None
    batch_size: str | None = None
    overwrite: bool | None = None
    custom_models: list[dict] = field(default_factory=list)


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

    cfg = RunConfig()
    field_names = {f.name for f in fields(RunConfig)}
    for key, val in raw.items():
        if key in field_names:
            setattr(cfg, key, val)
        else:
            logger.warning("Unknown config key '%s' — ignored", key)
    logger.info("Loaded run config from '%s'", path)
    return cfg


def merge_with_args(config: RunConfig, args) -> None:
    """Apply config file values to args namespace — CLI wins (only fills unset/default values).

    For list fields (entities, preserve_entities, allow_list), the config value
    is used only when the CLI argument is empty/default.
    For boolean/None fields, the config value fills in when the arg is None or default.
    """
    # Fields where CLI default is "" (empty string) — treated as "not set"
    _EMPTY_STR_FIELDS = {"entities", "preserve_entities", "allow_list"}
    # Fields where CLI default is None
    _NONE_FIELDS = {
        "anonymization_config", "word_list", "db_mode", "log_level",
        "regex_priority", "min_word_length", "skip_numeric", "use_cache",
        "max_cache_size", "batch_size", "overwrite",
    }

    mappings = {
        "strategy": "anonymization_strategy",
        "entities": "entities",
        "preserve_entities": "preserve_entities",
        "allow_list": "allow_list",
        "slug_length": "slug_length",
        "lang": "lang",
        "output_dir": "output_dir",
        "ocr_engine": "ocr_engine",
        "ocr_preprocess": "ocr_preprocess",
        "ocr_preprocess_preset": "ocr_preprocess_preset",
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
    }

    for cfg_key, arg_key in mappings.items():
        cfg_val = getattr(config, cfg_key, None)
        if cfg_val is None:
            continue
        current = getattr(args, arg_key, _SENTINEL)
        if current is _SENTINEL:
            continue

        if cfg_key in _EMPTY_STR_FIELDS:
            # list fields: use config value if CLI is empty string
            if isinstance(current, str) and not current.strip():
                # Convert list to comma-separated string (CLI format)
                if isinstance(cfg_val, list):
                    setattr(args, arg_key, ",".join(str(v) for v in cfg_val))
                else:
                    setattr(args, arg_key, cfg_val)
        elif cfg_key in _NONE_FIELDS:
            if current is None:
                setattr(args, arg_key, cfg_val)
        else:
            # For simple scalar fields, only override if current equals the parser default
            # We do a soft override: config fills if current is empty/falsy default
            if not current and cfg_val:
                setattr(args, arg_key, cfg_val)
            elif current and cfg_key == "strategy":
                pass  # CLI wins
            elif not current:
                setattr(args, arg_key, cfg_val)

    # custom_patterns is handled separately — returned as list of dicts
    # anon.py will call _load_custom_patterns_from_config() after merge


_SENTINEL = object()

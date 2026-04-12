"""YAML profile validation."""
import re
from typing import Any

import yaml


VALID_STRATEGIES = {"filtered", "standalone", "regex", "hybrid", "presidio"}
VALID_KEYS = {
    "strategy", "lang", "slug_length", "ocr_engine", "entities",
    "preserve_entities", "allow_list", "custom_patterns", "word_list",
    "anonymization_config", "transformer_model", "custom_models",
}


def validate_profile(content: str) -> dict[str, Any]:
    """Parse and validate a YAML profile string.

    Returns {"valid": True, ...} or {"valid": False, "error": "..."}.
    """
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        return {"valid": False, "error": f"YAML parse error: {exc}"}

    if not isinstance(data, dict):
        return {"valid": False, "error": "Profile must be a YAML mapping"}

    unknown = set(data.keys()) - VALID_KEYS
    if unknown:
        return {"valid": False, "error": f"Unknown keys: {sorted(unknown)}"}

    if "strategy" in data and data["strategy"] not in VALID_STRATEGIES:
        return {
            "valid": False,
            "error": f"Invalid strategy '{data['strategy']}'. Valid: {sorted(VALID_STRATEGIES)}",
        }

    patterns = data.get("custom_patterns", [])
    if not isinstance(patterns, list):
        return {"valid": False, "error": "'custom_patterns' must be a list"}

    for i, p in enumerate(patterns):
        if not isinstance(p, dict):
            return {"valid": False, "error": f"Pattern #{i} must be a mapping"}
        for required in ("entity_type", "pattern"):
            if required not in p:
                return {"valid": False, "error": f"Pattern #{i} missing '{required}'"}
        try:
            re.compile(p["pattern"])
        except re.error as exc:
            return {
                "valid": False,
                "error": f"Pattern #{i} ({p['entity_type']}): invalid regex — {exc}",
            }

    return {
        "valid": True,
        "entities_count": len(data.get("entities", [])),
        "patterns_count": len(patterns),
    }

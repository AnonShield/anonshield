"""YAML profile validation."""
import re
from typing import Any

import yaml


VALID_STRATEGIES = {"filtered", "standalone", "regex", "hybrid", "presidio"}
VALID_KEYS = {
    "strategy", "lang", "slug_length", "ocr_engine", "entities",
    "preserve_entities", "allow_list", "custom_patterns", "word_list",
    "anonymization_config", "transformer_model", "custom_models",
    "ner_score_threshold", "ner_aggregation_strategy",
}


def validate_profile(content: str) -> dict[str, Any]:
    """Parse and validate a YAML profile string.

    Returns {"valid": True, ...} or {"valid": False, "error": "..."}.
    """
    if not isinstance(content, str):
        return {"valid": False, "error": "Profile content must be YAML text"}
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        return {"valid": False, "error": f"YAML parse error: {exc}"}

    if not isinstance(data, dict):
        return {"valid": False, "error": "Profile must be a YAML mapping"}

    unknown = set(data.keys()) - VALID_KEYS
    if unknown:
        return {"valid": False, "error": f"Unknown keys: {sorted(map(str, unknown))}"}

    if "strategy" in data and (not isinstance(data["strategy"], str) or data["strategy"] not in VALID_STRATEGIES):
        return {
            "valid": False,
            "error": f"Invalid strategy '{data['strategy']}'. Valid: {sorted(VALID_STRATEGIES)}",
        }

    for name in ("lang", "transformer_model", "ocr_engine", "ner_aggregation_strategy"):
        if name in data and not isinstance(data[name], str):
            return {"valid": False, "error": f"'{name}' must be text"}
    for name in ("entities", "preserve_entities", "allow_list"):
        value = data.get(name, [])
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            return {"valid": False, "error": f"'{name}' must be a list of text values"}
    if "slug_length" in data and (type(data["slug_length"]) is not int or not 0 <= data["slug_length"] <= 64):
        return {"valid": False, "error": "'slug_length' must be an integer between 0 and 64"}
    if "ner_score_threshold" in data and (type(data["ner_score_threshold"]) not in (int, float) or not 0 <= data["ner_score_threshold"] <= 1):
        return {"valid": False, "error": "'ner_score_threshold' must be a number between 0 and 1"}

    patterns = data.get("custom_patterns", [])
    if not isinstance(patterns, list):
        return {"valid": False, "error": "'custom_patterns' must be a list"}

    for i, p in enumerate(patterns):
        if not isinstance(p, dict):
            return {"valid": False, "error": f"Pattern #{i} must be a mapping"}
        for required in ("entity_type", "pattern"):
            if not isinstance(p.get(required), str) or not p[required]:
                return {"valid": False, "error": f"Pattern #{i} requires text in '{required}'"}
        if type(p.get("score", 0.85)) not in (int, float) or not 0 <= p.get("score", 0.85) <= 1:
            return {"valid": False, "error": f"Pattern #{i} score must be between 0 and 1"}
        if "flags" in p and not isinstance(p["flags"], str):
            return {"valid": False, "error": f"Pattern #{i} flags must be text"}
        try:
            re.compile(p["pattern"])
        except re.error as exc:
            return {
                "valid": False,
                "error": f"Pattern #{i} ({p['entity_type']}): invalid regex ({exc})",
            }

    return {
        "valid": True,
        "entities_count": len(data.get("entities", [])),
        "patterns_count": len(patterns),
    }

"""GET /api/entities — dynamic entity list sourced from the real Presidio engine."""
import json
import logging
import sys
from pathlib import Path
from fastapi import APIRouter, Query

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/entities", tags=["entities"])

_REPO_ROOT = Path(__file__).resolve().parents[1]
if not (_REPO_ROOT / "anon.py").exists():
    _REPO_ROOT = Path(__file__).resolve().parents[3]

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Entities that Presidio detects but are not personally sensitive (never anonymize)
_NON_PII = {"MISC", "LANGUAGE"}

# NER-only entities (not available in regex-only strategy)
_NER_ONLY = {
    "PERSON", "ORGANIZATION", "LOCATION", "NRP", "DATE_TIME", "AGE", "ID",
    "MEDICAL_LICENSE", "US_SSN", "US_PASSPORT", "US_BANK_NUMBER",
    "US_DRIVER_LICENSE", "US_ITIN", "AU_ABN", "AU_ACN", "AU_MEDICARE",
    "AU_TFN", "IN_AADHAAR", "IN_PAN", "IN_PASSPORT", "IN_VEHICLE_REGISTRATION",
    "IN_VOTER", "SG_NRIC_FIN", "UK_NHS", "UK_NINO",
}

# Human-readable labels for known entity IDs
_LABELS: dict[str, tuple[str, str]] = {
    # (label, example)
    "PERSON":              ("Person",              "John Smith"),
    "ORGANIZATION":        ("Organization",        "Acme Corp"),
    "LOCATION":            ("Location",            "New York, USA"),
    "DATE_TIME":           ("Date / Time",         "January 1, 2024"),
    "NRP":                 ("Nationality/Religion","Brazilian"),
    "AGE":                 ("Age",                 "42 years old"),
    "ID":                  ("Generic ID",          "ID-98765"),
    "EMAIL_ADDRESS":       ("E-mail",              "user@example.com"),
    "EMAIL":               ("E-mail",              "user@example.com"),
    "PHONE_NUMBER":        ("Phone number",        "+55 11 91234-5678"),
    "CREDIT_CARD":         ("Credit card",         "4111 1111 1111 1111"),
    "CRYPTO":              ("Crypto address",      "1A2B3C4D5E6F..."),
    "IBAN_CODE":           ("IBAN",                "DE89370400440532013000"),
    "US_BANK_NUMBER":      ("US Bank account",     "12345678"),
    "US_SSN":              ("US SSN",              "123-45-6789"),
    "US_PASSPORT":         ("US Passport",         "A12345678"),
    "US_DRIVER_LICENSE":   ("US Driver License",   "D1234567"),
    "US_ITIN":             ("US ITIN",             "912-34-5678"),
    "MEDICAL_LICENSE":     ("Medical license",     "CRM-SP 123456"),
    "AU_ABN":              ("AU ABN",              "51 824 753 556"),
    "AU_ACN":              ("AU ACN",              "000 000 019"),
    "AU_MEDICARE":         ("AU Medicare",         "2123456701"),
    "AU_TFN":              ("AU TFN",              "123 456 782"),
    "IN_AADHAAR":          ("IN Aadhaar",          "1234 5678 9012"),
    "IN_PAN":              ("IN PAN",              "ABCDE1234F"),
    "IN_PASSPORT":         ("IN Passport",         "A1234567"),
    "IN_VEHICLE_REGISTRATION": ("IN Vehicle Reg",  "MH 01 AB 1234"),
    "IN_VOTER":            ("IN Voter ID",         "ABC1234567"),
    "SG_NRIC_FIN":         ("SG NRIC/FIN",         "S1234567D"),
    "UK_NHS":              ("UK NHS",              "485 777 3456"),
    "UK_NINO":             ("UK NINO",             "AB 12 34 56 C"),
    # Custom recognizers (always available, independent of NER model)
    "IP_ADDRESS":          ("IP Address",          "192.168.1.1"),
    "URL":                 ("URL",                 "https://example.com"),
    "HOSTNAME":            ("Hostname / FQDN",     "server.internal.corp"),
    "MAC_ADDRESS":         ("MAC Address",         "AA:BB:CC:DD:EE:FF"),
    "FILE_PATH":           ("File path",           "/home/user/.ssh/id_rsa"),
    "HASH":                ("Hash (MD5/SHA)",      "5d41402abc4b2a76b9719d911017c592"),
    "AUTH_TOKEN":          ("Auth token / Cookie", "session=abc123..."),
    "CVE_ID":              ("CVE ID",              "CVE-2024-12345"),
    "CPE_STRING":          ("CPE string",          "cpe:2.3:a:vendor:product"),
    "CERT_SERIAL":         ("Cert serial",         "1a:2b:3c:4d"),
    "CERTIFICATE":         ("Certificate (PEM)",   "-----BEGIN CERTIFICATE-----"),
    "CRYPTOGRAPHIC_KEY":   ("Cryptographic key",   "-----BEGIN RSA PRIVATE KEY-----"),
    "PGP_BLOCK":           ("PGP block",           "-----BEGIN PGP MESSAGE-----"),
    "PASSWORD":            ("Password (context)",  "password=s3cr3t"),
    "USERNAME":            ("Username (context)",  "username=admin"),
    "UUID":                ("UUID",                "550e8400-e29b-41d4-a716-446655440000"),
    "PORT":                ("Port / Protocol",     "tcp/8443"),
    "OID":                 ("OID",                 "1.2.840.113549.1.1.11"),
    # ── Biomedical — d4data/biomedical-ner-all (MACCROBAT) ──────────────────
    # These are custom Presidio entity types produced by the biomedical model.
    # i2b2 model labels (PATIENT, STAFF, HOSP, LOC, PATORG, OTHERPHI) all
    # map to existing types above (PERSON, LOCATION, ORGANIZATION, ID).
    "DISEASE":             ("Disease / Disorder",  "Hypertension, COVID-19"),
    "DRUG":                ("Drug / Medication",   "Aspirin, Metformin"),
    # ── SecureModernBERT-NER specific entities ───────────────────────────────
    "REGISTRY_KEY":        ("Registry key",        r"HKLM\Software\Microsoft"),
    "THREAT_ACTOR":        ("Threat actor",        "APT28 / Lazarus Group"),
    "MALWARE":             ("Malware",             "WannaCry, NotPetya"),
    "PLATFORM":            ("Platform",            "Windows, Linux, Android"),
    "PRODUCT":             ("Product",             "Apache, OpenSSL, Chrome"),
    "SECTOR":              ("Sector",              "Healthcare, Finance, Energy"),
    "TOOL":                ("Tool",                "Mimikatz, Cobalt Strike"),
    "CAMPAIGN":            ("Campaign",            "Operation Aurora"),
    "MITRE_TACTIC":        ("MITRE tactic",        "TA0001 Initial Access"),
    "SERVICE":             ("Service",             "SSH, RDP, SMB"),
}

# Grouping map: entity_id → group label
_GROUPS_MAP: dict[str, str] = {
    "PERSON": "Identity", "NRP": "Identity", "AGE": "Identity",
    "ORGANIZATION": "Organization", "LOCATION": "Organization",
    "EMAIL_ADDRESS": "Identity", "EMAIL": "Identity",
    "PHONE_NUMBER": "Identity", "DATE_TIME": "Identity", "ID": "Identity",
    "CREDIT_CARD": "Financial", "IBAN_CODE": "Financial", "CRYPTO": "Financial",
    "US_BANK_NUMBER": "Financial", "US_SSN": "Documents",
    "US_PASSPORT": "Documents", "US_DRIVER_LICENSE": "Documents",
    "US_ITIN": "Documents", "MEDICAL_LICENSE": "Healthcare",
    "DISEASE": "Healthcare", "DRUG": "Healthcare",
    "AU_ABN": "Australia", "AU_ACN": "Australia",
    "AU_MEDICARE": "Australia", "AU_TFN": "Australia",
    "IN_AADHAAR": "India", "IN_PAN": "India", "IN_PASSPORT": "India",
    "IN_VEHICLE_REGISTRATION": "India", "IN_VOTER": "India",
    "SG_NRIC_FIN": "Singapore",
    "UK_NHS": "United Kingdom", "UK_NINO": "United Kingdom",
    "IP_ADDRESS": "Network", "URL": "Network", "HOSTNAME": "Network",
    "MAC_ADDRESS": "Network", "PORT": "Network",
    "FILE_PATH": "System", "HASH": "System", "AUTH_TOKEN": "System",
    "PASSWORD": "System", "USERNAME": "System",
    "CVE_ID": "Security", "CPE_STRING": "Security", "CERT_SERIAL": "Security",
    "CERTIFICATE": "Security", "CRYPTOGRAPHIC_KEY": "Security",
    "PGP_BLOCK": "Security", "OID": "Security",
    # SecureModernBERT cybersecurity entities
    "REGISTRY_KEY": "Cybersecurity", "THREAT_ACTOR": "Cybersecurity",
    "MALWARE": "Cybersecurity", "TOOL": "Cybersecurity",
    "CAMPAIGN": "Cybersecurity", "MITRE_TACTIC": "Cybersecurity",
    "PLATFORM": "Cybersecurity", "PRODUCT": "Cybersecurity",
    "SECTOR": "Cybersecurity", "SERVICE": "Cybersecurity",
    "UUID": "Identifiers",
}

_GROUP_ORDER = [
    "Identity", "Organization", "Financial", "Documents", "Healthcare",
    "Network", "Security", "Cybersecurity", "System", "Identifiers",
    "Australia", "India", "Singapore", "United Kingdom",
    "Other",
]


def _build_response(entity_ids: list[str], strategy: str) -> dict:
    is_regex = strategy == "regex"
    grouped: dict[str, list[dict]] = {}

    for eid in entity_ids:
        if eid in _NON_PII:
            continue
        if is_regex and eid in _NER_ONLY:
            continue
        label, example = _LABELS.get(eid, (eid.replace("_", " ").title(), ""))
        group = _GROUPS_MAP.get(eid, "Other")
        if group not in grouped:
            grouped[group] = []
        grouped[group].append({"id": eid, "label": label, "example": example})

    groups = []
    for g in _GROUP_ORDER:
        if g in grouped:
            groups.append({"label": g, "entities": grouped[g]})
    # Any remaining groups not in order
    for g, entities in grouped.items():
        if g not in _GROUP_ORDER:
            groups.append({"label": g, "entities": entities})

    return {"groups": groups, "strategy": strategy}


_ENTITIES_TTL = 86400  # 24h — entity list changes only on deploy
_ENTITIES_VERSION = "v2"  # bump this to invalidate all cached entity lists on deploy


def _redis_cache_key(strategy: str, model: str, lang: str) -> str:
    return f"entities:{_ENTITIES_VERSION}:{strategy}:{model}:{lang}"


def _get_from_redis(key: str) -> list[str] | None:
    try:
        from services.job_service import _client
        raw = _client().get(key)
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return None


def _set_in_redis(key: str, entity_ids: list[str]) -> None:
    try:
        from services.job_service import _client
        _client().setex(key, _ENTITIES_TTL, json.dumps(entity_ids))
    except Exception:
        pass  # Redis unavailable — in-memory cache in api.py still works


@router.get("")
def list_entities(
    strategy: str = Query("filtered"),
    model: str = Query("Davlan/xlm-roberta-base-ner-hrl"),
    lang: str = Query("en"),
) -> dict:
    """Return entities supported by the engine for the given strategy + model + lang.

    Results are cached in Redis (24h TTL) keyed by strategy:model:lang.
    On cache miss the engine is loaded once and the result stored.
    """
    from fastapi.responses import JSONResponse

    cache_key = _redis_cache_key(strategy, model, lang)

    # ── Redis cache hit ───────────────────────────────────────────────────────
    entity_ids = _get_from_redis(cache_key)

    # ── Cache miss: compute and store ────────────────────────────────────────
    if entity_ids is None:
        entity_ids = []
        try:
            from src.anon.api import get_supported_entities
            entity_ids = get_supported_entities(strategy=strategy, lang=lang, model=model)
        except Exception as exc:
            log.warning("Presidio entity discovery failed: %s", exc)
            # Fallback 1: custom recognizers + model registry (no Presidio needed)
            try:
                from src.anon.engine import load_custom_recognizers
                from src.anon.model_registry import get_entity_mapping
                custom = [r.supported_entities[0] for r in load_custom_recognizers([lang])]
                model_entities = list(get_entity_mapping(model).values()) if strategy != "regex" else []
                entity_ids = sorted(set(custom + model_entities))
            except Exception as exc2:
                log.warning("Custom recognizer fallback also failed: %s", exc2)

        # Fallback 2: static label dict (always safe)
        if not entity_ids:
            log.warning("Using static label dict as ultimate fallback")
            if strategy == "regex":
                entity_ids = [eid for eid in _LABELS if eid not in _NER_ONLY and eid not in _NON_PII]
            else:
                entity_ids = [eid for eid in _LABELS if eid not in _NON_PII]

        _set_in_redis(cache_key, entity_ids)

    data = _build_response(entity_ids, strategy)
    return JSONResponse(
        content=data,
        headers={"Cache-Control": "public, max-age=300, stale-while-revalidate=60"},
    )

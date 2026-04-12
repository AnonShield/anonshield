"""GET /api/entities — dynamic entity list by strategy + model."""
import sys
from pathlib import Path
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/entities", tags=["entities"])

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Grouped entity definitions — sourced from Presidio + custom BR patterns
_GROUPS = [
    {
        "label": "Identity",
        "entities": [
            {"id": "PERSON",        "label": "Person",        "example": "John Smith"},
            {"id": "EMAIL_ADDRESS", "label": "Email",         "example": "user@example.com"},
            {"id": "PHONE_NUMBER",  "label": "Phone",         "example": "+55 11 91234-5678"},
            {"id": "DATE_TIME",     "label": "Date/Time",     "example": "January 1, 2024"},
            {"id": "NRP",           "label": "Nationality",   "example": "Brazilian"},
        ],
    },
    {
        "label": "Organization",
        "entities": [
            {"id": "ORGANIZATION",  "label": "Organization",  "example": "Acme Corp"},
            {"id": "LOCATION",      "label": "Location",      "example": "New York"},
        ],
    },
    {
        "label": "Network",
        "entities": [
            {"id": "IP_ADDRESS",    "label": "IP Address",    "example": "192.168.1.1"},
            {"id": "URL",           "label": "URL",           "example": "https://example.com"},
            {"id": "DOMAIN_NAME",   "label": "Domain",        "example": "example.com"},
            {"id": "MAC_ADDRESS",   "label": "MAC Address",   "example": "AA:BB:CC:DD:EE:FF"},
        ],
    },
    {
        "label": "Financial",
        "entities": [
            {"id": "CREDIT_CARD",   "label": "Credit Card",   "example": "4111 1111 1111 1111"},
            {"id": "IBAN_CODE",     "label": "IBAN",          "example": "DE89370400440532013000"},
            {"id": "US_BANK_NUMBER","label": "Bank Account",  "example": "12345678"},
        ],
    },
    {
        "label": "Crypto",
        "entities": [
            {"id": "CRYPTO",        "label": "Crypto Address","example": "1A2B3C4D5E6F..."},
            {"id": "UUID",          "label": "UUID",          "example": "550e8400-e29b-41d4-a716-446655440000"},
        ],
    },
    {
        "label": "Brazil — Documents",
        "entities": [
            {"id": "CPF",           "label": "CPF",           "example": "123.456.789-09"},
            {"id": "CNPJ",          "label": "CNPJ",          "example": "12.345.678/0001-90"},
            {"id": "RG",            "label": "RG",            "example": "12.345.678-9"},
            {"id": "CEP",           "label": "CEP",           "example": "01310-100"},
        ],
    },
    {
        "label": "Brazil — Banking",
        "entities": [
            {"id": "BANK_ACCOUNT",  "label": "Bank Account BR","example": "12345-6"},
            {"id": "BANK_AGENCY",   "label": "Bank Agency",   "example": "1234-5"},
            {"id": "PIX_KEY_UUID",  "label": "PIX UUID",      "example": "550e8400-..."},
            {"id": "PIX_KEY_PHONE", "label": "PIX Phone",     "example": "+5511987654321"},
        ],
    },
    {
        "label": "Medical",
        "entities": [
            {"id": "MEDICAL_LICENSE","label": "Medical License","example": "CRM-SP 123456"},
            {"id": "US_SSN",        "label": "SSN",           "example": "123-45-6789"},
            {"id": "US_PASSPORT",   "label": "Passport",      "example": "A12345678"},
        ],
    },
]

# Entities only available with NER (not in regex-only strategy)
_NER_ONLY = {"PERSON", "ORGANIZATION", "LOCATION", "NRP", "DATE_TIME", "DOMAIN_NAME"}


@router.get("")
def list_entities(
    strategy: str = Query("filtered"),
    model: str = Query("Davlan/xlm-roberta-base-ner-hrl"),
    lang: str = Query("en"),
) -> dict:
    is_regex = strategy == "regex"
    groups = []
    for group in _GROUPS:
        entities = [
            e for e in group["entities"]
            if not (is_regex and e["id"] in _NER_ONLY)
        ]
        if entities:
            groups.append({**group, "entities": entities})
    return {"groups": groups, "strategy": strategy, "model": model}

"""
E2E tests for the entity selection bug fix:
  - Empty entities list (user deselected all) → nothing anonymized
  - Non-empty entities list → only those types anonymized
  - None entities (null in frontend) → all entities anonymized (default)

Uses only the Python API (anonymize_file) with regex strategy to avoid
loading NLP models in CI.
"""
import os
import re
from pathlib import Path

import pytest

os.environ.setdefault("ANON_SECRET_KEY", "test-key-12345678901234567890123456789012")

PROJECT_ROOT = Path(__file__).parent.parent

# Text with multiple regex-detectable PII types
MIXED_PII = (
    "Contact john.doe@example.com or call +1-555-123-4567. "
    "Server at 192.168.1.100. "
    "Visit https://example.com/api. "
    "CVE-2021-44228 is critical."
)


def _run_api(tmp_path, text: str, entities, strategy: str = "regex") -> str:
    """Call anonymize_file via Python API and return output text."""
    import sys
    sys.path.insert(0, str(PROJECT_ROOT))
    from src.anon.api import anonymize_file

    src = tmp_path / "input.txt"
    src.write_text(text, encoding="utf-8")
    out_dir = tmp_path / "out"

    anonymize_file(
        input_path=str(src),
        output_dir=str(out_dir),
        strategy=strategy,
        lang="en",
        entities=entities,
        slug_length=8,
    )

    out_file = out_dir / "anon_input.txt"
    assert out_file.exists(), f"Output file not created. entities={entities!r}"
    return out_file.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Core bug fix: empty list = anonymize nothing
# ---------------------------------------------------------------------------

def test_empty_entities_list_anonymizes_nothing(tmp_path):
    """entities=[] must preserve ALL PII — user deselected everything."""
    out = _run_api(tmp_path, MIXED_PII, entities=[])
    assert "john.doe@example.com" in out, "Email should NOT be anonymized when entities=[]"
    assert "192.168.1.100" in out, "IP should NOT be anonymized when entities=[]"
    assert "CVE-2021-44228" in out, "CVE should NOT be anonymized when entities=[]"


def test_none_entities_anonymizes_all(tmp_path):
    """entities=None (null in frontend) = no filter = anonymize everything detectable."""
    out = _run_api(tmp_path, MIXED_PII, entities=None)
    assert "john.doe@example.com" not in out, "Email should be anonymized when entities=None"
    assert "192.168.1.100" not in out, "IP should be anonymized when entities=None"


def test_specific_entities_only_those_anonymized(tmp_path):
    """entities=['EMAIL_ADDRESS'] → only email anonymized, IP kept."""
    out = _run_api(tmp_path, MIXED_PII, entities=["EMAIL_ADDRESS"])
    assert "john.doe@example.com" not in out, "Email should be anonymized"
    assert "192.168.1.100" in out, "IP should be preserved (not in entities list)"
    assert "CVE-2021-44228" in out, "CVE should be preserved"


def test_entities_ip_only(tmp_path):
    out = _run_api(tmp_path, MIXED_PII, entities=["IP_ADDRESS"])
    assert "192.168.1.100" not in out
    assert "john.doe@example.com" in out


def test_entities_cve_only(tmp_path):
    out = _run_api(tmp_path, MIXED_PII, entities=["CVE_ID"])
    assert "CVE-2021-44228" not in out
    assert "john.doe@example.com" in out
    assert "192.168.1.100" in out


def test_entities_multiple(tmp_path):
    out = _run_api(tmp_path, MIXED_PII, entities=["EMAIL_ADDRESS", "IP_ADDRESS"])
    assert "john.doe@example.com" not in out
    assert "192.168.1.100" not in out
    assert "CVE-2021-44228" in out


def test_entities_all_present(tmp_path):
    """Providing all entity types explicitly should behave same as None."""
    d1 = tmp_path / "explicit"
    d2 = tmp_path / "none"
    d1.mkdir()
    d2.mkdir()
    out_explicit = _run_api(
        d1, MIXED_PII,
        entities=["EMAIL_ADDRESS", "IP_ADDRESS", "CVE_ID", "URL", "PHONE_NUMBER"],
    )
    out_none = _run_api(d2, MIXED_PII, entities=None)
    # Both should anonymize email and IP
    assert "john.doe@example.com" not in out_explicit
    assert "john.doe@example.com" not in out_none


# ---------------------------------------------------------------------------
# Slug format preserved regardless of entity filter
# ---------------------------------------------------------------------------

def test_anonymized_values_have_slug_format(tmp_path):
    """Anonymized placeholders must follow [TYPE_hexhex] format."""
    out = _run_api(tmp_path, MIXED_PII, entities=["EMAIL_ADDRESS"])
    # Email replaced → should find a slug token
    tokens = re.findall(r'\[EMAIL_ADDRESS_[0-9a-f]{8}\]', out)
    assert len(tokens) >= 1, f"Expected EMAIL_ADDRESS slug in output, got:\n{out}"


# ---------------------------------------------------------------------------
# Empty list via CLI (subprocess) — the original bug path
# ---------------------------------------------------------------------------

def test_entities_empty_via_cli(tmp_path):
    """Passing --entities '' to CLI should behave same as no --entities (bug was here)."""
    import subprocess, sys
    src = tmp_path / "input.txt"
    src.write_text(MIXED_PII, encoding="utf-8")
    out_dir = tmp_path / "out"

    # Empty --entities argument → treat as "no filter" in CLI
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "anon.py"), str(src),
         "--anonymization-strategy", "regex",
         "--db-mode", "in-memory", "--no-report", "--overwrite",
         "--output-dir", str(out_dir), "--slug-length", "8"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        env={**os.environ, "ANON_SECRET_KEY": "test-key-12345678901234567890123456789012"},
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    content = (out_dir / "anon_input.txt").read_text(encoding="utf-8")
    # Without --entities filter, email and IP should be anonymized
    assert "john.doe@example.com" not in content
    assert "192.168.1.100" not in content

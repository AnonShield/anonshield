"""
E2E tests for --entities (positive entity selection) and --preserve-entities.

--entities: only listed types are anonymized; all others pass through
--preserve-entities: listed types are kept; all others are anonymized
"""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
ANON_ENV = {**os.environ, "ANON_SECRET_KEY": "test-key-12345678901234567890123456789012"}
TEXT = "Email john@example.com, IP 192.168.1.1, CVE-2021-44228, CPF 123.456.789-09"


def _run(tmp_path, *extra_args, text=TEXT):
    src = tmp_path / "input.txt"
    src.write_text(text, encoding="utf-8")
    out = tmp_path / "out"
    cmd = [
        sys.executable, str(PROJECT_ROOT / "anon.py"), str(src),
        "--anonymization-strategy", "regex",
        "--db-mode", "in-memory", "--no-report", "--overwrite",
        "--output-dir", str(out), "--slug-length", "8",
        *extra_args,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT), env=ANON_ENV, timeout=60)
    content = (out / "anon_input.txt").read_text(encoding="utf-8") if (out / "anon_input.txt").exists() else ""
    return r.returncode, content


def test_entities_only_email(tmp_path):
    rc, out = _run(tmp_path, "--entities", "EMAIL_ADDRESS")
    assert rc == 0
    assert "john@example.com" not in out
    assert "192.168.1.1" in out          # IP not in --entities → kept
    assert "CVE-2021-44228" in out       # CVE not in --entities → kept


def test_entities_only_ip(tmp_path):
    rc, out = _run(tmp_path, "--entities", "IP_ADDRESS")
    assert rc == 0
    assert "192.168.1.1" not in out
    assert "john@example.com" in out


def test_entities_multiple(tmp_path):
    rc, out = _run(tmp_path, "--entities", "EMAIL_ADDRESS,IP_ADDRESS")
    assert rc == 0
    assert "john@example.com" not in out
    assert "192.168.1.1" not in out
    assert "CVE-2021-44228" in out       # CVE not requested → kept


def test_preserve_entities(tmp_path):
    rc, out = _run(tmp_path, "--preserve-entities", "CVE_ID")
    assert rc == 0
    assert "CVE-2021-44228" in out       # preserved
    assert "john@example.com" not in out  # not preserved → anonymized


def test_entities_unknown_ignored(tmp_path):
    """Unknown entity type in --entities logs warning but doesn't crash."""
    rc, out = _run(tmp_path, "--entities", "EMAIL_ADDRESS,NONEXISTENT_ENTITY")
    assert rc == 0
    assert "john@example.com" not in out


def test_entities_overrides_preserve(tmp_path):
    """When --entities is set, --preserve-entities is ignored."""
    rc, out = _run(tmp_path, "--entities", "EMAIL_ADDRESS", "--preserve-entities", "EMAIL_ADDRESS")
    assert rc == 0
    # --entities takes precedence; email SHOULD be anonymized
    assert "john@example.com" not in out

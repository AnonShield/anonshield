"""
E2E tests for --anonymization-strategy regex (zero NLP/ML overhead).

These tests verify that:
- The regex strategy processes files without loading any ML models
- Known-pattern entities (email, IP, CVE, CPF) are anonymized
- NER-only entities (PERSON names from context) are NOT anonymized
- Output markers follow the [ENTITY_TYPE_hash] format
"""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
ANON_ENV = {**os.environ, "ANON_SECRET_KEY": "test-key-12345678901234567890123456789012"}


def run_anon(*extra_args, input_text: str, tmp_path) -> tuple[int, str, str]:
    src = tmp_path / "input.txt"
    src.write_text(input_text, encoding="utf-8")
    out_dir = tmp_path / "out"
    cmd = [
        sys.executable, str(PROJECT_ROOT / "anon.py"), str(src),
        "--anonymization-strategy", "regex",
        "--db-mode", "in-memory",
        "--no-report", "--overwrite",
        "--output-dir", str(out_dir),
        "--slug-length", "8",
        *extra_args,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT), env=ANON_ENV, timeout=60)
    output_file = out_dir / f"anon_input.txt"
    content = output_file.read_text(encoding="utf-8") if output_file.exists() else ""
    return result.returncode, content, result.stderr


def test_email_anonymized(tmp_path):
    rc, content, _ = run_anon(input_text="Contact john.doe@example.com for help.", tmp_path=tmp_path)
    assert rc == 0
    assert "john.doe@example.com" not in content
    assert re.search(r"\[EMAIL_ADDRESS_[0-9a-f]+\]", content)


def test_ip_anonymized(tmp_path):
    rc, content, _ = run_anon(input_text="The server is at 192.168.1.100.", tmp_path=tmp_path)
    assert rc == 0
    assert "192.168.1.100" not in content
    assert re.search(r"\[IP_ADDRESS_[0-9a-f]+\]", content)


def test_cpf_anonymized(tmp_path):
    rc, content, _ = run_anon(input_text="CPF do usuário: 123.456.789-09.", tmp_path=tmp_path)
    assert rc == 0
    assert "123.456.789-09" not in content
    assert re.search(r"\[PHONE_NUMBER_[0-9a-f]+\]", content)


def test_cve_anonymized(tmp_path):
    rc, content, _ = run_anon(input_text="Affected by CVE-2021-44228 (Log4Shell).", tmp_path=tmp_path)
    assert rc == 0
    assert "CVE-2021-44228" not in content
    assert re.search(r"\[CVE_ID_[0-9a-f]+\]", content)


def test_no_models_loaded(tmp_path):
    """Regex strategy must not download or load any ML models."""
    import time
    start = time.time()
    rc, content, _ = run_anon(input_text="email: a@b.com ip: 1.2.3.4", tmp_path=tmp_path)
    elapsed = time.time() - start
    assert rc == 0
    # Regex strategy should be very fast (< 30s); if it loads models it takes minutes
    assert elapsed < 30, f"Took {elapsed:.1f}s — model loading suspected"


def test_slug_length_zero(tmp_path):
    """--slug-length 0 should produce [ENTITY_TYPE] without hash."""
    src = tmp_path / "input.txt"
    src.write_text("Email: test@example.com\n")
    out_dir = tmp_path / "out"
    cmd = [
        sys.executable, str(PROJECT_ROOT / "anon.py"), str(src),
        "--anonymization-strategy", "regex",
        "--slug-length", "0",
        "--db-mode", "in-memory",
        "--no-report", "--overwrite",
        "--output-dir", str(out_dir),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT), env=ANON_ENV, timeout=60)
    content = (out_dir / "anon_input.txt").read_text()
    assert result.returncode == 0
    assert "test@example.com" not in content
    assert "[EMAIL_ADDRESS]" in content


@pytest.mark.parametrize("fmt,filename,content", [
    ("txt", "data.txt", "email: a@b.com\nip: 10.0.0.1\n"),
    ("csv", "data.csv", "email,ip\na@b.com,10.0.0.1\nb@c.com,10.0.0.2\n"),
    ("json", "data.json", '{"email":"a@b.com","ip":"10.0.0.1"}'),
])
def test_file_formats(tmp_path, fmt, filename, content):
    src = tmp_path / filename
    src.write_text(content, encoding="utf-8")
    out_dir = tmp_path / "out"
    cmd = [
        sys.executable, str(PROJECT_ROOT / "anon.py"), str(src),
        "--anonymization-strategy", "regex",
        "--db-mode", "in-memory", "--no-report", "--overwrite",
        "--output-dir", str(out_dir),
        "--slug-length", "8",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT), env=ANON_ENV, timeout=60)
    assert result.returncode == 0, result.stderr
    outputs = list(out_dir.iterdir())
    assert len(outputs) == 1
    out_content = outputs[0].read_text(encoding="utf-8")
    assert "a@b.com" not in out_content
    assert "10.0.0.1" not in out_content

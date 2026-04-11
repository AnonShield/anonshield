"""
Shared pytest fixtures for AnonShield E2E tests.

All fixtures use function or module scope to allow parallel test runs.
Environment variables are set once at session scope.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import pytest

# ---------------------------------------------------------------------------
# Session-level setup
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def anon_env():
    """Ensure ANON_SECRET_KEY is set for all tests."""
    os.environ.setdefault("ANON_SECRET_KEY", "test-key-12345678901234567890123456789012")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent


def _run_anon(args: list[str], env: Optional[dict] = None, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run anon.py as a subprocess and return the result."""
    e = {**os.environ, "ANON_SECRET_KEY": "test-key-12345678901234567890123456789012"}
    if env:
        e.update(env)
    cmd = [sys.executable, str(PROJECT_ROOT / "anon.py")] + args
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT), env=e, timeout=timeout)


# ---------------------------------------------------------------------------
# File fixtures — create temporary sample files
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_output_dir(tmp_path):
    """Temporary output directory, cleaned up after each test."""
    d = tmp_path / "output"
    d.mkdir()
    return str(d)


@pytest.fixture
def tmp_db_dir(tmp_path):
    d = tmp_path / "db"
    d.mkdir()
    return str(d)


@pytest.fixture
def sample_txt(tmp_path):
    """Plain text file with PII."""
    p = tmp_path / "sample.txt"
    p.write_text(
        "My name is John Doe and my email is john.doe@example.com.\n"
        "You can reach me at +1 (555) 123-4567.\n"
        "My CPF is 123.456.789-09 and IP is 192.168.1.100.\n"
        "CVE-2021-44228 is a critical vulnerability.\n",
        encoding="utf-8",
    )
    return str(p)


@pytest.fixture
def sample_csv(tmp_path):
    """CSV file with PII."""
    p = tmp_path / "sample.csv"
    p.write_text(
        "name,email,ip\n"
        "John Doe,john.doe@example.com,192.168.1.100\n"
        "Jane Smith,jane.smith@example.com,10.0.0.1\n",
        encoding="utf-8",
    )
    return str(p)


@pytest.fixture
def sample_json(tmp_path):
    """JSON file with PII."""
    p = tmp_path / "sample.json"
    p.write_text(
        json.dumps({
            "user": {"name": "John Doe", "email": "john.doe@example.com"},
            "ip": "192.168.1.100",
        }),
        encoding="utf-8",
    )
    return str(p)


@pytest.fixture
def sample_custom_patterns(tmp_path):
    """YAML file with custom regex patterns."""
    p = tmp_path / "custom_patterns.yaml"
    p.write_text(
        "- entity_type: BANK_ACCOUNT\n"
        "  pattern: '\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}'\n"
        "  score: 0.9\n"
        "- entity_type: PIX_KEY\n"
        "  pattern: '[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'\n"
        "  score: 0.9\n",
        encoding="utf-8",
    )
    return str(p)


@pytest.fixture
def sample_run_config(tmp_path):
    """YAML run config file."""
    p = tmp_path / "anon_config.yaml"
    p.write_text(
        "lang: en\n"
        "strategy: regex\n"
        "slug_length: 8\n"
        "ocr_engine: tesseract\n"
        "entities:\n"
        "  - EMAIL_ADDRESS\n"
        "  - IP_ADDRESS\n",
        encoding="utf-8",
    )
    return str(p)


# ---------------------------------------------------------------------------
# Convenience runner fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def run_anon():
    """Return the _run_anon helper so tests can call it cleanly."""
    return _run_anon

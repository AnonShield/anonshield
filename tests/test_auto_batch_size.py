"""E2E tests for --batch-size auto adaptive sizing."""
import subprocess
import sys
import os
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def _run(file_path, strategy, output_dir):
    env = {**os.environ, "ANON_SECRET_KEY": "test-key-12345678901234567890123456789012"}
    return subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "anon.py"), str(file_path),
         "--batch-size", "auto",
         "--anonymization-strategy", strategy,
         "--no-report", "--overwrite",
         "--output-dir", str(output_dir),
         "--db-mode", "in-memory"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT), env=env, timeout=120,
    )


@pytest.mark.parametrize("strategy", ["filtered", "standalone"])
def test_auto_batch_size_txt(tmp_path, strategy):
    src = tmp_path / "input.txt"
    src.write_text("My email is john@example.com and IP is 192.168.1.1.\n" * 10)
    result = _run(src, strategy, tmp_path / "out")
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("strategy", ["filtered", "standalone"])
def test_auto_batch_size_csv(tmp_path, strategy):
    src = tmp_path / "input.csv"
    src.write_text("name,email\nJohn Doe,john@example.com\nJane,jane@example.com\n")
    result = _run(src, strategy, tmp_path / "out")
    assert result.returncode == 0, result.stderr

"""
E2E tests for --config YAML run config file and --custom-patterns.

Tests verify that:
  - Settings from a YAML config file are applied correctly
  - CLI arguments override config file values
  - Entity selection from config is honored
  - Custom regex patterns file is loaded and used
  - Inline custom patterns in config file work
  - Banking profile example works end-to-end
"""
import re

from tests.conftest import _run_anon


# ---------------------------------------------------------------------------
# --config flag: basic loading
# ---------------------------------------------------------------------------

def test_config_strategy_applied(sample_txt, tmp_output_dir, sample_run_config):
    """Strategy from config file (regex) is applied when --config is given."""
    result = _run_anon([
        sample_txt,
        "--config", sample_run_config,
        "--output-dir", tmp_output_dir,
        "--slug-length", "0",
        "--overwrite",
    ])
    assert result.returncode == 0, result.stderr
    import glob
    files = glob.glob(f"{tmp_output_dir}/*.txt")
    assert files, "No output file produced"
    content = open(files[0]).read()
    # regex strategy should still anonymize email — original address should be gone
    assert "john.doe@example.com" not in content, f"Email not anonymized: {content!r}"


def test_config_entities_applied(tmp_path, tmp_output_dir, sample_run_config):
    """Entities list from config (EMAIL_ADDRESS, IP_ADDRESS) limits what is anonymized."""
    # Text with email, IP, and a CVE — only email+IP should be anonymized
    p = tmp_path / "mixed.txt"
    p.write_text(
        "Contact: admin@example.com  IP: 10.0.0.1  Bug: CVE-2021-44228\n",
        encoding="utf-8",
    )
    result = _run_anon([
        str(p),
        "--config", sample_run_config,
        "--output-dir", tmp_output_dir,
        "--slug-length", "0",
        "--overwrite",
    ])
    assert result.returncode == 0, result.stderr
    import glob
    files = glob.glob(f"{tmp_output_dir}/*.txt")
    content = open(files[0]).read()
    assert "admin@example.com" not in content, f"Email not anonymized: {content!r}"
    assert "10.0.0.1" not in content, f"IP not anonymized: {content!r}"
    # CVE should NOT be anonymized (not in entities list)
    assert "CVE-2021-44228" in content


def test_cli_overrides_config_strategy(tmp_path, tmp_output_dir, sample_run_config):
    """CLI --anonymization-strategy wins over config file strategy."""
    p = tmp_path / "override.txt"
    p.write_text("Email: test@example.com\n", encoding="utf-8")
    # Config says regex; we force standalone via CLI
    result = _run_anon([
        str(p),
        "--config", sample_run_config,
        "--anonymization-strategy", "standalone",
        "--output-dir", tmp_output_dir,
        "--slug-length", "0",
        "--overwrite",
    ])
    assert result.returncode == 0, result.stderr
    import glob
    files = glob.glob(f"{tmp_output_dir}/*.txt")
    content = open(files[0]).read()
    assert "test@example.com" not in content, f"Email not anonymized: {content!r}"


def test_cli_slug_overrides_config(tmp_path, tmp_output_dir, sample_run_config):
    """CLI --slug-length overrides slug_length from config file."""
    p = tmp_path / "slug.txt"
    p.write_text("admin@example.com\n", encoding="utf-8")
    # Config has slug_length: 8; we override to 4
    result = _run_anon([
        str(p),
        "--config", sample_run_config,
        "--slug-length", "4",
        "--output-dir", tmp_output_dir,
        "--overwrite",
    ])
    assert result.returncode == 0, result.stderr
    import glob
    files = glob.glob(f"{tmp_output_dir}/*.txt")
    content = open(files[0]).read()
    # slug should be 4 hex chars, not 8
    m = re.search(r'\[EMAIL_ADDRESS_([0-9a-f]+)\]', content)
    assert m is not None, f"No anonymized email found in: {content!r}"
    assert len(m.group(1)) == 4, f"Expected slug length 4, got {len(m.group(1))}: {m.group(1)}"


def test_config_not_found_exits_nonzero(tmp_path, tmp_output_dir):
    """Missing config file causes non-zero exit."""
    p = tmp_path / "x.txt"
    p.write_text("hello\n", encoding="utf-8")
    result = _run_anon([
        str(p),
        "--config", str(tmp_path / "nonexistent.yaml"),
        "--output-dir", tmp_output_dir,
    ])
    assert result.returncode != 0


# ---------------------------------------------------------------------------
# --custom-patterns flag
# ---------------------------------------------------------------------------

def test_custom_patterns_detects_new_entity(tmp_path, tmp_output_dir, sample_custom_patterns):
    """Custom pattern for BANK_ACCOUNT is detected in output."""
    p = tmp_path / "bank.txt"
    p.write_text("Account: 1234-5678-9012-3456\n", encoding="utf-8")
    result = _run_anon([
        str(p),
        "--anonymization-strategy", "regex",
        "--custom-patterns", sample_custom_patterns,
        "--output-dir", tmp_output_dir,
        "--slug-length", "0",
        "--overwrite",
    ])
    assert result.returncode == 0, result.stderr
    import glob
    files = glob.glob(f"{tmp_output_dir}/*.txt")
    content = open(files[0]).read()
    assert "[BANK_ACCOUNT]" in content, f"BANK_ACCOUNT not anonymized: {content!r}"


def test_custom_patterns_pix_key(tmp_path, tmp_output_dir, sample_custom_patterns):
    """Custom PIX_KEY UUID pattern is detected."""
    pix = "3e4a1b2c-dead-beef-cafe-000000000000"
    p = tmp_path / "pix.txt"
    p.write_text(f"PIX key: {pix}\n", encoding="utf-8")
    result = _run_anon([
        str(p),
        "--anonymization-strategy", "regex",
        "--custom-patterns", sample_custom_patterns,
        "--output-dir", tmp_output_dir,
        "--slug-length", "0",
        "--overwrite",
    ])
    assert result.returncode == 0, result.stderr
    import glob
    files = glob.glob(f"{tmp_output_dir}/*.txt")
    content = open(files[0]).read()
    assert pix not in content, f"PIX key not anonymized: {content!r}"


def test_custom_patterns_combined_with_builtin(tmp_path, tmp_output_dir, sample_custom_patterns):
    """Custom patterns work alongside built-in patterns in regex strategy."""
    p = tmp_path / "combined.txt"
    p.write_text(
        "Email: info@corp.com\nAccount: 9999-8888-7777-6666\n",
        encoding="utf-8",
    )
    result = _run_anon([
        str(p),
        "--anonymization-strategy", "regex",
        "--custom-patterns", sample_custom_patterns,
        "--output-dir", tmp_output_dir,
        "--slug-length", "0",
        "--overwrite",
    ])
    assert result.returncode == 0, result.stderr
    import glob
    files = glob.glob(f"{tmp_output_dir}/*.txt")
    content = open(files[0]).read()
    assert "[EMAIL_ADDRESS]" in content
    assert "[BANK_ACCOUNT]" in content


def test_custom_patterns_json_format(tmp_path, tmp_output_dir):
    """Custom patterns can be loaded from a JSON file."""
    patterns_file = tmp_path / "patterns.json"
    patterns_file.write_text(
        '[{"entity_type": "EMPLOYEE_ID", "pattern": "EMP-\\\\d{6}", "score": 0.9}]',
        encoding="utf-8",
    )
    p = tmp_path / "hr.txt"
    p.write_text("Employee EMP-001234 is on leave.\n", encoding="utf-8")
    result = _run_anon([
        str(p),
        "--anonymization-strategy", "regex",
        "--custom-patterns", str(patterns_file),
        "--output-dir", tmp_output_dir,
        "--slug-length", "0",
        "--overwrite",
    ])
    assert result.returncode == 0, result.stderr
    import glob
    files = glob.glob(f"{tmp_output_dir}/*.txt")
    content = open(files[0]).read()
    assert "EMP-001234" not in content
    assert "[EMPLOYEE_ID]" in content


# ---------------------------------------------------------------------------
# Banking profile (examples/profiles/banking_pt.yaml)
# ---------------------------------------------------------------------------

def test_banking_profile_cpf(tmp_path, tmp_output_dir):
    """Banking profile with CPF custom pattern anonymizes CPF numbers."""
    p = tmp_path / "doc.txt"
    p.write_text(
        "Cliente: João Silva  CPF: 123.456.789-09  Email: joao@banco.com.br\n",
        encoding="utf-8",
    )
    result = _run_anon([
        str(p),
        "--config", "examples/profiles/banking_pt.yaml",
        "--output-dir", tmp_output_dir,
        "--slug-length", "0",
        "--overwrite",
    ])
    assert result.returncode == 0, result.stderr
    import glob
    files = glob.glob(f"{tmp_output_dir}/*.txt")
    content = open(files[0]).read()
    # CPF number must be gone — label may be CPF or PHONE_NUMBER depending on pattern priority
    assert "123.456.789-09" not in content, f"CPF not anonymized: {content!r}"


def test_banking_profile_email_preserved_label(tmp_path, tmp_output_dir):
    """Banking profile still anonymizes EMAIL_ADDRESS."""
    p = tmp_path / "email_doc.txt"
    p.write_text("Contact: manager@bank.com.br\n", encoding="utf-8")
    result = _run_anon([
        str(p),
        "--config", "examples/profiles/banking_pt.yaml",
        "--output-dir", tmp_output_dir,
        "--slug-length", "0",
        "--overwrite",
    ])
    assert result.returncode == 0, result.stderr
    import glob
    files = glob.glob(f"{tmp_output_dir}/*.txt")
    content = open(files[0]).read()
    assert "manager@bank.com.br" not in content

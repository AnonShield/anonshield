"""Failure boundaries and configuration precedence, without model downloads."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_regressions import process, regex_orchestrator
from src.anon.processors import ProcessorRegistry

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("suffix,content,message", [
    ("jsonl", '{"email":"a@example.com"}\n{"email":"b@example.com",broken\n', "line 2"),
    ("xlsx", 'private email a@example.com', "Cannot read XLSX"),
    ("xml", '<root><email>a@example.com</root>', "Invalid XML"),
    ("xml", '<!DOCTYPE root [<!ENTITY email "a@example.com">]><root>&email;</root>', "ENTITY"),
])
def test_malformed_input_never_publishes_original(tmp_path, suffix, content, message):
    source = tmp_path / f"private.{suffix}"
    source.write_text(content)
    output = tmp_path / "output"
    with pytest.raises(ValueError, match=message):
        process(source, regex_orchestrator(), output)
    assert not list(output.iterdir())


def test_xml_doctype_without_entities_is_processed(tmp_path):
    source = tmp_path / "scan.xml"
    source.write_text('<?xml version="1.0"?>\n<!DOCTYPE nmaprun>\n<nmaprun><owner>a@example.com</owner></nmaprun>')
    content = process(source, regex_orchestrator(), tmp_path / "output").read_text()
    assert "a@example.com" not in content


def test_existing_output_is_not_reported_as_a_new_result(tmp_path):
    source = tmp_path / "input.txt"
    source.write_text("a@example.com")
    output = tmp_path / "output"
    previous = process(source, regex_orchestrator(), output).read_bytes()
    processor = ProcessorRegistry.get_processor(str(source), regex_orchestrator(), output_dir=str(output))
    with pytest.raises(FileExistsError, match="--overwrite"):
        processor.process()
    assert (output / "anon_input.txt").read_bytes() == previous


def test_profile_applies_defaults_and_explicit_cli_values_win(tmp_path, monkeypatch):
    from anon import _parse_arguments
    profile = tmp_path / "profile.yaml"
    profile.write_text("strategy: regex\nlang: pt\nslug_length: 0\nuse_cache: false\ndb_mode: in-memory\nbatch_size: 7\n")
    monkeypatch.setattr(sys, "argv", ["anon.py", "sample.txt", "--config", str(profile)])
    args = _parse_arguments()
    assert (args.anonymization_strategy, args.lang, args.slug_length, args.use_cache, args.db_mode, args.batch_size) == ("regex", "pt", 0, False, "in-memory", 7)
    monkeypatch.setattr(sys, "argv", [*sys.argv, "--anonymization-strategy=filtered", "--lang=en", "--slug-length=64", "--use-cache"])
    args = _parse_arguments()
    assert (args.anonymization_strategy, args.lang, args.slug_length, args.use_cache) == ("filtered", "en", 64, True)


def test_web_profile_field_rules_work_in_cli(tmp_path):
    source = tmp_path / "input.csv"
    source.write_text("email,keep\na@example.com,b@example.com\n")
    profile = tmp_path / "web-profile.yaml"
    profile.write_text("strategy: regex\nslug_length: 0\nanonymization_config:\n  fields_to_exclude: [keep]\n")
    result = subprocess.run(
        [sys.executable, str(ROOT / "anon.py"), str(source), "--config", str(profile),
         "--output-dir", str(tmp_path / "out"), "--db-mode", "in-memory", "--no-report"],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr
    content = (tmp_path / "out" / "anon_input.csv").read_text()
    assert "a@example.com" not in content
    assert "b@example.com" in content


@pytest.mark.parametrize("option,value", [("--batch-size", "0"), ("--csv-chunk-size", "0"), ("--ner-score-threshold", "2")])
def test_invalid_sizes_fail_before_engine_start(monkeypatch, option, value):
    from anon import _parse_arguments
    monkeypatch.setattr(sys, "argv", ["anon.py", "sample.txt", option, value])
    with pytest.raises(SystemExit) as error:
        _parse_arguments()
    assert error.value.code == 2


def test_directory_keeps_subdirectories_and_reports_partial_failure(tmp_path):
    source = tmp_path / "input"
    for name in ("one", "two"):
        (source / name).mkdir(parents=True)
        (source / name / "report.txt").write_text(f"{name}@example.com")
    (source / "broken.json").write_text("{broken")
    output = source / "results"
    result = subprocess.run(
        [sys.executable, str(ROOT / "anon.py"), str(source), "--output-dir", str(output),
         "--anonymization-strategy", "regex", "--slug-length", "0", "--db-mode", "in-memory", "--no-report"],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 1
    assert "output is incomplete" in result.stdout + result.stderr
    assert "Traceback" not in result.stdout + result.stderr
    for name in ("one", "two"):
        assert (output / name / "anon_report.txt").read_text() == "[EMAIL_ADDRESS]"
    assert not (output / "results").exists()


def test_docker_wrapper_help_needs_no_docker_or_workspace(tmp_path):
    result = subprocess.run(["/bin/bash", str(ROOT / "docker/run.sh"), "--help"], cwd=tmp_path,
                            capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"}, timeout=5)
    assert result.returncode == 0
    assert "Usage:" in result.stdout and "--cli-help" in result.stdout
    assert not (tmp_path / "anon").exists()


def test_docker_wrapper_maps_new_nested_directories(tmp_path):
    docker = tmp_path / "docker"
    record = tmp_path / "docker-args.json"
    docker.write_text(f'#!{sys.executable}\nimport json,sys\nfrom pathlib import Path\nif sys.argv[1] == "run": Path({str(record)!r}).write_text(json.dumps(sys.argv[1:]))\n')
    docker.chmod(0o755)
    (tmp_path / "sample file.txt").write_text("a@example.com")
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "ANON_DIR": "relative workspace", "ANON_SECRET_KEY": "test-key"}
    command = ["bash", str(ROOT / "docker/run.sh"), "sample file.txt", "--output-dir", "new/nested/output", "--db-dir", "private/mapping"]
    result = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
    args = json.loads(record.read_text())
    assert f"{tmp_path}/relative workspace/models:/app/models" in args
    assert f"{tmp_path}/new/nested/output:/anon_output" in args
    assert f"{tmp_path}/private/mapping:/app/db" in args
    assert "/anon_input/sample file.txt" in args
    result = subprocess.run(command[:3] + ["--output-dir"], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    assert "needs a value" in result.stdout + result.stderr
    assert "unbound variable" not in result.stdout + result.stderr


def test_windows_and_utf16_text_files_are_read(tmp_path):
    windows = tmp_path / "planilha.csv"
    windows.write_bytes("nome;email\nJoão;joao@example.com\n".encode("cp1252"))
    utf16 = tmp_path / "notas.txt"
    utf16.write_text("Contato: maria@example.com, São Paulo", encoding="utf-16")
    for source in (windows, utf16):
        content = process(source, regex_orchestrator(), tmp_path / "out").read_text(encoding="utf-8")
        assert "@example.com" not in content
        assert "Jo\u00e3o" in content or "S\u00e3o Paulo" in content


def test_undecodable_text_is_a_clear_error(tmp_path):
    source = tmp_path / "broken.txt"
    source.write_bytes(b"caf\xc3 \x81 a@example.com")
    with pytest.raises(ValueError, match="Save it as UTF-8"):
        process(source, regex_orchestrator(), tmp_path / "out")

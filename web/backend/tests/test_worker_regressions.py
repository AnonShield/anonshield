"""The worker must preserve the requested scope and publish complete archives."""
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workers.tasks import _anonymize, _process_zip


def test_worker_empty_selection_leaves_data_untouched(tmp_path):
    source = tmp_path / "private.txt"
    source.write_text("a@example.com 10.0.0.1")
    out = tmp_path / "out"
    result = _anonymize(source, out, {"strategy": "regex", "entities": [], "slug_length": 0}, "")
    assert result["entity_count"] == 0
    assert (out / "anon_private.txt").read_text() == source.read_text()


def test_zip_keeps_folders_with_duplicate_basenames(tmp_path):
    source = tmp_path / "reports.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("one/report.txt", "a@example.com")
        archive.writestr("two/report.txt", "b@example.com")
    out = tmp_path / "out"
    out.mkdir()
    result = _process_zip(source, out, {"strategy": "regex", "slug_length": 0}, "")
    assert result["files_processed"] == 2
    with zipfile.ZipFile(out / "anon_reports.zip") as archive:
        assert set(archive.namelist()) == {"one/anon_report.txt", "two/anon_report.txt"}
        assert all(b"example.com" not in archive.read(name) for name in archive.namelist())


def test_zip_never_publishes_incomplete_success(tmp_path):
    source = tmp_path / "reports.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("ok.txt", "a@example.com")
        archive.writestr("broken.json", '{"email":"private@example.com",broken')
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(ValueError, match=r"Invalid JSON in broken\.json") as error:
        _process_zip(source, out, {"strategy": "regex", "slug_length": 0}, "")
    assert str(tmp_path) not in str(error.value)
    assert not list(out.iterdir())


def test_zip_skips_unsupported_files_and_macos_metadata(tmp_path):
    source = tmp_path / "reports.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("report.txt", "a@example.com")
        archive.writestr("notes.md", "b@example.com")
        archive.writestr("__MACOSX/._report.txt", "metadata")
        archive.writestr(".DS_Store", "metadata")
    out = tmp_path / "out"
    out.mkdir()
    result = _process_zip(source, out, {"strategy": "regex", "slug_length": 0}, "")
    assert (result["files_processed"], result["skipped_files"]) == (1, ["notes.md"])
    with zipfile.ZipFile(out / "anon_reports.zip") as archive:
        assert archive.namelist() == ["anon_report.txt"]


def test_local_xml_has_no_artificial_size_limit(tmp_path, monkeypatch):
    from src.anon.config import ProcessingLimits
    monkeypatch.setattr(ProcessingLimits, "XML_MEMORY_THRESHOLD_MB", 0)
    source = tmp_path / "private.xml"
    source.write_text("<root>a@example.com</root>")
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="Threshold"):
        _anonymize(source, out, {"strategy": "regex", "slug_length": 0}, "")
    monkeypatch.setenv("ANON_FORCE_LARGE_XML", "true")
    _anonymize(source, out, {"strategy": "regex", "slug_length": 0}, "")
    assert b"a@example.com" not in (out / "anon_private.xml").read_bytes()


def test_engine_progress_bars_become_job_progress(monkeypatch):
    import io
    from tqdm import tqdm
    from workers import tasks
    sent = []
    monkeypatch.setattr(tasks.job_service, "set_status", lambda job, status, **extra: sent.append(extra["progress"]))
    monkeypatch.setattr(tasks.job_service, "get_status", lambda job: {"status": "running"})
    monkeypatch.setattr(tasks, "_PROGRESS_EVERY_S", 0)
    with tasks._progress_to_status("job", 0.0):
        for _ in tqdm(range(4), desc="Pass 1/2: Reading x", file=io.StringIO()):
            pass
        for _ in tqdm(range(3), desc="Detecting Entities for x", file=io.StringIO()):
            pass
        bar = tqdm(total=100, desc="Pass 2/2: Writing x", file=io.StringIO())
        bar.update(50)
        bar.update(50)
    assert sent == [12.5, 25.0, 37.5, 50.0, 75.0, 99.9]
    assert tqdm.update.__name__ == "update"


def test_cancelling_a_running_job_stops_it(monkeypatch):
    import io
    from tqdm import tqdm
    from workers import tasks
    monkeypatch.setattr(tasks.job_service, "get_status", lambda job: None)
    monkeypatch.setattr(tasks, "_PROGRESS_EVERY_S", 0)
    seen = []
    with pytest.raises(tasks.JobCancelled):
        with tasks._progress_to_status("job", 0.0):
            for item in tqdm(range(100), desc="Processing x", file=io.StringIO()):
                seen.append(item)
    assert len(seen) < 3

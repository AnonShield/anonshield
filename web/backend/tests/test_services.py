"""Unit tests for backend services — no Redis, no disk I/O required."""
import re
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add backend root to path so imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ── storage ───────────────────────────────────────────────────────────────────

class TestStorage:
    def test_job_dir_uses_env_var(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ANON_JOBS_DIR", str(tmp_path / "jobs"))
        import importlib
        import services.storage as mod
        importlib.reload(mod)
        assert str(tmp_path / "jobs") in str(mod.JOBS_ROOT)

    def test_create_and_delete_job(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ANON_JOBS_DIR", str(tmp_path / "jobs"))
        import importlib
        import services.storage as mod
        importlib.reload(mod)

        job_id = "test-job-123"
        mod.create_job_dir(job_id)
        assert mod.job_dir(job_id).exists()
        assert mod.output_dir(job_id).exists()

        # Write a fake input file
        inp = mod.input_path(job_id, "txt")
        inp.write_text("hello")
        mod.delete_input(job_id)
        assert not inp.exists()

        # Write a fake output file
        out = mod.output_dir(job_id) / "result.txt"
        out.write_text("anon")
        assert mod.get_output_file(job_id) == out

        mod.delete_output(job_id)
        assert not mod.output_dir(job_id).exists()

        mod.delete_job(job_id)
        assert not mod.job_dir(job_id).exists()

    def test_sweep_removes_old_jobs(self, tmp_path, monkeypatch):
        import time
        monkeypatch.setenv("ANON_JOBS_DIR", str(tmp_path / "jobs"))
        import importlib
        import services.storage as mod
        importlib.reload(mod)

        mod.create_job_dir("old-job")
        d = mod.job_dir("old-job")
        # Backdate mtime by 2 hours
        old_time = time.time() - 7300
        import os
        os.utime(d, (old_time, old_time))

        deleted = mod.sweep_orphaned_jobs(max_age_seconds=7200)
        assert deleted == 1
        assert not d.exists()


# ── profile validation ─────────────────────────────────────────────────────────

class TestProfileValidation:
    def setup_method(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from services.profile import validate_profile
        self.validate = validate_profile

    def test_valid_minimal(self):
        result = self.validate("strategy: regex\nlang: pt\n")
        assert result["valid"] is True
        assert result["entities_count"] == 0

    def test_valid_with_patterns(self):
        yaml = """
strategy: regex
custom_patterns:
  - entity_type: CPF
    pattern: '\\d{3}\\.\\d{3}\\.\\d{3}-\\d{2}'
    score: 0.9
"""
        result = self.validate(yaml)
        assert result["valid"] is True
        assert result["patterns_count"] == 1

    def test_invalid_strategy(self):
        result = self.validate("strategy: nonexistent\n")
        assert result["valid"] is False
        assert "strategy" in result["error"]

    def test_invalid_regex(self):
        yaml = """
custom_patterns:
  - entity_type: BAD
    pattern: '[unclosed'
"""
        result = self.validate(yaml)
        assert result["valid"] is False
        assert "regex" in result["error"].lower()

    def test_missing_pattern_field(self):
        yaml = """
custom_patterns:
  - entity_type: CPF
"""
        result = self.validate(yaml)
        assert result["valid"] is False
        assert "pattern" in result["error"]

    def test_invalid_yaml(self):
        result = self.validate("key: [unclosed")
        assert result["valid"] is False

    def test_unknown_key(self):
        result = self.validate("unknown_key: value\n")
        assert result["valid"] is False
        assert "unknown_key" in result["error"]


# ── entity endpoint ─────────────────────────────────────────────────────────────

class TestEntitiesEndpoint:
    def test_regex_excludes_ner_entities(self):
        from routers.entities import list_entities
        result = list_entities(strategy="regex")
        all_ids = [e["id"] for g in result["groups"] for e in g["entities"]]
        assert "PERSON" not in all_ids
        assert "CPF" in all_ids

    def test_filtered_includes_ner_entities(self):
        from routers.entities import list_entities
        result = list_entities(strategy="filtered")
        all_ids = [e["id"] for g in result["groups"] for e in g["entities"]]
        assert "PERSON" in all_ids
        assert "CPF" in all_ids

    def test_response_structure(self):
        from routers.entities import list_entities
        result = list_entities()
        assert "groups" in result
        for group in result["groups"]:
            assert "label" in group
            assert "entities" in group
            for e in group["entities"]:
                assert "id" in e
                assert "label" in e
                assert "example" in e

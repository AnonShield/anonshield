import unittest
import os
import subprocess
import sys
import tempfile
import shutil
import json
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock

class TestOutputDirectories(unittest.TestCase):
    def setUp(self):
        self.original_cwd = Path.cwd()
        self.test_dir = Path(tempfile.mkdtemp())
        self.output_dir = self.original_cwd / "output"

        # Create dummy input files
        self.entity_map_path = self.test_dir / "entity_map.jsonl"
        with open(self.entity_map_path, "w") as f:
            f.write('{"entity_type": "URL", "text": "http://example.com"}\n')
            f.write('{"entity_type": "PERSON", "text": "John Doe"}\n')

        self.text_to_anonymize_path = self.test_dir / "text_to_anonymize.txt"
        with open(self.text_to_anonymize_path, "w") as f:
            f.write("My name is John Doe and my email is john.doe@example.com.")

        # Add project root to sys.path to allow imports from src
        if str(self.original_cwd) not in sys.path:
            sys.path.insert(0, str(self.original_cwd))

        os.environ["ANON_SECRET_KEY"] = "test-secret"


    def tearDown(self):
        shutil.rmtree(self.test_dir)
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir, ignore_errors=True)
        if str(self.original_cwd) in sys.path:
            sys.path.remove(str(self.original_cwd))


    def run_script(self, script_name, args):
        script_path = self.original_cwd / "scripts" / script_name
        command = [sys.executable, str(script_path)] + args
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                cwd=self.original_cwd,
                timeout=60 # 1 minute timeout
            )
            return result
        except subprocess.CalledProcessError as e:
            self.fail(f"Script {script_name} failed with stdout:\n{e.stdout}\n\nstderr:\n{e.stderr}")
        except subprocess.TimeoutExpired as e:
            self.fail(f"Script {script_name} timed out. stdout:\n{e.stdout}\n\nstderr:\n{e.stderr}")


    def test_export_and_clear_db_output(self):
        db_dir = self.test_dir / "db"
        db_dir.mkdir()
        db_path = db_dir / "entities.db"

        # Create a dummy database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE entities (
                id INTEGER PRIMARY KEY,
                entity_type TEXT NOT NULL,
                original_name TEXT NOT NULL,
                slug_name TEXT NOT NULL,
                full_hash TEXT NOT NULL UNIQUE,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL
            )
        """)
        cursor.execute("INSERT INTO entities VALUES (1, 'PERSON', 'John Doe', 'slug', 'hash', '2025-01-01', '2025-01-01')")
        conn.commit()
        conn.close()

        script_name = "export_and_clear_db.py"
        
        self.run_script(script_name, ["--db-dir", str(db_dir)])
        
        expected_dir = self.output_dir / "export_and_clear_db"
        expected_file = expected_dir / "entities_export.csv"

        self.assertTrue(expected_dir.is_dir())
        self.assertTrue(expected_file.is_file())

    @patch('scripts.slm_regex_generator.get_slm_client')
    def test_slm_regex_generator_output(self, mock_get_slm_client):
        mock_client = MagicMock()
        mock_client.query_json.return_value = {"regex": ".*"}
        mock_get_slm_client.return_value = mock_client

        from scripts import slm_regex_generator
        
        with patch.object(sys, 'argv', ['scripts/slm_regex_generator.py', str(self.entity_map_path)]):
            slm_regex_generator.main()

        expected_dir = self.output_dir / "slm_regex_generator"
        expected_file = expected_dir / "slm_regex_report.json"

        self.assertTrue(expected_dir.is_dir())
        self.assertTrue(expected_file.is_file())

        with open(expected_file, "r") as f:
            data = json.load(f)
            self.assertIn("URL", data)
            self.assertEqual(data["URL"]["slm_response"]["regex"], ".*")

if __name__ == "__main__":
    unittest.main()

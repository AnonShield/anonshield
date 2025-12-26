
import unittest
import os
import shutil
import subprocess
from pathlib import Path

class TestAnalyzeJsonScript(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path("temp_test_dir_for_analyze_json")
        self.output_dir = self.test_dir / "output"
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

        # Create a sample JSON file
        self.json_file_path = self.test_dir / "sample.json"
        with open(self.json_file_path, "w") as f:
            f.write("""
            [
                {
                    "name": "test1",
                    "value": 1,
                    "nested": {"id": "a"},
                    "tags": ["x", "y"]
                },
                {
                    "name": "test2",
                    "value": 2,
                    "nested": {"id": "b"},
                    "tags": ["x", "z"]
                }
            ]
            """)

        # Create a sample JSONL file
        self.jsonl_file_path = self.test_dir / "sample.jsonl"
        with open(self.jsonl_file_path, "w") as f:
            f.write('{"name": "test3", "value": 3, "nested": {"id": "c"}}\n')
            f.write('{"name": "test1", "value": 4, "nested": {"id": "d"}}\n')
            
    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_script_execution(self):
        # Run the script
        script_path = "scripts/analyze_json.py"
        try:
            result = subprocess.run(
                ["python", script_path, str(self.test_dir), "--output_dir", str(self.output_dir)],
                capture_output=True, text=True, check=True, timeout=30
            )
            print(result.stdout)
            print(result.stderr)
        except subprocess.CalledProcessError as e:
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
            self.fail(f"Script execution failed with exit code {e.returncode}")
        except subprocess.TimeoutExpired as e:
            print("STDOUT:", e.stdout)
            print("STDERR:", e.stderr)
            self.fail("Script execution timed out.")


        # Find the dynamically created run output directory
        run_output_dirs = [d for d in self.output_dir.iterdir() if d.is_dir() and d.name.startswith(f"analysis_{self.test_dir.name}")]
        self.assertEqual(len(run_output_dirs), 1, "Should find exactly one output directory for the run.")
        run_output_dir = run_output_dirs[0]

        # 1. Check if unique_fields.txt was created and has correct content
        unique_fields_file = run_output_dir / "unique_fields.txt"
        self.assertTrue(unique_fields_file.exists())
        
        with open(unique_fields_file, "r") as f:
            content = f.read().splitlines()
        
        expected_keys = sorted(["name", "value", "nested", "nested.id", "tags"])
        self.assertEqual(sorted(content), expected_keys)

        # 2. Check if field_values directory and files were created
        field_values_dir = run_output_dir / "field_values"
        self.assertTrue(field_values_dir.exists())

        # Check content of name.txt
        name_values_file = field_values_dir / "name.txt"
        self.assertTrue(name_values_file.exists())
        with open(name_values_file, "r") as f:
            content = f.read().splitlines()
        self.assertEqual(sorted(content), ["test1", "test2", "test3"])

        # Check content of value.txt
        value_values_file = field_values_dir / "value.txt"
        self.assertTrue(value_values_file.exists())
        with open(value_values_file, "r") as f:
            content = f.read().splitlines()
        self.assertEqual(sorted(content), ["1", "2", "3", "4"])

        # Check content of nested.id.txt
        nested_id_values_file = field_values_dir / "nested_id.txt"
        self.assertTrue(nested_id_values_file.exists())
        with open(nested_id_values_file, "r") as f:
            content = f.read().splitlines()
        self.assertEqual(sorted(content), ["a", "b", "c", "d"])

        # Check content of tags.txt
        tags_values_file = field_values_dir / "tags.txt"
        self.assertTrue(tags_values_file.exists())
        with open(tags_values_file, "r") as f:
            content = f.read().splitlines()
        self.assertEqual(sorted(content), ["x", "y", "z"])


if __name__ == '__main__':
    unittest.main()

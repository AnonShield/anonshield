import unittest
import os
import orjson
import shutil
import subprocess

class TestJsonAnonymization(unittest.TestCase):
    def setUp(self):
        self.output_dir = "output"
        self.test_data_dir = "tests/test_data_pytest"
        self.test_array_file = os.path.join(self.test_data_dir, "test_array.json")
        self.test_jsonl_file = os.path.join(self.test_data_dir, "test.jsonl")
        self.config_file = os.path.join(self.test_data_dir, "new_anonymization_config.json")

        # Create a correctly formatted config file for this test
        config_data = {
            "force_anonymize": {
                "user": {"entity_type": "USERNAME"}
            },
            "fields_to_anonymize": [
                "comment",
                "email"
            ],
            "fields_to_exclude": [
                "ip_address"
            ]
        }
        with open(self.config_file, "wb") as f:
            f.write(orjson.dumps(config_data))

        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Ensure the secret key is set
        os.environ["ANON_SECRET_KEY"] = "test-secret-key"

    def tearDown(self):
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        if os.path.exists(self.config_file):
            os.remove(self.config_file)

    def _run_anonymizer(self, file_path):
        """Helper to run the anonymization script."""
        command = [
            "uv", "run", "python", "anon.py", file_path,
            "--anonymization-config", self.config_file,
            "--db-mode", "in-memory"
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, f"Anonymizer script failed for '{file_path}'.\nStderr: {result.stderr}\nStdout: {result.stdout}")

    def test_anonymize_json_array_with_new_config(self):
        """Tests that a JSON array is correctly anonymized using the new config schema."""
        self.test_array_file = os.path.join(self.test_data_dir, "test_array_for_comment_test.json")
        self._run_anonymizer(self.test_array_file)
        
        output_file = os.path.join(self.output_dir, "anon_test_array_for_comment_test.json")
        self.assertTrue(os.path.exists(output_file))
        
        with open(output_file, "rb") as f:
            data = orjson.loads(f.read())
        
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 3) # Should process all 3 objects

        # Check object 1
        self.assertTrue(data[0]["user"].startswith("[USERNAME_"))
        self.assertTrue(data[0]["email"].startswith("[EMAIL_ADDRESS_"))
        self.assertEqual(data[0]["ip_address"], "192.168.1.1") # Excluded
        self.assertNotIn("John Doe", data[0]["comment"]) # Auto-detected in 'comment'
        self.assertNotIn("New York", data[0]["comment"]) # Auto-detected in 'comment'

        # Check object 2
        self.assertTrue(data[1]["user"].startswith("[USERNAME_"))
        self.assertTrue(data[1]["email"].startswith("[EMAIL_ADDRESS_"))
        self.assertEqual(data[1]["ip_address"], "10.0.0.5") # Excluded
        self.assertNotIn("Jane Smith", data[1]["comment"]) # Auto-detected in 'comment'
        
        # Check object 3 (no PII in comment)
        self.assertTrue(data[2]["user"].startswith("[USERNAME_"))
        self.assertTrue(data[2]["email"].startswith("[EMAIL_ADDRESS_"))
        self.assertEqual(data[2]["ip_address"], "8.8.8.8") # Excluded
        self.assertEqual(data[2]["comment"], "Google's DNS")

    def test_anonymize_jsonl_with_new_config(self):
        """Tests that a JSONL file is correctly anonymized using the new config schema."""
        self._run_anonymizer(self.test_jsonl_file)

        output_file = os.path.join(self.output_dir, "anon_test.jsonl")
        self.assertTrue(os.path.exists(output_file))
        
        with open(output_file, "r") as f:
            lines = f.readlines()
        
        self.assertEqual(len(lines), 3) # Should process all 3 lines

        # Check line 1
        data1 = orjson.loads(lines[0])
        self.assertTrue(data1["user"].startswith("[USERNAME_"))
        self.assertTrue(data1["email"].startswith("[EMAIL_ADDRESS_"))
        self.assertEqual(data1["ip_address"], "192.168.1.100") # Excluded

if __name__ == "__main__":
    unittest.main()
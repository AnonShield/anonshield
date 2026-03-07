import unittest
import os
import subprocess
import sys
import orjson
import shutil

class TestNewConfigLogic(unittest.TestCase):
    CONFIG_FILE = "examples/anonymization_config.json"
    OUTPUT_DIR = "test_output_new_config"
    TEST_ARRAY_FILE = "tests/test_data_pytest/test_array.json"
    TEST_SHORT_WORD_FILE = "tests/test_data_pytest/test_short_words.json"
    TEST_AUTODETECT_FILE = "tests/test_data_pytest/test_autodetect.json"

    def setUp(self):
        self.assertTrue(os.path.exists(self.CONFIG_FILE), "Main examples/anonymization_config.json not found")
        if os.path.exists(self.OUTPUT_DIR):
            shutil.rmtree(self.OUTPUT_DIR)
        os.makedirs(self.OUTPUT_DIR)

    def tearDown(self):
        if os.path.exists(self.OUTPUT_DIR):
            shutil.rmtree(self.OUTPUT_DIR)

    def _run_anonymizer(self, file_path, *extra_args):
        """Helper function to run the main anonymization script with extra arguments."""
        self.assertTrue(os.path.exists(file_path), f"Test data file not found: {file_path}")
        command = [
            sys.executable, "anon.py", file_path,
            "--db-mode", "in-memory",
            "--output-dir", self.OUTPUT_DIR,
            *extra_args
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, f"Anonymizer script failed for '{file_path}' with args {extra_args}.\nStderr: {result.stderr}\nStdout: {result.stdout}")
        
        base_name, ext = os.path.splitext(os.path.basename(file_path))
        output_file = os.path.join(self.OUTPUT_DIR, f"anon_{base_name}{ext}")
        self.assertTrue(os.path.exists(output_file), f"Output file not found at {output_file}")
        return output_file

    def test_forced_anonymization_bypasses_min_length(self):
        """
        Tests that forced anonymization works on short words, bypassing the min_word_length filter.
        """
        # Config forces asset.tags.value, which contains "OK" (length 2)
        output_file = self._run_anonymizer(self.TEST_SHORT_WORD_FILE, "--anonymization-config", self.CONFIG_FILE, "--min-word-length=3")

        with open(output_file, "rb") as f:
            anon_data = orjson.loads(f.read())

        # "OK" should be anonymized because its path `asset.tags.value` is in `forced_anonymization`
        self.assertTrue(anon_data["asset"]["tags"][0]["value"].startswith("[ASSET_TAG_VALUE_"))
        # "comment" is not forced and is long enough, so it should be processed by auto-detection.
        # As "This is a test" contains no PII, it should remain unchanged.
        self.assertEqual(anon_data["comment"], "This is a test")

    def test_min_word_length_filters_autodetect(self):
        """
        Tests that --min-word-length filters auto-detected fields but not forced ones.
        """
        # This test uses a config that only allows 'analyst_name' for auto-detection
        temp_config = {
            "fields_to_anonymize": ["analyst_name"]
        }
        temp_config_path = "temp_autodetect_config.json"
        with open(temp_config_path, "wb") as f:
            f.write(orjson.dumps(temp_config))

        output_file = self._run_anonymizer(self.TEST_AUTODETECT_FILE, "--anonymization-config", temp_config_path, "--min-word-length=3")

        with open(output_file, "rb") as f:
            anon_data = orjson.loads(f.read())
        
        # "John Doe" is long enough and should be auto-detected as PERSON
        self.assertTrue(anon_data["analyst_name"].startswith("[PERSON_"))
        # "Jo" is not in the allow-list, so it should be skipped
        self.assertEqual(anon_data["short_name"], "Jo")
        
        os.remove(temp_config_path)

    def test_fields_to_anonymize_as_allow_list(self):
        """
        Tests that a non-empty `fields_to_anonymize` acts as a strict allow-list for auto-detection.
        """
        # Create a temporary config where only 'analyst.name' is in the auto-detection allow-list
        with open(self.CONFIG_FILE, "rb") as f:
            config = orjson.loads(f.read())
        
        config["fields_to_anonymize"] = ["user"] # Only allow this for auto-detection
        temp_config_path = "temp_allowlist_config.json"
        with open(temp_config_path, "wb") as f:
            f.write(orjson.dumps(config))

        output_file = self._run_anonymizer(self.TEST_ARRAY_FILE, "--anonymization-config", temp_config_path)

        with open(output_file, "rb") as f:
            anon_data = orjson.loads(f.read())[0] # Check first object

        # This is in the allow-list, should be anonymized
        self.assertTrue(anon_data["user"].startswith("[PERSON_"))
        # This is NOT in the allow-list, should be skipped
        self.assertEqual(anon_data["email"], "john.doe@example.com")

        os.remove(temp_config_path)

if __name__ == '__main__':
    unittest.main()

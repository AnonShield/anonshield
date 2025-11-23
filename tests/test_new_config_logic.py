import unittest
import os
import subprocess
import orjson
import shutil

class TestNewConfigLogic(unittest.TestCase):
    CONFIG_FILE = "anonymization_config.json"
    OUTPUT_DIR = "output"
    TEST_ARRAY_FILE = "tests/test_data_pytest/test_array.json"
    TEST_SHORT_WORD_FILE = "tests/test_data_pytest/test_short_words.json"
    TEST_AUTODETECT_FILE = "tests/test_data_pytest/test_autodetect.json"

    def setUp(self):
        self.assertTrue(os.path.exists(self.CONFIG_FILE), "Main anonymization_config.json not found")
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
            "uv", "run", "python", "anon.py", file_path,
            "--db-mode", "in-memory",
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
        # This test uses a config that does not force `analyst_name` or `short_name`
        output_file = self._run_anonymizer(self.TEST_AUTODETECT_FILE, "--anonymization-config", "anonymization_config.json", "--min-word-length=3")

        with open(output_file, "rb") as f:
            anon_data = orjson.loads(f.read())
        
        # "John Doe" is long enough and should be auto-detected as PERSON
        self.assertTrue(anon_data["analyst_name"].startswith("[PERSON_"))
        # "Jo" is shorter than min-word-length and should be skipped
        self.assertEqual(anon_data["short_name"], "Jo")

    def test_technical_stoplist_argument(self):
        """
        Tests that the --technical-stoplist argument prevents auto-detection.
        """
        # Run with default min-word-length (0), so "Jo" would normally be processed
        output_file = self._run_anonymizer(self.TEST_AUTODETECT_FILE, "--anonymization-config", "anonymization_config.json", "--technical-stoplist", "john doe,jo")

        with open(output_file, "rb") as f:
            anon_data = orjson.loads(f.read())

        # Both names should be skipped because they are in the custom stoplist
        self.assertEqual(anon_data["analyst_name"], "John Doe")
        self.assertEqual(anon_data["short_name"], "Jo")

    def test_fields_to_anonymize_as_allow_list(self):
        """
        Tests that a non-empty `fields_to_anonymize` acts as a strict allow-list for auto-detection.
        """
        # Create a temporary config where only 'analyst.name' is in the auto-detection allow-list
        with open(self.CONFIG_FILE, "rb") as f:
            config = orjson.loads(f.read())
        
        config["fields_to_anonymize"] = ["analyst.name"] # Only allow this for auto-detection
        temp_config_path = "temp_allowlist_config.json"
        with open(temp_config_path, "wb") as f:
            f.write(orjson.dumps(config))

        output_file = self._run_anonymizer(self.TEST_ARRAY_FILE, "--anonymization-config", temp_config_path)

        with open(output_file, "rb") as f:
            anon_data = orjson.loads(f.read())[0] # Check first object

        # This is in the allow-list, should be anonymized
        self.assertTrue(anon_data["analyst"]["name"].startswith("[PERSON_"))
        # This is NOT in the allow-list, should be skipped
        self.assertEqual(anon_data["analyst"]["email"], "jane.smith@example.com")

        os.remove(temp_config_path)

if __name__ == '__main__':
    unittest.main()

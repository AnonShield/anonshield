import unittest
import os
import subprocess
import sys
import shutil

class TestSecretKeyValidation(unittest.TestCase):

    def setUp(self):
        # Store original SECRET_KEY if set, and then unset it
        self._original_secret_key = os.environ.get("ANON_SECRET_KEY")
        if self._original_secret_key:
            del os.environ["ANON_SECRET_KEY"]

    def tearDown(self):
        # Restore original SECRET_KEY
        if self._original_secret_key:
            os.environ["ANON_SECRET_KEY"] = self._original_secret_key
        else:
            if "ANON_SECRET_KEY" in os.environ:
                del os.environ["ANON_SECRET_KEY"]

    def test_anonymization_fails_without_secret_key(self):
        # Create a dummy file so the path check passes
        dummy_file = "dummy_for_fail_test.txt"
        with open(dummy_file, "w") as f:
            f.write("Some text.")

        # Run anon.py in anonymization mode (default) without SECRET_KEY
        # Expect it to exit with an error code and print the specific error message
        command = [sys.executable, "anon.py", dummy_file]
        result = subprocess.run(command, capture_output=True, text=True)
        
        self.assertNotEqual(result.returncode, 0, "anon.py should fail without SECRET_KEY")
        # The TqdmLoggingHandler redirects all logs to stdout, so we check there.
        self.assertIn("ANON_SECRET_KEY or ANON_SECRET_KEY_FILE not set", result.stdout)
        
        # Clean up dummy file
        os.remove(dummy_file)

    def test_ner_data_generation_succeeds_without_secret_key(self):
        # Run anon.py in NER data generation mode without SECRET_KEY
        # Expect it to succeed (or at least not fail due to missing SECRET_KEY)
        # We need a dummy file for it to process
        dummy_file = "dummy.txt"
        with open(dummy_file, "w") as f:
            f.write("Some text.")
        
        command = [sys.executable, "anon.py", dummy_file, "--generate-ner-data"]
        result = subprocess.run(command, capture_output=True, text=True)
        
        # We assert that the specific error message for missing SECRET_KEY is NOT present.
        self.assertNotIn("ANON_SECRET_KEY or ANON_SECRET_KEY_FILE not set", result.stderr)
        
        # The return code might still be non-zero if other errors occur (e.g., no processor for dummy.txt or model download issues)
        # So we specifically check for the absence of the SECRET_KEY error.
        
        # Clean up dummy file
        os.remove(dummy_file)

    def test_anonymization_succeeds_with_secret_key(self):
        # Set a dummy SECRET_KEY and run in anonymization mode
        os.environ["ANON_SECRET_KEY"] = "test-key"
        
        # We need a dummy file for it to process
        dummy_file = "dummy.txt"
        with open(dummy_file, "w") as f:
            f.write("My name is John Doe.")
        
        # Create a temporary output directory for this test case to avoid conflicts
        temp_output_dir = "temp_output_for_secret_key_test"
        os.makedirs(temp_output_dir, exist_ok=True)

        command = [sys.executable, "anon.py", dummy_file, "--output-dir", temp_output_dir]
        result = subprocess.run(command, capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0, f"anon.py failed even with SECRET_KEY set. Stderr: {result.stderr}")
        self.assertNotIn("ANON_SECRET_KEY or ANON_SECRET_KEY_FILE not set", result.stderr)

        # Verify output file exists and is anonymized
        output_file_path = os.path.join(temp_output_dir, "anon_dummy.txt")
        self.assertTrue(os.path.exists(output_file_path))
        with open(output_file_path, "r") as f:
            content = f.read()
            self.assertIn("[PERSON_", content)
            self.assertNotIn("John Doe", content)

        # Clean up dummy file and generated output directory
        os.remove(dummy_file)
        shutil.rmtree(temp_output_dir)

if __name__ == '__main__':
    unittest.main()

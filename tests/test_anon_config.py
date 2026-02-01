import unittest
import os
import json
import subprocess
import sys
import tempfile
import shutil
import logging

class TestAnonymizationConfig(unittest.TestCase):
    def setUp(self):
        # Configure logging to DEBUG level for tests
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', force=True)
        
        self.test_dir = tempfile.mkdtemp()
        self.output_dir = os.path.join(self.test_dir, "output")
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir) # Change CWD to test dir to find anon.py
        
        # Make sure the root anon.py is in the python path
        sys.path.insert(0, self.original_cwd)

    def tearDown(self):
        # Reset logging configuration to avoid affecting other tests or subsequent runs
        logging.basicConfig(level=logging.WARNING, force=True) # Reset to default or preferred quiet level

        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
        sys.path.pop(0)

    def test_json_field_specific_anonymization(self):
        # 1. Create the configuration file
        config_path = os.path.join(self.test_dir, "config.json")
        config_data = {
            "force_anonymize": {
                "asset.name": {"entity_type": "CUSTOM_ASSET_NAME"}
            },
            "fields_to_anonymize": [
                "asset.tags.value",
                "asset.ipv4_addresses",
                "scan.target"
            ],
            "fields_to_exclude": [
                "scan.id"
            ]
        }
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        # 2. Create the input JSON file
        input_path = os.path.join(self.test_dir, "input.json")
        input_data = {
            "asset": {
                "name": "Server-01",
                "tags": [
                    {"category": "OS", "value": "Windows"},
                    {"category": "Location", "value": "New York"}
                ],
                "ipv4_addresses": ["192.168.1.10", "10.0.0.5"],
                "display_ipv4_address": "192.168.1.10"
            },
            "scan": {
                "id": "scan-12345",
                "target": "server-01.example.com"
            }
        }
        with open(input_path, "w") as f:
            json.dump(input_data, f)

        # 3. Run the anonymization script
        script_path = os.path.join(self.original_cwd, "anon.py")
        command = [
            sys.executable, script_path,
            input_path,
            "--anonymization-config", config_path,
            "--lang", "en",
            "--log-level", "DEBUG"
        ]
        
        # Set the secret key for the subprocess
        env = os.environ.copy()
        env["ANON_SECRET_KEY"] = "test-secret-key-for-config"

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                env=env,
                cwd=self.original_cwd # Run from original CWD
            )
        except subprocess.CalledProcessError as e:
            self.fail(f"Subprocess failed with stdout:\n{e.stdout}\n\nstderr:\n{e.stderr}")

        # 4. Read and verify the output
        output_file_path = os.path.join(self.original_cwd, "output", "anon_input.json")
        self.assertTrue(os.path.exists(output_file_path), "Output file was not created.")

        with open(output_file_path, "r") as f:
            output_data = json.load(f)

        # Assertions
        self.assertIn("CUSTOM_ASSET_NAME", output_data["asset"]["name"])
        self.assertNotIn("Server-01", output_data["asset"]["name"])

        # This was not in fields_to_anonymize, so it should be unchanged
        self.assertEqual("OS", output_data["asset"]["tags"][0]["category"])
        
        # This was in fields_to_anonymize (auto-detected)
        self.assertIn("LOCATION", output_data["asset"]["tags"][1]["value"])
        self.assertNotIn("New York", output_data["asset"]["tags"][1]["value"])

        # List of IPs
        self.assertIn("IP_ADDRESS", output_data["asset"]["ipv4_addresses"][0])
        self.assertIn("IP_ADDRESS", output_data["asset"]["ipv4_addresses"][1])

        # This field was not in the config, so it should be unchanged as per the new rules
        self.assertEqual("192.168.1.10", output_data["asset"]["display_ipv4_address"])

        # This field was excluded
        self.assertEqual("scan-12345", output_data["scan"]["id"])

        # This field was included for auto-detection
        self.assertIn("HOSTNAME", output_data["scan"]["target"])
        self.assertNotIn("server-01.example.com", output_data["scan"]["target"])
        
        # Clean up the single output file
        os.remove(output_file_path)

if __name__ == "__main__":
    unittest.main()

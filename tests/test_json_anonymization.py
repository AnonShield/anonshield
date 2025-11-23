import unittest
import os
import json
import sys
from unittest.mock import patch
from anon import main

class TestJsonAnonymization(unittest.TestCase):
    def setUp(self):
        self.test_array_file = "tests/test_data_pytest/test_array.json"
        self.test_jsonl_file = "tests/test_data_pytest/test.jsonl"
        self.config_file = "tests/test_data_pytest/anonymization_config.json"
        self.output_dir = "output"
        os.makedirs(self.output_dir, exist_ok=True)

    def tearDown(self):
        # Clean up output files
        for f in os.listdir(self.output_dir):
            os.remove(os.path.join(self.output_dir, f))

    def test_anonymize_json_array_with_config(self):
        test_args = ["anon.py", self.test_array_file, "--anonymization-config", self.config_file]
        with patch.object(sys, 'argv', test_args):
            main()
        
        output_file = os.path.join(self.output_dir, "anon_test_array.json")
        self.assertTrue(os.path.exists(output_file))
        with open(output_file, "r") as f:
            data = json.load(f)
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 2)
            self.assertIn("PERSON", data[0]["name"])
            self.assertIn("EMAIL_ADDRESS", data[0]["email"])
            self.assertIn("PERSON", data[1]["name"])
            self.assertIn("EMAIL_ADDRESS", data[1]["email"])

    def test_anonymize_jsonl_with_config(self):
        test_args = ["anon.py", self.test_jsonl_file, "--anonymization-config", self.config_file]
        with patch.object(sys, 'argv', test_args):
            main()

        output_file = os.path.join(self.output_dir, "anon_test.jsonl")
        self.assertTrue(os.path.exists(output_file))
        with open(output_file, "r") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 2)
            data1 = json.loads(lines[0])
            data2 = json.loads(lines[1])
            self.assertIn("PERSON", data1["name"])
            self.assertIn("EMAIL_ADDRESS", data1["email"])
            self.assertIn("PERSON", data2["name"])
            self.assertIn("EMAIL_ADDRESS", data2["email"])

if __name__ == "__main__":
    unittest.main()

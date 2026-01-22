import unittest
import os
import subprocess
import shutil
import json

class TestNerGeneration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_data_dir = "tests/test_data_ner"
        cls.output_dir = "test_output_ner"

        for d in [cls.test_data_dir, cls.output_dir]:
            if os.path.exists(d):
                shutil.rmtree(d)
            os.makedirs(d, exist_ok=True)

        cls.original_text = "My name is John Doe and I live in New York."
        cls.test_file = os.path.join(cls.test_data_dir, "test.txt")
        with open(cls.test_file, "w") as f:
            f.write(cls.original_text)

    @classmethod
    def tearDownClass(cls):
        for d in [cls.test_data_dir, cls.output_dir]:
            if os.path.exists(d):
                shutil.rmtree(d)

    def test_ner_data_generation(self):
        cmd = [
            "python", os.path.join(os.getcwd(), "anon.py"),
            self.test_file,
            "--generate-ner-data",
            "--output-dir", self.output_dir,
            "--overwrite"
        ]
        env = os.environ.copy()
        current_dir = os.getcwd()
        env["PYTHONPATH"] = current_dir + os.pathsep + env.get("PYTHONPATH", "")
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=os.getcwd())

        if result.returncode != 0:
            print("NER generation run failed:")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)

        self.assertEqual(result.returncode, 0)

        output_file = os.path.join(self.output_dir, "ner_data_anon_test.jsonl")
        self.assertTrue(os.path.exists(output_file))

        with open(output_file, "r") as f:
            lines = f.readlines()
        
        self.assertGreater(len(lines), 0, "NER output file is empty.")

        data = json.loads(lines[0])

        # Verify Doccano-compatible format
        self.assertIn("id", data, "Missing 'id' field for Doccano compatibility.")
        self.assertIn("text", data)
        self.assertIn("label", data)
        self.assertEqual(data["id"], 0, "First document should have id=0.")
        self.assertEqual(data["text"], self.original_text)
        
        labels = data["label"]
        self.assertGreater(len(labels), 0, "No labels found in NER output.")
        
        found_person = False
        found_location = False
        for start, end, entity_type in labels:
            if entity_type == "PERSON" and data["text"][start:end] == "John Doe":
                found_person = True
            if entity_type == "LOCATION" and data["text"][start:end] == "New York":
                found_location = True
        
        self.assertTrue(found_person, "PERSON 'John Doe' not found in labels.")
        self.assertTrue(found_location, "LOCATION 'New York' not found in labels.")

    def test_ner_data_generation_with_force_anonymize(self):
        """Test that force_anonymize in anonymization_config adds forced labels."""
        # Create a JSON test file
        json_data = {"user": {"name": "Alice", "phone": "555-1234"}}
        json_file = os.path.join(self.test_data_dir, "test_force.json")
        with open(json_file, "w") as f:
            json.dump(json_data, f)

        # Create anonymization config with force_anonymize
        config = {
            "force_anonymize": {
                "user.phone": {"entity_type": "PHONE_NUMBER"}
            }
        }
        config_file = os.path.join(self.test_data_dir, "config.json")
        with open(config_file, "w") as f:
            json.dump(config, f)

        cmd = [
            "python", os.path.join(os.getcwd(), "anon.py"),
            json_file,
            "--generate-ner-data",
            "--output-dir", self.output_dir,
            "--overwrite",
            "--anonymization-config", config_file
        ]
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd() + os.pathsep + env.get("PYTHONPATH", "")
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=os.getcwd())

        if result.returncode != 0:
            print("NER generation with force_anonymize failed:")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)

        self.assertEqual(result.returncode, 0)

        output_file = os.path.join(self.output_dir, "ner_data_anon_test_force.jsonl")
        self.assertTrue(os.path.exists(output_file), f"Output file not found: {output_file}")

        with open(output_file, "r") as f:
            lines = f.readlines()

        self.assertGreater(len(lines), 0, "NER output file is empty.")

        # Find the record with the phone number
        found_forced_phone = False
        for line in lines:
            data = json.loads(line)
            if data["text"] == "555-1234":
                for start, end, entity_type in data.get("label", []):
                    if entity_type == "PHONE_NUMBER" and start == 0 and end == len("555-1234"):
                        found_forced_phone = True
                        break

        self.assertTrue(found_forced_phone, "Forced PHONE_NUMBER label not found for '555-1234'.")


if __name__ == "__main__":
    unittest.main()

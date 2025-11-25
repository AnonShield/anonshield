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

        self.assertIn("text", data)
        self.assertIn("label", data)
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

if __name__ == "__main__":
    unittest.main()

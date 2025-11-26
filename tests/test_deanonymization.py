import unittest
import os
import subprocess
import shutil
import re

class TestDeanonymization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_data_dir = "tests/test_data_deanonymization"
        cls.output_dir = "test_output_deanonymization"
        cls.db_dir = "db_pytest_deanonymization"
        
        for d in [cls.test_data_dir, cls.output_dir, cls.db_dir]:
            if os.path.exists(d):
                shutil.rmtree(d)
            os.makedirs(d, exist_ok=True)

        cls.original_name = "John Doe"
        cls.original_email = "john.doe@example.com"
        text = f"My name is {cls.original_name} and my email is {cls.original_email}."
        
        cls.test_file = os.path.join(cls.test_data_dir, "test.txt")
        with open(cls.test_file, "w") as f:
            f.write(text)

        os.environ["ANON_SECRET_KEY"] = "test-secret-key-deanonymization"

        # Run anonymization to populate the database
        cmd = [
            "python", os.path.join(os.getcwd(), "anon.py"),
            cls.test_file,
            "--db-dir", cls.db_dir,
            "--output-dir", cls.output_dir,
            "--overwrite"
        ]
        env = os.environ.copy()
        current_dir = os.getcwd()
        env["PYTHONPATH"] = current_dir + os.pathsep + env.get("PYTHONPATH", "")
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=os.getcwd())
        if result.returncode != 0:
            print("Anonymization pre-run failed:")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)


    @classmethod
    def tearDownClass(cls):
        for d in [cls.test_data_dir, cls.output_dir, cls.db_dir]:
            if os.path.exists(d):
                shutil.rmtree(d)

    def _run_deanonymize_py(self, slug):
        cmd = [
            "python", os.path.join(os.getcwd(), "scripts/deanonymize.py"),
            slug,
            "--db-dir", self.db_dir
        ]
        env = os.environ.copy()
        current_dir = os.getcwd()
        env["PYTHONPATH"] = current_dir + os.pathsep + env.get("PYTHONPATH", "")
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=os.getcwd())
        return result.stdout.strip()

    def test_deanonymization(self):
        output_file = os.path.join(self.output_dir, "anon_test.txt")
        self.assertTrue(os.path.exists(output_file))

        with open(output_file, "r") as f:
            content = f.read()

        matches = re.findall(r"(\[([A-Z_]+)_[a-f0-9]+\])", content)
        self.assertGreaterEqual(len(matches), 2, "Expected at least two anonymized slugs.")

        slug_map = {entity_type: slug for slug, entity_type in matches}
        
        self.assertIn("PERSON", slug_map)
        self.assertIn("EMAIL_ADDRESS", slug_map)

        person_slug = slug_map["PERSON"]
        email_slug = slug_map["EMAIL_ADDRESS"]

        deanonymized_name_output = self._run_deanonymize_py(person_slug)
        self.assertIn(self.original_name, deanonymized_name_output)

        deanonymized_email_output = self._run_deanonymize_py(email_slug)
        self.assertIn(self.original_email, deanonymized_email_output)

if __name__ == "__main__":
    unittest.main()

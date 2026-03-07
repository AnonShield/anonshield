import unittest
import os
import shutil
from src.anon.processors import get_output_path

class TestSecurity(unittest.TestCase):

    def setUp(self):
        self.project_dir = os.path.realpath(os.getcwd())
        self.output_dir = os.path.join(self.project_dir, "test_output_dir")
        os.makedirs(self.output_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

    def test_path_traversal_in_filename(self):
        """Tests if a malicious original_path (filename part) can cause traversal."""
        # os.path.basename should handle this, but we test for completeness.
        malicious_path = "../../../etc/passwd"
        # The current implementation should handle this safely by taking the basename 'passwd'.
        # A truly robust implementation should probably reject this path earlier,
        # but for get_output_path, the goal is to not write outside the output_dir.
        try:
            output_path = get_output_path(malicious_path, ".txt", output_dir=self.output_dir)
            real_output_path = os.path.realpath(output_path)
            self.assertTrue(real_output_path.startswith(self.output_dir + os.sep))
        except ValueError:
            self.fail("get_output_path() raised ValueError on a basename-sanitizable path.")

    def test_legitimate_path(self):
        """Tests that a legitimate file path is handled correctly."""
        legitimate_path = "my_safe_file.txt"
        
        try:
            output_path = get_output_path(legitimate_path, ".txt", output_dir=self.output_dir)
            real_output_path = os.path.realpath(output_path)
            self.assertTrue(real_output_path.startswith(self.output_dir + os.sep))
        except ValueError:
            self.fail("get_output_path() raised ValueError unexpectedly for a safe path.")

    def test_invalid_filename(self):
        """Tests that obviously invalid filenames are rejected."""
        with self.assertRaises(ValueError):
            get_output_path("..", ".txt", output_dir=self.output_dir)
        
        with self.assertRaises(ValueError):
            get_output_path(".", ".txt", output_dir=self.output_dir)

if __name__ == '__main__':
    unittest.main()
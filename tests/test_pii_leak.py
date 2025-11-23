import unittest
from unittest.mock import patch, MagicMock
import os
import shutil
from src.anon.processors import TextFileProcessor
from src.anon.engine import AnonymizationOrchestrator

class TestPiiLeak(unittest.TestCase):

    def setUp(self):
        self.output_dir = "test_pii_leak_output"
        self.test_data_dir = "test_pii_leak_data"
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.test_data_dir, exist_ok=True)
        self.test_file = os.path.join(self.test_data_dir, "test.txt")
        with open(self.test_file, "w") as f:
            f.write("line 1\nline 2\nline 3")

    def tearDown(self):
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        if os.path.exists(self.test_data_dir):
            shutil.rmtree(self.test_data_dir)

    @patch('src.anon.processors.AnonymizationOrchestrator')
    def test_pii_leak_prevention(self, MockOrchestrator):
        # Configure the mock orchestrator
        mock_orchestrator_instance = MockOrchestrator.return_value
        
        # This is the crucial part: make anonymize_texts return a list of a different size
        mock_orchestrator_instance.anonymize_texts.return_value = ["anonymized_line_1"] # Original has 3 lines

        # Instantiate the processor with the mock
        processor = TextFileProcessor(
            self.test_file,
            mock_orchestrator_instance,
            output_dir=self.output_dir
        )
        
        # Assert that a RuntimeError is raised
        with self.assertRaises(RuntimeError) as context:
            processor.process()
        
        self.assertIn("Anonymization failed to prevent data leak", str(context.exception))

if __name__ == '__main__':
    unittest.main()

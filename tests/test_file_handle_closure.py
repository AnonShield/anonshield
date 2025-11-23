import unittest
import os
import shutil
from unittest.mock import MagicMock, patch
from src.anon.processors import TextFileProcessor
from src.anon.engine import AnonymizationOrchestrator # Import the actual class

class TestFileHandleClosure(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_data_dir = "test_file_handle_data"
        os.makedirs(cls.test_data_dir, exist_ok=True)
        cls.test_file = os.path.join(cls.test_data_dir, "test.txt")
        with open(cls.test_file, "w") as f:
            f.write("line 1\nline 2\nline 3")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_data_dir):
            shutil.rmtree(cls.test_data_dir)

    def setUp(self):
        self.output_dir = "test_file_handle_output"
        # Ensure output_dir is clean for each test method
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Mock the AnonymizationOrchestrator
        self.mock_orchestrator = MagicMock(spec=AnonymizationOrchestrator)
        self.mock_orchestrator.detect_entities.return_value = [] # Avoid actual NER processing
        self.mock_orchestrator.anonymize_texts.return_value = ["anon 1", "anon 2", "anon 3"] # For non-NER mode

    def tearDown(self):
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

    def test_ner_file_handle_closed_on_success(self):
        processor = TextFileProcessor(
            self.test_file,
            self.mock_orchestrator,
            ner_data_generation=True,
            output_dir=self.output_dir
        )
        
        self.assertIsNone(processor.ner_file_handle) # Should be None initially

        processor.process() 
        
        # Assert that the handle was opened and then closed
        self.assertIsNotNone(processor.ner_file_handle)
        self.assertTrue(processor.ner_file_handle.closed)

    @patch('src.anon.processors.os.makedirs', side_effect=OSError("Disk full"))
    def test_ner_file_handle_not_opened_on_makedirs_exception(self, mock_makedirs):
        processor = TextFileProcessor(
            self.test_file,
            self.mock_orchestrator,
            ner_data_generation=True,
            output_dir=self.output_dir
        )
        
        with self.assertRaises(OSError):
            processor.process()
            
        # File handle should never have been opened
        self.assertIsNone(processor.ner_file_handle) 

    def test_ner_file_handle_closed_on_process_exception(self):
        # Simulate an exception during _run_ner_pipeline
        self.mock_orchestrator.detect_entities.side_effect = Exception("NER pipeline error")

        processor = TextFileProcessor(
            self.test_file,
            self.mock_orchestrator,
            ner_data_generation=True,
            output_dir=self.output_dir
        )
        
        self.assertIsNone(processor.ner_file_handle) # Should be None initially

        # We expect process() to raise an Exception due to detect_entities.side_effect
        with self.assertRaises(Exception):
            processor.process()
        
        # Assert that the handle was opened and then closed
        self.assertIsNotNone(processor.ner_file_handle)
        self.assertTrue(processor.ner_file_handle.closed)

if __name__ == '__main__':
    unittest.main()
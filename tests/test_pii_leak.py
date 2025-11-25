import unittest
from unittest.mock import patch
import os
import shutil
import logging
from src.anon.processors import TextFileProcessor
from src.anon.engine import AnonymizationOrchestrator

class TestPiiLeak(unittest.TestCase):

    def setUp(self):
        self.output_dir = "test_pii_leak_output"
        self.test_data_dir = "test_pii_leak_data"
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.test_data_dir, exist_ok=True)
        self.test_file = os.path.join(self.test_data_dir, "test.txt")
        self.input_lines = ["line 1", "line 2", "line 3"]
        with open(self.test_file, "w") as f:
            f.write("\n".join(self.input_lines))
        
        # The secret key is required to instantiate the real orchestrator
        os.environ["ANON_SECRET_KEY"] = "test-secret"

    def tearDown(self):
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        if os.path.exists(self.test_data_dir):
            shutil.rmtree(self.test_data_dir)
        if "ANON_SECRET_KEY" in os.environ:
            del os.environ["ANON_SECRET_KEY"]

    @patch('src.anon.strategies.PresidioStrategy.anonymize')
    def test_fallback_strategy_prevents_pii_leak_error(self, mock_anonymize_strategy):
        """
        Tests that the fallback strategy prevents the PII leak RuntimeError
        by gracefully handling batch mismatches.
        """
        # Configure the mock for the strategy's anonymize method to return a list of the wrong size.
        # This simulates a failure inside the batch processor.
        mock_anonymize_strategy.return_value = (["mocked_anonymized_line"], [])

        # Instantiate a REAL orchestrator. The fallback logic we want to test is inside it.
        # The orchestrator will use the default 'presidio' strategy, which we have mocked.
        orchestrator = AnonymizationOrchestrator(
            lang="en",
            db_context=None,
            allow_list=[],
            entities_to_preserve=[]
            # Other dependencies will be created with defaults inside the orchestrator,
            # which is fine because our mock intercepts the call before they are used.
        )

        processor = TextFileProcessor(
            self.test_file,
            orchestrator,
            output_dir=self.output_dir
        )
        
        # The main assertion: The process should NOT raise a RuntimeError anymore.
        # It should complete successfully.
        try:
            output_path = processor.process()
            self.assertTrue(os.path.exists(output_path))
        except RuntimeError:
            self.fail("RuntimeError was raised, but the fallback strategy should have prevented it.")

        # Verify the output. The fallback re-processes item by item. Inside the loop, it calls
        # the strategy again. Our mock will be called for each item.
        with open(output_path, "r") as f:
            output_lines = f.read().splitlines()
        
        # The key check: Did we get the same number of lines back?
        self.assertEqual(len(output_lines), len(self.input_lines))
        
        # Check content. The fallback calls the strategy for each of the 3 lines.
        # The mock returns ["mocked_anonymized_line"] each time. The fallback takes the first element.
        self.assertEqual(output_lines[0], "mocked_anonymized_line")
        self.assertEqual(output_lines[1], "mocked_anonymized_line")
        self.assertEqual(output_lines[2], "mocked_anonymized_line")


if __name__ == '__main__':
    unittest.main()
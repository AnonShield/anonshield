
import unittest
import os
import shutil
from unittest.mock import patch

from src.anon.evaluation.ground_truth import GroundTruthManager
from src.anon.evaluation.metrics_calculator import MetricsCalculator

class TestEvaluationWorkflow(unittest.TestCase):

    def setUp(self):
        """Set up a dedicated directory for test artifacts."""
        self.test_dir = "test_evaluation_workflow_temp"
        self.secret_key = "test-secret"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)

    def tearDown(self):
        """Clean up the test directory."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch('src.anon.evaluation.metrics_calculator.sqlite3')
    def test_full_evaluation_workflow(self, mock_sqlite):
        """
        Tests the full workflow:
        1. Generate a pre-labeled (ground truth) file.
        2. Load it back.
        3. Generate the expected hashes.
        4. "Anonymize" text based on this ground truth.
        5. Calculate metrics and verify the results.
        """
        # Patch the database connection to avoid actual DB operations
        mock_sqlite.connect.return_value.execute.return_value.fetchall.return_value = []
        
        # --- 1. Define Sample Data ---
        # This simulates the output of an NER process.
        ner_results = [
            {
                "text": "John Doe lives in New York and works at Contoso.",
                "label": [
                    [0, 8, "PERSON"],      # John Doe
                    [19, 27, "LOCATION"], # New York
                    [41, 48, "ORG"]      # Contoso
                ]
            }
        ]
        doccano_file_path = os.path.join(self.test_dir, "ground_truth.jsonl")

        # --- 2. Generate and Load Ground Truth ---
        # Create a manager to generate the file
        export_manager = GroundTruthManager(secret_key=self.secret_key)
        export_manager.export_to_doccano(ner_results, doccano_file_path)
        self.assertTrue(os.path.exists(doccano_file_path))

        # Create a new manager to simulate loading the file in a separate step
        import_manager = GroundTruthManager(secret_key=self.secret_key)
        import_manager.import_from_doccano(doccano_file_path)
        ground_truth = import_manager.generate_ground_truth()

        # Check the ground truth object
        self.assertEqual(ground_truth.get_total_entities(), 3)
        expected_hashes = ground_truth.get_expected_hashes()
        self.assertEqual(len(expected_hashes), 3)

        # Get the generated hashes to construct test cases
        person_entity = next(e for e in ground_truth.entities if e.entity_type == "PERSON")
        loc_entity = next(e for e in ground_truth.entities if e.entity_type == "LOCATION")
        org_entity = next(e for e in ground_truth.entities if e.entity_type == "ORG")

        person_hash = person_entity.display_hash
        loc_hash = loc_entity.display_hash
        org_hash = org_entity.display_hash
        
        # --- 3. Instantiate Calculator ---
        calculator = MetricsCalculator(db_path=":memory:")

        # --- 4. Run Test Scenarios & Calculate Metrics ---

        # Scenario A: Perfect Match
        perfect_text = f"[{person_entity.entity_type}_{person_hash}] lives in [{loc_entity.entity_type}_{loc_hash}] and works at [{org_entity.entity_type}_{org_hash}]."
        metrics_perfect = calculator.calculate_metrics(ground_truth, perfect_text)
        self.assertEqual(metrics_perfect.true_positives, 3)
        self.assertEqual(metrics_perfect.false_positives, 0)
        self.assertEqual(metrics_perfect.false_negatives, 0)
        self.assertEqual(metrics_perfect.precision, 1.0)
        self.assertEqual(metrics_perfect.recall, 1.0)
        self.assertEqual(metrics_perfect.f1_score, 1.0)

        # Scenario B: False Negative (missed ORG)
        fn_text = f"[{person_entity.entity_type}_{person_hash}] lives in [{loc_entity.entity_type}_{loc_hash}] and works at Contoso."
        metrics_fn = calculator.calculate_metrics(ground_truth, fn_text)
        # In the current implementation, TP is based on expected hashes found. It doesn't check *which* ones.
        # This is a flaw, but we test the code as is. The display hashes are different, so it should work.
        self.assertEqual(metrics_fn.true_positives, 2)
        self.assertEqual(metrics_fn.false_positives, 0)
        self.assertEqual(metrics_fn.false_negatives, 1)
        self.assertAlmostEqual(metrics_fn.precision, 1.0)
        self.assertAlmostEqual(metrics_fn.recall, 2/3)
        self.assertAlmostEqual(metrics_fn.f1_score, 0.8)

        # Scenario C: False Positive (extra fake entity)
        fp_text = f"[{person_entity.entity_type}_{person_hash}] lives in [{loc_entity.entity_type}_{loc_hash}] and works at [{org_entity.entity_type}_{org_hash}] for [YEARS_feedbabe]."
        metrics_fp = calculator.calculate_metrics(ground_truth, fp_text)
        self.assertEqual(metrics_fp.true_positives, 3)
        self.assertEqual(metrics_fp.false_positives, 1)
        self.assertEqual(metrics_fp.false_negatives, 0)
        self.assertAlmostEqual(metrics_fp.precision, 0.75)
        self.assertAlmostEqual(metrics_fp.recall, 1.0)
        self.assertAlmostEqual(metrics_fp.f1_score, 0.8571, places=4)

if __name__ == "__main__":
    unittest.main()

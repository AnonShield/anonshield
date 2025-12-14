
import unittest
from unittest.mock import patch
from src.anon.evaluation.metrics_calculator import MetricsCalculator, EvaluationMetrics
from src.anon.evaluation.ground_truth import GroundTruth, GroundTruthEntity

class TestMetricsCalculator(unittest.TestCase):

    @patch('src.anon.evaluation.metrics_calculator.sqlite3')
    def setUp(self, mock_sqlite):
        """Set up a new MetricsCalculator instance before each test."""
        mock_sqlite.connect.return_value.execute.return_value.fetchall.return_value = []
        self.calculator = MetricsCalculator(db_path=":memory:")

    def test_perfect_match(self):
        """Tests metrics when anonymized output perfectly matches ground truth."""
        ground_truth = GroundTruth()
        # Using valid hex strings for hashes
        hash1 = "deadbeef01"
        hash2 = "badc0ffee2"
        ground_truth.add_entity("John Doe", "PERSON", hash1, hash1, 1, 0, 8)
        ground_truth.add_entity("New York", "LOCATION", hash2, hash2, 1, 20, 28)
        ground_truth.hash_to_entity = {hash1: ground_truth.entities[0], hash2: ground_truth.entities[1]}
        
        anonymized_text = f"My name is [PERSON_{hash1}] and I live in [LOCATION_{hash2}]."
        
        metrics = self.calculator.calculate_metrics(ground_truth, anonymized_text)

        self.assertEqual(metrics.true_positives, 2)
        self.assertEqual(metrics.false_positives, 0)
        self.assertEqual(metrics.false_negatives, 0)
        self.assertEqual(metrics.precision, 1.0)
        self.assertEqual(metrics.recall, 1.0)
        self.assertEqual(metrics.f1_score, 1.0)

    def test_with_false_positives(self):
        """Tests metrics with an extra, unexpected entity in the output."""
        ground_truth = GroundTruth()
        hash1 = "deadbeef01"
        ground_truth.add_entity("John Doe", "PERSON", hash1, hash1, 1, 0, 8)
        ground_truth.hash_to_entity = {hash1: ground_truth.entities[0]}

        false_positive_hash = "feedbabe"
        anonymized_text = f"This is [PERSON_{hash1}] and also [LOCATION_{false_positive_hash}]."
        
        metrics = self.calculator.calculate_metrics(ground_truth, anonymized_text)

        self.assertEqual(metrics.true_positives, 1)
        self.assertEqual(metrics.false_positives, 1)
        self.assertEqual(metrics.false_negatives, 0)
        self.assertAlmostEqual(metrics.precision, 0.5)
        self.assertAlmostEqual(metrics.recall, 1.0)
        self.assertAlmostEqual(metrics.f1_score, 2/3)

    def test_with_false_negatives(self):
        """Tests metrics with a missed entity in the output."""
        ground_truth = GroundTruth()
        hash1 = "deadbeef01"
        hash2 = "badc0ffee2"
        ground_truth.add_entity("John Doe", "PERSON", hash1, hash1, 1, 0, 8)
        ground_truth.add_entity("New York", "LOCATION", hash2, hash2, 1, 20, 28)
        ground_truth.hash_to_entity = {hash1: ground_truth.entities[0], hash2: ground_truth.entities[1]}

        anonymized_text = f"This is [PERSON_{hash1}] but New York was missed."

        metrics = self.calculator.calculate_metrics(ground_truth, anonymized_text)

        self.assertEqual(metrics.true_positives, 1)
        self.assertEqual(metrics.false_positives, 0)
        self.assertEqual(metrics.false_negatives, 1)
        self.assertAlmostEqual(metrics.precision, 1.0)
        self.assertAlmostEqual(metrics.recall, 0.5)
        self.assertAlmostEqual(metrics.f1_score, 2/3)

    def test_empty_ground_truth(self):
        """Tests metrics when the ground truth is empty but the output has entities."""
        ground_truth = GroundTruth() # Empty
        anonymized_text = f"This is a [LOCATION_feedbabe]."
        
        metrics = self.calculator.calculate_metrics(ground_truth, anonymized_text)

        self.assertEqual(metrics.true_positives, 0)
        self.assertEqual(metrics.false_positives, 1)
        self.assertEqual(metrics.false_negatives, 0)
        self.assertEqual(metrics.precision, 0.0)
        self.assertEqual(metrics.recall, 0.0)
        self.assertEqual(metrics.f1_score, 0.0)

    def test_empty_anonymized_text(self):
        """Tests metrics when the output is empty but ground truth expects entities."""
        ground_truth = GroundTruth()
        hash1 = "deadbeef01"
        ground_truth.add_entity("John Doe", "PERSON", hash1, hash1, 1, 0, 8)
        ground_truth.hash_to_entity = {hash1: ground_truth.entities[0]}

        anonymized_text = "This text has no anonymized entities."
        
        metrics = self.calculator.calculate_metrics(ground_truth, anonymized_text)

        self.assertEqual(metrics.true_positives, 0)
        self.assertEqual(metrics.false_positives, 0)
        self.assertEqual(metrics.false_negatives, 1)
        self.assertEqual(metrics.precision, 0.0)
        self.assertEqual(metrics.recall, 0.0)
        self.assertEqual(metrics.f1_score, 0.0)
        
    def test_no_entities_found(self):
        """Tests metrics when both ground truth and output are empty."""
        ground_truth = GroundTruth()
        anonymized_text = "This is a plain text."
        
        metrics = self.calculator.calculate_metrics(ground_truth, anonymized_text)
        
        self.assertEqual(metrics.true_positives, 0)
        self.assertEqual(metrics.false_positives, 0)
        self.assertEqual(metrics.false_negatives, .0)
        self.assertEqual(metrics.precision, 0.0)
        self.assertEqual(metrics.recall, 0.0)
        self.assertEqual(metrics.f1_score, 0.0)

if __name__ == "__main__":
    unittest.main()

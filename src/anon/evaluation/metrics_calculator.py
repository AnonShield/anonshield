from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
import logging
import json
import hashlib
import hmac
from pathlib import Path
from collections import defaultdict, Counter
import sqlite3
from datetime import datetime

# Local imports for metrics_calculator
from .ground_truth import GroundTruth
from .hash_tracker import HashTracker

# ============================================================================
# Metrics Calculation
# ============================================================================

@dataclass
class EvaluationMetrics:
    """
    Complete evaluation metrics for anonymization quality.
    
    Attributes:
        true_positives: Correctly anonymized entities
        false_positives: Incorrectly anonymized (over-anonymization)
        false_negatives: Missed entities (under-anonymization)
        precision: TP / (TP + FP)
        recall: TP / (TP + FN)
        f1_score: 2 * (precision * recall) / (precision + recall)
    """
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    
    def calculate(self):
        """Calculate precision, recall, and F1 score."""
        # Precision: TP / (TP + FP)
        if self.true_positives + self.false_positives > 0:
            self.precision = self.true_positives / (self.true_positives + self.false_positives)
        else:
            self.precision = 0.0
        
        # Recall: TP / (TP + FN)
        if self.true_positives + self.false_negatives > 0:
            self.recall = self.true_positives / (self.true_positives + self.false_negatives)
        else:
            self.recall = 0.0
        
        # F1 Score: 2 * (precision * recall) / (precision + recall)
        if self.precision + self.recall > 0:
            self.f1_score = 2 * (self.precision * self.recall) / (self.precision + self.recall)
        else:
            self.f1_score = 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4)
        }
    
    def __str__(self) -> str:
        """Pretty print metrics."""
        return (
            f"Precision: {self.precision:.2%} | "
            f"Recall: {self.recall:.2%} | "
            f"F1 Score: {self.f1_score:.2%}"
        )


class MetricsCalculator:
    """
    Calculates evaluation metrics by comparing anonymized output with ground truth.
    
    This is the core evaluation engine that determines quality.
    """
    
    def __init__(self, db_path: str = "db/entities.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__class__.__name__)
    
    def _get_anonymized_entities(self) -> List[Tuple[str, str, str, str]]:
        """
        Retrieve all anonymized entities from the database.
        
        Returns:
            List of (entity_type, original_name, slug_name, full_hash)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(
                "SELECT entity_type, original_name, slug_name, full_hash FROM entities"
            )
            results = cursor.fetchall()
            conn.close()
            return results
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {e}")
            return []
    
    def calculate_metrics(
        self,
        ground_truth: GroundTruth,
        anonymized_text: str
    ) -> EvaluationMetrics:
        """
        Calculate metrics by comparing anonymized output with ground truth.
        
        Args:
            ground_truth: The gold standard
            anonymized_text: The output to evaluate
        
        Returns:
            EvaluationMetrics with TP, FP, FN, and scores
        """
        metrics = EvaluationMetrics()
        
        # Count hashes in anonymized text
        tracker = HashTracker()
        actual_counts = tracker.count_hashes(anonymized_text)
        
        # Get expected display hashes to match what the tracker finds
        expected_hashes = ground_truth.get_expected_display_hashes()
        
        # Get anonymized entities from database
        db_entities = self._get_anonymized_entities()
        db_hashes = {full_hash for _, _, _, full_hash in db_entities}
        
        # Calculate True Positives: hashes that should be there and are there
        for hash_value in expected_hashes:
            if hash_value in actual_counts:
                metrics.true_positives += 1
        
        # Calculate False Negatives: hashes that should be there but aren't
        metrics.false_negatives = len(expected_hashes - set(actual_counts.keys()))
        
        # Calculate False Positives: hashes that appear but shouldn't
        # These are hashes in the output but not in ground truth
        unexpected_hashes = set(actual_counts.keys()) - expected_hashes
        metrics.false_positives = len(unexpected_hashes)
        
        # Calculate scores
        metrics.calculate()
        
        return metrics
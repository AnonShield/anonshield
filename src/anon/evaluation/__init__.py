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

# Import local modules
from .ground_truth import GroundTruthManager, GroundTruth
from .hash_tracker import HashTracker
from .metrics_calculator import MetricsCalculator, EvaluationMetrics


# ============================================================================
# Complete Evaluation Pipeline
# ============================================================================

class EvaluationPipeline:
    """
    Orchestrates the complete evaluation workflow.
    
    Usage:
        pipeline = EvaluationPipeline(
            secret_key="your-secret-key",
            db_path="db/entities.db"
        )
        
        # Step 1: Prepare ground truth (one-time)
        pipeline.prepare_ground_truth(
            ner_file="data/ner_output.jsonl",
            doccano_export="ground_truth_for_labeling.jsonl"
        )
        
        # Manual: Label in Doccano, export as "ground_truth_corrected.jsonl"
        
        # Step 2: Generate ground truth
        pipeline.generate_ground_truth("ground_truth_corrected.jsonl")
        
        # Step 3: Evaluate anonymization
        metrics = pipeline.evaluate_anonymization(
            anonymized_file="output/anon_file.txt",
            ground_truth_file="ground_truth.json"
        )
        
        print(metrics)
    """
    
    def __init__(self, secret_key: str, db_path: str = "db/entities.db"):
        self.secret_key = secret_key
        self.db_path = db_path
        self.gt_manager = GroundTruthManager(secret_key)
        self.metrics_calc = MetricsCalculator(db_path)
        self.logger = logging.getLogger(__class__.__name__)
    
    def prepare_ground_truth(
        self,
        ner_file: str | Path,
        doccano_export: str | Path
    ):
        """
        Step 1: Convert NER output to Doccano format for labeling.
        
        Args:
            ner_file: Path to NER output (JSONL with {"text": ..., "label": [...]})
            doccano_export: Path to save Doccano format
        """
        # Load NER data
        ner_results = []
        with open(ner_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    ner_results.append(json.loads(line))
        
        # Export to Doccano
        self.gt_manager.export_to_doccano(ner_results, doccano_export)
    
    def generate_ground_truth(
        self,
        doccano_corrected: str | Path,
        output_file: Optional[str | Path] = None
    ) -> GroundTruth:
        """
        Step 2: Generate ground truth from corrected Doccano file.
        
        Args:
            doccano_corrected: Path to Doccano file after human correction
            output_file: Optional path to save ground truth JSON
        
        Returns:
            GroundTruth object
        """
        # Import corrected labels
        self.gt_manager.import_from_doccano(doccano_corrected)
        
        # Generate ground truth with hashes
        ground_truth = self.gt_manager.generate_ground_truth()
        
        # Save if requested
        if output_file:
            ground_truth.save(output_file)
        
        self.logger.info(f"Ground truth generated with {ground_truth.get_total_entities()} entities")
        return ground_truth
    
    def evaluate_anonymization(
        self,
        anonymized_file: str | Path,
        ground_truth_file: str | Path,
        output_report: Optional[str | Path] = None
    ) -> EvaluationMetrics:
        """
        Step 3: Evaluate anonymization quality.
        
        Args:
            anonymized_file: Path to anonymized output
            ground_truth_file: Path to ground truth JSON
            output_report: Optional path to save detailed report
        
        Returns:
            EvaluationMetrics
        """
        # Load ground truth
        ground_truth = GroundTruth.load(ground_truth_file)
        
        # Load anonymized text
        with open(anonymized_file, 'r', encoding='utf-8') as f:
            anonymized_text = f.read()
        
        # Calculate metrics
        metrics = self.metrics_calc.calculate_metrics(ground_truth, anonymized_text)
        
        # Generate report if requested
        if output_report:
            self._generate_report(metrics, ground_truth, anonymized_text, output_report)
        
        return metrics
    
    def _generate_report(
        self,
        metrics: EvaluationMetrics,
        ground_truth: GroundTruth,
        anonymized_text: str,
        output_path: str | Path
    ):
        """Generate detailed evaluation report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics.to_dict(),
            "ground_truth_summary": {
                "total_entities": ground_truth.get_total_entities(),
                "expected_hashes": len(ground_truth.get_expected_hashes())
            },
            "anonymized_text_summary": {
                "length": len(anonymized_text),
                "hash_count": len(HashTracker().count_hashes(anonymized_text))
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Evaluation report saved to {output_path}")

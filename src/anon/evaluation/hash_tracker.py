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


# ============================================================================
# Hash Tracking and Validation
# ============================================================================

class HashTracker:
    """
    Tracks hash occurrences in anonymized output.
    
    Compares actual hash counts against expected counts from ground truth.
    """
    
    def __init__(self):
        self.hash_counts: Counter = Counter()
        self.logger = logging.getLogger(__class__.__name__)
    
    def count_hashes(self, anonymized_text: str) -> Dict[str, int]:
        """
        Count all hash occurrences in anonymized text.
        
        Looks for patterns like [TYPE_hash123]
        """
        import re
        
        # Pattern: [ENTITY_TYPE_hash]
        pattern = r'\[([A-Z_]+)_([a-f0-9]+)\]'
        
        hash_counts = Counter()
        
        for match in re.finditer(pattern, anonymized_text):
            entity_type = match.group(1)
            hash_value = match.group(2)
            hash_counts[hash_value] += 1
        
        self.hash_counts = hash_counts
        return dict(hash_counts)
    
    def compare_with_expected(
        self,
        expected_counts: Dict[str, int]
    ) -> Tuple[Dict[str, int], Dict[str, int], Dict[str, int]]:
        """
        Compare actual counts with expected counts.
        
        Returns:
            Tuple of (correct_counts, over_counts, under_counts)
        """
        correct = {}
        over = {}
        under = {}
        
        all_hashes = set(expected_counts.keys()) | set(self.hash_counts.keys())
        
        for hash_value in all_hashes:
            expected = expected_counts.get(hash_value, 0)
            actual = self.hash_counts.get(hash_value, 0)
            
            if expected == actual:
                correct[hash_value] = actual
            elif actual > expected:
                over[hash_value] = actual - expected
            else:  # actual < expected
                under[hash_value] = expected - actual
        
        return correct, over, under
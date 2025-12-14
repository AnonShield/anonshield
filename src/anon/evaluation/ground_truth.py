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
# Ground Truth Management
# ============================================================================

@dataclass
class DoccanoLabel:
    """Represents a single labeled entity in Doccano format."""
    id: int
    start: int
    end: int
    label: str
    text: str  # Added for convenience


@dataclass
class DoccanoDocument:
    """
    Represents a document in Doccano format.
    
    Format example:
    {
      "id": 1,
      "text": "John Doe works at john @example.com",
      "labels": [[0, 8, "PERSON"], [18, 35, "EMAIL"]]
    }
    """
    id: int
    text: str
    labels: List[DoccanoLabel] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict) -> DoccanoDocument:
        """Create from dictionary (JSON)."""
        labels = []
        for i, (start, end, label) in enumerate(data.get("labels", [])):
            text = data["text"][start:end]
            labels.append(DoccanoLabel(i, start, end, label, text))
        
        return cls(
            id=data["id"],
            text=data["text"],
            labels=labels
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON export."""
        return {
            "id": self.id,
            "text": self.text,
            "labels": [[l.start, l.end, l.label] for l in self.labels]
        }


class GroundTruthManager:
    """
    Manages ground truth data with deterministic hash generation.
    
    Workflow:
    1. Export NER data to Doccano format
    2. Human corrects labels in Doccano
    3. Import corrected data
    4. Generate deterministic hashes for each entity
    5. Store as ground truth
    
    Example:
        manager = GroundTruthManager(secret_key="my-secret")
        
        # Export for labeling
        manager.export_to_doccano(ner_data, "ground_truth.jsonl")
        
        # After human correction in Doccano, import
        manager.import_from_doccano("ground_truth_corrected.jsonl")
        
        # Generate ground truth with hashes
        ground_truth = manager.generate_ground_truth()
    """
    
    def __init__(self, secret_key: str):
        if not secret_key:
            raise ValueError("Secret key is required for hash generation")
        
        self.secret_key = secret_key.encode()
        self.logger = logging.getLogger(__class__.__name__)
        self.documents: List[DoccanoDocument] = []
    
    def _generate_hash(self, text: str) -> Tuple[str, str]:
        """
        Generate deterministic HMAC-SHA256 hash for an entity.
        
        Returns:
            Tuple of (display_hash, full_hash)
        """
        # Normalize text
        clean_text = " ".join(text.split()).strip()
        
        # Generate HMAC-SHA256
        full_hash = hmac.new(
            self.secret_key,
            clean_text.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Use first 8 characters as display hash (configurable)
        display_hash = full_hash[:8]
        
        return display_hash, full_hash
    
    def export_to_doccano(
        self,
        ner_results: List[Dict],
        output_path: str | Path
    ):
        """
        Export NER results to Doccano JSONL format.
        
        Args:
            ner_results: List of dicts with {"text": str, "label": [[start, end, type]]}
            output_path: Path to output JSONL file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, result in enumerate(ner_results):
                doc = DoccanoDocument(
                    id=i,
                    text=result["text"],
                    labels=[
                        DoccanoLabel(
                            id=j,
                            start=start,
                            end=end,
                            label=label,
                            text=result["text"][start:end]
                        )
                        for j, (start, end, label) in enumerate(result.get("label", []))
                    ]
                )
                f.write(json.dumps(doc.to_dict(), ensure_ascii=False) + '\n')
        
        self.logger.info(f"Exported {len(ner_results)} documents to {output_path}")
        print(f"\n{'='*70}")
        print(f"Ground Truth Export Complete")
        print(f"{'='*70}")
        print(f"File: {output_path}")
        print(f"Documents: {len(ner_results)}")
        print(f"\nNext steps:")
        print(f"1. Import this file into Doccano")
        print(f"2. Manually review and correct all labels")
        print(f"3. Export from Doccano (JSONL format)")
        print(f"4. Use import_from_doccano() with the corrected file")
        print(f"{'='*70}\n")
    
    def import_from_doccano(self, input_path: str | Path):
        """
        Import corrected data from Doccano JSONL file.
        
        This loads the human-verified ground truth.
        """
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Doccano file not found: {input_path}")
        
        self.documents = []
        
        with open(input_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    doc = DoccanoDocument.from_dict(data)
                    self.documents.append(doc)
        
        self.logger.info(f"Imported {len(self.documents)} documents from {input_path}")
    
    def generate_ground_truth(self) -> 'GroundTruth':
        """
        Generate ground truth with deterministic hashes.
        
        Returns:
            GroundTruth object with hash mappings
        """
        if not self.documents:
            raise ValueError("No documents loaded. Import from Doccano first.")
        
        ground_truth = GroundTruth()
        
        for doc in self.documents:
            doc_hash_mapping = {}
            
            for label in doc.labels:
                display_hash, full_hash = self._generate_hash(label.text)
                
                # Create expected anonymized form
                expected_anon = f"[{label.label}_{display_hash}]"
                
                # Track this entity
                ground_truth.add_entity(
                    original_text=label.text,
                    entity_type=label.label,
                    display_hash=display_hash,
                    full_hash=full_hash,
                    document_id=doc.id,
                    start=label.start,
                    end=label.end
                )
                
                doc_hash_mapping[label.text] = expected_anon
            
            # Store document-level information
            ground_truth.add_document(
                document_id=doc.id,
                original_text=doc.text,
                hash_mapping=doc_hash_mapping
            )
        
        self.logger.info(f"Generated ground truth with {ground_truth.get_total_entities()} entities")
        return ground_truth


@dataclass
class GroundTruthEntity:
    """Represents a single entity in ground truth."""
    original_text: str
    entity_type: str
    display_hash: str
    full_hash: str
    document_id: int
    start: int
    end: int
    expected_count: int = 1  # How many times should this hash appear


class GroundTruth:
    """
    Stores ground truth data with hash mappings.
    
    This is the gold standard against which we evaluate anonymization quality.
    """
    
    def __init__(self):
        self.entities: List[GroundTruthEntity] = []
        self.hash_to_entity: Dict[str, GroundTruthEntity] = {}
        self.document_texts: Dict[int, str] = {}
        self.document_mappings: Dict[int, Dict[str, str]] = {}
        self.logger = logging.getLogger(__class__.__name__)
    
    def add_entity(
        self,
        original_text: str,
        entity_type: str,
        display_hash: str,
        full_hash: str,
        document_id: int,
        start: int,
        end: int
    ):
        """Add an entity to ground truth."""
        entity = GroundTruthEntity(
            original_text=original_text,
            entity_type=entity_type,
            display_hash=display_hash,
            full_hash=full_hash,
            document_id=document_id,
            start=start,
            end=end
        )
        
        self.entities.append(entity)
        self.hash_to_entity[full_hash] = entity
    
    def add_document(
        self,
        document_id: int,
        original_text: str,
        hash_mapping: Dict[str, str]
    ):
        """Add document-level information."""
        self.document_texts[document_id] = original_text
        self.document_mappings[document_id] = hash_mapping
    
    def get_expected_hashes(self) -> Set[str]:
        """Get all expected full hashes."""
        return set(self.hash_to_entity.keys())

    def get_expected_display_hashes(self) -> Set[str]:
        """Get all expected display hashes."""
        return {entity.display_hash for entity in self.entities}
    
    def get_total_entities(self) -> int:
        """Get total number of entities in ground truth."""
        return len(self.entities)
    
    def calculate_expected_counts(self, document_id: int) -> Dict[str, int]:
        """
        Calculate how many times each hash should appear in anonymized text.
        
        Returns:
            Dict mapping display_hash to expected count
        """
        expected_counts = Counter()
        
        for entity in self.entities:
            if entity.document_id == document_id:
                expected_counts[entity.display_hash] += 1
        
        return dict(expected_counts)
    
    def save(self, filepath: str | Path):
        """Save ground truth to JSON file."""
        data = {
            "entities": [
                {
                    "original_text": e.original_text,
                    "entity_type": e.entity_type,
                    "display_hash": e.display_hash,
                    "full_hash": e.full_hash,
                    "document_id": e.document_id,
                    "start": e.start,
                    "end": e.end
                }
                for e in self.entities
            ],
            "documents": {
                str(doc_id): {
                    "text": text,
                    "mapping": self.document_mappings.get(doc_id, {})
                }
                for doc_id, text in self.document_texts.items()
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Saved ground truth to {filepath}")
    
    @classmethod
    def load(cls, filepath: str | Path) -> GroundTruth:
        """Load ground truth from JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        ground_truth = cls()
        
        for entity_data in data["entities"]:
            ground_truth.add_entity(**entity_data)
        
        for doc_id_str, doc_data in data["documents"].items():
            doc_id = int(doc_id_str)
            ground_truth.add_document(
                document_id=doc_id,
                original_text=doc_data["text"],
                hash_mapping=doc_data["mapping"]
            )
        
        return ground_truth
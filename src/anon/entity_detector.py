import logging
from typing import List, Dict, Set, Optional

from .config import ENTITY_MAPPING

class EntityDetector:
    """
    A class dedicated to detecting and merging entities from text using NLP models and regex.
    """
    def __init__(self, compiled_patterns: List[Dict], entities_to_preserve: Set[str], allow_list: Set[str], entity_mapping: Optional[Dict[str, str]] = None):
        self.compiled_patterns = compiled_patterns
        self.entities_to_preserve = entities_to_preserve
        self.allow_list = allow_list
        self.entity_mapping = entity_mapping or ENTITY_MAPPING
        self.logger = logging.getLogger(__class__.__name__)

    def extract_entities(self, doc, original_doc_text: str) -> List[Dict]:
        """Extracts entities from a spaCy Doc object and custom regex patterns."""
        detected_entities = []

        # Extract entities from spaCy Doc
        for ent in doc.ents:
            normalized_label = self.entity_mapping.get(ent.label_, ent.label_)
            if normalized_label not in self.entities_to_preserve:
                detected_entities.append({
                    "start": ent.start_char, "end": ent.end_char, "label": normalized_label,
                    "text": ent.text, "score": 1.0
                })

        # Extract entities from custom regex patterns
        for pat in self.compiled_patterns:
            for match in pat["regex"].finditer(original_doc_text):
                match_text = match.group()
                if match_text not in self.allow_list and pat["label"] not in self.entities_to_preserve:
                    detected_entities.append({
                        "start": match.start(), "end": match.end(), "label": pat["label"],
                        "text": match_text, "score": pat["score"]
                    })
        return detected_entities

    def extract_regex_entities(self, text: str) -> List[Dict]:
        """Detect entities using only compiled regex patterns — no spaCy doc required."""
        detected_entities = []
        for pat in self.compiled_patterns:
            for match in pat["regex"].finditer(text):
                match_text = match.group()
                if match_text in self.allow_list or pat["label"] in self.entities_to_preserve:
                    continue
                detected_entities.append({
                    "start": match.start(), "end": match.end(),
                    "label": pat["label"], "text": match_text, "score": pat["score"],
                })
        return detected_entities

    def merge_overlapping_entities(self, detected_entities: List[Dict]) -> List[Dict]:
        """Sorts and merges overlapping entities based on score and length."""
        # Sort by start position, then by inverse score (higher score first), then by inverse length (longer first)
        detected_entities.sort(key=lambda x: (x["start"], -x["score"], -(x["end"] - x["start"])))
        
        merged_entities = []
        last_end = -1
        for ent in detected_entities:
            if ent["start"] >= last_end:
                merged_entities.append(ent)
                last_end = ent["end"]
        return merged_entities

    def detect_entities_in_docs(self, docs) -> List[dict]:
        """The core logic of entity detection for a collection of spaCy docs."""
        results = []
        for doc in docs:
            original_doc_text = doc.text
            
            extracted = self.extract_entities(doc, original_doc_text)
            merged = self.merge_overlapping_entities(extracted)

            final_merged = []
            for ent in merged:
                if ent["label"] in self.entities_to_preserve: continue
                if original_doc_text[ent['start']:ent['end']] in self.allow_list: continue
                final_merged.append(ent)

            if final_merged:
                labels = [[ent['start'], ent['end'], ent['label']] for ent in final_merged]
                results.append({"text": original_doc_text, "label": labels})
        
        return results

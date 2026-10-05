import logging
from typing import List, Dict, Set, Optional, Tuple

from .config import ENTITY_MAPPING
from .entity_selection import is_entity_excluded

class EntityDetector:
    """
    A class dedicated to detecting and merging entities from text using NLP models and regex.

    ``compiled_patterns`` holds every regex the run uses (built-in recognizers for
    the language plus word-list and custom patterns). ``custom_patterns`` is the
    word-list/custom subset: the Presidio-based strategies already get the
    built-ins from the Presidio registry and only need the extras from here.

    Detection returns every match, including types the user preserves. The
    strategies then call ``finalize``: an entity that must stay in clear text
    still claims its span, so another recognizer cannot anonymize it under a
    different label (a preserved IP address coming back as a PHONE_NUMBER).
    """
    def __init__(self, compiled_patterns: List[Dict], entities_to_preserve: Set[str], allow_list: Set[str],
                 entity_mapping: Optional[Dict[str, str]] = None,
                 entities_to_anonymize: Optional[Set[str]] = None,
                 custom_patterns: Optional[List[Dict]] = None):
        self.compiled_patterns = compiled_patterns
        self.custom_patterns = custom_patterns or []
        self.entities_to_preserve = entities_to_preserve
        self.entities_to_anonymize = entities_to_anonymize
        self.allow_list = allow_list
        self.entity_mapping = entity_mapping or ENTITY_MAPPING
        self.logger = logging.getLogger(__class__.__name__)

    def is_excluded(self, label: str) -> bool:
        """True when entities of this type must not be anonymized."""
        return is_entity_excluded(label, self.entities_to_preserve, self.entities_to_anonymize)

    def extract_entities(self, doc, original_doc_text: str) -> List[Dict]:
        """Extracts entities from a spaCy Doc object and custom regex patterns."""
        detected_entities = []

        # Extract entities from spaCy Doc
        for ent in doc.ents:
            normalized_label = self.entity_mapping.get(ent.label_, ent.label_)
            detected_entities.append({
                "start": ent.start_char, "end": ent.end_char, "label": normalized_label,
                "text": ent.text, "score": 1.0
            })

        detected_entities.extend(self._match(self.compiled_patterns, original_doc_text))
        return detected_entities

    @staticmethod
    def _match(patterns: List[Dict], text: str) -> List[Dict]:
        detected_entities = []
        for pat in patterns:
            for match in pat["regex"].finditer(text):
                detected_entities.append({
                    "start": match.start(), "end": match.end(),
                    "label": pat["label"], "text": match.group(), "score": pat["score"],
                })
        return detected_entities

    def extract_regex_entities(self, text: str) -> List[Dict]:
        """Detect entities using only compiled regex patterns; no spaCy doc required."""
        return self._match(self.compiled_patterns, text)

    def extract_custom_entities(self, text: str) -> List[Dict]:
        """Detect entities from word-list and custom patterns only."""
        return self._match(self.custom_patterns, text)

    def _allow_list_spans(self, text: str) -> List[Tuple[int, int]]:
        spans = []
        for term in self.allow_list:
            if not term:
                continue
            i = text.find(term)
            while i != -1:
                spans.append((i, i + len(term)))
                i = text.find(term, i + 1)
        return spans

    def apply_exclusions(self, text: str, detected_entities: List[Dict]) -> List[Dict]:
        """Drop the detections that must stay in clear text.

        An entity is dropped when its type is preserved or not selected, when it
        lies inside an allow-listed term (an allowed e-mail must not lose its
        local part to the HOSTNAME regex), or when it overlaps a detection of an
        excluded type that scores at least as high.
        """
        allowed_spans = self._allow_list_spans(text) if self.allow_list else []
        protected = [e for e in detected_entities if self.is_excluded(e["label"])]
        kept = []
        for ent in detected_entities:
            if self.is_excluded(ent["label"]):
                continue
            if any(s <= ent["start"] and ent["end"] <= e for s, e in allowed_spans):
                continue
            if any(p["start"] < ent["end"] and ent["start"] < p["end"] and p["score"] >= ent["score"]
                   for p in protected):
                continue
            kept.append(ent)
        return kept

    def finalize(self, text: str, detected_entities: List[Dict]) -> List[Dict]:
        """Apply exclusions, then resolve overlaps among what is left."""
        return self.merge_overlapping_entities(self.apply_exclusions(text, detected_entities), text)

    def merge_overlapping_entities(self, detected_entities: List[Dict], text: Optional[str] = None) -> List[Dict]:
        """Sorts and merges overlapping entities based on score and length.

        The entity that starts first (then higher score, then longer) keeps the
        label. With ``text``, a later entity that overlaps it partially extends
        its span instead of being dropped, so the uncovered tail is not left in
        clear text.
        """
        # Sort by start position, then by inverse score (higher score first), then by inverse length (longer first)
        detected_entities.sort(key=lambda x: (x["start"], -x["score"], -(x["end"] - x["start"])))

        merged_entities = []
        last_end = -1
        for ent in detected_entities:
            if ent["start"] >= last_end:
                merged_entities.append(dict(ent))
                last_end = ent["end"]
            elif text is not None and ent["end"] > last_end:
                last = merged_entities[-1]
                last["end"] = last_end = ent["end"]
                last["text"] = text[last["start"]:last["end"]]
        return merged_entities

    def detect_entities_in_docs(self, docs) -> List[dict]:
        """The core logic of entity detection for a collection of spaCy docs."""
        results = []
        for doc in docs:
            original_doc_text = doc.text
            final_merged = self.finalize(original_doc_text, self.extract_entities(doc, original_doc_text))
            if final_merged:
                labels = [[ent['start'], ent['end'], ent['label']] for ent in final_merged]
                results.append({"text": original_doc_text, "label": labels})

        return results

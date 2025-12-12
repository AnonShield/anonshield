"""
SLM Entity Detector Module - Task 2: Replace NER models with SLM

This module provides an alternative to traditional NER models (like xlm-roberta)
by using a Small Language Model for entity detection. It maintains compatibility
with the existing EntityDetector interface.

Key Design Decisions:
- Protocol-based: Compatible with existing EntityDetector interface
- Cacheable: Results can be cached for performance
- Fallback-ready: Can gracefully degrade to regex-only if SLM fails
"""
from __future__ import annotations
from typing import List, Dict, Set, Optional, Protocol
import logging
from dataclasses import dataclass
import time


@dataclass
class DetectedEntity:
    """
    Represents an entity detected by the SLM.
    Compatible with Presidio's RecognizerResult format.
    """
    text: str
    entity_type: str
    start: int
    end: int
    score: float
    
    def to_presidio_format(self) -> Dict:
        """Convert to format compatible with Presidio."""
        return {
            "start": self.start,
            "end": self.end,
            "entity_type": self.entity_type,
            "score": self.score
        }


class SLMEntityDetector:
    """
    Entity detector that uses SLM instead of traditional NER models.
    
    This class is designed to be a drop-in replacement for the transformer-based
    NER system, but uses a local SLM for inference.
    
    Advantages over traditional NER:
    - Context-aware: Better understanding of domain-specific entities
    - Flexible: Easy to adapt to new entity types via prompt engineering
    - Explainable: Can provide reasoning for detections
    
    Trade-offs:
    - Slower than fine-tuned models (mitigated with caching)
    - Requires Ollama running locally
    - Higher resource usage per inference
    
    Example:
        from slm.client import OllamaClient
        from slm.prompts import PromptManager
        
        client = OllamaClient(model="llama3")
        prompt_mgr = PromptManager()
        
        detector = SLMEntityDetector(
            slm_client=client,
            prompt_manager=prompt_mgr,
            entities_to_preserve={"ORGANIZATION"},
            allow_list={"localhost", "example.com"}
        )
        
        text = "John Doe works at john@company.com, IP: 192.168.1.1"
        entities = detector.detect_entities([text])
    """
    
    def __init__(
        self,
        slm_client,  # SLMClient protocol
        prompt_manager,  # PromptManager
        entities_to_preserve: Set[str],
        allow_list: Set[str],
        confidence_threshold: float = 0.6,
        use_cache: bool = True,
        max_cache_size: int = 1000,
        fallback_to_regex: bool = True,
        compiled_patterns: Optional[List[Dict]] = None,
        prompt_version: Optional[str] = None
    ):
        self.client = slm_client
        self.prompt_manager = prompt_manager
        self.entities_to_preserve = entities_to_preserve
        self.allow_list = allow_list
        self.confidence_threshold = confidence_threshold
        self.use_cache = use_cache
        self.fallback_to_regex = fallback_to_regex
        self.compiled_patterns = compiled_patterns or []
        self.prompt_version = prompt_version
        
        self.logger = logging.getLogger(__class__.__name__)
        
        # Simple LRU cache for repeated texts
        self._cache: Dict[str, List[DetectedEntity]] = {}
        self._max_cache_size = max_cache_size
        self._cache_hits = 0
        self._cache_misses = 0
    
    def _get_from_cache(self, text: str) -> Optional[List[DetectedEntity]]:
        """Retrieve cached detection results."""
        if not self.use_cache:
            return None
        
        if text in self._cache:
            self._cache_hits += 1
            self.logger.debug(f"Cache hit (hit rate: {self._cache_hits/(self._cache_hits+self._cache_misses):.2%})")
            return self._cache[text]
        
        self._cache_misses += 1
        return None
    
    def _add_to_cache(self, text: str, entities: List[DetectedEntity]):
        """Add detection results to cache with LRU eviction."""
        if not self.use_cache:
            return
        
        if len(self._cache) >= self._max_cache_size:
            # Simple LRU: remove first item
            self._cache.pop(next(iter(self._cache)))
        
        self._cache[text] = entities
    
    def _parse_slm_response(self, response_json: Dict, original_text: str) -> List[DetectedEntity]:
        """Parse SLM JSON response into DetectedEntity objects."""
        if "error" in response_json:
            self.logger.error(f"SLM error: {response_json['error']}")
            return []
        
        entities_data = response_json.get("entities", [])
        detected = []
        
        for entity_data in entities_data:
            try:
                entity_type = entity_data.get("type", "UNKNOWN")
                
                # Skip preserved entities
                if entity_type in self.entities_to_preserve:
                    continue
                
                # Validate required fields
                if not all(k in entity_data for k in ["text", "type", "start", "end"]):
                    self.logger.warning(f"Skipping malformed entity: {entity_data}")
                    continue
                
                text = entity_data["text"]
                
                # Skip allow-listed items
                if text.lower() in self.allow_list:
                    continue
                
                score = float(entity_data.get("confidence", entity_data.get("score", 0.9)))
                
                # Apply confidence threshold
                if score < self.confidence_threshold:
                    continue
                
                detected.append(DetectedEntity(
                    text=text,
                    entity_type=entity_type,
                    start=int(entity_data["start"]),
                    end=int(entity_data["end"]),
                    score=score
                ))
                
            except (ValueError, KeyError) as e:
                self.logger.warning(f"Failed to parse entity: {e}")
                continue
        
        return detected
    
    def _fallback_regex_detection(self, text: str) -> List[DetectedEntity]:
        """
        Fallback to regex-based detection if SLM fails.
        
        This ensures the system remains functional even when SLM is unavailable.
        """
        if not self.compiled_patterns:
            return []
        
        self.logger.info("Using fallback regex detection")
        detected = []
        
        for pattern_dict in self.compiled_patterns:
            entity_type = pattern_dict["label"]
            
            if entity_type in self.entities_to_preserve:
                continue
            
            regex = pattern_dict["regex"]
            score = pattern_dict["score"]
            
            for match in regex.finditer(text):
                matched_text = match.group()
                
                if matched_text.lower() in self.allow_list:
                    continue
                
                detected.append(DetectedEntity(
                    text=matched_text,
                    entity_type=entity_type,
                    start=match.start(),
                    end=match.end(),
                    score=score
                ))
        
        return detected
    
    def _merge_overlapping_entities(self, entities: List[DetectedEntity]) -> List[DetectedEntity]:
        """
        Merge overlapping entities, keeping highest-scoring ones.
        
        This prevents issues like "John" and "John Doe" both being detected.
        """
        if not entities:
            return []
        
        # Sort by start position, then by score (descending), then by length (descending)
        entities.sort(key=lambda e: (e.start, -e.score, -(e.end - e.start)))
        
        merged = []
        last_end = -1
        
        for entity in entities:
            if entity.start >= last_end:
                merged.append(entity)
                last_end = entity.end
        
        return merged
    
    def detect_entities(
        self, 
        texts: List[str], 
        language: str = "en",
        prompt_version: Optional[str] = None
    ) -> List[Dict]:
        """
        Detect entities in a list of texts.
        
        This is the main interface method, compatible with the existing
        EntityDetector.detect_entities_in_docs() signature.
        
        Args:
            texts: List of text strings to analyze
            language: Language code
            prompt_version: Specific prompt version to use. Overrides instance default.
        
        Returns:
            List of dicts with format: {"text": str, "label": [[start, end, type]]}
        """
        results = []
        
        # Use the method's prompt_version if provided, otherwise fall back to the instance's default.
        version = prompt_version or self.prompt_version

        # Get prompt template
        try:
            template = self.prompt_manager.get(
                "entity_detector",
                version=version,
                language=language
            )
        except KeyError as e:
            self.logger.error(f"Prompt not found: {e}. Using fallback.")
            # If prompt not found, use regex fallback for all texts
            for text in texts:
                entities = self._fallback_regex_detection(text)
                if entities:
                    labels = [[e.start, e.end, e.entity_type] for e in entities]
                    results.append({"text": text, "label": labels})
            return results
        
        for text in texts:
            # Check cache first
            cached = self._get_from_cache(text)
            if cached is not None:
                if cached:
                    labels = [[e.start, e.end, e.entity_type] for e in cached]
                    results.append({"text": text, "label": labels})
                continue
            
            # Query SLM
            system_prompt, user_prompt = template.format(text=text)
            
            start_time = time.time()
            response = self.client.query_json(
                prompt=user_prompt,
                system_prompt=system_prompt
            )
            elapsed = time.time() - start_time
            
            self.logger.debug(f"SLM detection took {elapsed:.2f}s")
            
            # Parse response
            if "error" in response and self.fallback_to_regex:
                entities = self._fallback_regex_detection(text)
            else:
                entities = self._parse_slm_response(response, text)
            
            # Merge overlapping
            entities = self._merge_overlapping_entities(entities)
            
            # Cache result
            self._add_to_cache(text, entities)
            
            # Format output
            if entities:
                labels = [[e.start, e.end, e.entity_type] for e in entities]
                results.append({"text": text, "label": labels})
        
        return results
    
    def get_cache_stats(self) -> Dict:
        """Return cache performance statistics."""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0.0
        
        return {
            "cache_size": len(self._cache),
            "max_cache_size": self._max_cache_size,
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": hit_rate
        }
    
    def clear_cache(self):
        """Clear the detection cache."""
        self._cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        self.logger.info("Detection cache cleared")


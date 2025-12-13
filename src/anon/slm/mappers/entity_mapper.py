"""
Entity Mapper Module - Task 1: Map potential entities using SLM

This module uses a Small Language Model to analyze text and identify entities
that should be anonymized, outputting structured data that can be used to
create regex patterns or other recognizers.

Design Principles:
- Single Responsibility: Only maps entities, doesn't anonymize
- Strategy Pattern: Different mapping strategies can be swapped
- Open/Closed: Easy to extend with new entity types
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Protocol
import logging
import json
from pathlib import Path


@dataclass
class MappedEntity:
    """
    Represents a potential entity identified by the SLM.
    
    Attributes:
        text: The actual text of the entity
        entity_type: Classification (PERSON, EMAIL, IP_ADDRESS, etc.)
        start: Character start position
        end: Character end position
        confidence: Confidence score from 0.0 to 1.0
        reason: Explanation for why this should be anonymized
        context: Surrounding text for validation
    """
    text: str
    entity_type: str
    start: int
    end: int
    confidence: float
    reason: str = ""
    context: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "entity_type": self.entity_type,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
            "reason": self.reason,
            "context": self.context
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> MappedEntity:
        """Create instance from dictionary."""
        return cls(
            text=data["text"],
            entity_type=data["entity_type"],
            start=data["start"],
            end=data["end"],
            confidence=data.get("confidence", 1.0),
            reason=data.get("reason", ""),
            context=data.get("context", "")
        )


@dataclass
class EntityMappingResult:
    """
    Result of entity mapping operation for a text chunk.
    
    Attributes:
        original_text: The input text
        entities: List of identified entities
        suggestions: Suggested regex patterns or improvements
        metadata: Additional info (tokens used, time taken, etc.)
    """
    original_text: str
    entities: List[MappedEntity] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps({
            "original_text": self.original_text,
            "entities": [e.to_dict() for e in self.entities],
            "suggestions": self.suggestions,
            "metadata": self.metadata
        }, indent=2, ensure_ascii=False)
    
    def save(self, filepath: str | Path):
        """Save mapping result to JSON file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json())


class EntityMapper(ABC):
    """Abstract base class for entity mapping strategies."""
    
    @abstractmethod
    def map_entities(self, text: str, language: str = "en") -> EntityMappingResult:
        """Map entities in the given text."""
        pass


class SLMEntityMapper(EntityMapper):
    """
    Concrete implementation using a Small Language Model via Ollama.
    
    This mapper uses few-shot learning with carefully crafted prompts to
    identify entities that should be anonymized.
    
    Example:
        from slm.client import OllamaClient
        from slm.prompts import PromptManager
        
        client = OllamaClient(model="llama3")
        prompt_mgr = PromptManager()
        
        mapper = SLMEntityMapper(client, prompt_mgr)
        result = mapper.map_entities(
            "John Doe (john@example.com) accessed server 192.168.1.1"
        )
        
        for entity in result.entities:
            print(f"{entity.entity_type}: {entity.text}")
    """
    
    def __init__(
        self,
        slm_client,  # SLMClient protocol
        prompt_manager,  # PromptManager
        confidence_threshold: float = 0.7,
        max_chunk_size: int = 2000,
        include_context: bool = True,
        context_window: int = 50
    ):
        self.client = slm_client
        self.prompt_manager = prompt_manager
        self.confidence_threshold = confidence_threshold
        self.max_chunk_size = max_chunk_size
        self.include_context = include_context
        self.context_window = context_window
        self.logger = logging.getLogger(__class__.__name__)
    
    def _chunk_text(self, text: str) -> List[str]:
        """
        Split text into processable chunks while preserving sentence boundaries.
        
        Uses a simple sentence-aware chunking to avoid breaking mid-sentence.
        """
        if len(text) <= self.max_chunk_size:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # Simple sentence splitting (can be improved with NLTK/spaCy)
        sentences = text.replace('\n', ' ').split('. ')
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > self.max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _extract_context(self, text: str, start: int, end: int) -> str:
        """Extract surrounding context for an entity."""
        if not self.include_context:
            return ""
        
        context_start = max(0, start - self.context_window)
        context_end = min(len(text), end + self.context_window)
        
        return text[context_start:context_end]
    
    def _parse_slm_response(self, response_json: Dict, original_text: str) -> List[MappedEntity]:
        """
        Parse the SLM's JSON response and deterministically find positions in python.
        This fixes hallucination (text not in source) and index errors (LLM bad math).
        """
        if "error" in response_json:
            self.logger.error(f"SLM returned error: {response_json['error']}")
            return []
        
        entities_data = response_json.get("entities", [])
        mapped_entities = []
        
        # Normaliza o texto original para busca (opcional, se quiser case-insensitive)
        # original_lower = original_text.lower() 

        for entity_data in entities_data:
            try:
                # 1. Validação básica de campos
                if "text" not in entity_data or "type" not in entity_data:
                    continue
                
                text_to_find = entity_data["text"]
                entity_type = entity_data["type"]
                confidence = entity_data.get("confidence", 1.0)

                # 2. CHECK ANTI-ALUCINAÇÃO & ANTI-GENÉRICO
                # Se a string extraída for muito curta (ex: "a") ou não estiver no texto, ignorar.
                if len(text_to_find) < 2 or text_to_find not in original_text:
                    self.logger.debug(f"Hallucination or formatting mismatch dropped: '{text_to_find}'")
                    continue

                # 2.5. CHECK CONFIDENCE THRESHOLD
                if confidence < 0.1:
                    self.logger.debug(f"Entity '{text_to_find}' dropped due to low confidence: {confidence}")
                    continue

                # 3. BUSCA DETERMINÍSTICA (Find All Occurrences)
                # A LLM achou o padrão. Nós achamos TODAS as ocorrências dele no chunk.
                start_search = 0
                while True:
                    start_index = original_text.find(text_to_find, start_search)
                    if start_index == -1:
                        break
                    
                    end_index = start_index + len(text_to_find)
                    
                    # Extrai contexto real do Python
                    context = self._extract_context(original_text, start_index, end_index)

                    entity = MappedEntity(
                        text=text_to_find,
                        entity_type=entity_type,
                        start=start_index,
                        end=end_index,
                        confidence=confidence,
                        reason=entity_data.get("reason", "Detected by SLM"),
                        context=context
                    )
                    mapped_entities.append(entity)
                    
                    # Avança a busca para não pegar o mesmo índice
                    start_search = end_index

            except Exception as e:
                self.logger.warning(f"Failed to process entity '{entity_data.get('text', 'unknown')}': {e}")
                continue
        
        return mapped_entities
    
    def map_entities(
        self, 
        text: str, 
        language: str = "en",
        prompt_version: Optional[str] = None
    ) -> EntityMappingResult:
        """
        Map all entities in the text using the SLM.
        
        Args:
            text: Input text to analyze
            language: Language code (en, pt, etc.)
            prompt_version: Specific prompt version to use
        
        Returns:
            EntityMappingResult with all identified entities
        """
        self.logger.info(f"Mapping entities in text of length {len(text)}")
        
        # Get the appropriate prompt
        try:
            template = self.prompt_manager.get(
                "entity_mapper",
                version=prompt_version,
                language=language
            )
        except KeyError as e:
            self.logger.error(f"Prompt not found: {e}")
            return EntityMappingResult(original_text=text)
        
        # Process text in chunks if necessary
        chunks = self._chunk_text(text)
        all_entities = []
        offset = 0
        
        for i, chunk in enumerate(chunks):
            self.logger.debug(f"Processing chunk {i+1}/{len(chunks)}")
            
            # Format prompt
            system_prompt, user_prompt = template.format(
                text=chunk,
                language=language
            )
            
            self.logger.debug(f"SLM query for chunk {i+1}/{len(chunks)}. System prompt: {system_prompt}")
            self.logger.debug(f"User prompt: {user_prompt}")
            
            # Query SLM
            response = self.client.query_json(
                prompt=user_prompt,
                system_prompt=system_prompt
            )
            
            self.logger.debug(f"SLM raw response for chunk {i+1}/{len(chunks)}: {response}")

            # Parse response
            chunk_entities = self._parse_slm_response(response, chunk)
            self.logger.debug(f"Parsed {len(chunk_entities)} entities from chunk {i+1}/{len(chunks)}.")
            
            # Adjust entity positions for multi-chunk processing
            for entity in chunk_entities:
                entity.start += offset
                entity.end += offset
                all_entities.append(entity)
            
            offset += len(chunk)
        
        self.logger.info(f"Mapped {len(all_entities)} total entities")
        self.logger.debug(f"Final mapped entities: {[e.to_dict() for e in all_entities]}")

        return EntityMappingResult(
            original_text=text,
            entities=all_entities,
            metadata={
                "chunks_processed": len(chunks),
                "model": getattr(self.client, 'model', 'unknown'),
                "confidence_threshold": self.confidence_threshold
            }
        )
    
    def batch_map(
        self, 
        texts: List[str], 
        language: str = "en",
        prompt_version: Optional[str] = None
    ) -> List[EntityMappingResult]:
        """
        Process multiple texts in batch.
        
        This is more efficient than calling map_entities multiple times
        as it can reuse prompts and potentially batch API calls.
        """
        results = []
        
        for i, text in enumerate(texts):
            self.logger.debug(f"Batch mapping {i+1}/{len(texts)}")
            result = self.map_entities(text, language, prompt_version=prompt_version)
            results.append(result)
        
        return results


class EntityMapperExporter:
    """
    Utility class to export mapping results in various formats.
    
    Supports:
    - JSON (structured data)
    - CSV (for spreadsheet analysis)
    - Regex patterns (for creating custom recognizers)
    """
    
    @staticmethod
    def to_csv(results: List[EntityMappingResult], output_path: str | Path):
        """Export mapping results to CSV format."""
        import csv
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Text", "Entity Type", "Start", "End", 
                "Confidence", "Reason", "Context"
            ])
            
            for result in results:
                for entity in result.entities:
                    writer.writerow([
                        entity.text,
                        entity.entity_type,
                        entity.start,
                        entity.end,
                        entity.confidence,
                        entity.reason,
                        entity.context
                    ])
    
    @staticmethod
    def suggest_regex_patterns(results: List[EntityMappingResult]) -> Dict[str, List[str]]:
        """
        Analyze mapped entities and suggest regex patterns.
        
        Returns a dictionary mapping entity types to suggested regex patterns.
        """
        from collections import defaultdict
        import re
        
        entity_examples = defaultdict(list)
        
        # Collect examples by type
        for result in results:
            for entity in result.entities:
                entity_examples[entity.entity_type].append(entity.text)
        
        # Generate pattern suggestions (simplified - can be much more sophisticated)
        patterns = {}
        
        for entity_type, examples in entity_examples.items():
            if not examples:
                continue
            
            # Simple heuristic-based pattern generation
            if entity_type == "EMAIL_ADDRESS":
                patterns[entity_type] = [r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"]
            elif entity_type == "IP_ADDRESS":
                patterns[entity_type] = [r"\b(?:\d{1,3}\.){3}\d{1,3}\b"]
            elif entity_type == "PHONE_NUMBER":
                patterns[entity_type] = [r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"]
            # Add more sophisticated pattern generation logic here
        
        return patterns
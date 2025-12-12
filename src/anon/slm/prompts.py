from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Tuple, Optional

class PromptManager:
    """
    Loads and manages SLM prompts from a structured directory.

    This allows for easy versioning, A/B testing, and modification of prompts
    without changing the application code.

    Expected directory structure:
    /prompts
    ├── entity_mapper/
    │   ├── v1_en.json
    │   └── v1_pt.json
    ├── entity_detector/
    │   └── v1_en.json
    └── full_anonymizer/
        └── v1_en.json
    """
    def __init__(self, base_path: str | Path = "prompts"):
        self.base_path = Path(base_path)
        if not self.base_path.exists():
            self.base_path.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Dict] = {}

    def _load_prompt_file(self, task: str, version: str, language: str) -> Dict:
        """Loads a specific prompt file from disk."""
        key = f"{task}-{version}-{language}"
        if key in self._cache:
            return self._cache[key]

        file_path = self.base_path / task / f"{version}_{language}.json"
        if not file_path.exists():
            # Fallback to language 'en' if the specified language is not found
            fallback_path = self.base_path / task / f"{version}_en.json"
            if not fallback_path.exists():
                raise FileNotFoundError(f"Prompt file not found for task '{task}' with version '{version}' for language '{language}' or fallback 'en'.")
            file_path = fallback_path

        with open(file_path, 'r', encoding='utf-8') as f:
            prompt_data = json.load(f)
            self._cache[key] = prompt_data
            return prompt_data

    def get(
        self,
        task: str,
        language: str = "en",
        version: Optional[str] = "v1"
    ) -> "PromptTemplate":
        """
        Get a formattable prompt template for a given task.
        """
        if version is None:
            version = "v1" # Default version

        prompt_data = self._load_prompt_file(task, version, language)
        return PromptTemplate(prompt_data.get("system", ""), prompt_data.get("user", ""))

class PromptTemplate:
    """A simple template wrapper for system and user prompts."""
    def __init__(self, system_template: str, user_template: str):
        self.system_template = system_template
        self.user_template = user_template

    def format(self, **kwargs) -> Tuple[str, str]:
        """Formats both system and user prompts with the given data."""
        return (
            self.system_template.format(**kwargs),
            self.user_template.format(**kwargs)
        )

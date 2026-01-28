"""
Model Manager - Lazy loading system for ML models and heavy dependencies.

This module implements the Strategy pattern for model provisioning, allowing
different models to be downloaded/loaded on-demand rather than at startup.

Design Principles:
- Single Responsibility: Each ModelProvider handles one type of model
- Open/Closed: Easy to add new model types without modifying existing code
- Dependency Inversion: Core logic depends on abstractions (ModelProvider protocol)

Usage:
    manager = ModelManager()
    manager.ensure_available("spacy", "en_core_web_lg")
    manager.ensure_available("transformer", "Davlan/xlm-roberta-base-ner-hrl")
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Protocol


class ModelStatus(Enum):
    """Status of a model in the system."""
    NOT_INSTALLED = "not_installed"
    DOWNLOADING = "downloading"
    AVAILABLE = "available"
    ERROR = "error"


@dataclass
class ModelInfo:
    """Information about a model."""
    name: str
    provider: str
    status: ModelStatus
    path: Optional[Path] = None
    size_mb: Optional[int] = None
    error: Optional[str] = None


class ModelProvider(Protocol):
    """Protocol defining interface for model providers."""

    def is_available(self, model_name: str) -> bool:
        """Check if model is already available locally."""
        ...

    def download(self, model_name: str) -> bool:
        """Download the model. Returns True on success."""
        ...

    def get_info(self, model_name: str) -> ModelInfo:
        """Get information about a model."""
        ...


class SpacyModelProvider:
    """Provider for spaCy language models."""

    MODELS = {
        "en_core_web_lg": {"size_mb": 560, "lang": "en"},
        "pt_core_news_lg": {"size_mb": 540, "lang": "pt"},
        "en_core_web_sm": {"size_mb": 12, "lang": "en"},
        "pt_core_news_sm": {"size_mb": 15, "lang": "pt"},
    }

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def is_available(self, model_name: str) -> bool:
        """Check if spaCy model is installed."""
        try:
            import spacy.util
            return spacy.util.is_package(model_name)
        except ImportError:
            return False

    def download(self, model_name: str) -> bool:
        """Download spaCy model."""
        self.logger.info(f"Downloading spaCy model '{model_name}'...")
        print(f"[ModelManager] Downloading spaCy model '{model_name}'...", flush=True)

        try:
            result = subprocess.run(
                [sys.executable, "-m", "spacy", "download", model_name],
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )

            if result.returncode == 0:
                print(f"[ModelManager] spaCy model '{model_name}' downloaded successfully.", flush=True)
                self.logger.info(f"spaCy model '{model_name}' downloaded successfully.")
                return True
            else:
                self.logger.error(f"Failed to download spaCy model: {result.stderr}")
                print(f"[ModelManager] ERROR: Failed to download '{model_name}': {result.stderr}", flush=True)
                return False

        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout downloading spaCy model '{model_name}'")
            return False
        except Exception as e:
            self.logger.error(f"Error downloading spaCy model: {e}")
            return False

    def get_info(self, model_name: str) -> ModelInfo:
        """Get information about a spaCy model."""
        model_meta = self.MODELS.get(model_name, {})
        return ModelInfo(
            name=model_name,
            provider="spacy",
            status=ModelStatus.AVAILABLE if self.is_available(model_name) else ModelStatus.NOT_INSTALLED,
            size_mb=model_meta.get("size_mb")
        )


class TransformerModelProvider:
    """Provider for HuggingFace transformer models."""

    DEFAULT_CACHE_DIR = Path("models")

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or self.DEFAULT_CACHE_DIR
        self.logger = logging.getLogger(self.__class__.__name__)

    def _get_model_path(self, model_name: str) -> Path:
        """Get the local path for a model."""
        return self.cache_dir / model_name

    def is_available(self, model_name: str) -> bool:
        """Check if transformer model is cached locally."""
        model_path = self._get_model_path(model_name)
        # Check if model directory exists and has content
        if model_path.exists():
            # Look for model files (pytorch_model.bin, model.safetensors, etc.)
            model_files = list(model_path.rglob("*.bin")) + list(model_path.rglob("*.safetensors"))
            return len(model_files) > 0
        return False

    def download(self, model_name: str) -> bool:
        """Download transformer model from HuggingFace."""
        self.logger.info(f"Downloading transformer model '{model_name}'...")
        print(f"[ModelManager] Downloading transformer model '{model_name}'...", flush=True)

        try:
            from huggingface_hub import snapshot_download

            model_path = self._get_model_path(model_name)
            model_path.mkdir(parents=True, exist_ok=True)

            snapshot_download(
                repo_id=model_name,
                cache_dir=str(model_path),
                max_workers=4
            )

            print(f"[ModelManager] Transformer model '{model_name}' downloaded successfully.", flush=True)
            self.logger.info(f"Transformer model '{model_name}' downloaded successfully.")
            return True

        except Exception as e:
            self.logger.error(f"Error downloading transformer model: {e}")
            print(f"[ModelManager] ERROR: Failed to download '{model_name}': {e}", flush=True)
            return False

    def get_info(self, model_name: str) -> ModelInfo:
        """Get information about a transformer model."""
        return ModelInfo(
            name=model_name,
            provider="transformer",
            status=ModelStatus.AVAILABLE if self.is_available(model_name) else ModelStatus.NOT_INSTALLED,
            path=self._get_model_path(model_name)
        )


class TesseractProvider:
    """Provider for Tesseract OCR."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def is_available(self, model_name: str = "tesseract") -> bool:
        """Check if Tesseract is installed."""
        try:
            result = subprocess.run(
                ["tesseract", "--version"],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def download(self, model_name: str = "tesseract") -> bool:
        """
        Tesseract must be installed via system package manager.
        This method provides guidance rather than automatic installation.
        """
        print("[ModelManager] Tesseract OCR is not installed.", flush=True)
        print("[ModelManager] Install it with: apt-get install tesseract-ocr", flush=True)
        self.logger.warning("Tesseract OCR is not installed. Install with: apt-get install tesseract-ocr")
        return False

    def get_info(self, model_name: str = "tesseract") -> ModelInfo:
        """Get information about Tesseract."""
        return ModelInfo(
            name="tesseract",
            provider="system",
            status=ModelStatus.AVAILABLE if self.is_available() else ModelStatus.NOT_INSTALLED
        )


class ModelManager:
    """
    Central manager for lazy loading of ML models.

    This class implements the Facade pattern, providing a simple interface
    to manage various model providers.

    Example:
        manager = ModelManager()

        # Check and download if needed
        if not manager.ensure_available("spacy", "en_core_web_lg"):
            raise RuntimeError("Failed to provision spaCy model")

        # Get status of all models
        for info in manager.get_all_status():
            print(f"{info.name}: {info.status.value}")
    """

    def __init__(self, models_dir: Optional[Path] = None):
        self.models_dir = models_dir or Path("models")
        self.logger = logging.getLogger(self.__class__.__name__)

        # Register providers
        self._providers: dict[str, ModelProvider] = {
            "spacy": SpacyModelProvider(),
            "transformer": TransformerModelProvider(cache_dir=self.models_dir),
            "tesseract": TesseractProvider(),
        }

    def register_provider(self, name: str, provider: ModelProvider) -> None:
        """Register a new model provider (Open/Closed principle)."""
        self._providers[name] = provider

    def is_available(self, provider_name: str, model_name: str) -> bool:
        """Check if a model is available."""
        provider = self._providers.get(provider_name)
        if not provider:
            self.logger.warning(f"Unknown provider: {provider_name}")
            return False
        return provider.is_available(model_name)

    def ensure_available(self, provider_name: str, model_name: str) -> bool:
        """
        Ensure a model is available, downloading if necessary.

        This is the main entry point for lazy loading.

        Args:
            provider_name: Name of the provider (spacy, transformer, tesseract)
            model_name: Name of the model to ensure

        Returns:
            True if model is available (was already or successfully downloaded)
        """
        provider = self._providers.get(provider_name)
        if not provider:
            self.logger.error(f"Unknown provider: {provider_name}")
            return False

        if provider.is_available(model_name):
            self.logger.debug(f"Model '{model_name}' already available.")
            return True

        self.logger.info(f"Model '{model_name}' not found. Initiating download...")
        return provider.download(model_name)

    def get_info(self, provider_name: str, model_name: str) -> Optional[ModelInfo]:
        """Get information about a specific model."""
        provider = self._providers.get(provider_name)
        if not provider:
            return None
        return provider.get_info(model_name)

    def get_required_models_for_args(self, args) -> list[tuple[str, str]]:
        """
        Determine which models are required based on CLI arguments.

        This method implements the logic for lazy loading based on
        what features the user is actually using.

        Returns:
            List of (provider, model_name) tuples that need to be available
        """
        required = []

        # Language models (always needed for NER)
        lang = getattr(args, 'lang', 'en')
        spacy_model = f"{lang}_core_news_lg" if lang != 'en' else "en_core_web_lg"
        required.append(("spacy", spacy_model))

        # English model is always needed as fallback
        if lang != 'en':
            required.append(("spacy", "en_core_web_lg"))

        # Transformer model (needed for NER unless using SLM-only)
        strategy = getattr(args, 'anonymization_strategy', 'presidio')
        if strategy != 'slm':
            required.append(("transformer", "Davlan/xlm-roberta-base-ner-hrl"))

        # Tesseract (only for image/PDF processing)
        file_path = getattr(args, 'file_path', '')
        if file_path:
            ext = Path(file_path).suffix.lower() if isinstance(file_path, str) else ''
            if ext in ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                required.append(("tesseract", "tesseract"))

        return required

    def ensure_required_for_args(self, args) -> bool:
        """
        Ensure all required models for the given arguments are available.

        Returns:
            True if all required models are available
        """
        required = self.get_required_models_for_args(args)
        all_available = True

        for provider_name, model_name in required:
            if not self.ensure_available(provider_name, model_name):
                self.logger.error(f"Failed to provision {provider_name}:{model_name}")
                all_available = False

        return all_available


# Singleton instance for global access
_model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """Get the global ModelManager instance."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager

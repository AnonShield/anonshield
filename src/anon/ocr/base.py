"""Abstract base class for OCR engines."""
from abc import ABC, abstractmethod


class OCREngine(ABC):
    """Interface for OCR backends used to extract text from images."""

    @abstractmethod
    def extract_text(self, image_bytes: bytes) -> str:
        """Extract text from raw image bytes. Returns empty string on failure."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the engine and its dependencies are installed."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Canonical name of this engine (e.g. 'tesseract')."""

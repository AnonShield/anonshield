"""
Security Module

This module centralizes security-related functionalities, including:
- Securely loading the secret key for HMAC operations.
- File type validation using magic bytes to prevent spoofing.
"""

import os
import logging
from typing import Optional, Any
import magic # type: ignore

from .core.protocols import SecretManager, FileValidator, AnonymizationOrchestrator

class SecretManagerImpl(SecretManager):
    """
    Manages the retrieval of the secret key for anonymization.
    Supports loading from an environment variable or a file.
    """
    def get_secret_key(self) -> Optional[str]:
        """
        Retrieves the secret key. Prioritizes a file path specified by
        ANON_SECRET_KEY_FILE, then falls back to ANON_SECRET_KEY environment variable.
        """
        # Priority 1: From a file path specified by ANON_SECRET_KEY_FILE
        key_file_path = os.environ.get("ANON_SECRET_KEY_FILE")
        if key_file_path:
            if os.path.exists(key_file_path):
                try:
                    with open(key_file_path, 'r') as f:
                        secret = f.read().strip()
                        if secret:
                            logging.info("Secret key loaded successfully from file.")
                            return secret
                        else:
                            logging.error(f"Secret key file '{key_file_path}' is empty.")
                except IOError as e:
                    logging.error(f"Error reading secret key from file '{key_file_path}': {e}")
            else:
                logging.warning(f"Secret key file not found at '{key_file_path}'.")

        # Priority 2: From ANON_SECRET_KEY environment variable
        secret_key = os.environ.get("ANON_SECRET_KEY")
        if secret_key:
            logging.info("Secret key loaded successfully from environment variable.")
            return secret_key
        
        return None

class FileTypeValidator(FileValidator):
    """
    Validates file types based on magic bytes using python-magic.
    """
    MIME_TO_EXT_MAP = {
        "application/pdf": ".pdf",
        "application/json": ".json",
        "application/jsonl": ".jsonl", # Although not a standard MIME type, often used for JSON Lines
        "application/xml": ".xml",
        "text/plain": ".txt",
        "text/csv": ".csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx", # .xlsx
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx", # .docx
        "image/png": ".png",
        "image/jpeg": ".jpeg",
        "image/gif": ".gif",
        "image/bmp": ".bmp",
        "image/tiff": ".tiff",
        "image/webp": ".webp",
        # Add more mappings as needed
    }

    def get_file_extension_from_magic(self, file_path: str) -> Optional[str]:
        """
        Determines the true file extension based on magic bytes.
        """
        try:
            mime_type = magic.from_file(file_path, mime=True)
            return self.MIME_TO_EXT_MAP.get(mime_type, None)
        except Exception as e:
            logging.error(f"Error determining MIME type for '{file_path}': {e}")
            return None

    def get_processor(self, file_path: str, orchestrator: AnonymizationOrchestrator, **kwargs) -> Optional[Any]:
        """
        Delegates to the actual processor factory after validating file type.
        This method will be integrated with the existing get_processor logic in processors.py.
        """
        # This is a placeholder. The actual logic for selecting the processor
        # will remain in processors.py, but this validator can enforce security checks
        # before that selection.
        logging.debug(f"Validating file type for {file_path}")
        true_ext = self.get_file_extension_from_magic(file_path)
        if not true_ext:
            logging.warning(f"Could not determine true file type for {file_path} or unsupported type.")
            return None

        # Compare true_ext with the file's declared extension (os.path.splitext)
        # Or simply pass the true_ext to the get_processor for it to use.
        # For now, this just ensures the type is recognizable.
        
        # This part will be completed in Sprint 1 (task 12)
        from ..processors import get_processor as original_get_processor
        return original_get_processor(file_path, orchestrator, detected_ext=true_ext, **kwargs)

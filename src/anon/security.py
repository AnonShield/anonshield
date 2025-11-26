"""
Security Module

This module centralizes security-related functionalities, including:
- Securely loading the secret key for HMAC operations.
- File type validation using magic bytes to prevent spoofing.
"""

import os
import logging
from typing import Optional

from .core.protocols import SecretManager

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
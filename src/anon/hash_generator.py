import hashlib
import hmac
import logging
from typing import Tuple, Optional

from .config import SECRET_KEY

class HashGenerator:
    """
    Generates secure HMAC-SHA256 based slugs for anonymization.
    Encapsulates the hashing logic, ensuring consistency and security.
    """

    def __init__(self):
        if not SECRET_KEY:
            logging.warning("SECRET_KEY is not set. Hashing operations will raise an error if performed.")

    def generate_slug(self, text: str, slug_length: Optional[int] = None) -> Tuple[str, str]:
        """
        Generates a display hash (slug) and a full hash for a given text.
        
        Args:
            text: The original text to hash.
            slug_length: The desired length of the display hash. If None, the full hash is used.
            
        Returns:
            A tuple containing (display_hash, full_hash).
        
        Raises:
            ValueError: If SECRET_KEY is not set.
        """
        if not SECRET_KEY:
            raise ValueError("SECRET_KEY environment variable is not set. Cannot generate hash.")

        clean_text = " ".join(text.split()).strip()
        
        full_hash = hmac.new(
            SECRET_KEY.encode(), 
            clean_text.encode(), 
            hashlib.sha256
        ).hexdigest()
        
        display_hash = full_hash[:slug_length] if slug_length is not None else full_hash
        
        return display_hash, full_hash
import hashlib
import hmac
import logging
from typing import Tuple, Optional

from .config import SECRET_KEY

class HashGenerator:
    """
    Generates secure HMAC-SHA256 based slugs for anonymization.
    Encapsulates the hashing logic, ensuring consistency and security.

    The key defaults to the process-wide SECRET_KEY (read once at import). Callers
    that receive a key per request (the web worker) pass it explicitly, because
    changing os.environ after import does not change SECRET_KEY.
    """

    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or SECRET_KEY
        if not self.secret_key:
            logging.warning("SECRET_KEY is not set. Hashing operations will raise an error if performed.")

    def generate_slug(self, text: str, slug_length: Optional[int] = None) -> Tuple[str, str]:
        """
        Generates a display hash (slug) and a full hash for a given text.

        Args:
            text: The original text to hash.
            slug_length: The desired length of the display hash. If None, the full hash is used.
                If 0, no hash is computed and no key is needed (entity-type-only output).

        Returns:
            A tuple containing (display_hash, full_hash).

        Raises:
            ValueError: If SECRET_KEY is not set and a hash is needed.
        """
        if slug_length == 0:
            return "", ""

        if not self.secret_key:
            raise ValueError("SECRET_KEY environment variable is not set. Cannot generate hash.")

        clean_text = " ".join(text.split()).strip()

        full_hash = hmac.new(
            self.secret_key.encode(),
            clean_text.encode(),
            hashlib.sha256
        ).hexdigest()

        display_hash = full_hash[:slug_length] if slug_length is not None else full_hash

        return display_hash, full_hash

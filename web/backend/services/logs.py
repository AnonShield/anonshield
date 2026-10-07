"""Third-party log lines that say nothing to the person running AnonShield."""
import logging


def quiet_third_party_logs() -> None:
    """Presidio warns on every start once per recognizer of another language,
    and the Hugging Face Hub about unauthenticated downloads of public models;
    the command line (anon.py) silences the same loggers."""
    for name in ("presidio-analyzer", "presidio-anonymizer", "huggingface_hub"):
        logging.getLogger(name).setLevel(logging.ERROR)

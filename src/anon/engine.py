# src/anon/engine.py

import hashlib
import hmac
import re
from typing import Dict, List, Optional, Union, Tuple
import logging

import pandas as pd  # type: ignore
import spacy  # type: ignore
import torch  # type: ignore
from presidio_analyzer import (  # type: ignore
    AnalyzerEngine,
    Pattern,
    PatternRecognizer,
    RecognizerResult,
)
from presidio_analyzer.batch_analyzer_engine import (  # type: ignore
    BatchAnalyzerEngine,
)
from presidio_analyzer.nlp_engine import (  # type: ignore
    NerModelConfiguration,
    SpacyNlpEngine,
    TransformersNlpEngine,
)
from presidio_anonymizer import AnonymizerEngine, OperatorConfig  # type: ignore
from presidio_anonymizer.operators import Operator, OperatorType  # type: ignore

from .config import (
    SECRET_KEY,
    TRANSFORMER_MODEL,
    ProcessingLimits,
    DefaultSizes,
)
from .database import DatabaseContext
from .cache_manager import CacheManager
from .hash_generator import HashGenerator
from .strategies import strategy_factory
from .entity_detector import EntityDetector
from .core.protocols import EntityStorage, CacheStrategy, HashingStrategy, AnonymizationStrategy


SUPPORTED_LANGUAGES = {
    "ca": "Catalan", "zh": "Chinese", "hr": "Croatian", "da": "Danish",
    "nl": "Dutch", "en": "English", "fi": "Finnish", "fr": "French",
    "de": "German", "el": "Greek", "it": "Italian", "ja": "Japanese",
    "ko": "Korean", "lt": "Lithuanian", "mk": "Macedonian", "nb": "Norwegian Bokmål",
    "pl": "Polish", "pt": "Portuguese", "ro": "Romanian", "ru": "Russian",
    "sl": "Slovenian", "es": "Spanish", "sv": "Swedish", "uk": "Ukrainian"
}


# ---------------------------------------------------------------------------
# Module-level engine cache — keyed by (transformer_model, lang).
# TransformersNlpEngine takes 30-60 s to load; caching it means the second
# job with the same model is near-instant. Safe to share because
# BatchAnalyzerEngine and AnonymizerEngine are stateless inference objects.
# ---------------------------------------------------------------------------
_ENGINE_CACHE: dict[str, tuple["BatchAnalyzerEngine", "AnonymizerEngine"]] = {}


# Some PT-BR NER tokenizers (e.g. pierreguillou/ner-bert-large-cased-pt-lenerbr)
# publish no model_max_length in tokenizer_config.json, so HF defaults to ~1e20.
# transformers 5.x pipeline.preprocess trusts that value and skips truncation;
# any doc >512 tokens then crashes BERT's positional embedding. spaCy's
# hf_token_pipe catches the exception and silently returns zero entities, so
# the anonymizer appears to "succeed" with everything passed through untouched.
# Monkey-patch _get_annotations to tokenize once, slide a 400-token window
# with 50-token overlap, and stitch char offsets back to the original doc.
_HF_TOKEN_PIPE_PATCHED = False


def _patch_hf_token_pipe_for_long_docs() -> None:
    global _HF_TOKEN_PIPE_PATCHED
    if _HF_TOKEN_PIPE_PATCHED:
        return
    try:
        from spacy_huggingface_pipelines.token_classification import HFTokenPipe
    except ImportError:
        return

    def _chunked_ner(hf_pipeline, text: str, chunk_tokens: int = 400, overlap: int = 50):
        tok = hf_pipeline.tokenizer
        enc = tok(text, return_offsets_mapping=True, add_special_tokens=False, truncation=False)
        offsets = enc["offset_mapping"]
        if len(offsets) <= chunk_tokens:
            return hf_pipeline(text)
        results, seen = [], set()
        stride = chunk_tokens - overlap
        i = 0
        while i < len(offsets):
            end = min(i + chunk_tokens, len(offsets))
            char_start = offsets[i][0]
            char_end = offsets[end - 1][1]
            chunk = text[char_start:char_end]
            for ent in hf_pipeline(chunk):
                gs, ge = ent["start"] + char_start, ent["end"] + char_start
                key = (gs, ge, ent["entity_group"])
                if key in seen:
                    continue
                seen.add(key)
                results.append({**ent, "start": gs, "end": ge})
            if end >= len(offsets):
                break
            i += stride
        return results

    def _patched_get_annotations(self, docs):
        import warnings as _w
        if len(docs) > 1:
            try:
                return [_chunked_ner(self.hf_pipeline, d.text) for d in docs]
            except Exception:
                _w.warn("Unable to process texts as batch, backing off individually")
        out = []
        for d in docs:
            try:
                out.append(_chunked_ner(self.hf_pipeline, d.text))
            except Exception as exc:
                excerpt = d.text if len(d.text) < 100 else d.text[:100] + "..."
                _w.warn(f"Unable to process, skipping annotation for doc '{excerpt}': {exc}")
                out.append([])
        return out

    HFTokenPipe._get_annotations = _patched_get_annotations
    _HF_TOKEN_PIPE_PATCHED = True
    logging.info("Patched spacy_huggingface_pipelines.HFTokenPipe with sliding-window chunker.")


_patch_hf_token_pipe_for_long_docs()


def warm_up_model(
    transformer_model: str = "Davlan/xlm-roberta-base-ner-hrl",
    lang: str = "en",
) -> None:
    """Pre-load a transformer model into the engine cache.

    Call this at worker startup (Celery worker_ready signal) so the model is
    already in memory before the first job arrives.
    """
    import logging as _log
    logger = _log.getLogger(__name__)
    cache_key = f"{transformer_model}:{lang}"
    if cache_key in _ENGINE_CACHE:
        logger.info("warm_up_model: '%s' already cached — skipping.", transformer_model)
        return
    logger.info("warm_up_model: loading '%s' (lang=%s) …", transformer_model, lang)
    try:
        lang_model_map = {"pt": "pt_core_news_lg", "en": "en_core_web_lg"}
        effective_lang = lang if lang in lang_model_map else "en"
        spacy_model_name = lang_model_map.get(effective_lang, f"{effective_lang}_core_news_lg")
        trf_model_config = [
            {"lang_code": effective_lang,
             "model_name": {"spacy": spacy_model_name, "transformers": transformer_model}}
        ]
        from .model_registry import get_entity_mapping
        entity_mapping = get_entity_mapping(transformer_model)
        ner_config = NerModelConfiguration(
            model_to_presidio_entity_mapping=entity_mapping,
            aggregation_strategy="max",
            labels_to_ignore=["O"],
        )
        nlp_engine = TransformersNlpEngine(models=trf_model_config, ner_model_configuration=ner_config)
        core_analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en", "pt"])
        for recognizer in load_custom_recognizers(langs=[effective_lang]):
            core_analyzer.registry.add_recognizer(recognizer)
        batch_analyzer = BatchAnalyzerEngine(analyzer_engine=core_analyzer)
        anonymizer = AnonymizerEngine()
        anonymizer.add_anonymizer(CustomSlugAnonymizer)
        _ENGINE_CACHE[cache_key] = (batch_analyzer, anonymizer)
        logger.info("warm_up_model: '%s' ready.", transformer_model)
    except Exception as exc:
        logger.warning("warm_up_model: failed for '%s': %s", transformer_model, exc)


# =============================================================================
# SHARED REGEX PATTERNS - DRY PRINCIPLE
# Used by both Presidio-based strategies and Standalone strategy
# =============================================================================

class RegexPatterns:
    """
    Centralized repository of all regex patterns used across the system.
    
    Design Principle: Don't Repeat Yourself (DRY)
    - Presidio strategies: Wrap these in Pattern objects with scores
    - Standalone strategy: Use these regexes directly
    
    Benefits:
    - Single source of truth for all pattern definitions
    - Easy to update and maintain
    - Consistent behavior across all strategies
    """
    
    # URL & Network Patterns
    URL = r"(?:https?://|ftp://|www\.)\S+?(?:\.(?:com|net|org|edu|gov|mil|int|br|app|dev|io|co|uk|de|fr|es|it|ru|cn|jp|kr|au|ca|mx|ar|cl|pe|co\.uk|com\.br|org\.br|gov\.br|edu\.br|net\.br|vercel\.app|herokuapp\.com|github\.io|gitlab\.io|netlify\.app|firebase\.app|appspot\.com|cloudfront\.net|amazonaws\.com|azure\.com|digitalocean\.com)|localhost|(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))(?::[0-9]{1,5})?(?:/[^\s]*)?"
    
    IPV4 = r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
    
    IPV6 = r"(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,7}:|::(?:ffff:)?(?:[0-9]{1,3}\.){3}[0-9]{1,3}|fe80:(?::[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]+"
    
    MAC_ADDRESS = r"\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b"
    
    PORT = r"\b\d{1,5}/(?:tcp|udp|sctp)\b"
    
    # Hostname Patterns
    FQDN = r"\b(?<!@)(?!Not-A\.Brand)([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b"
    CERT_CN = r"CN=([a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]|[a-f0-9]{8,16})\b"
    HEX_HOSTNAME = r"(?<![:/])(?<![vV])\b(?!20\d{10})[a-f0-9]{12,16}\b(?!\.)"
    
    # Hash Patterns (ordered by specificity)
    SHA512 = r"\b[0-9a-fA-F]{128}\b"
    SHA256 = r"\b[0-9a-fA-F]{64}\b(?![0-9a-fA-F])"
    SHA1 = r"\b[0-9a-fA-F]{40}\b(?![0-9a-fA-F])"
    MD5_COLON = r"\b([0-9a-fA-F]{2}:){15}[0-9a-fA-F]{2}\b"
    MD5 = r"\b[0-9a-fA-F]{32}\b(?![0-9a-fA-F])"
    
    # Security Identifiers
    CVE = r"\bCVE-\d{4}-\d{4,}\b"
    CPE = r"\bcpe:(?:/|2\.3:)[aho](?::[A-Za-z0-9\._\-~%*]+){2,}\b"
    CERT_SERIAL = r"\b[0-9a-fA-F]{16,40}\b"
    OID = r"\b[0-2](?:\.\d+){3,}\b"
    
    # Authentication & Secrets
    COOKIE_SESSION = r"=[a-zA-Z0-9\-_]{32,128}\b"
    AUTH_TOKEN = r"\b[a-zA-Z0-9]{32,128}\b"
    PASSWORD_CONTEXT = r"(?:password|passwd|pwd|secret|api_key|apikey|access_key|client_secret)=([^\",;'\s]{4,128})\b"
    USERNAME_CONTEXT = r"(?:user|username|uid|login|user_id)=([a-zA-Z0-9_.-]{2,64})\b"
    
    # PII Patterns
    EMAIL = r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
    PHONE = r"\b(?:\+?\d{1,3}[-. ]?)?\(?\d{2,3}\)?[-. ]?\d{4,5}[-. ]?\d{4}\b"
    CPF = r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"
    CREDIT_CARD = r"\b(?:\d{4}[- ]?){3}\d{4}\b"
    UUID = r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
    
    # Certificate & Cryptographic Patterns
    CERT_PEM = r"-----BEGIN CERTIFICATE-----[A-Za-z0-9+/=\n\r]{50,8000}-----END CERTIFICATE-----"
    CERT_REQUEST_PEM = r"-----BEGIN CERTIFICATE REQUEST-----[A-Za-z0-9+/=\n\r]{50,4000}-----END CERTIFICATE REQUEST-----"
    PRIVATE_KEY_PEM = r"-----BEGIN (?:RSA |DSA |EC )?PRIVATE KEY-----[A-Za-z0-9+/=\n\r]{50,4000}-----END (?:RSA |DSA |EC )?PRIVATE KEY-----"
    CERT_DER = r"\bMII[A-Za-z0-9+/=\n]{100,2000}\b"
    CERT_THUMBPRINT = r"(?:thumbprint|sha1|sha256)[:=\s]+[0-9a-fA-F]{40,128}"
    
    RSA_MODULUS = r"(?:Modulus|n)[:=\s]+[0-9a-fA-F]{128,512}"
    JWT = r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
    BASE64_KEY = r"(?:key|secret|password)[:=\s]+([A-Za-z0-9+/]{40,}={0,2})"
    
    # File System
    USER_PATH = r"(?:/home/|/Users/|C:\\Users\\)([^/\\]+)"

    # PGP
    PGP_BLOCK = r"-----BEGIN PGP (?:SIGNATURE|PUBLIC KEY BLOCK)-----[\s\S]{10,8000}?-----END PGP (?:SIGNATURE|PUBLIC KEY BLOCK)-----"

    # ─────────────────────────────────────────────────────────────────────────
    # Brazilian documents (PT-BR)
    #
    # Patterns match only the canonical formatted versions of each ID. Matching
    # raw digit sequences would create too many false positives on random text
    # (account numbers, line numbers, SKUs, etc.). The NER model complements
    # these by catching unformatted IDs in context.
    # ─────────────────────────────────────────────────────────────────────────
    CNPJ            = r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"
    RG_SP           = r"\b\d{1,2}\.\d{3}\.\d{3}-[0-9Xx]\b"
    CEP             = r"\b\d{5}-\d{3}\b"
    PIS_PASEP       = r"\b\d{3}\.\d{5}\.\d{2}-\d\b"
    TITULO_ELEITOR  = r"\b\d{4}\s\d{4}\s\d{4}\b"
    MONEY_BRL       = r"R\$\s?\d{1,3}(?:\.\d{3})*(?:,\d{2})?"
    DATE_BR         = r"\b(?:0?[1-9]|[12]\d|3[01])/(?:0?[1-9]|1[0-2])/\d{4}\b"
    BANK_AGENCY     = r"(?i)(?:ag[êe]ncia|ag\.?)\s*:?\s*\d{4,5}[-\s]?\d?\b"
    BANK_ACCOUNT    = r"(?i)(?:conta(?:\s+corrente|\s+poupan[çc]a)?|c/c|cc)\s*:?\s*\d{4,10}[-\s]?\d?\b"


class CustomSlugAnonymizer(Operator):
    """
    Custom Presidio operator that replaces text with an HMAC-based slug.
    """
    def operate(self, text: str, params: dict | None = None) -> str:
        """Replace entity text with an HMAC-based slug.

        Args:
            text: The raw entity text detected by Presidio.
            params: Operator parameters including hash_generator, entity_type,
                custom_slug_length, and entity_collector.

        Returns:
            A pseudonym string of the form ``[ENTITY_TYPE_hash]``, or
            ``[ENTITY_TYPE]`` when slug_length is 0.
        """
        # 1. Clean the text (remove extra spaces)
        clean_text = " ".join(text.split()).strip()
        
        
        params = params or {}
        entity_type = params.get("entity_type", "UNKNOWN")
        logging.debug(f"Anonymizing text '{clean_text}' with entity type '{entity_type}'.")

        hash_generator = params.get("hash_generator")
        if not hash_generator:
            raise ValueError("HashGenerator instance not provided in operator params.")

        # Try to get the slug length from our custom parameter first.
        slug_length = params.get("custom_slug_length", 8)
        logging.debug(f"CustomSlugAnonymizer.operate, received slug_length = {slug_length}")

        if slug_length == 0:
            if "entity_collector" in params:
                params["entity_collector"].append((entity_type, clean_text, "", "", False))
            return f"[{entity_type}]"

        display_hash, full_hash = hash_generator.generate_slug(clean_text, slug_length)

        if "entity_collector" in params:
            params["entity_collector"].append((entity_type, clean_text, display_hash, full_hash, True))

        return f"[{entity_type}_{display_hash}]"

    def validate(self, params: dict | None = None) -> None:
        """Validate operator parameters (no-op; validation is handled upstream)."""

    def operator_name(self) -> str:
        """Return the unique name identifying this Presidio operator."""
        return "custom_slug"

    def operator_type(self) -> OperatorType:
        """Return the Presidio operator type (Anonymize)."""
        return OperatorType.Anonymize


def load_custom_recognizers(langs: List[str], regex_priority: bool = False) -> List[PatternRecognizer]:
    """
    Loads Presidio PatternRecognizers using centralized regex patterns.
    
    Architecture: Uses RegexPatterns class as single source of truth (DRY principle).
    The same regexes are used by StandaloneStrategy without Presidio wrapping.
    """
    
    # Define a score boost for regex patterns if priority is enabled
    SCORE_BOOST = 0.15 if regex_priority else 0.0

    # --- 1. URL & NETWORK ---
    url_pattern = Pattern(
        name="URL Pattern", 
        regex=RegexPatterns.URL,
        score=0.7 + SCORE_BOOST
    )

    ip_pattern = Pattern(
        name="IPv4 Address Pattern", 
        regex=RegexPatterns.IPV4, 
        score=0.85 + SCORE_BOOST
    )
    
    ipv6_pattern = Pattern(
        name="IPv6 Address Pattern", 
        regex=RegexPatterns.IPV6, 
        score=0.6 + SCORE_BOOST
    )
    
    mac_pattern = Pattern(
        name="MAC Address", 
        regex=RegexPatterns.MAC_ADDRESS, 
        score=0.8 + SCORE_BOOST
    )
    
    port_pattern = Pattern(
        name="Port/Protocol",
        regex=RegexPatterns.PORT,
        score=0.85 + SCORE_BOOST
    )
    
    hostname_patterns = [
        Pattern(name="FQDN Pattern", regex=RegexPatterns.FQDN, score=0.6 + SCORE_BOOST),
        Pattern(name="Certificate CN Pattern", regex=RegexPatterns.CERT_CN, score=0.7 + SCORE_BOOST),
        Pattern(name="Standalone Hex Hostname Pattern", regex=RegexPatterns.HEX_HOSTNAME, score=0.6 + SCORE_BOOST),
    ]

    hash_patterns = [
        # Hash patterns ordered by specificity (most specific first)
        Pattern(name="SHA512 Hash", regex=RegexPatterns.SHA512, score=0.95 + SCORE_BOOST),
        Pattern(name="SHA256 Hash", regex=RegexPatterns.SHA256, score=0.92 + SCORE_BOOST),
        Pattern(name="SHA1 Hash", regex=RegexPatterns.SHA1, score=0.88 + SCORE_BOOST),
        Pattern(name="MD5 Colon-Separated Hash", regex=RegexPatterns.MD5_COLON, score=0.93 + SCORE_BOOST),
        Pattern(name="MD5 Hash", regex=RegexPatterns.MD5, score=0.88 + SCORE_BOOST),
    ]

    cve_pattern = Pattern(
        name="CVE ID Pattern",
        regex=RegexPatterns.CVE, 
        score=0.95 + SCORE_BOOST
    )

    cpe_pattern = Pattern(
        name="CPE String",
        regex=RegexPatterns.CPE,
        score=0.9 + SCORE_BOOST
    )
    
    serial_pattern = Pattern(
        name="Certificate Serial",
        regex=RegexPatterns.CERT_SERIAL,
        score=0.75 + SCORE_BOOST
    )
    
    oid_pattern = Pattern(
        name="OID Pattern",
        regex=RegexPatterns.OID, 
        score=0.95 + SCORE_BOOST
    )

    auth_token_patterns = [
        Pattern(name="Cookie/Session Assignment", regex=RegexPatterns.COOKIE_SESSION, score=0.9 + SCORE_BOOST),
        Pattern(name="Generic Auth Token", regex=RegexPatterns.AUTH_TOKEN, score=0.5 + SCORE_BOOST)
    ]

    password_pattern = Pattern(
        name="Contextual Password",
        regex=RegexPatterns.PASSWORD_CONTEXT,
        score=0.95 + SCORE_BOOST
    )

    username_pattern = Pattern(
        name="Contextual Username",
        regex=RegexPatterns.USERNAME_CONTEXT,
        score=0.8 + SCORE_BOOST
    )

    email_pattern = Pattern(
        name="Email Pattern", 
        regex=RegexPatterns.EMAIL, 
        score=1.0 + SCORE_BOOST
    )
    
    phone_pattern = Pattern(
        name="Phone Number Pattern",
        regex=RegexPatterns.PHONE,
        score=0.6 + SCORE_BOOST
    )

    cpf_pattern = Pattern(
        name="CPF Pattern", 
        regex=RegexPatterns.CPF, 
        score=0.85 + SCORE_BOOST
    )

    cc_pattern = Pattern(
        name="Credit Card Pattern", 
        regex=RegexPatterns.CREDIT_CARD, 
        score=0.7 + SCORE_BOOST
    )

    uuid_pattern = Pattern(
        name="UUID Pattern", 
        regex=RegexPatterns.UUID, 
        score=0.8 + SCORE_BOOST
    )
    
    cert_patterns = [
        Pattern(name="Certificate PEM Block", regex=RegexPatterns.CERT_PEM, score=0.95 + SCORE_BOOST),
        Pattern(name="Certificate Request PEM Block", regex=RegexPatterns.CERT_REQUEST_PEM, score=0.95 + SCORE_BOOST),
        Pattern(name="Private Key PEM Block", regex=RegexPatterns.PRIVATE_KEY_PEM, score=0.95 + SCORE_BOOST),
        Pattern(name="Certificate Body DER", regex=RegexPatterns.CERT_DER, score=0.8 + SCORE_BOOST),
        Pattern(name="Certificate Thumbprint", regex=RegexPatterns.CERT_THUMBPRINT, score=0.85 + SCORE_BOOST),
    ]

    crypto_patterns = [
        Pattern(name="RSA Public Key Modulus", regex=RegexPatterns.RSA_MODULUS, score=0.8 + SCORE_BOOST),
        Pattern(name="JWT Token", regex=RegexPatterns.JWT, score=0.9 + SCORE_BOOST),
        Pattern(name="Base64 Encoded Key", regex=RegexPatterns.BASE64_KEY, score=0.7 + SCORE_BOOST),
    ]
    
    path_pattern = Pattern(
        name="User Home Path", 
        regex=RegexPatterns.USER_PATH, 
        score=0.6 + SCORE_BOOST
    )
    
    pgp_pattern = Pattern(
        name="PGP Block",
        regex=RegexPatterns.PGP_BLOCK,
        score=0.95 + SCORE_BOOST
    )

    # ── Brazilian documents (PT-BR only) ────────────────────────────────────
    br_cpf_pattern       = Pattern(name="BR CPF",        regex=RegexPatterns.CPF,            score=0.95 + SCORE_BOOST)
    br_cnpj_pattern      = Pattern(name="BR CNPJ",       regex=RegexPatterns.CNPJ,           score=0.95 + SCORE_BOOST)
    br_rg_pattern        = Pattern(name="BR RG (SP)",    regex=RegexPatterns.RG_SP,          score=0.80 + SCORE_BOOST)
    br_cep_pattern       = Pattern(name="BR CEP",        regex=RegexPatterns.CEP,            score=0.85 + SCORE_BOOST)
    br_pis_pattern       = Pattern(name="BR PIS/PASEP",  regex=RegexPatterns.PIS_PASEP,      score=0.90 + SCORE_BOOST)
    br_titulo_pattern    = Pattern(name="BR Título Eleitoral", regex=RegexPatterns.TITULO_ELEITOR, score=0.80 + SCORE_BOOST)
    br_money_pattern     = Pattern(name="BR BRL Amount", regex=RegexPatterns.MONEY_BRL,      score=0.90 + SCORE_BOOST)
    br_date_pattern      = Pattern(name="BR Date",       regex=RegexPatterns.DATE_BR,        score=0.60 + SCORE_BOOST)
    br_agency_pattern    = Pattern(name="BR Bank Agency",  regex=RegexPatterns.BANK_AGENCY,  score=0.80 + SCORE_BOOST)
    br_account_pattern   = Pattern(name="BR Bank Account", regex=RegexPatterns.BANK_ACCOUNT, score=0.80 + SCORE_BOOST)

    recognizers = []
    for lang in langs:
        recognizers.extend([
            PatternRecognizer(supported_entity="URL", patterns=[url_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="IP_ADDRESS", patterns=[ip_pattern, ipv6_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="HOSTNAME", patterns=hostname_patterns, supported_language=lang),
            PatternRecognizer(supported_entity="MAC_ADDRESS", patterns=[mac_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="FILE_PATH", patterns=[path_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="HASH", patterns=hash_patterns, supported_language=lang),
            PatternRecognizer(supported_entity="AUTH_TOKEN", patterns=auth_token_patterns, supported_language=lang),
            PatternRecognizer(supported_entity="CVE_ID", patterns=[cve_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="CPE_STRING", patterns=[cpe_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="CERT_SERIAL", patterns=[serial_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="CERTIFICATE", patterns=cert_patterns, supported_language=lang),
            PatternRecognizer(supported_entity="CRYPTOGRAPHIC_KEY", patterns=crypto_patterns, supported_language=lang),
            PatternRecognizer(supported_entity="PASSWORD", patterns=[password_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="USERNAME", patterns=[username_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="EMAIL_ADDRESS", patterns=[email_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="PHONE_NUMBER", patterns=[phone_pattern, cpf_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="CREDIT_CARD", patterns=[cc_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="UUID", patterns=[uuid_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="PGP_BLOCK", patterns=[pgp_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="PORT", patterns=[port_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="OID", patterns=[oid_pattern], supported_language=lang),
        ])
        if lang == "pt":
            recognizers.extend([
                PatternRecognizer(supported_entity="BR_CPF",       patterns=[br_cpf_pattern],     supported_language=lang),
                PatternRecognizer(supported_entity="BR_CNPJ",      patterns=[br_cnpj_pattern],    supported_language=lang),
                PatternRecognizer(supported_entity="BR_RG",        patterns=[br_rg_pattern],      supported_language=lang),
                PatternRecognizer(supported_entity="BR_CEP",       patterns=[br_cep_pattern],     supported_language=lang),
                PatternRecognizer(supported_entity="BR_PIS",       patterns=[br_pis_pattern],     supported_language=lang),
                PatternRecognizer(supported_entity="BR_TITULO_ELEITORAL", patterns=[br_titulo_pattern], supported_language=lang),
                PatternRecognizer(supported_entity="MONEY",        patterns=[br_money_pattern],   supported_language=lang),
                PatternRecognizer(supported_entity="DATE_TIME",    patterns=[br_date_pattern],    supported_language=lang),
                PatternRecognizer(supported_entity="BR_BANK_AGENCY",  patterns=[br_agency_pattern],  supported_language=lang),
                PatternRecognizer(supported_entity="BR_BANK_ACCOUNT", patterns=[br_account_pattern], supported_language=lang),
            ])
    return recognizers

class AnonymizationOrchestrator:
    """
    Coordinates the anonymization process by selecting and executing a strategy.
    This class is responsible for high-level workflow, dependency injection,
    and fallback mechanisms, but delegates the core logic to strategy objects.
    """

    def __init__(self,
                 lang: str,
                 db_context: Optional[EntityStorage],
                 allow_list: List[str],
                 entities_to_preserve: List[str],
                 slug_length: int = 8,
                 strategy: Optional[AnonymizationStrategy] = None,
                 strategy_name: Optional[str] = "presidio",
                 regex_priority: bool = False,
                 analyzer_engine: Optional[BatchAnalyzerEngine] = None,
                 anonymizer_engine: Optional[AnonymizerEngine] = None,
                 nlp_batch_size: int = DefaultSizes.NLP_BATCH_SIZE,
                 cache_manager: Optional[CacheStrategy] = None,
                 hash_generator: Optional[HashingStrategy] = None,
                 entity_detector: Optional[EntityDetector] = None,
                 slm_detector: Optional[AnonymizationStrategy] = None,
                 slm_detector_mode: str = "hybrid",
                 ner_data_generation: bool = False,
                 transformer_model: str = "Davlan/xlm-roberta-base-ner-hrl",
                 parallel_workers: int = 1,
                 ner_score_threshold: Optional[float] = None,
                 ner_aggregation_strategy: Optional[str] = None):

        self.lang = lang
        self.db_context = db_context
        self.allow_list = set(allow_list)
        self.entities_to_preserve = set(entities_to_preserve)
        self.slug_length = slug_length
        self.nlp_batch_size = nlp_batch_size
        self.regex_priority = regex_priority
        self.ner_data_generation = ner_data_generation
        self.transformer_model = transformer_model
        self.parallel_workers = parallel_workers
        from .config import NerDefaults
        self.ner_score_threshold = ner_score_threshold if ner_score_threshold is not None else NerDefaults.SCORE_THRESHOLD
        self.ner_aggregation_strategy = ner_aggregation_strategy or NerDefaults.AGGREGATION_STRATEGY

        self.total_entities_processed = 0
        self.entity_counts: Dict[str, int] = {}

        # --- Dependency Injection and Engine Setup ---
        self.cache_manager = cache_manager or CacheManager(use_cache=False, max_cache_size=0)
        self.hash_generator = hash_generator or HashGenerator()

        # Initialize Presidio engines for all strategies (xlm-roberta used by fast as well)
        if analyzer_engine and anonymizer_engine:
            self.analyzer_engine = analyzer_engine
            self.anonymizer_engine = anonymizer_engine
        elif strategy_name in ("slm", "standalone", "regex"):
            # SLM, Standalone, and Regex-only strategies don't need Presidio engines
            self.analyzer_engine = None
            self.anonymizer_engine = None
            logging.info(f"Skipping Presidio initialization for '{strategy_name}' strategy (Presidio-free mode).")
        else:
            # Initialize Presidio for presidio, filtered, and hybrid strategies
            self.analyzer_engine, self.anonymizer_engine = self._setup_engines()

        # If entity_detector was not provided, create a default one.
        if entity_detector:
            self.entity_detector = entity_detector
        else:
            custom_recognizers = load_custom_recognizers([self.lang], regex_priority=regex_priority)
            compiled_patterns = []
            for recognizer in custom_recognizers:
                entity_type = recognizer.supported_entities[0]
                if entity_type in self.entities_to_preserve:
                    continue
                for pattern in recognizer.patterns:
                    try:
                        compiled_patterns.append({
                            "label": entity_type,
                            "regex": re.compile(pattern.regex, flags=re.DOTALL | re.IGNORECASE),
                            "score": pattern.score
                        })
                    except re.error as e:
                        logging.warning(f"Invalid regex pattern skipped: {pattern.regex} - {e}")
            self.entity_detector = EntityDetector(
                compiled_patterns=compiled_patterns,
                entities_to_preserve=self.entities_to_preserve,
                allow_list=self.allow_list
            )

        # --- Strategy Initialization: Prefer injected strategy, fallback to factory ---
        if strategy:
            self.anonymization_strategy = strategy
            logging.info(f"Using injected anonymization strategy: '{strategy.__class__.__name__}'.")
        else:
            self.anonymization_strategy = strategy_factory(
                strategy_name=strategy_name,
                transformer_model=self.transformer_model,
                analyzer_engine=self.analyzer_engine,
                anonymizer_engine=self.anonymizer_engine,
                entity_detector=self.entity_detector,
                slm_detector=slm_detector,
                slm_detector_mode=slm_detector_mode,
                hash_generator=self.hash_generator,
                cache_manager=self.cache_manager,
                lang=self.lang,
                entities_to_preserve=self.entities_to_preserve,
                allow_list=self.allow_list,
                nlp_batch_size=self.nlp_batch_size,
                score_threshold=self.ner_score_threshold,
            )
            logging.info(f"Anonymization strategy '{strategy_name}' initialized via factory.")


    def _setup_engines(self) -> tuple[BatchAnalyzerEngine, AnonymizerEngine]:
        """Initializes the Presidio engines, switching between models based on `ner_data_generation`.

        Results are cached at module level keyed by (transformer_model, lang) so that
        subsequent jobs with the same model skip the 30-60 s load time entirely.
        NER data generation mode is never cached (rare, spaCy-only path).
        """
        logging.info("Setting up Presidio analyzer and anonymizer engines.")
        lang_model_map = {"pt": "pt_core_news_lg", "en": "en_core_web_lg"}

        effective_lang = self.lang if self.lang in lang_model_map else "en"
        spacy_model_name = lang_model_map.get(effective_lang, f"{effective_lang}_core_news_lg")

        if self.ner_data_generation:
            logging.info("NER data generation mode: Initializing SpacyNlpEngine for '%s'.", effective_lang)
            nlp_engine = SpacyNlpEngine(models=[{"lang_code": effective_lang, "model_name": spacy_model_name}])
            core_analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en", "pt"])
            for recognizer in load_custom_recognizers(langs=[effective_lang], regex_priority=self.regex_priority):
                core_analyzer.registry.add_recognizer(recognizer)
            batch_analyzer = BatchAnalyzerEngine(analyzer_engine=core_analyzer)
            anonymizer = AnonymizerEngine()
            anonymizer.add_anonymizer(CustomSlugAnonymizer)
            return batch_analyzer, anonymizer

        # --- Transformer path — check module-level cache first ---
        cache_key = f"{self.transformer_model}:{effective_lang}:{self.ner_aggregation_strategy}"
        if cache_key in _ENGINE_CACHE:
            logging.info("Engine cache hit for '%s' (lang=%s) — skipping model load.", self.transformer_model, effective_lang)
            return _ENGINE_CACHE[cache_key]

        logging.info("Engine cache miss — loading TransformersNlpEngine for '%s' (lang=%s).", self.transformer_model, effective_lang)
        trf_model_config = [
            {"lang_code": effective_lang,
             "model_name": {"spacy": spacy_model_name, "transformers": self.transformer_model}}
        ]

        from .model_registry import get_entity_mapping
        entity_mapping = get_entity_mapping(self.transformer_model)

        ner_config = NerModelConfiguration(
            model_to_presidio_entity_mapping=entity_mapping,
            aggregation_strategy=self.ner_aggregation_strategy,
            labels_to_ignore=["O"],
        )
        nlp_engine = TransformersNlpEngine(models=trf_model_config, ner_model_configuration=ner_config)
        core_analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en", "pt"])

        for recognizer in load_custom_recognizers(langs=[effective_lang], regex_priority=self.regex_priority):
            core_analyzer.registry.add_recognizer(recognizer)

        batch_analyzer = BatchAnalyzerEngine(analyzer_engine=core_analyzer)
        anonymizer = AnonymizerEngine()
        anonymizer.add_anonymizer(CustomSlugAnonymizer)

        _ENGINE_CACHE[cache_key] = (batch_analyzer, anonymizer)
        logging.info("Presidio engines ready and cached for '%s'.", self.transformer_model)
        return batch_analyzer, anonymizer

    def anonymize_text(self, text: str, forced_entity_type: Optional[Union[str, List[str]]] = None) -> str:
        """Anonymize a single text string.

        Convenience wrapper around ``anonymize_texts`` for single-item use.

        Args:
            text: The raw input string to anonymize.
            forced_entity_type: If set, skip NER and treat the whole text as
                this entity type. Accepts a single type string or a list of
                candidate types.

        Returns:
            The anonymized string with PII replaced by pseudonyms.
        """
        if not isinstance(text, str) or not text.strip():
            return text
        anonymized_texts, _ = self.anonymize_texts([text], forced_entity_type=forced_entity_type)
        return anonymized_texts[0]

    def anonymize_texts(self, texts: List[str], forced_entity_type: Optional[Union[str, List[str]]] = None) -> List[str]:
        """
        Anonymizes a list of texts and saves the generated entity mappings to the database.
        This method dispatches to the appropriate internal method, collects all generated
        entities, and handles micro-batching persistence and entity counting.
        """
        # Use parallel processing if enabled
        if self.parallel_workers > 1 and len(texts) > self.parallel_workers:
            return self._anonymize_texts_parallel(texts, forced_entity_type)
        
        # Single-threaded processing (original implementation)
        all_collected_entities: List[Tuple] = [] # Orchestrator's master collector for micro-batching
        operator_params = {
            "hash_generator": self.hash_generator,
            "custom_slug_length": self.slug_length,
            # entity_collector will be passed to CustomSlugAnonymizer via operator_params in strategies
        }

        logging.debug(f"Anonymizing {len(texts)} texts using strategy: '{self.anonymization_strategy.__class__.__name__}'. Forced entity type: '{forced_entity_type}'")
        
        anonymized_results: List[str]
        collected_from_current_run: List[Tuple] = []

        if isinstance(forced_entity_type, list):
            logging.debug("Dispatching to _anonymize_texts_pick_one strategy.")
            anonymized_results, collected_from_current_run = self._anonymize_texts_pick_one(texts, forced_entity_type, operator_params)
        elif isinstance(forced_entity_type, str):
            logging.debug("Dispatching to _anonymize_texts_forced_type strategy.")
            anonymized_results, collected_from_current_run = self._anonymize_texts_forced_type(texts, forced_entity_type, operator_params)
        else:
            anonymized_results, collected_from_current_run = self.anonymization_strategy.anonymize(texts, operator_params)

        all_collected_entities.extend(collected_from_current_run)
        
        # Implement micro-batching: save entities if the collector grows large
        if self.db_context and len(all_collected_entities) >= ProcessingLimits.MICRO_BATCH_SAVE_SIZE:
            self._save_and_clear_entities(all_collected_entities)

        # --- FALLBACK ARCHITECTURE ---
        if len(anonymized_results) != len(texts):
            logging.warning(
                "Batch integrity failure detected (Input: %d vs Output: %d). "
                "Triggering Safe Fallback Mechanism.",
                len(texts), len(anonymized_results)
            )
            # The fallback will manage its own entity collection and saving.
            anonymized_results, collected_from_fallback = self._safe_fallback_processing(texts, operator_params, forced_entity_type)
            all_collected_entities.extend(collected_from_fallback) # Add any entities collected during fallback

        # --- DATABASE PERSISTENCE (Final Flush) ---
        # Any remaining entities from fallback or prior micro-batches will be flushed here.
        self._save_and_clear_entities(all_collected_entities) 

        return anonymized_results

    def _safe_fallback_processing(self, texts: List[str], operator_params: Optional[Dict], forced_entity_type: Optional[Union[str, List[str]]]) -> Tuple[List[str], List[Tuple]]:
        """
        Fallback Method: Processes item by item to ensure atomicity and alignment,
        with a circuit breaker to prevent runaway failures.
        """
        fallback_results = []
        collected_entities_fallback: List[Tuple] = []
        failure_count = 0
        # Circuit breaker activates if a defined percentage of the batch fails.
        failure_threshold = max(
            ProcessingLimits.CIRCUIT_BREAKER_MIN_FAILURES,
            int(len(texts) * ProcessingLimits.CIRCUIT_BREAKER_FAILURE_RATE)
        )

        for text in texts:
            single_item_collected_entities: List[Tuple] = []
            single_item_operator_params = operator_params.copy() if operator_params else {}
            single_item_operator_params["entity_collector"] = single_item_collected_entities # Pass collector to the operator
            
            single_anonymized_list = []
            
            try:
                # Re-use existing dispatch logic to keep it DRY
                if isinstance(forced_entity_type, list):
                    single_anonymized_list, collected_for_item = self._anonymize_texts_pick_one([text], forced_entity_type, single_item_operator_params)
                elif isinstance(forced_entity_type, str):
                    single_anonymized_list, collected_for_item = self._anonymize_texts_forced_type([text], forced_entity_type, single_item_operator_params)
                else:
                    # Use the strategy for the single text
                    single_anonymized_list, collected_for_item = self.anonymization_strategy.anonymize([text], single_item_operator_params)

                if collected_for_item:
                    collected_entities_fallback.extend(collected_for_item)
                    # Micro-batch save for fallback items
                    if self.db_context and len(collected_entities_fallback) >= ProcessingLimits.MICRO_BATCH_SAVE_SIZE:
                        self._save_and_clear_entities(collected_entities_fallback)

                if not single_anonymized_list:
                    fallback_results.append(text) 
                else:
                    fallback_results.append(single_anonymized_list[0])

            except Exception as e:
                logging.error(f"Fallback failed for a specific item: {str(e)[:100]}...", exc_info=True)
                fallback_results.append(text)
                failure_count += 1
                if failure_count > failure_threshold:
                    logging.critical(
                        f"Circuit breaker tripped! More than {failure_threshold} items failed in fallback processing. "
                        "Aborting processing for this batch to prevent further errors."
                    )
                    # Re-raise the last exception to halt processing of this file
                    raise e
        
        return fallback_results, collected_entities_fallback


    def _anonymize_texts_pick_one(self, texts: List[str], entity_types: List[str], operator_params: Optional[Dict] = None) -> Tuple[List[str], List[Tuple]]:
        anonymized_list = []
        collected_entities_from_pick_one: List[Tuple] = []
        if operator_params is None: operator_params = {}
        
        analyzer_results_iterator = self.analyzer_engine.analyze_iterator(
            texts, language=self.lang, entities=entity_types
        )

        for text, analyzer_results in zip(texts, analyzer_results_iterator):
            if not analyzer_results:
                anonymized_list.append(text)
                continue
            
            best_result: RecognizerResult = max(analyzer_results, key=lambda r: r.score)
            anonymized_text_list, collected_from_forced = self._anonymize_texts_forced_type([text], best_result.entity_type, operator_params)
            anonymized_list.append(anonymized_text_list[0])
            collected_entities_from_pick_one.extend(collected_from_forced)
            
        return anonymized_list, collected_entities_from_pick_one

    def _anonymize_texts_forced_type(self, texts: List[str], entity_type: str, operator_params: Optional[Dict] = None) -> Tuple[List[str], List[Tuple]]:
        anonymized_list = []
        collected_entities_from_forced: List[Tuple] = []
        if operator_params is None: operator_params = {}
        
        for text in texts:
            if not isinstance(text, str) or not text.strip():
                anonymized_list.append(text)
                continue

            clean_text = " ".join(text.split()).strip()
            
            cache_key = f"forced_{entity_type}_{clean_text}"
            cached_value = self.cache_manager.get(cache_key) # Use CacheManager
            if cached_value:
                anonymized_list.append(cached_value)
                # No entities collected if from cache
                continue

            if self.slug_length == 0:
                collected_entities_from_forced.append((entity_type, clean_text, "", ""))
                anonymized_text = f"[{entity_type}]"
            else:
                display_hash, full_hash = self.hash_generator.generate_slug(clean_text, self.slug_length)
                collected_entities_from_forced.append((entity_type, clean_text, display_hash, full_hash))
                anonymized_text = f"[{entity_type}_{display_hash}]"

            self.cache_manager.add(cache_key, anonymized_text) # Use CacheManager
            anonymized_list.append(anonymized_text)
        return anonymized_list, collected_entities_from_forced

    def detect_entities(self, texts: List[str]) -> List[dict]:
        """Detect PII entities in a list of texts using the Presidio analyzer.

        Args:
            texts: Input strings to analyze.

        Returns:
            A list of dicts, one per text that contains at least one entity.
            Each dict has keys ``text`` (original) and ``labels`` (list of
            recognized entity dicts with ``label``, ``start``, ``end``).
        """
        if not texts:
            return []

        logging.debug(f"Detecting entities for {len(texts)} texts using analyzer_engine.")
        
        results = []
        
        # Get all supported entities, but filter out those the user wants to preserve.
        if self.analyzer_engine and self.analyzer_engine.analyzer_engine:
            all_entities = self.analyzer_engine.analyzer_engine.get_supported_entities()
            entities_to_analyze = [e for e in all_entities if e not in self.entities_to_preserve]
        else:
            entities_to_analyze = []

        analyzer_results_iterator = self.analyzer_engine.analyze_iterator(
            texts,
            language=self.lang,
            entities=entities_to_analyze,
            allow_list=self.allow_list,
            score_threshold=0.1
        )

        for i, analyzer_results in enumerate(analyzer_results_iterator):
            text = texts[i]
            # Even if there are no PIIs, we might want to return the text.
            # The current NER implementation expects a "label" key.
            # We will only append if entities are found.
            if analyzer_results:
                # Sort by start offset to ensure labels are ordered
                sorted_results = sorted(analyzer_results, key=lambda r: r.start)
                labels = [[res.start, res.end, res.entity_type] for res in sorted_results]
                results.append({"text": text, "label": labels})
        
        return results

    def _save_and_clear_entities(self, entities: List[Tuple]):
        """Counts entities for statistics and saves only those marked for persistence to the database."""
        if not entities:
            return
            
        # Sempre conta para estatísticas
        self._increment_entity_counters_for_batch(entities)
        
        # Filtra apenas as que devem ser persistidas (5º elemento da tupla)
        entities_to_persist = []
        for entity in entities:
            # Tuplas podem ter 4 elementos (antigas) ou 5 elementos (novas com should_persist)
            if len(entity) >= 5 and entity[4]:  # should_persist = True
                # Remove o flag antes de salvar (banco espera 4 elementos)
                entities_to_persist.append(entity[:4])
            elif len(entity) == 4:
                # Formato antigo sem flag, assume que deve persistir
                entities_to_persist.append(entity)
        
        if self.db_context and entities_to_persist:
            self.db_context.save_entities(entities_to_persist)
        
        entities.clear()  # Clear the list to free memory

    def _increment_entity_counters_for_batch(self, entities: List[Tuple]):
        """Increments internal counters for a batch of entities."""
        for entity in entities:
            entity_type = entity[0] # entity_type is the first element of the tuple
            self.total_entities_processed += 1
            self.entity_counts[entity_type] = self.entity_counts.get(entity_type, 0) + 1
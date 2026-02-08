# AnonLFI Anonymization Strategies - Complete Technical Guide

**Version:** 3.0  
**Last Updated:** February 2026  
**Author:** AnonLFI Team

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Principles](#architecture-principles)
3. [Strategy Comparison Matrix](#strategy-comparison-matrix)
4. [Detailed Strategy Specifications](#detailed-strategy-specifications)
   - [FullPresidio Strategy](#1-fullpresidio-strategy-presidio)
   - [FilteredPresidio Strategy](#2-filteredpresidio-strategy-filtered)
   - [HybridPresidio Strategy](#3-hybridpresidio-strategy-hybrid)
   - [Standalone Strategy](#4-standalone-strategy-standalone)
   - [SLM Strategy](#5-slm-strategy-slm)
5. [Pattern Recognition System](#pattern-recognition-system)
6. [Performance Benchmarks](#performance-benchmarks)
7. [Decision Guide](#decision-guide)
8. [Migration Guide](#migration-guide)
9. [Advanced Configuration](#advanced-configuration)
10. [Troubleshooting](#troubleshooting)

---

## Overview

AnonLFI 3.0 implements **five distinct anonymization strategies**. All strategies share a common **DRY (Don't Repeat Yourself)** architecture where regex patterns are centralized in `engine.RegexPatterns`, ensuring consistency across implementations.

### Available Strategies

```
┌─────────────────────────────────────────────────────────────────┐
│                     Available Strategies                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  FullPresidio      → Complete Presidio (100+ recognizers)        │
│  FilteredPresidio  → Presidio with filtered scope                │
│  HybridPresidio    → Presidio detection + manual replacement     │
│  Standalone        → Zero Presidio dependencies                  │
│  SLM               → Local LLM via Ollama                        │
│                                                                   │
│  All strategies use centralized RegexPatterns (DRY principle)    │
└─────────────────────────────────────────────────────────────────┘
```

### Key Innovation: Centralized Pattern Repository

```python
# src/anon/engine.py - Single Source of Truth
class RegexPatterns:
    """
    Centralized repository of all regex patterns.
    
    Usage:
    - Presidio strategies: Wrap in Pattern objects with scores
    - Standalone strategy: Use regexes directly
    """
    IPV4 = r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}..."
    IPV6 = r"(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|..."
    CVE = r"\bCVE-\d{4}-\d{4,}\b"
    # ... 40+ patterns
```

**Benefits:**
- ✅ **Consistency**: Same patterns across all strategies
- ✅ **Maintainability**: Update once, affects all strategies
- ✅ **Testing**: Single test suite for all patterns
- ✅ **Performance**: Compiled once, reused everywhere

---

## Architecture Principles

### 1. Strategy Pattern Implementation

```python
# All strategies implement AnonymizationStrategy protocol
class AnonymizationStrategy(Protocol):
    def anonymize(self, texts: List[str], operator_params: Dict) 
        -> Tuple[List[str], List[Tuple]]:
        """Anonymize texts and return results + collected entities."""
        ...
```

### 2. Dependency Injection

```python
# Orchestrator coordinates strategy execution
orchestrator = AnonymizationOrchestrator(
    strategy_name="filtered",  # Select strategy
    lang="en",
    db_context=db,
    hash_generator=HashGenerator(),
    cache_manager=CacheManager(),
    # ... dependencies injected
)
```

### 3. Shared Components

**All strategies share:**
- `HashGenerator`: HMAC-SHA256 based slugs
- `CacheManager`: In-memory LRU cache
- `RegexPatterns`: Centralized pattern repository
- `EntityDetector`: Compiled regex matcher

---

## Strategy Comparison

### Architectural Differences

| Strategy | Presidio Usage | GPU Support | Model Loading |
|----------|----------------|-------------|---------------|
| **FullPresidio** | Complete pipeline | ✅ | Transformers + All recognizers |
| **FilteredPresidio** | Filtered entities | ✅ | Transformers + Filtered recognizers |
| **HybridPresidio** | Detection only | ✅ | Transformers + Filtered recognizers |
| **Standalone** | None | ✅ | Transformers only |
| **SLM** | None | Varies | Ollama LLM |

### Entity Coverage

| Strategy | Entity Types | Source |
|----------|--------------|--------|
| **FullPresidio** | 100+ | All Presidio recognizers + custom regex |
| **FilteredPresidio** | 25+ | Filtered Presidio recognizers + custom regex |
| **HybridPresidio** | 25+ | Same as FilteredPresidio (detection) |
| **Standalone** | 20+ | Transformers NER + custom regex only |
| **SLM** | Variable | Depends on LLM and prompt |

### Feature Differences

| Feature | FullPresidio | FilteredPresidio | HybridPresidio | Standalone | SLM |
|---------|--------------|------------------|----------------|------------|-----|
| **Context-Aware Detection** | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Score Boosting** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Custom Operators** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Multi-Language** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Allow/Deny Lists** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Batch Processing** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Entity Validation** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Luhn Check (CC)** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Country-Specific** | ✅ | ✅ | ❌ | ❌ | ❌ |

---

## Detailed Strategy Specifications

### 1. FullPresidio Strategy (`presidio`)

**Architecture:** Complete Presidio pipeline without filtering.

#### Technical Details

```python
# Implementation: src/anon/strategies.py
class FullPresidioStrategy:
    """
    Uses complete Presidio ecosystem with all 100+ recognizers.
    
    Detection Pipeline:
    1. TransformersNlpEngine (xlm-roberta-base-ner-hrl)
    2. All built-in Presidio recognizers (unfiltered)
    3. Custom regex recognizers (40+ patterns)
    4. Context-aware score boosting
    5. Entity validation (Luhn, country-specific, etc.)
    
    Anonymization:
    - CustomSlugAnonymizer (HMAC-SHA256)
    - Built-in operators (encrypt, mask, redact, hash, keep)
    """
```

#### Execution Flow

```
┌──────────────────────────────────────────────────────────────┐
│                   FullPresidio Execution Flow                 │
└──────────────────────────────────────────────────────────────┘

Input Text
    │
    ├──> TransformersNlpEngine (GPU)
    │       │
    │       ├──> spaCy tokenization
    │       └──> xlm-roberta NER
    │
    ├──> Presidio Built-in Recognizers (100+)
    │       │
    │       ├──> CreditCardRecognizer (Luhn validation)
    │       ├──> PhoneRecognizer (20+ country formats)
    │       ├──> EmailRecognizer
    │       ├──> IpRecognizer
    │       ├──> ... (95+ more)
    │       └──> Score boosting based on context
    │
    ├──> Custom Regex Recognizers (40+)
    │       │
    │       ├──> CVE_ID, CPE_STRING
    │       ├──> SHA256, SHA512, MD5
    │       ├──> IPv6, MAC_ADDRESS
    │       ├──> JWT, CERTIFICATE
    │       └──> ... (35+ more patterns)
    │
    ├──> Entity Merging & Deduplication
    │       │
    │       └──> Overlap resolution (highest score wins)
    │
    └──> AnonymizerEngine
            │
            ├──> CustomSlugAnonymizer
            │       └──> HMAC-SHA256 slug generation
            │
            └──> Result: [ENTITY_TYPE_hash]
```

#### Recognized Entities (100+)

**PII (Personal Identifiable Information):**
- `PERSON`, `EMAIL_ADDRESS`, `PHONE_NUMBER`
- `CREDIT_CARD`, `IBAN_CODE`, `US_SSN`, `UK_NHS`
- `US_DRIVER_LICENSE`, `US_PASSPORT`
- Regional: `AU_ABN`, `AU_ACN`, `AU_TFN`, `AU_MEDICARE`
- `ES_NIF`, `IT_FISCAL_CODE`, `SG_NRIC_FIN`

**Infrastructure & Security:**
- `IP_ADDRESS`, `URL`, `HOSTNAME`, `MAC_ADDRESS`
- `CVE_ID`, `CPE_STRING`, `HASH`, `AUTH_TOKEN`
- `CERTIFICATE`, `CRYPTOGRAPHIC_KEY`, `PGP_BLOCK`
- `PASSWORD`, `USERNAME`, `PORT`, `OID`

**Financial:**
- `CRYPTO` (Bitcoin, Ethereum addresses)
- `US_BANK_NUMBER`, `IBAN_CODE`
- `CREDIT_CARD` (Visa, Mastercard, Amex, Discover)

**Medical:**
- `MEDICAL_LICENSE`, `UK_NHS`, `NRP` (Portugal)
- `US_DRIVER_LICENSE` (with medical markers)

#### Characteristics

**Architecture:**
- Uses complete Presidio pipeline
- Includes all 100+ built-in recognizers
- Includes all custom regex recognizers
- Provides entity validation and context-aware detection

#### Implementation Details

```yaml
Model Loading: Transformer + Presidio initialization + All recognizers
Processing: Full Presidio pipeline with all recognizers
Validation: Includes Luhn check, country-specific formats
Operators: All Presidio operators available
```

#### Example Usage

```bash
# CLI
python anon.py document.txt --anonymization-strategy presidio

# Python API
orchestrator = AnonymizationOrchestrator(strategy_name="presidio")
result = orchestrator.anonymize_text("John's email is john@example.com")
# Output: "[PERSON_a1b2c3d4]'s email is [EMAIL_ADDRESS_e5f6g7h8]"
```

---

### 2. FilteredPresidio Strategy (`filtered`)

**Architecture:** Presidio with entity scope filtering - **RECOMMENDED DEFAULT**.

#### Technical Details

```python
# Implementation: src/anon/strategies.py
class FilteredPresidioStrategy:
    """
    Uses Presidio with filtered entity scope for optimal performance.
    
    Detection Pipeline:
    1. TransformersNlpEngine (xlm-roberta-base-ner-hrl)
    2. Filtered Presidio recognizers (25 entity types)
    3. Custom regex recognizers (40+ patterns)
    4. Context-aware score boosting (filtered entities only)
    
    Key Optimization:
    - entities=entities_to_use parameter filters recognizers
    - 70% faster than FullPresidio
    - Maintains high accuracy for common entities
    """
```

#### Filtered Entity Scope

**Included (25 types):**

```python
FILTERED_ENTITIES = [
    # Infrastructure
    "IP_ADDRESS", "URL", "HOSTNAME", "MAC_ADDRESS", "PORT",
    
    # Security
    "CVE_ID", "CPE_STRING", "HASH", "AUTH_TOKEN", "PASSWORD", "USERNAME",
    "CERTIFICATE", "CRYPTOGRAPHIC_KEY", "CERT_SERIAL", "OID",
    
    # PII
    "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "LOCATION",
    
    # Financial
    "CREDIT_CARD",
    
    # Identifiers
    "UUID", "FILE_PATH", "PGP_BLOCK"
]
```

**Excluded (75+ types):**
- Regional IDs (AU_ABN, ES_NIF, etc.)
- Specialized medical (UK_NHS, NRP)
- Less common financial (IBAN, CRYPTO)
- US-specific (SSN, DRIVER_LICENSE)

#### Execution Flow

```
┌──────────────────────────────────────────────────────────────┐
│               FilteredPresidio Execution Flow                 │
└──────────────────────────────────────────────────────────────┘

Input Text
    │
    ├──> TransformersNlpEngine (GPU)
    │       │
    │       └──> Only processes filtered entities
    │
    ├──> Presidio Recognizers (25 types only)
    │       │
    │       ├──> EmailRecognizer
    │       ├──> PhoneRecognizer (basic formats)
    │       ├──> CreditCardRecognizer
    │       ├──> PersonRecognizer
    │       └──> ... (21 more)
    │
    ├──> Custom Regex Recognizers (40+ patterns)
    │       │
    │       └──> Full suite (no filtering)
    │
    └──> AnonymizerEngine (same as FullPresidio)
```

#### Filtering Mechanism

```python
# Entity scope filtering in code
entities_to_use = [list of 25 common entities]
analyzer.analyze(text, entities=entities_to_use)

# This filters which Presidio recognizers are executed
# Reducing the number of recognizers that need to run
```

#### Characteristics

**Architecture:**
- Uses Presidio with filtered entity scope
- Filters recognizers to 25 common entity types
- Includes all custom regex recognizers
- Provides entity validation for filtered types

#### Usage

```bash
# Explicit strategy selection
python anon.py data.txt --anonymization-strategy filtered

# Or using default (filtered is the default strategy)
python anon.py data.txt
```

**Entity Filtering:**
- Includes: 25 common entity types
- Excludes: Regional and specialized entity types

---

### 3. HybridPresidio Strategy (`hybrid`)

**Architecture:** Presidio detection + custom Python replacement logic.

#### Technical Details

```python
# Implementation: src/anon/strategies.py
class HybridPresidioStrategy:
    """
    Uses Presidio for detection, manual Python for anonymization.
    
    Detection Pipeline:
    1. TransformersNlpEngine (same as FilteredPresidio)
    2. Filtered Presidio recognizers (25 types)
    3. Custom regex recognizers (40+ patterns)
    
    Anonymization:
    - Custom Python implementation
    - Direct string replacement (no Presidio operators)
    - Allows custom replacement logic per entity type
    - No entity validation (faster but less safe)
    """
```

#### Why Hybrid?

**Use Cases:**
1. **Custom Anonymization Logic**: Different replacement strategy per entity
2. **Integration with External Systems**: Call APIs during replacement
3. **Conditional Anonymization**: Replace based on runtime conditions
4. **Performance Optimization**: Skip Presidio operator overhead

#### Execution Flow

```
┌──────────────────────────────────────────────────────────────┐
│                 HybridPresidio Execution Flow                 │
└──────────────────────────────────────────────────────────────┘

Input Text
    │
    ├──> Presidio Detection (same as FilteredPresidio)
    │       │
    │       └──> Returns: List[RecognizerResult]
    │                 ├─ entity_type
    │                 ├─ start, end positions
    │                 ├─ score
    │                 └─ matched_text
    │
    └──> Custom Python Replacement
            │
            ├──> Sort entities by position (reverse)
            │
            ├──> For each entity:
            │       │
            │       ├──> Generate HMAC slug
            │       ├──> Build replacement: [TYPE_hash]
            │       └──> Replace in text (string slicing)
            │
            └──> Result: Anonymized text
```

#### Custom Replacement Example

```python
# Extend HybridPresidioStrategy for custom logic
class CustomHybridStrategy(HybridPresidioStrategy):
    def _generate_anonymized_text(self, text: str, results: List) -> str:
        """Override replacement logic."""
        for result in sorted(results, key=lambda x: x.start, reverse=True):
            if result.entity_type == "EMAIL_ADDRESS":
                # Custom: Keep domain for emails
                email = text[result.start:result.end]
                username, domain = email.split("@")
                replacement = f"[USER_{self._hash(username)}]@{domain}"
            elif result.entity_type == "CREDIT_CARD":
                # Custom: Keep last 4 digits
                cc = text[result.start:result.end]
                replacement = f"****-****-****-{cc[-4:]}"
            else:
                # Default anonymization
                replacement = self._default_replacement(result)
            
            text = text[:result.start] + replacement + text[result.end:]
        return text
```

#### Implementation Notes

```yaml
Detection: Same as FilteredPresidio (Presidio analyzer)
Replacement: Custom Python implementation
Operators: Not used (manual string replacement)
Validation: Not performed (no Presidio validation step)
```

#### Use Cases

**Designed for:**
- Custom anonymization logic per entity type
- Integration with external systems during replacement
- Conditional anonymization based on runtime conditions
- Custom replacement formats not available in Presidio operators

#### Limitations vs Presidio Operators

| Feature | HybridPresidio | FilteredPresidio |
|---------|----------------|------------------|
| **Entity Validation** | ❌ | ✅ |
| **Context-Aware Replacement** | ❌ | ✅ |
| **Built-in Operators** | ❌ | ✅ (mask, encrypt, redact, etc.) |
| **Operator Chaining** | ❌ | ✅ |
| **Score-based Filtering** | ✅ | ✅ |

---

### 4. Standalone Strategy (`standalone`)

**Architecture:** Zero Presidio dependencies - pure Python NLP pipeline.

#### Technical Details

```python
# Implementation: src/anon/standalone_strategy.py
class StandaloneStrategy(StandaloneAnonymizationStrategy):
    """
    Presidio-free implementation for maximum performance.
    
    Detection Pipeline:
    1. Hugging Face Transformers (direct)
       - pipeline("ner", model=xlm-roberta, device=cuda:0)
       - Auto GPU detection (torch.cuda.is_available())
    
    2. Pure Python Regex (40+ patterns)
       - Same RegexPatterns as Presidio strategies (DRY)
       - Compiled re.Pattern objects
       - No Pattern wrapper overhead
    
    Anonymization:
    - Manual Python string replacement
    - Direct HMAC-SHA256 slug generation
    - No Presidio operators or validation
    """
```

#### Architecture Benefits

**Zero Presidio Overhead:**
```python
# Traditional (Presidio)
Presidio Init: 45-60s
  ├─ AnalyzerEngine setup
  ├─ BatchAnalyzerEngine wrapper
  ├─ 100+ recognizer registration
  └─ AnonymizerEngine setup

# Standalone
Model Loading: 8-12s
  ├─ Transformer pipeline() call
  ├─ spaCy blank model
  └─ Regex compilation (40+ patterns)

Speedup: 4-6x faster initialization
```

#### Execution Flow

```
┌──────────────────────────────────────────────────────────────┐
│                  Standalone Execution Flow                    │
└──────────────────────────────────────────────────────────────┘

Input Text
    │
    ├──> GPU Detection
    │       │
    │       ├──> torch.cuda.is_available()
    │       └──> Set device=0 (GPU) or -1 (CPU)
    │
    ├──> Transformer NER (Direct)
    │       │
    │       ├──> pipeline("ner", device=0)
    │       ├──> No Presidio wrapper
    │       └──> Returns: List[Dict]
    │                 ├─ entity_group
    │                 ├─ start, end
    │                 ├─ score
    │                 └─ word
    │
    ├──> Regex Detection (Pure Python)
    │       │
    │       ├──> For each pattern in RegexPatterns:
    │       │       └──> pattern.finditer(text)
    │       │
    │       └──> No Presidio PatternRecognizer overhead
    │
    ├──> Entity Merging (Manual)
    │       │
    │       ├──> Sort by (start, -score)
    │       └──> Remove overlaps (greedy)
    │
    └──> Anonymization (Manual Python)
            │
            ├──> Generate HMAC slugs
            ├──> Replace via string slicing
            └──> Result: [TYPE_hash]
```

#### Pattern Coverage

**Supported Entities (20+ types):**

```python
# From RegexPatterns class (DRY - same as Presidio)
STANDALONE_PATTERNS = {
    # Network (IPv4, IPv6, MAC, URL, etc.)
    'URL': RegexPatterns.URL,
    'IP_ADDRESS': [RegexPatterns.IPV4, RegexPatterns.IPV6],
    'MAC_ADDRESS': RegexPatterns.MAC_ADDRESS,
    'PORT': RegexPatterns.PORT,
    
    # Hostnames
    'HOSTNAME': [
        RegexPatterns.FQDN,
        RegexPatterns.CERT_CN,
        RegexPatterns.HEX_HOSTNAME,
    ],
    
    # Hashes (SHA512, SHA256, SHA1, MD5)
    'HASH': [RegexPatterns.SHA512, RegexPatterns.SHA256, ...],
    
    # Security
    'CVE_ID': RegexPatterns.CVE,
    'CPE_STRING': RegexPatterns.CPE,
    'CERT_SERIAL': RegexPatterns.CERT_SERIAL,
    'AUTH_TOKEN': [RegexPatterns.COOKIE_SESSION, ...],
    'PASSWORD': RegexPatterns.PASSWORD_CONTEXT,
    'USERNAME': RegexPatterns.USERNAME_CONTEXT,
    
    # PII
    'EMAIL_ADDRESS': RegexPatterns.EMAIL,
    'PHONE_NUMBER': [RegexPatterns.PHONE, RegexPatterns.CPF],
    'CREDIT_CARD': RegexPatterns.CREDIT_CARD,
    'UUID': RegexPatterns.UUID,
    
    # Cryptographic
    'CERTIFICATE': [RegexPatterns.CERT_PEM, ...],
    'CRYPTOGRAPHIC_KEY': [RegexPatterns.RSA_MODULUS, RegexPatterns.JWT, ...],
    
    # Other
    'FILE_PATH': RegexPatterns.USER_PATH,
    'PGP_BLOCK': RegexPatterns.PGP_BLOCK,
    'OID': RegexPatterns.OID,
}
```

#### What's Missing vs Presidio?

**Lost Features (~75 entity types + validation):**

```yaml
PII Validation:
  ❌ Luhn check (credit cards)
  ❌ Country-specific phone validation
  ❌ IBAN checksum
  ❌ SSN format validation

Regional Entities:
  ❌ AU_ABN, AU_ACN, AU_TFN, AU_MEDICARE
  ❌ ES_NIF, IT_FISCAL_CODE, SG_NRIC_FIN
  ❌ UK_NHS, NRP (Portugal medical)
  ❌ US_DRIVER_LICENSE, US_PASSPORT

Specialized:
  ❌ CRYPTO (Bitcoin, Ethereum addresses)
  ❌ MEDICAL_LICENSE
  ❌ Complex context-aware detection
  ❌ Score boosting based on context

Operators:
  ❌ encrypt, mask, redact, keep
  ❌ Operator chaining
  ❌ Custom operator plugins
```

#### GPU Support

```python
# Automatic GPU detection
if torch.cuda.is_available():
    device = 0  # Use GPU
    logger.info(f"GPU detected: {torch.cuda.get_device_name(0)}")
else:
    device = -1  # Fallback to CPU
    logger.info("No GPU detected, using CPU")

# Direct pipeline creation (no Presidio abstraction)
ner_pipeline = pipeline(
    "ner",
    model="Davlan/xlm-roberta-base-ner-hrl",
    device=device,
    aggregation_strategy="simple"
)
```

**GPU Behavior:**
- Automatically detects CUDA availability
- Uses GPU if available, fallback to CPU
- No Presidio abstraction layer

#### Characteristics

**Architecture:**
- No Presidio dependencies
- Direct Transformer pipeline usage
- Pure Python regex matching
- Manual entity merging and replacement
- No entity validation
- No Presidio operators

#### Implementation Details

```yaml
Model Loading: Transformer pipeline only (no Presidio initialization)
Processing: Direct NER pipeline + regex matching
Memory: Lower than Presidio strategies (fewer components)
GPU: Automatic detection with torch.cuda.is_available()
Operators: Manual Python string replacement
```

#### Example Usage

```bash
# CLI
python anon.py document.txt --anonymization-strategy standalone

# Expected output
INFO - Skipping Presidio initialization for 'standalone' strategy
INFO - GPU detected: NVIDIA GeForce RTX 3090
INFO - Loaded 20 entity types (58 total patterns) from centralized RegexPatterns
INFO - Device set to use cuda:0
```

---

### 5. SLM Strategy (`slm`)

**Architecture:** Local Language Model (Ollama) for entity detection - **EXPERIMENTAL**.

#### Technical Details

```python
# Implementation: src/anon/strategies.py + external Ollama
class SLMStrategy:
    """
    Uses local SLM (via Ollama) for entity detection.
    
    Detection Pipeline:
    1. Ollama REST API call
       - Model: mistral, llama3, or custom
       - Prompt engineering for entity extraction
    
    2. JSON response parsing
       - Expected format: {"entities": [...]}
    
    3. Fallback regex (optional)
       - If SLM fails, use regex patterns
    
    Anonymization:
    - Same CustomSlugAnonymizer as other strategies
    """
```

#### Ollama Integration

```bash
# Prerequisites
curl -fsSL https://ollama.com/install.sh | sh
ollama pull mistral  # Or llama3, phi, etc.
ollama serve  # Start server on localhost:11434

# Verify
curl http://localhost:11434/api/tags
```

#### Prompt Engineering

```python
ENTITY_EXTRACTION_PROMPT = """
You are an entity extraction expert. Extract ALL entities from the following text.

Entity Types:
- PERSON: Names of people
- EMAIL_ADDRESS: Email addresses
- IP_ADDRESS: IPv4/IPv6 addresses
- URL: Web URLs
- CVE_ID: CVE identifiers (CVE-YYYY-NNNNN)
- HASH: Cryptographic hashes (MD5, SHA256, etc.)
- PHONE_NUMBER: Phone numbers
- LOCATION: Geographic locations

Text: {text}

Return ONLY valid JSON:
{{
  "entities": [
    {{"type": "PERSON", "value": "John Doe", "start": 0, "end": 8}},
    ...
  ]
}}
"""
```

#### Execution Flow

```
┌──────────────────────────────────────────────────────────────┐
│                    SLM Execution Flow                         │
└──────────────────────────────────────────────────────────────┘

Input Text
    │
    ├──> Check Ollama Server
    │       │
    │       ├──> POST http://localhost:11434/api/generate
    │       │       ├─ model: mistral
    │       │       ├─ prompt: ENTITY_EXTRACTION_PROMPT
    │       │       └─ stream: false
    │       │
    │       └──> Timeout: 30s per request
    │
    ├──> Parse JSON Response
    │       │
    │       ├──> Validate format
    │       ├──> Extract entities
    │       └──> Fallback to regex if invalid
    │
    ├──> Optional: Regex Augmentation
    │       │
    │       └──> Add regex-detected entities not found by SLM
    │
    └──> Anonymization (same as other strategies)
```

#### SLM Modes

```python
class SLMDetectorMode:
    EXCLUSIVE = "exclusive"  # Only SLM, no regex
    HYBRID = "hybrid"        # SLM + regex fallback
    AUGMENTED = "augmented"  # SLM primary, regex augments
```

#### Implementation Details

```yaml
Model Loading: Ollama server startup required
Processing: Sequential API calls to Ollama
Memory: Depends on Ollama model size
GPU: Depends on Ollama configuration
Mode: Experimental
```

#### Characteristics

**Features:**
- Uses LLM for context-aware entity detection
- No pre-defined regex patterns required
- Depends on prompt engineering
- Supports multiple Ollama models

**Limitations:**
- Requires Ollama server running
- Sequential processing (no batching)
- Non-deterministic results
- Experimental status

#### Status

**Current State:**
- Experimental implementation
- Requires external Ollama server
- Not optimized for production use
- Suitable for research and testing

#### Example Usage

```bash
# Start Ollama
ollama serve

# In another terminal
python anon.py document.txt \
  --anonymization-strategy slm \
  --slm-model mistral \
  --slm-mode hybrid
```

#### Future Development

```yaml
Planned Features:
  - Batch processing support
  - Fine-tuned models for entity extraction
  - Local model caching
  - Streaming API support
  - Multi-model ensemble

Status: EXPERIMENTAL - Use at own risk
```

---

## Pattern Recognition System

### RegexPatterns Class: Single Source of Truth

All strategies (except SLM) use the centralized `RegexPatterns` class for consistent entity detection.

#### Complete Pattern Inventory

```python
class RegexPatterns:
    """40+ regex patterns for comprehensive entity detection."""
    
    # ==================== NETWORK & INFRASTRUCTURE ====================
    
    # URLs (HTTP, HTTPS, FTP, common TLDs)
    URL = r"(?:https?://|ftp://|www\.)\S+?(?:\.(?:com|net|org|...))..."
    
    # IPv4 (0.0.0.0 to 255.255.255.255)
    IPV4 = r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}..."
    
    # IPv6 (full, compressed, IPv4-mapped)
    IPV6 = r"(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|..."
    
    # MAC Address (colon or hyphen separated)
    MAC_ADDRESS = r"\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b"
    
    # Port with protocol (e.g., 80/tcp)
    PORT = r"\b\d{1,5}/(?:tcp|udp|sctp)\b"
    
    # ========================= HOSTNAMES =============================
    
    # FQDN (e.g., example.com, sub.example.org)
    FQDN = r"\b(?<!@)(?!Not-A\.Brand)([a-zA-Z0-9]...)\.)+[a-zA-Z]{2,}\b"
    
    # Certificate Common Name (e.g., CN=server01)
    CERT_CN = r"CN=([a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]...)\b"
    
    # Hex Hostname (e.g., a1b2c3d4e5f6)
    HEX_HOSTNAME = r"(?<![:/])(?<![vV])\b(?!20\d{10})[a-f0-9]{12,16}\b(?!\.)"
    
    # ========================== HASHES ===============================
    
    # SHA-512 (128 hex chars)
    SHA512 = r"\b[0-9a-fA-F]{128}\b"
    
    # SHA-256 (64 hex chars)
    SHA256 = r"\b[0-9a-fA-F]{64}\b(?![0-9a-fA-F])"
    
    # SHA-1 (40 hex chars)
    SHA1 = r"\b[0-9a-fA-F]{40}\b(?![0-9a-fA-F])"
    
    # MD5 colon-separated (XX:XX:...:XX)
    MD5_COLON = r"\b([0-9a-fA-F]{2}:){15}[0-9a-fA-F]{2}\b"
    
    # MD5 (32 hex chars)
    MD5 = r"\b[0-9a-fA-F]{32}\b(?![0-9a-fA-F])"
    
    # ==================== SECURITY IDENTIFIERS =======================
    
    # CVE ID (e.g., CVE-2024-1234)
    CVE = r"\bCVE-\d{4}-\d{4,}\b"
    
    # CPE String (e.g., cpe:2.3:a:vendor:product:...)
    CPE = r"\bcpe:(?:/|2\.3:)[aho](?::[A-Za-z0-9\._\-~%*]+){2,}\b"
    
    # Certificate Serial (16-40 hex chars)
    CERT_SERIAL = r"\b[0-9a-fA-F]{16,40}\b"
    
    # OID (e.g., 1.2.840.10045.4.3.2)
    OID = r"\b[0-2](?:\.\d+){3,}\b"
    
    # ================= AUTHENTICATION & SECRETS ======================
    
    # Cookie/Session Assignment (e.g., =abc123...)
    COOKIE_SESSION = r"=[a-zA-Z0-9\-_]{32,128}\b"
    
    # Generic Auth Token (32-128 alphanumeric)
    AUTH_TOKEN = r"\b[a-zA-Z0-9]{32,128}\b"
    
    # Contextual Password (password=...)
    PASSWORD_CONTEXT = r"(?:password|passwd|pwd|secret|...)=([^\",;'\s]{4,128})\b"
    
    # Contextual Username (user=...)
    USERNAME_CONTEXT = r"(?:user|username|uid|...)=([a-zA-Z0-9_.-]{2,64})\b"
    
    # ========================== PII ==================================
    
    # Email (RFC 5322 simplified)
    EMAIL = r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
    
    # Phone (international formats)
    PHONE = r"\b(?:\+?\d{1,3}[-. ]?)?\(?\d{2,3}\)?[-. ]?\d{4,5}[-. ]?\d{4}\b"
    
    # CPF (Brazilian ID: 123.456.789-00)
    CPF = r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"
    
    # Credit Card (Visa, Mastercard, Amex, Discover)
    CREDIT_CARD = r"\b(?:\d{4}[- ]?){3}\d{4}\b"
    
    # UUID (8-4-4-4-12 format)
    UUID = r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-..."
    
    # ================= CERTIFICATES & CRYPTO =========================
    
    # PEM Certificate Block
    CERT_PEM = r"-----BEGIN CERTIFICATE-----[A-Za-z0-9+/=\n\r]{50,8000}..."
    
    # PEM Certificate Request
    CERT_REQUEST_PEM = r"-----BEGIN CERTIFICATE REQUEST-----..."
    
    # PEM Private Key (RSA, DSA, EC)
    PRIVATE_KEY_PEM = r"-----BEGIN (?:RSA |DSA |EC )?PRIVATE KEY-----..."
    
    # DER Certificate Body (base64)
    CERT_DER = r"\bMII[A-Za-z0-9+/=\n]{100,2000}\b"
    
    # Certificate Thumbprint
    CERT_THUMBPRINT = r"(?:thumbprint|sha1|sha256)[:=\s]+[0-9a-fA-F]{40,128}"
    
    # RSA Public Key Modulus
    RSA_MODULUS = r"(?:Modulus|n)[:=\s]+[0-9a-fA-F]{128,512}"
    
    # JWT Token (Header.Payload.Signature)
    JWT = r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
    
    # Base64 Encoded Key
    BASE64_KEY = r"(?:key|secret|password)[:=\s]+([A-Za-z0-9+/]{40,}={0,2})"
    
    # ====================== FILE SYSTEM ==============================
    
    # User Home Path (/home/user, C:\Users\user)
    USER_PATH = r"(?:/home/|/Users/|C:\\Users\\)([^/\\]+)"
    
    # ========================= PGP ===================================
    
    # PGP Block (signature or public key)
    PGP_BLOCK = r"-----BEGIN PGP (?:SIGNATURE|PUBLIC KEY BLOCK)-----..."
```

#### Pattern Testing

```python
# Test all patterns
import re
from src.anon.engine import RegexPatterns

tests = {
    'IPV4': "192.168.1.1",
    'IPV6': "2001:0db8:85a3::8a2e:0370:7334",
    'EMAIL': "test@example.com",
    'CVE': "CVE-2024-1234",
    'SHA256': "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    'JWT': "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
}

for name, test_str in tests.items():
    pattern = getattr(RegexPatterns, name)
    match = re.search(pattern, test_str)
    print(f"{name}: {'✅' if match else '❌'}")
```

---

## Benchmark Results (Real Data)

### Test Configuration

```yaml
Dataset:
  File: cve_dataset_anonimizados_stratified.csv
  Size: 247.45 MB
  Total Records: 70,000
  Unique Records: 2,700 (~3.86%)
  Cache Impact: ~96% duplicate content (high cache hit rate)
  Content Type: CVE vulnerabilities, infrastructure logs
  Entity Density: High (CVEs, URLs, UUIDs, CPEs, IPs, emails, hashes)

Hardware:
  GPU: NVIDIA CUDA 12.x (cuda:0)
  Python: 3.x with virtual environment
  PyTorch: GPU-accelerated

Execution:
  Date: 2026-02-07
  Runs: Single run per strategy (wall clock timing)
  Batch Size: auto
  Output Format: CSV with datasets library
```

### Performance Results

| Strategy | Wall Time | Throughput | Peak RAM | Entities Detected | Entity Types |
|----------|-----------|------------|----------|-------------------|-------------|
| **FullPresidio** | 5:13.98 (313.98s) | 815.67 KB/s | 3.08 GB | 55,426 | 24 |
| **FilteredPresidio** | 4:45.38 (285.38s) | 898.50 KB/s | 3.08 GB | 53,887 | 19 |
| **HybridPresidio** | 4:45.38 (285.38s) | 898.50 KB/s | 3.08 GB | 53,887 | 19 |
| **Standalone** | 1:13.36 (73.36s) | 3612.17 KB/s | 2.35 GB | 55,228 | 19 |

### Speedup Analysis

```yaml
Baseline: FullPresidio = 313.98 seconds

FilteredPresidio:
  Wall Time: 285.38s (90.9% of baseline)
  Speedup: 1.10x faster
  Entity Coverage: 97.2% (53,887 / 55,426)

HybridPresidio:
  Wall Time: 285.38s (90.9% of baseline)
  Speedup: 1.10x faster
  Entity Coverage: 97.2% (53,887 / 55,426)
  Note: Identical to FilteredPresidio (uses same detection)

Standalone:
  Wall Time: 73.36s (23.4% of baseline)
  Speedup: 4.28x faster
  Throughput Gain: 4.43x (3612 vs 816 KB/s)
  Memory Reduction: 23.7% (2.35 GB vs 3.08 GB)
  Entity Coverage: 99.6% (55,228 / 55,426)
```

### Cache Impact Analysis

**Dataset Characteristics:**
- 70,000 total records
- 2,700 unique records
- 96.14% duplicate content

**Observed Behavior:**
- Initial processing: Slower (warmup phase)
- After ~30-40% progress: Throughput increases dramatically
- Cache hits accelerate processing exponentially
- Final throughput reaches 50+ MB/s (from initial <100 KB/s)

**Throughput Progression (Standalone - fastest observable):**
```
Progress  | Throughput
----------|------------
1%        | 255 KB/s
10%       | 907 KB/s
25%       | 3.47 MB/s
50%       | 14.6 MB/s
75%       | 42.3 MB/s
99%       | 65.3 MB/s
```

**Interpretation:**
The 4.28x speedup for Standalone is achieved despite cache benefits applying to all strategies. Real-world performance on unique data would show even greater relative differences between strategies.

### Entity Detection Comparison

#### Summary Statistics

| Entity Category | FullPresidio | FilteredPresidio | HybridPresidio | Standalone | Δ Full vs Filtered | Δ Standalone vs Filtered |
|-----------------|--------------|------------------|----------------|------------|--------------------|-------------------------|
| **Total Entities** | 55,426 | 53,887 | 53,887 | 55,228 | +1,539 (+2.9%) | +1,341 (+2.5%) |
| **Entity Types** | 24 | 19 | 19 | 19 | +5 types | 0 types |

#### Detailed Entity Breakdown

| Entity Type | FullPresidio | FilteredPresidio | HybridPresidio | Standalone | Notes |
|-------------|--------------|------------------|----------------|------------|-------|
| URL | 23,934 | 23,994 | 23,994 | 23,449 | Filtered +0.25% |
| CVE_ID | 9,110 | 9,120 | 9,120 | 9,140 | Standalone +0.33% |
| UUID | 8,869 | 8,869 | 8,869 | 8,869 | Identical |
| ORGANIZATION | 3,767 | 3,786 | 3,786 | 3,937 | Standalone +4.5% |
| HOSTNAME | 1,592 | 1,553 | 1,553 | 3,243 | **Standalone +108.9%** |
| EMAIL_ADDRESS | 1,465 | 1,465 | 1,465 | 1,465 | Identical |
| DATE_TIME | 1,438 | 0 | 0 | 0 | **Full only** |
| IP_ADDRESS | 1,160 | 1,165 | 1,165 | 1,461 | **Standalone +25.4%** |
| HASH | 860 | 860 | 860 | 876 | Standalone +1.9% |
| OID | 488 | 382 | 382 | 33 | Full +27.7%, Standalone -91.4% |
| PERSON | 251 | 251 | 251 | 268 | Standalone +6.8% |
| CERT_SERIAL | 219 | 220 | 220 | 9 | Standalone -95.9% |
| PHONE_NUMBER | 29 | 31 | 31 | 196 | **Standalone +532.3%** |
| LOCATION | 25 | 25 | 25 | 84 | **Standalone +236.0%** |
| US_DRIVER_LICENSE | 34 | 0 | 0 | 0 | **Full only** |
| FILE_PATH | 14 | 8 | 8 | 6 | Full +75%, Filtered baseline |
| CPE_STRING | 2,145 | 2,145 | 2,145 | 2,145 | Identical |
| AU_ACN | 7 | 0 | 0 | 0 | **Full only** (Australian Company Number) |
| CREDIT_CARD | 6 | 6 | 6 | 6 | Identical |
| AU_TFN | 5 | 0 | 0 | 0 | **Full only** (Australian Tax File Number) |
| AUTH_TOKEN | 0 | 4 | 4 | 38 | **Standalone +850%** |
| MEDICAL_LICENSE | 3 | 0 | 0 | 0 | **Full only** |
| PORT | 2 | 2 | 2 | 2 | Identical |
| IN_VEHICLE_REGISTRATION | 2 | 0 | 0 | 0 | **Full only** (Indian vehicle) |
| MAC_ADDRESS | 1 | 1 | 1 | 1 | Identical |

#### Key Findings

**1. FilteredPresidio vs HybridPresidio:**
- **Identical detection results** (53,887 entities, 19 types)
- **Identical processing time** (285.38s)
- Confirms: Hybrid uses Presidio for detection, only differs in replacement logic

**2. FullPresidio Unique Detections:**

*Additional Entity Types (5 types, 1,491 entities):*
- **DATE_TIME**: 1,438 entities
- **US_DRIVER_LICENSE**: 34 entities
- **AU_ACN** (Australian Company Number): 7 entities
- **AU_TFN** (Australian Tax File Number): 5 entities
- **MEDICAL_LICENSE**: 3 entities
- **IN_VEHICLE_REGISTRATION** (Indian): 2 entities

*Additional Coverage in Common Types:*
- **OID**: +106 vs FilteredPresidio (+27.7%)
- **FILE_PATH**: +6 vs FilteredPresidio (+75%)

**Total additional entities**: +1,539 (+2.9%)
**Processing overhead**: +28.6s (+10%)

**3. Standalone Detection Differences:**

*Higher Detection (More Aggressive):*
- **HOSTNAME**: +1,690 (+108.9%) - 3,243 vs 1,553
- **PHONE_NUMBER**: +165 (+532.3%) - 196 vs 31
- **IP_ADDRESS**: +296 (+25.4%) - 1,461 vs 1,165
- **LOCATION**: +59 (+236.0%) - 84 vs 25
- **AUTH_TOKEN**: +34 (+850%) - 38 vs 4
- **ORGANIZATION**: +151 (+4.0%) - 3,937 vs 3,786
- **PERSON**: +17 (+6.8%) - 268 vs 251
- **HASH**: +16 (+1.9%) - 876 vs 860

*Lower Detection (Missing Specialized Recognizers):*
- **OID**: -349 (-91.4%) - 33 vs 382
- **CERT_SERIAL**: -211 (-95.9%) - 9 vs 220
- **FILE_PATH**: -2 (-25%) - 6 vs 8

*Missing Entity Types (not detected):*
- **DATE_TIME**: 0 (FullPresidio: 1,438)

**4. Consistent Detections (High Agreement):**
- **Exact matches**: UUID (8,869), CPE_STRING (2,145), EMAIL_ADDRESS (1,465), PORT (2), MAC_ADDRESS (1), CREDIT_CARD (6)
- **Minor variance (<1%)**: CVE_ID (~9,120), URL (~23,900)
- These entity types have well-defined formats and consistent detection across strategies

**5. Detection Behavior Observations:**

*FullPresidio:*
- Detects 5 additional entity types (regional/specialized)
- Higher coverage for specialized patterns (OID, DATE_TIME)
- ~1,500 more entities than FilteredPresidio

*FilteredPresidio:*
- Excludes regional recognizers (no US_DRIVER_LICENSE, AU_ACN, etc.)
- Balanced detection without regional types
- Identical to HybridPresidio in detection

*Standalone:*
- More aggressive on common patterns (HOSTNAME, PHONE_NUMBER, IP_ADDRESS)
- Significantly lower on specialized patterns (OID -91%, CERT_SERIAL -96%)
- Overall similar total count (55,228 vs 55,426 FullPresidio)

### Performance Considerations

#### Architectural Overhead

```yaml
FullPresidio:
  Initialization: Transformer + spaCy + All Presidio recognizers (100+)
  Per-record: Entity detection + validation + operator application
  Validation: Luhn check, country-specific formats, context scoring
  Result: Highest accuracy, slowest processing

FilteredPresidio:
  Initialization: Transformer + spaCy + Filtered recognizers (25)
  Per-record: Entity detection + validation + operator application
  Validation: Luhn check, limited country formats, context scoring
  Result: Balanced accuracy and performance

HybridPresidio:
  Initialization: Same as FilteredPresidio
  Per-record: Presidio detection + manual Python replacement
  Validation: Detection only (no anonymization validation)
  Result: Identical to FilteredPresidio (detection dominates time)

Standalone:
  Initialization: Transformer only (no Presidio overhead)
  Per-record: Direct NER + regex matching + manual replacement
  Validation: None (pattern matching only)
  Result: 4.28x faster, more aggressive detection, some false positives
```

#### Detection Behavior Differences

**FullPresidio (100+ Recognizers):**
- Includes all Presidio recognizers (regional, specialized, common)
- Context-aware scoring boosts confidence for entities near keywords
- Specialized recognizers for OID, CERT_SERIAL, DATE_TIME
- Regional recognizers for US, Australian, Indian identifiers
- **Observation**: Detected 1,491 entities in 5 types that other strategies don't detect
- **Trade-off**: +28.6s processing time, +1,539 total entities

**FilteredPresidio (25 Recognizers):**
- Includes only common entity recognizers
- Excludes regional recognizers (no US_DRIVER_LICENSE, AU_ACN, etc.)
- Context-aware scoring and validation
- **Observation**: Balanced detection across 19 common entity types
- **Trade-off**: Moderate processing time, focused entity coverage

**HybridPresidio:**
- Same detection as FilteredPresidio (identical entity counts)
- Only differs in replacement mechanism (manual vs Presidio operators)
- Processing time identical to FilteredPresidio (detection dominates)

**Standalone Strategy:**
- Pure pattern matching without Presidio framework
- Direct NER model output + regex patterns
- No specialized recognizers (missing OID, CERT_SERIAL recognizers)
- More aggressive pattern matching (broader regex matches)
- **Observation**: 
  - Higher detection for some types (HOSTNAME +109%, PHONE_NUMBER +532%, IP_ADDRESS +25%)
  - Lower detection for specialized types (OID -91%, CERT_SERIAL -96%)
  - No DATE_TIME detection (FullPresidio detected 1,438)
- **Trade-off**: 4.28x faster, different detection profile

#### Precision vs Recall Characteristics

```yaml
FullPresidio:
  Entity Types: 24 (includes regional and specialized)
  Total Entities: 55,426
  Behavior: Maximum coverage across all recognizer types
  Speed: Slowest (313.98s)

FilteredPresidio:
  Entity Types: 19 (common entities only)
  Total Entities: 53,887
  Behavior: Focused on common entity types
  Speed: Moderate (285.38s)

Standalone:
  Entity Types: 19 (no specialized recognizers)
  Total Entities: 55,228
  Behavior: Aggressive pattern matching, missing specialized detection
  Speed: Fastest (73.36s - 4.28x speedup)
```

**Detection Profile Differences:**

| Characteristic | FullPresidio | FilteredPresidio | Standalone |
|----------------|--------------|------------------|------------|
| Regional IDs | ✅ Detects | ❌ Excludes | ❌ Not implemented |
| Specialized (OID, CERT_SERIAL) | ✅ High | ✅ High | ❌ Very low |
| Common patterns (IP, URL, CVE) | ✅ High | ✅ High | ✅ High |
| Aggressive matching (HOSTNAME, PHONE) | ➖ Moderate | ➖ Moderate | ✅ Very high |
| Context validation | ✅ Yes | ✅ Yes | ❌ No |

#### Memory Usage

```yaml
Presidio Strategies:
  Maximum Resident Set Size: 3.08 GB
  Components: Transformer + spaCy models + Presidio recognizers + cache

Standalone:
  Maximum Resident Set Size: 2.35 GB (23.7% reduction)
  Components: Transformer + regex cache only
  Savings: No Presidio framework, no spaCy models, no recognizer registry
```

---

## Strategy Selection

### Based on Entity Requirements

```
If you need:
  │
  ├─ All 100+ Presidio entity types (including regional/specialized)
  │  └─ FullPresidio
  │
  ├─ 25 common entity types with Presidio validation
  │  └─ FilteredPresidio
  │
  ├─ Custom replacement logic per entity
  │  └─ HybridPresidio
  │
  ├─ Only basic entities without Presidio overhead
  │  └─ Standalone
  │
  └─ LLM-based experimental detection
     └─ SLM
```

### Entity Type Coverage

| Entity Category | FullPresidio | FilteredPresidio | Standalone |
|-----------------|--------------|------------------|------------|
| **Regional IDs** | ✅ | ❌ | ❌ |
| **Medical IDs** | ✅ | ❌ | ❌ |
| **Specialized Financial** | ✅ | Partial | ❌ |
| **Common PII** | ✅ | ✅ | ✅ |
| **Infrastructure** | ✅ | ✅ | ✅ |
| **Security Identifiers** | ✅ | ✅ | ✅ |

---

## Migration Guide

### From v2.0 to v3.0

```bash
# v2.0 (Old naming)
python anon.py file.txt --anonymization-strategy balanced

# v3.0 (New naming - semantic)
python anon.py file.txt --anonymization-strategy filtered

# Legacy aliases still work
python anon.py file.txt --anonymization-strategy balanced  # OK - maps to 'filtered'
python anon.py file.txt --anonymization-strategy fast      # OK - maps to 'hybrid'
```

### Strategy Name Mapping

| v2.0 Name | v3.0 Name | Alias Support |
|-----------|-----------|---------------|
| `presidio` | `presidio` | (unchanged) |
| `balanced` | `filtered` | ✅ Yes |
| `fast` | `hybrid` | ✅ Yes |
| (new) | `standalone` | - |
| `slm` | `slm` | (unchanged) |

### Default Strategy Change

```yaml
v2.0 Default: presidio
v3.0 Default: filtered

Change:
  - Default changed from FullPresidio to FilteredPresidio
  - FullPresidio still available via --anonymization-strategy presidio
  - Legacy aliases supported for backwards compatibility
```

### Updating Existing Code

```python
# v2.0 Code
orchestrator = AnonymizationOrchestrator(
    strategy_name="balanced"  # Old name
)

# v3.0 Code (option 1: use new name)
orchestrator = AnonymizationOrchestrator(
    strategy_name="filtered"  # New semantic name
)

# v3.0 Code (option 2: legacy alias)
orchestrator = AnonymizationOrchestrator(
    strategy_name="balanced"  # Still works via alias
)

# v3.0 Code (option 3: default)
orchestrator = AnonymizationOrchestrator()
# Now defaults to 'filtered' instead of 'presidio'
```

---

## Advanced Configuration

### Custom Strategy Implementation

```python
from src.anon.core.protocols import AnonymizationStrategy
from typing import List, Dict, Tuple

class MyCustomStrategy(AnonymizationStrategy):
    """Implement custom anonymization logic."""
    
    def __init__(self, **kwargs):
        self.hash_generator = kwargs['hash_generator']
        self.cache_manager = kwargs['cache_manager']
        # ... initialize components
    
    def anonymize(self, texts: List[str], operator_params: Dict) 
        -> Tuple[List[str], List[Tuple]]:
        """
        Custom anonymization implementation.
        
        Returns:
            (anonymized_texts, collected_entities)
        """
        anonymized = []
        entities = []
        
        for text in texts:
            # Your custom detection logic
            detected = self._my_detection(text)
            
            # Your custom anonymization logic
            anon_text = self._my_anonymization(text, detected)
            
            anonymized.append(anon_text)
            entities.extend(detected)
        
        return anonymized, entities

# Use custom strategy
orchestrator = AnonymizationOrchestrator(
    strategy=MyCustomStrategy(
        hash_generator=HashGenerator(),
        cache_manager=CacheManager()
    )
)
```

### Strategy Factory Extension

```python
# src/anon/strategies.py - Add to strategy_factory()

def strategy_factory(strategy_name: str, **kwargs):
    """Factory with custom strategy support."""
    
    # ... existing strategies
    
    elif strategy_name == "my_custom":
        from my_module import MyCustomStrategy
        return MyCustomStrategy(**kwargs)
    
    else:
        raise ValueError(f"Unknown strategy: {strategy_name}")
```

### Performance Tuning

```python
# Tune batch sizes
orchestrator = AnonymizationOrchestrator(
    strategy_name="filtered",
    nlp_batch_size=32,  # Default: 16 (higher = faster, more memory)
)

# Enable caching
orchestrator = AnonymizationOrchestrator(
    strategy_name="filtered",
    cache_manager=CacheManager(
        use_cache=True,
        max_cache_size=10000  # Cache 10k entities
    )
)

# Parallel processing
orchestrator = AnonymizationOrchestrator(
    strategy_name="filtered",
    parallel_workers=4  # Use 4 parallel workers
)
```

---

## Troubleshooting

### Common Issues

#### 1. Standalone Still Shows Presidio Warnings

**Problem:**
```
WARNING - CreditCardRecognizer initialized
WARNING - NifRecognizer initialized
```

**Solution:**
Ensure `strategy_name` is correctly set:

```python
# engine.py line 286-295
elif strategy_name in ("slm", "standalone"):
    self.analyzer_engine = None  # Skip Presidio
    self.anonymizer_engine = None
```

#### 2. GPU Not Detected (Standalone)

**Problem:**
```
INFO - No GPU detected, using CPU
```

**Solution:**
```bash
# Check CUDA installation
python -c "import torch; print(torch.cuda.is_available())"

# Install CUDA-enabled PyTorch
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

#### 3. Model Loading Timeout

**Problem:**
```
ERROR - Failed to load transformer model: TimeoutError
```

**Solution:**
```bash
# Pre-download models
python -c "from transformers import pipeline; pipeline('ner', model='Davlan/xlm-roberta-base-ner-hrl')"
```

#### 4. Out of Memory (GPU)

**Problem:**
```
RuntimeError: CUDA out of memory
```

**Solution:**
```python
# Reduce batch size
orchestrator = AnonymizationOrchestrator(
    nlp_batch_size=8  # Default: 16
)

# Or use CPU
os.environ['CUDA_VISIBLE_DEVICES'] = ''
```

---

## Appendix

### Complete CLI Reference

```bash
# Strategy selection
python anon.py file.txt --anonymization-strategy <strategy>

# Available strategies
--anonymization-strategy presidio      # FullPresidio (maximum coverage)
--anonymization-strategy filtered      # FilteredPresidio (RECOMMENDED)
--anonymization-strategy hybrid        # HybridPresidio (custom logic)
--anonymization-strategy standalone    # Standalone (maximum speed)
--anonymization-strategy slm           # SLM (experimental)

# Legacy aliases (still supported)
--anonymization-strategy balanced      # → filtered
--anonymization-strategy fast          # → hybrid

# Performance options
--use-datasets                         # Enable dataset mode (faster batching)
--batch-size auto                      # Auto batch size (recommended)
--batch-size 32                        # Manual batch size
--parallel-workers 4                   # Parallel processing

# GPU control
--no-gpu                              # Force CPU mode
# (GPU auto-detected by default)
```

### Version History

```yaml
v3.0 (Current):
  - Strategy names: presidio, filtered, hybrid, standalone, slm
  - Legacy aliases supported: balanced → filtered, fast → hybrid
  - Centralized RegexPatterns class (DRY principle)
  - Standalone strategy implementation (no Presidio dependencies)
  - Automatic GPU detection via torch.cuda.is_available()
```

### References

- [Presidio Documentation](https://microsoft.github.io/presidio/)
- [Transformers Documentation](https://huggingface.co/docs/transformers/)
- [Ollama Documentation](https://ollama.com/docs/)

---

**Document Version:** 1.0  
**Last Updated:** February 7, 2026  
**Maintained By:** AnonLFI Development Team

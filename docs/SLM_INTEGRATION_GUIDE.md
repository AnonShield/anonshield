# SLM (Small Language Model) Integration Guide

This document provides a deep dive into the architecture and design of the SLM integration module (`src/anon/slm/`). It is intended for developers who want to understand, maintain, or extend the SLM-powered capabilities of AnonLFI 3.0.

## 1. Overview and Design Philosophy

The SLM module is an advanced, experimental feature designed to leverage the contextual understanding of Small Language Models (like Llama 3) for PII detection and anonymization. It complements the existing Presidio-based engine by offering a more flexible and context-aware alternative.

The integration adheres to the project's core architectural principles:
- **Modularity & Single Responsibility:** The SLM functionality is broken down into three distinct, single-purpose tasks, each with its own set of modules (`mappers`, `detectors`, `anonymizers`).
- **Dependency Inversion:** The core logic interacts with an `SLMClient` protocol, not a concrete implementation. This decouples the application from a specific SLM provider (e.g., Ollama), making it easy to swap in a different backend (like `vLLM` or a cloud API) in the future.
- **Strategy Pattern:** The SLM-based anonymization methods are encapsulated in a `SLMAnonymizationStrategy`, allowing the main `AnonymizationOrchestrator` to switch between traditional and SLM-based anonymization seamlessly.
- **Configuration over Code:** Prompts, model names, and other parameters are managed via configuration files and CLI arguments, not hard-coded.

## 2. The Three SLM-Powered Tasks

The module is designed to perform three distinct tasks, selectable via CLI flags.

---

### Task 1: Entity Mapping (`--slm-map-entities`)

- **Purpose:** An analytical task for developers and data scientists. It uses the SLM to scan a document and generate a structured map of potential entities, their locations, confidence scores, and the SLM's reasoning. This output is invaluable for creating new regex recognizers or fine-tuning NER models. **This mode does not perform anonymization.**
- **Primary Module:** `src/anon/slm/mappers/slm_entity_mapper.py`
- **Workflow:**
    1. The `_handle_slm_entity_mapping` function in `anon.py` is invoked.
    2. It instantiates an `OllamaClient` and `PromptManager`.
    3. An `SLMEntityMapper` is created.
    4. The input text is read and broken into sentence-aware chunks to fit the SLM's context window.
    5. The mapper streams the chunks to the SLM using the `entity_mapper` prompt.
    6. For each chunk, the SLM returns a JSON object containing identified entities.
    7. The `_parse_slm_response` method robustly validates the SLM's output, checking for hallucinations (entities not actually in the text) and correcting character indices.
    8. Each validated `MappedEntity` is yielded and written progressively to both a `.jsonl` and `.csv` file by a dedicated writer thread, ensuring results are saved even if the process is interrupted.

---

### Task 2: SLM as an Entity Detector (`--slm-detector`)

- **Purpose:** Use the SLM as a high-powered, context-aware recognizer within the traditional anonymization pipeline. This enhances the existing Presidio engine by adding the SLM's analytical capabilities.
- **Primary Module:** `src/anon/slm/detectors/slm_detector.py`
- **Workflow:**
    1. The `AnonymizationOrchestrator` is initialized with an instance of `SLMEntityDetector`.
    2. The detector receives text chunks from the orchestrator.
    3. It uses the `entity_detector` prompt to ask the SLM to identify entities within the text.
    4. The results are parsed into `DetectedEntity` objects, compatible with Presidio's `RecognizerResult`.
    5. The orchestrator then takes these results and can operate in one of two modes (`--slm-detector-mode`):
        - **`hybrid` (default):** The SLM's findings are merged with the results from the traditional regex and NER model recognizers. A de-duplication and overlap-resolution step ensures the best result is chosen.
        - **`exclusive`:** Only the entities identified by the SLM are considered for anonymization.
    6. Anonymization proceeds using the standard HMAC-based slug generation.

---

### Task 3: End-to-End SLM Anonymization (`--anonymization-strategy slm`)

- **Purpose:** A fully autonomous anonymization mode where the SLM is responsible for both identifying and replacing sensitive data. This strategy prioritizes contextual consistency and readability over the rigid, hash-based replacements of the traditional engine.
- **Primary Module:** `src/anon/slm/anonymizers/slm_anonymizer.py`
- **Workflow:**
    1. The `AnonymizationOrchestrator` selects the `SLMAnonymizationStrategy`.
    2. This strategy contains an instance of `SLMFullAnonymizer`.
    3. The `SLMFullAnonymizer` is invoked with a text chunk and the `full_anonymizer` prompt.
    4. The SLM is instructed to return the *entire text*, fully anonymized, using contextual placeholders (e.g., `[PERSON_1]`, `[IP_ADDRESS_A]`).
    5. The returned text is validated to check for suspicious length changes or obvious PII leaks. A retry mechanism is triggered if validation fails.
    6. The final, anonymized text is returned to the orchestrator. **Note:** In this mode, the HMAC-SHA256 hashing mechanism and the `entities.db` database are not used, as the SLM manages consistency internally within the context of the document.

## 3. Component Deep Dive

### `OllamaClient` (`client.py`)

- **Purpose:** Provides a reliable, protocol-based interface for communicating with a local Ollama-served model.
- **Key Features:**
    - **Protocol-Based:** Implements the `SLMClient` protocol, allowing for easy mocking in tests (`MockSLMClient`) and future replacement with other backends.
    - **Connection Validation:** Checks for a running Ollama instance and the specified model on initialization, providing clear error messages.
    - **Robust JSON Parsing:** The `query_json` method is critical. If the SLM returns malformed JSON, it automatically sends a new prompt asking the SLM to *fix its own output*, significantly improving reliability.
    - **Retry Logic:** Implements exponential backoff for network-related failures.

### `PromptManager` (`prompts.py`)

- **Purpose:** Decouples prompt text from application code.
- **Key Features:**
    - **Structured Loading:** Loads prompts from a structured directory (`prompts/{task}/{version}_{lang}.json`). This allows for easy A/B testing of prompt versions and adding new languages.
    - **Templating:** Wraps prompts in a `PromptTemplate` class that allows for safe insertion of runtime data (e.g., the text to be processed).
    - **Language Fallback:** If a prompt for a specific language is not found, it gracefully falls back to the English (`en`) version.

## 4. How to Extend the SLM Module

### Adding a New Prompt Version

To test a new prompt for the entity mapping task, simply:
1. Copy `prompts/entity_mapper/v1_en.json` to `prompts/entity_mapper/v2_en.json`.
2. Modify the `system` and `user` prompts in the new `v2_en.json` file.
3. Run the mapping task with the new version:
   ```bash
   uv run anon.py <file> --slm-map-entities --slm-prompt-version v2
   ```

### Supporting a New Language

To add support for Spanish:
1. Create new prompt files (e.g., `v1_es.json`) in each task directory (`entity_mapper`, `entity_detector`, etc.).
2. Translate the system and user prompts, ensuring the JSON structure and placeholders (`{text}`) are maintained.
3. The application will now be able to use the Spanish prompts when run with `--lang es`.

### Supporting a Different SLM Backend

To switch from Ollama to a different provider (e.g., an OpenAI-compatible API):
1. Create a new client class, e.g., `OpenAIClient`.
2. Ensure it implements the `SLMClient` protocol, including the `query` and `query_json` methods.
3. In `anon.py`, instantiate your new client instead of `OllamaClient` based on a configuration setting or a new CLI argument.

Because the rest of the application depends on the protocol, no other code changes are required.
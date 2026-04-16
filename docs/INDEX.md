# Documentation Index

---

## Web Application

Browser-based UI for anonymization — upload files, select models and entities, download results.

| Document | What it covers |
|----------|---------------|
| [web/SETUP.md](web/SETUP.md) | **Production deploy (Docker + Caddy) and local development setup.** Start here for the web app. |
| [developers/WEB_SYSTEM_DESIGN.md](developers/WEB_SYSTEM_DESIGN.md) | Architecture internals — job lifecycle, data flow, Redis design, scaling path. |

---

## For Users (CLI)

No programming knowledge required. Start here if you want to anonymize files from the command line.

| Document | What it covers |
|----------|---------------|
| [users/CLI_REFERENCE.md](users/CLI_REFERENCE.md) | **Every command-line option explained with examples.** Start here. |
| [users/CONFIGURATION_FILE.md](users/CONFIGURATION_FILE.md) | YAML config file schema and pre-built profiles (banking, medical, CVE). |
| [users/OCR_ENGINES.md](users/OCR_ENGINES.md) | Comparison of 16 OCR engines: Tesseract, EasyOCR, PaddleOCR, DocTR, OnnxTR, Surya, RapidOCR, Keras-OCR, PaddleOCR-VL, DeepSeek-OCR, MonkeyOCR, GLM-OCR, LightOn-OCR, Chandra, DotsOCR, Qwen2.5-VL. GPU configuration included. |

---

## For Developers and Contributors

Internal architecture, strategy internals, evaluation, and helper scripts.

| Document | What it covers |
|----------|---------------|
| [developers/ARCHITECTURE.md](developers/ARCHITECTURE.md) | System design, component interactions, database schema, and processing pipeline. |
| [developers/ANONYMIZATION_STRATEGIES.md](developers/ANONYMIZATION_STRATEGIES.md) | Strategy internals, regex pattern system, and decision guide. |
| [developers/EXTENSIBILITY.md](developers/EXTENSIBILITY.md) | How to add new strategies, OCR engines, NER models, and custom patterns. |
| [developers/UTILITY_SCRIPTS_GUIDE.md](developers/UTILITY_SCRIPTS_GUIDE.md) | Helper scripts in `scripts/`: de-anonymization and DB management. |
| [developers/SLM_INTEGRATION_GUIDE.md](developers/SLM_INTEGRATION_GUIDE.md) | SLM/Ollama integration, prompt design, and experimental features. |

---

## OCR Evaluation

Formal benchmark suite for the OCR engines (targets ICDAR/SIBGRAPI/IJDAR venues).

| Document | What it covers |
|----------|---------------|
| [../benchmark/ocr/METHODOLOGY.md](../benchmark/ocr/METHODOLOGY.md) | Metrics (CER, WER, Field-F1, ANLS), statistical tests, and normalization pipeline. |
| [../benchmark/ocr/REPORT.md](../benchmark/ocr/REPORT.md) | Consolidated results — headline ranking, preprocess ablation, engine inventory. |
| [../benchmark/ocr/RESULTS_AUDIT.md](../benchmark/ocr/RESULTS_AUDIT.md) | Fairness audit — sample I/O pairs, known biases per engine, out-of-scope items. |

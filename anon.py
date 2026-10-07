import argparse
import importlib
import warnings
import re
import logging
import os
import shutil
import sys
import subprocess
import json
import torch
import spacy
import time
import signal
from pathlib import Path
import pandas as pd


from src.anon.config import (
    SECRET_KEY,
    TRANSFORMER_MODEL,
    ProcessingLimits,
    DefaultSizes,
    Global,
    NerDefaults
)
from src.anon.database import DatabaseContext
from src.anon.engine import AnonymizationOrchestrator, load_custom_recognizers, SUPPORTED_LANGUAGES
from src.anon.processors import ProcessorRegistry
from src.anon.cache_manager import CacheManager
from src.anon.hash_generator import HashGenerator
from src.anon.entity_detector import EntityDetector
from src.anon.tqdm_handler import HostPathFormatter, TqdmLoggingHandler

warnings.filterwarnings("ignore")
logging.getLogger("transformers").setLevel(logging.ERROR)


def _install_spacy_model(model: str) -> None:
    """Install a spaCy pipeline package into the running interpreter.

    ``spacy download`` shells out to pip, which a uv-created venv does not have;
    in that case the same wheel is installed with ``uv pip``.
    """
    logging.info(f"Spacy model '{model}' not found. Downloading...")
    try:
        subprocess.run([sys.executable, "-m", "spacy", "download", model],
                       check=True, capture_output=True, text=True)
        logging.info(f"Successfully downloaded '{model}'.")
        return
    except Exception as e:
        first_error = e
    uv = shutil.which("uv")
    if uv:
        try:
            from urllib.parse import urljoin
            from spacy import about
            from spacy.cli.download import get_compatibility, get_model_filename, get_version
            version = get_version(model, get_compatibility())
            url = urljoin(about.__download_url__.rstrip("/") + "/", get_model_filename(model, version))
            subprocess.run([uv, "pip", "install", "--python", sys.executable, f"{model} @ {url}"],
                           check=True, capture_output=True, text=True)
            importlib.invalidate_caches()
            logging.info(f"Successfully installed '{model}' with uv.")
            return
        except Exception as e:
            first_error = e
    logging.error(f"Failed to download spaCy model '{model}': {first_error}. "
                  f"Install it with `uv sync --group pt` (Portuguese) or `python -m spacy download {model}`.")
    sys.exit(1)


def models_check(lang: str, need_spacy: bool = True):
    """Make sure the spaCy pipeline the engine loads for ``lang`` is installed.

    The engine loads pt_core_news_lg for Portuguese and en_core_web_lg for every
    other language (see AnonymizationOrchestrator._setup_engines), so only that
    one is needed. The transformer model is fetched by transformers itself on
    first load, into the Hugging Face cache it reads from; it used to be
    pre-downloaded into ./models/<id>, a directory nothing ever loaded from.
    """
    import spacy.util

    if not need_spacy:
        return
    model = "pt_core_news_lg" if lang == "pt" else "en_core_web_lg"
    if not spacy.util.is_package(model):
        _install_spacy_model(model)


def write_report(file_path, start_time):
    """Writes a simple performance report."""
    os.makedirs("logs", exist_ok=True)
    base_name = os.path.basename(file_path)
    report_file = os.path.join("logs", f"report_{base_name}.txt")
    with open(report_file, "w", encoding="utf-8") as report:
        report.write(f"Processed file: {file_path}\n")
        report.write(f"Total elapsed time: {time.time() - start_time:.2f} seconds\n")
    logging.info(f"Report saved at: {report_file}")


def get_supported_entities(
    strategy_name: str = "filtered",
    transformer_model: str = TRANSFORMER_MODEL,
    lang: str = "en",
) -> list[str]:
    """Return a sorted list of entity types detectable for a given strategy + model combination.

    Args:
        strategy_name: One of presidio / filtered / hybrid / standalone / regex.
        transformer_model: HuggingFace model ID used for NER.

    Entity sources per strategy:
        presidio / filtered / hybrid  → custom regex + Presidio built-ins + NER model labels
        standalone / regex            → custom regex + NER model labels  (no Presidio engine)
    """
    from src.anon.model_registry import get_entity_mapping
    from presidio_analyzer import RecognizerRegistry  # type: ignore

    supported: set[str] = set()

    # 1. Custom regex recognizers — shared by all strategies (PT-BR adds BR_CPF, BR_CNPJ, ...)
    try:
        for r in load_custom_recognizers(langs=[lang]):
            supported.update(r.supported_entities)
    except Exception as exc:
        logging.warning(f"Failed to load custom recognizers: {exc}")

    # 2. Presidio built-in recognizers — only for the full Presidio strategy.
    if strategy_name == "presidio":
        try:
            registry = RecognizerRegistry()
            registry.load_predefined_recognizers()
            for r in registry.recognizers:
                supported.update(r.supported_entities)
        except Exception as exc:
            logging.warning(f"Failed to load Presidio built-in recognizers: {exc}")

    # 3. NER model entity labels — sourced from the model registry (single source of truth)
    if strategy_name != "regex":
        supported.update(get_entity_mapping(transformer_model).values())
    # The standalone strategy also emits labels the mapping does not cover
    # (DATE, for xlm-roberta), which must be selectable and preservable.
    if strategy_name == "standalone":
        from src.anon.model_registry import get_model_labels
        supported.update(get_model_labels(transformer_model))

    return sorted(supported)


def _handle_list_entities(strategy_name: str = "filtered", transformer_model: str = TRANSFORMER_MODEL, lang: str = "en"):
    """Prints the list of supported entities for the given strategy + model and exits."""
    print(f"Supported entity types (strategy={strategy_name}, model={transformer_model}, lang={lang}):")
    for entity in get_supported_entities(strategy_name, transformer_model, lang):
        print(f" - {entity}")
    sys.exit(0)


def _parse_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Anonymize sensitive information or generate NER training data.", allow_abbrev=False)
    parser.add_argument("file_path", nargs='?', help="Path to the file or directory to be processed.")

    # Config file (processed before all other args)
    parser.add_argument("--config", type=str, default=None, metavar="CONFIG_FILE",
                        help="Path to a YAML or JSON run config file. CLI arguments override config file values. "
                             "See examples/anon_config.example.yaml for format.")

    # General options
    parser.add_argument("--list-entities", action="store_true", help="List all supported entity types and exit.")
    parser.add_argument("--list-languages", action="store_true", help="List all supported languages and exit.")
    parser.add_argument("--lang", type=str, default="en", help="Language of the document.")
    parser.add_argument("--output-dir", type=str, default="output", help="Directory to save output files. Default is 'output'.")
    parser.add_argument("--overwrite", action="store_true", help="Allow overwriting of existing output files.")
    parser.add_argument("--no-report", action="store_true", help="Disable the creation of a performance report in the 'logs' directory.")

    # Anonymization options
    parser.add_argument("--entities", type=str, default="", help="Comma-separated list of entity types to anonymize. If set, ONLY these entities are anonymized (complement of --preserve-entities). Example: EMAIL_ADDRESS,IP_ADDRESS,CPF")
    parser.add_argument("--preserve-entities", type=str, default="", help="Comma-separated list of entity types to preserve (skip). Ignored when --entities is set.")
    parser.add_argument("--allow-list", type=str, default="", help="Comma-separated list of terms to never anonymize.")
    parser.add_argument("--slug-length", type=int, default=DefaultSizes.DEFAULT_SLUG_LENGTH, help=f"Length of the anonymized slug (0-64). If 0, only the entity type label is used and no secret key is required. Default: {DefaultSizes.DEFAULT_SLUG_LENGTH}.")
    parser.add_argument("--anonymization-config", type=str, default=None, help="Path to a .json file with field-level anonymization rules for structured files (JSON, CSV, XML). See documentation for format.")
    parser.add_argument("--word-list", type=str, default=None, help="Path to a .json file mapping category names to lists of known terms that must always be anonymized (e.g. organization names, internal system names, acronyms).")
    parser.add_argument("--custom-patterns", type=str, default=None, metavar="PATTERNS_FILE",
                        help="Path to a YAML or JSON file with custom regex patterns. "
                             "Format: [{entity_type, pattern, score, flags?}, ...]. "
                             "See examples/patterns/banking_pt.yaml for an example.")

    # OCR options
    parser.add_argument("--ocr-engine", type=str, default="tesseract",
                        choices=["tesseract"],
                        help="OCR engine for image and PDF text extraction. Default and only option: tesseract.")

    # Performance & Filtering options
    parser.add_argument("--preserve-row-context", action="store_true", help="For CSV/XLSX, process all values to preserve context instead of only unique values.")
    parser.add_argument("--json-stream-threshold-mb", type=int, default=ProcessingLimits.JSON_STREAM_THRESHOLD_MB, help=f"JSON streaming threshold in MB. Files larger than this will be streamed from disk. Default: {ProcessingLimits.JSON_STREAM_THRESHOLD_MB}")
    parser.add_argument("--optimize", action="store_true", help="Enable all optimizations (standalone strategy, cache, min-word-length=3, in-memory DB).")
    parser.add_argument("--use-cache", action="store_true", default=True, help="Enable in-memory caching for the run. Enabled by default. Use --no-use-cache to disable.")
    parser.add_argument("--no-use-cache", action="store_false", dest="use_cache", help="Disable in-memory caching for the run.")
    parser.add_argument("--max-cache-size", type=int, default=ProcessingLimits.MAX_CACHE_SIZE, help=f"Maximum number of items to store in the in-memory cache. Default: {ProcessingLimits.MAX_CACHE_SIZE}")
    parser.add_argument("--min-word-length", type=int, default=DefaultSizes.DEFAULT_MIN_WORD_LENGTH, help=f"Minimum character length for a word to be processed. Default: {DefaultSizes.DEFAULT_MIN_WORD_LENGTH} (no limit).")
    parser.add_argument("--skip-numeric", action="store_true", help="If set, numeric-only strings will not be anonymized.")
    parser.add_argument("--anonymization-strategy", type=str, default="filtered",
                       choices=["presidio", "filtered", "hybrid", "standalone", "regex"],
                       help="Anonymization strategy. "
                            "'filtered': Presidio pipeline with curated recognizer scope (default, best accuracy). "
                            "'presidio': Full Presidio pipeline. "
                            "'hybrid': Presidio detection + custom replacement. "
                            "'standalone': Zero Presidio dependencies, fastest on GPU. "
                            "'regex': Pure regex matching only, zero NLP/ML overhead (fastest).")
    parser.add_argument("--regex-priority", action="store_true", help="Give priority to custom regex recognizers over model-based ones.")
    parser.add_argument("--transformer-model", type=str, default=TRANSFORMER_MODEL, help=f"Transformer model for NER detection. Options: 'Davlan/xlm-roberta-base-ner-hrl' (default, multilingual), 'attack-vector/SecureModernBERT-NER' (cybersecurity-focused). Default: {TRANSFORMER_MODEL}.")
    parser.add_argument("--ner-score-threshold", type=float, default=NerDefaults.SCORE_THRESHOLD, help=f"Minimum confidence score (0.0-1.0) for a transformer NER detection to be kept. Lower values increase recall (catch more entities like surnames) at the cost of more false positives. Default: {NerDefaults.SCORE_THRESHOLD}.")
    parser.add_argument("--ner-aggregation-strategy", type=str, default=NerDefaults.AGGREGATION_STRATEGY, choices=list(NerDefaults.AGGREGATION_CHOICES), help=f"HuggingFace aggregation strategy for merging BILOU subword tokens into entities. Default: {NerDefaults.AGGREGATION_STRATEGY}.")
    parser.add_argument("--db-mode", type=str, default="persistent", choices=["persistent", "in-memory"], help="Database mode ('persistent' to save to disk, 'in-memory' for a temporary DB).")
    parser.add_argument("--db-dir", type=str, default="db", help="Directory for the database file.")
    parser.add_argument("--disable-gc", action="store_true", help="Disable automatic garbage collection during processing. May boost speed for single large files but increases memory usage.")
    parser.add_argument("--db-synchronous-mode", type=str, default=None, choices=["OFF", "NORMAL", "FULL", "EXTRA"], help="SQLite 'synchronous' PRAGMA mode. Overrides config file setting.")
    parser.add_argument("--log-level", type=str, default="WARNING", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Set the logging level (default: WARNING).")
    parser.add_argument("--force-large-xml", action="store_true", help="Force processing of XML files exceeding memory safety thresholds. Use with caution as it may lead to Out-of-Memory errors.")

    # NER Data Generation Options
    ner_group = parser.add_argument_group('NER Data Generation Options')
    ner_group.add_argument("--generate-ner-data", action="store_true", help="Enable NER data generation mode instead of anonymizing.")
    ner_group.add_argument("--ner-include-all", action="store_true", help="Include all texts in NER output, even those without detected entities.")
    ner_group.add_argument("--ner-aggregate-record", action="store_true", help="For JSON/JSONL files, aggregate each record into a single text line instead of extracting fields separately.")

    # Chunking & Batching Options
    chunk_group = parser.add_argument_group('Chunking and Batching')
    chunk_group.add_argument("--batch-size", type=str, default=str(DefaultSizes.BATCH_SIZE), help=f"Batch size for processing text chunks. Use 'auto' for adaptive sizing based on file characteristics and strategy, or specify an integer. Default: {DefaultSizes.BATCH_SIZE}.")
    chunk_group.add_argument("--csv-chunk-size", type=int, default=DefaultSizes.CSV_CHUNK_SIZE, help=f"Chunk size for reading CSV files with pandas. Default: {DefaultSizes.CSV_CHUNK_SIZE}.")
    chunk_group.add_argument("--json-chunk-size", type=int, default=DefaultSizes.JSON_CHUNK_SIZE, help=f"Chunk size for streaming large JSON arrays. Default: {DefaultSizes.JSON_CHUNK_SIZE}.")
    chunk_group.add_argument("--ner-chunk-size", type=int, default=DefaultSizes.NER_CHUNK_SIZE, help=f"Max character size for text chunks in NER data generation. Default: {DefaultSizes.NER_CHUNK_SIZE}.")
    chunk_group.add_argument("--nlp-batch-size", type=int, default=DefaultSizes.NLP_BATCH_SIZE, help=f"Batch size for spaCy's nlp.pipe() processing. Default: {DefaultSizes.NLP_BATCH_SIZE}.")
    chunk_group.add_argument("--use-datasets", action="store_true", help="Use HuggingFace datasets for batch processing on GPU. Eliminates 'pipelines sequentially on GPU' warning and improves GPU utilization. Recommended for large files (>50MB).")

    args = parser.parse_args()
    logging.debug(f"Parsed arguments: {args}")

    # --- Config file: merge before any other logic (CLI wins) ---
    if args.config:
        try:
            from src.anon.core.run_config import load_run_config, merge_with_args as _merge
            cfg = load_run_config(args.config)
            explicit_args = {
                action.dest for action in parser._actions
                if any(token.split("=", 1)[0] in action.option_strings for token in sys.argv[1:])
            }
            _merge(cfg, args, explicit_args)
            # Inject custom_patterns list from config into args for later processing
            if cfg.custom_patterns and not getattr(args, '_config_custom_patterns', None):
                args._config_custom_patterns = cfg.custom_patterns
            # Register custom models from config
            if cfg.custom_models:
                args._config_custom_models = cfg.custom_models
        except FileNotFoundError as e:
            parser.error(str(e))
        except Exception as e:
            parser.error(f"Failed to load config file '{args.config}': {e}")

    if args.list_entities:
        _handle_list_entities(args.anonymization_strategy, args.transformer_model, args.lang)

    if args.list_languages:
        _handle_list_languages()

    if args.slug_length is not None and (type(args.slug_length) is not int or not 0 <= args.slug_length <= 64):
        parser.error("--slug-length must be between 0 and 64.")

    for action in parser._actions:
        value = getattr(args, action.dest, None)
        if action.choices and value is not None and value not in action.choices:
            parser.error(f"--{action.dest.replace('_', '-')} must be one of: {', '.join(action.choices)}")
    for name in ("csv_chunk_size", "json_chunk_size", "ner_chunk_size", "nlp_batch_size"):
        if getattr(args, name) <= 0:
            parser.error(f"--{name.replace('_', '-')} must be greater than zero.")
    if not isinstance(args.ner_score_threshold, (int, float)) or not 0 <= args.ner_score_threshold <= 1:
        parser.error("--ner-score-threshold must be between 0 and 1.")
    if str(args.batch_size).lower() != "auto":
        try:
            if int(args.batch_size) <= 0:
                raise ValueError
        except (ValueError, TypeError):
            parser.error("--batch-size must be 'auto' or an integer greater than zero.")

    if not args.file_path and not (args.list_entities or args.list_languages):
        parser.error("A file path must be provided.")

    # Handle the --optimize flag
    if args.optimize:
        logging.info("Optimization mode enabled: setting standalone strategy, in-memory DB, cache, and min-word-length=3.")
        args.anonymization_strategy = "standalone"
        args.db_mode = "in-memory"
        args.use_cache = True
        if args.min_word_length == 0:
            args.min_word_length = 3

    # Auto-select a language-specific NER model when the user kept the default.
    # Portuguese docs benefit from a PT-BR fine-tuned model (better person-name
    # recall on certidões, extratos, cheques). CLI and config file can still
    # override by setting transformer_model explicitly.
    user_set_model = any(token.split("=", 1)[0] == "--transformer-model" for token in sys.argv[1:])
    if not user_set_model and args.transformer_model == TRANSFORMER_MODEL:
        from src.anon.model_registry import default_transformer_for_lang
        lang_default = default_transformer_for_lang(args.lang)
        if lang_default != args.transformer_model:
            logging.info(
                "Auto-selected NER model for lang='%s': %s (override with --transformer-model)",
                args.lang, lang_default,
            )
            args.transformer_model = lang_default
    return args


def _handle_list_languages():
    """Prints the list of supported languages and exits."""
    print("Supported languages:")
    for lang_code, lang_name in SUPPORTED_LANGUAGES.items():
        print(f" - {lang_code}: {lang_name}")
    sys.exit(0)


def _load_word_list_patterns(word_list_path: str) -> list:
    """Loads a word list JSON and returns compiled exact-match regex patterns.

    The JSON key is used directly as the entity type label (uppercased).
    Any string key is valid — no preset mapping is required.

    Example:
        {
          "ORGANIZATION": ["AcmeCorp", "CSIRT-BR"],
          "HOSTNAME":     ["fw-edge.internal"],
          "MY_CUSTOM_TYPE": ["codename-x"]
        }
    """
    if not os.path.exists(word_list_path):
        logging.error(f"Word list file not found: '{word_list_path}'")
        sys.exit(1)
    try:
        with open(word_list_path, 'r', encoding='utf-8') as f:
            word_list_data: dict = json.load(f)
    except json.JSONDecodeError:
        logging.error(f"Could not parse word list JSON: '{word_list_path}'")
        sys.exit(1)

    patterns = []
    total_terms = 0
    for category, terms in word_list_data.items():
        entity_type = category.upper()
        for term in terms:
            term = term.strip()
            if not term:
                continue
            patterns.append({
                "label": entity_type,
                "regex": re.compile(r'(?<!\w)' + re.escape(term) + r'(?!\w)', flags=re.IGNORECASE),
                "score": 1.0,
            })
            total_terms += 1
    logging.info(f"Word list loaded: {total_terms} terms from {len(word_list_data)} categories.")
    return patterns


def _compile_inline_patterns(pattern_list: list) -> list:
    """Compile a list of pattern dicts (from config file) into compiled_patterns format."""
    import re as _re
    compiled = []
    for entry in pattern_list:
        entity_type = str(entry.get("entity_type", "CUSTOM")).upper()
        pattern_str = entry.get("pattern")
        if not pattern_str:
            logging.warning("Custom pattern entry missing 'pattern' field: %s", entry)
            continue
        score = float(entry.get("score", 0.8))
        flag_str = str(entry.get("flags", "")).upper()
        flags = _re.DOTALL | _re.IGNORECASE
        if "MULTILINE" in flag_str:
            flags |= _re.MULTILINE
        try:
            compiled.append({"label": entity_type, "regex": _re.compile(pattern_str, flags), "score": score})
        except _re.error as e:
            logging.warning("Invalid custom pattern '%s': %s", pattern_str, e)
    return compiled


def _load_custom_patterns(path: str) -> list:
    """Load custom regex patterns from a YAML or JSON file."""
    import re as _re
    p = Path(path)
    if not p.exists():
        logging.error("Custom patterns file not found: '%s'", path)
        sys.exit(1)
    try:
        if p.suffix in (".yaml", ".yml"):
            import yaml
            with p.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or []
        else:
            with p.open(encoding="utf-8") as f:
                data = json.load(f)
        if not isinstance(data, list):
            logging.error("Custom patterns file must be a list of objects: '%s'", path)
            sys.exit(1)
    except Exception as e:
        logging.error("Failed to parse custom patterns file '%s': %s", path, e)
        sys.exit(1)

    result = _compile_inline_patterns(data)
    logging.info("Custom patterns loaded: %d patterns from '%s'", len(result), path)
    return result


def main():
    """Main function to orchestrate the anonymization or NER data generation process."""
    args = _parse_arguments()
    
    # Configure logging to be tqdm-friendly
    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {args.log_level}")
    
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    # Add our Tqdm-friendly handler
    tqdm_handler = TqdmLoggingHandler()
    tqdm_handler.setFormatter(HostPathFormatter('%(asctime)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(tqdm_handler)
    
    logging.debug(f"Resolved log level to: {numeric_level} and configured TqdmLoggingHandler.")

    # Silence noisy third-party loggers (Presidio, transformers, etc.)
    # These emit repetitive INFO lines ("Fetching all recognizers...") per batch,
    # flooding the output for large files without adding useful information.
    for noisy_logger in ("transformers", "sentence_transformers"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
    # Presidio logs as "presidio-analyzer"/"presidio-anonymizer" (with a hyphen).
    # At WARNING it prints, on every run, one line per built-in recognizer of
    # another language ("Recognizer not added to registry because language is
    # not supported by registry - EsNifRecognizer ..."). The Hub client prints
    # "You are sending unauthenticated requests" on a model download; public
    # models need no token.
    for quiet_logger in ("presidio-analyzer", "presidio-anonymizer", "huggingface_hub"):
        logging.getLogger(quiet_logger).setLevel(logging.ERROR)

    logging.info("Starting anonymization process...")

    if not args.file_path or not os.path.exists(args.file_path):
        logging.critical(f"Input path not found: {args.file_path}")
        sys.exit(1)

    # --- Load Anonymization Config ---
    anonymization_config = None
    if isinstance(args.anonymization_config, dict):
        anonymization_config = args.anonymization_config
    elif args.anonymization_config:
        if not os.path.exists(args.anonymization_config):
            logging.error(f"Anonymization config file not found at '{args.anonymization_config}'")
            sys.exit(1)
        try:
            with open(args.anonymization_config, 'r', encoding='utf-8') as f:
                anonymization_config = json.load(f)
            logging.info(f"Loaded advanced anonymization rules from '{args.anonymization_config}'.")
        except json.JSONDecodeError:
            logging.error(f"Could not decode JSON from '{args.anonymization_config}'. Please check the file format.")
            sys.exit(1)
        except Exception as e:
            logging.error(f"Error reading anonymization config file: {e}")
            sys.exit(1)
    else:
        logging.info("Anonymization config not provided. Proceeding without specific rules for structured files.")

    # --- Common Setup ---
    # Dynamically set LD_LIBRARY_PATH for NVIDIA CUDA libraries.
    # Strategy: check system-wide CUDA paths first (Docker nvidia/cuda image),
    # then fall back to pip-installed nvidia packages (local development).
    cuda_lib_paths = []

    # 1. System-wide CUDA installation (Docker nvidia/cuda base image)
    for sys_path in ["/usr/local/cuda/lib64", "/usr/local/cuda/lib"]:
        if os.path.isdir(sys_path):
            cuda_lib_paths.append(sys_path)

    # 2. Pip-installed NVIDIA packages (local venv)
    if not cuda_lib_paths:
        venv_python_path = os.path.dirname(sys.executable)
        venv_lib_path = os.path.join(os.path.dirname(venv_python_path), "lib")
        if os.path.exists(venv_lib_path):
            venv_pyver = next(
                (d for d in os.listdir(venv_lib_path)
                 if d.startswith("python") and os.path.isdir(os.path.join(venv_lib_path, d))),
                None
            )
            if venv_pyver:
                nvidia_base_path = os.path.join(venv_lib_path, venv_pyver, "site-packages", "nvidia")
                if os.path.exists(nvidia_base_path):
                    for pkg in os.listdir(nvidia_base_path):
                        lib_path = os.path.join(nvidia_base_path, pkg, "lib")
                        if os.path.isdir(lib_path):
                            cuda_lib_paths.append(lib_path)

    if cuda_lib_paths:
        existing = os.environ.get("LD_LIBRARY_PATH", "")
        new_paths = ":".join(cuda_lib_paths)
        os.environ["LD_LIBRARY_PATH"] = f"{new_paths}:{existing}" if existing else new_paths
        logging.info(f"CUDA libraries configured ({len(cuda_lib_paths)} paths added to LD_LIBRARY_PATH)")
    else:
        logging.debug("No NVIDIA CUDA libraries found (CPU-only mode)")

    # --- GPU Activation ---
    logging.info("Verifying hardware...")
    from src.anon.device import cuda_usable
    if cuda_usable():
        gpu_name = torch.cuda.get_device_name(0)
        logging.info(f"CUDA GPU detected: {gpu_name}")
        # Test if CuPy actually works on this GPU architecture before enabling spaCy GPU
        cupy_works = False
        try:
            import cupy
            a = cupy.array([1.0, 2.0])
            _ = (a * a).sum()  # Force kernel compilation to detect arch incompatibility
            cupy.cuda.Stream.null.synchronize()
            cupy_works = True
        except Exception as e:
            logging.info(f"CuPy not usable on this GPU ({e}). spaCy will use CPU.")
        if cupy_works and spacy.prefer_gpu():  # type: ignore
            logging.info(f"spaCy GPU activated (CuPy backend on {gpu_name})")
        else:
            # CuPy unavailable/incompatible: spaCy stays on CPU, but force the
            # HuggingFace transformer pipeline to use GPU via PyTorch directly.
            # hf_token_pipe reads get_torch_default_device() from its module scope,
            # so patching it here (before any nlp.add_pipe call) redirects to CUDA.
            try:
                import spacy_huggingface_pipelines.token_classification as _shp_tc
                _shp_tc.get_torch_default_device = lambda: torch.device("cuda:0")
                logging.info(f"Transformers pipeline GPU activated via PyTorch direct (spaCy NLP on CPU).")
            except Exception as e2:
                logging.info(f"Could not activate GPU for transformer pipeline: {e2}. Running fully on CPU.")
    else:
        logging.info("No usable CUDA GPU. Running on CPU.")

    # --- SECRET_KEY Validation (Early Exit) ---
    # slug_length=0 means entity type only (no HMAC), so no key needed
    if not args.generate_ner_data and not SECRET_KEY and args.slug_length != 0:
        logging.error("ANON_SECRET_KEY or ANON_SECRET_KEY_FILE not set for anonymization.")
        sys.exit(1)

    start_time = time.time()
    
    db_context = None
    if not args.generate_ner_data:
        db_context = DatabaseContext(mode=args.db_mode, db_dir=args.db_dir)
        db_context.initialize(synchronous=args.db_synchronous_mode)
        logging.info(f"Database initialized in '{args.db_mode}' mode with synchronous PRAGMA set to '{args.db_synchronous_mode or 'NORMAL'}'.")

    # The spaCy pipeline is needed by every NLP strategy and by NER data
    # generation (which always runs on the Presidio analyzer).
    models_check(args.lang, need_spacy=args.anonymization_strategy != "regex" or args.generate_ner_data)

    allow_list = [term.strip() for term in args.allow_list.split(',') if term and term.strip()]
    logging.debug(f"Allow list: {allow_list}")

    # --- Word list and custom patterns, loaded first: their labels are valid
    # values for --entities / --preserve-entities.
    extra_patterns = []
    if args.word_list:
        extra_patterns.extend(_load_word_list_patterns(args.word_list))
    custom_pattern_sources = []
    if getattr(args, 'custom_patterns', None):
        custom_pattern_sources.append(args.custom_patterns)
    if getattr(args, '_config_custom_patterns', None):
        custom_pattern_sources.append(getattr(args, '_config_custom_patterns', None))
    for src in custom_pattern_sources:
        if isinstance(src, str):
            extra_patterns.extend(_load_custom_patterns(src))
        elif isinstance(src, list):
            extra_patterns.extend(_compile_inline_patterns(src))

    # --- Custom models from config file (before anything reads the entity mapping) ---
    custom_models_cfg = getattr(args, '_config_custom_models', None)
    if custom_models_cfg:
        from src.anon.model_registry import register_model
        for m in custom_models_cfg:
            mid = m.get("id") or m.get("model_id")
            mapping = m.get("entity_mapping", {})
            if mid and mapping:
                register_model(mid, mapping, description=m.get("description", ""))

    supported_entities = set(get_supported_entities(args.anonymization_strategy, args.transformer_model, args.lang))
    supported_entities.update(p["label"] for p in extra_patterns)

    from src.anon.entity_selection import resolve_entity_selection
    requested_entities = [e for e in args.entities.split(',') if e and e.strip()]
    selection = resolve_entity_selection(
        supported_entities,
        entities=requested_entities or None,
        preserve_entities=args.preserve_entities.split(','),
    )
    if selection.unknown:
        flag = "--entities" if requested_entities else "--preserve-entities"
        logging.warning(f"Unknown entity types in {flag} (will be ignored): {', '.join(selection.unknown)}")
    if selection.entities_to_anonymize is not None:
        logging.info(f"--entities mode: anonymizing only {sorted(selection.entities_to_anonymize)}")
    entities_to_preserve = sorted(selection.entities_to_preserve)

    logging.info(f"Auto-preserving non-PII entities: {', '.join(sorted(Global.NON_PII_ENTITIES))}")
    logging.debug(f"Effective entities to preserve: {entities_to_preserve}")

    try:
        engine_message = "NER detection engine" if args.generate_ner_data else "anonymization engine"
        logging.info(f"Initializing {engine_message} for language '{args.lang}' with transformer model '{args.transformer_model}'...")
        
        # Instantiate dependencies for injection
        cache_manager = CacheManager(
            use_cache=args.use_cache,
            max_cache_size=args.max_cache_size
        )
        hash_generator = HashGenerator()
        
        # --- Determine entity mapping based on transformer model ---
        from src.anon.model_registry import get_entity_mapping
        entity_mapping = get_entity_mapping(args.transformer_model)
        logging.info(f"Using entity mapping for model: {args.transformer_model}")
        
        # --- Entity Detector Setup ---
        # Preserved types stay in the list: they claim their span so another
        # recognizer cannot anonymize it (EntityDetector.finalize).
        custom_recognizers = load_custom_recognizers([args.lang], regex_priority=args.regex_priority)
        compiled_patterns = []
        for recognizer in custom_recognizers:
            entity_type = recognizer.supported_entities[0]
            for pattern in recognizer.patterns:
                try:
                    compiled_patterns.append({
                        "label": entity_type,
                        "regex": re.compile(pattern.regex, flags=re.DOTALL | re.IGNORECASE),
                        "score": pattern.score
                    })
                except re.error:
                    logging.warning(f"Invalid regex pattern skipped: {pattern.regex}")

        # --- Word list and custom patterns (known terms, user regexes) ---
        compiled_patterns.extend(extra_patterns)

        entity_detector = EntityDetector(
            compiled_patterns=compiled_patterns,
            entities_to_preserve=set(entities_to_preserve),
            allow_list=set(allow_list),
            entity_mapping=entity_mapping,
            entities_to_anonymize=selection.entities_to_anonymize,
            custom_patterns=extra_patterns,
        )

        # --- Orchestrator ---
        orchestrator = AnonymizationOrchestrator(
            lang=args.lang,
            db_context=db_context,
            allow_list=allow_list, 
            entities_to_preserve=entities_to_preserve,
            slug_length=args.slug_length,
            strategy_name=args.anonymization_strategy,
            regex_priority=args.regex_priority,
            nlp_batch_size=args.nlp_batch_size,
            cache_manager=cache_manager,
            hash_generator=hash_generator,
            entity_detector=entity_detector,
            ner_data_generation=args.generate_ner_data,
            transformer_model=args.transformer_model,
            ner_score_threshold=args.ner_score_threshold,
            ner_aggregation_strategy=args.ner_aggregation_strategy,
            entities_to_anonymize=selection.entities_to_anonymize,
        )
        
        # --- Processing ---
        # Convert batch_size to int if not 'auto'
        batch_size_value = args.batch_size
        if isinstance(batch_size_value, str) and batch_size_value.lower() != "auto":
            try:
                batch_size_value = int(batch_size_value)
            except ValueError:
                logging.error(f"Invalid --batch-size value: '{batch_size_value}'. Use 'auto' or an integer. Defaulting to {DefaultSizes.BATCH_SIZE}.")
                batch_size_value = DefaultSizes.BATCH_SIZE
        
        # --- OCR Engine (tesseract only) ---
        from src.anon.ocr.factory import get_ocr_engine
        try:
            ocr_engine = get_ocr_engine(args.ocr_engine)
            logging.info(f"OCR engine: {args.ocr_engine}")
        except RuntimeError as e:
            logging.error(str(e))
            sys.exit(1)

        processor_factory_args = {
            "ner_data_generation": args.generate_ner_data,
            "ner_include_all": args.ner_include_all,
            "ner_aggregate_record": args.ner_aggregate_record,
            "anonymization_config": anonymization_config,
            "min_word_length": args.min_word_length,
            "skip_numeric": args.skip_numeric,
            "output_dir": args.output_dir,
            "overwrite": args.overwrite,
            "disable_gc": args.disable_gc,
            "json_stream_threshold_mb": args.json_stream_threshold_mb,
            "preserve_row_context": args.preserve_row_context,
            "batch_size": batch_size_value,
            "csv_chunk_size": args.csv_chunk_size,
            "json_chunk_size": args.json_chunk_size,
            "ner_chunk_size": args.ner_chunk_size,
            "force_large_xml": args.force_large_xml,
            "use_datasets": args.use_datasets,
            "ocr_engine": ocr_engine,
        }
        logging.debug(f"Processor factory arguments: {processor_factory_args}")

        if os.path.isdir(args.file_path):
            mode_str = "Generating NER data from" if args.generate_ner_data else "Processing"
            logging.info(f"{mode_str} directory: {args.file_path}...")
            processed_files_count = 0
            failed_files_count = 0
            skipped_files_count = 0
            output_root = Path(args.output_dir).resolve()
            input_root = Path(args.file_path).resolve()
            if output_root == input_root:
                raise ValueError("Choose an --output-dir outside the input directory or in a separate subfolder.")
            
            for root, dirs, files in os.walk(args.file_path):
                dirs[:] = sorted(d for d in dirs if (Path(root) / d).resolve() != output_root)
                for file_name in sorted(files):
                    file_full_path = os.path.join(root, file_name)
                    logging.debug(f"Attempting to get processor for file: {file_full_path}")
                    try:
                        file_args = {**processor_factory_args, "output_dir": str(output_root / Path(root).resolve().relative_to(input_root))}
                        processor = ProcessorRegistry.get_processor(file_full_path, orchestrator, **file_args)
                        if not processor:
                            skipped_files_count += 1
                            logging.warning(f"Unsupported file skipped: {file_full_path}")
                            continue

                        _bt_start = time.time()
                        output_file = processor.process()
                        _bt_elapsed = time.time() - _bt_start
                        _bt_size = os.path.getsize(file_full_path) if os.path.isfile(file_full_path) else 0
                        logging.debug(f"[BENCHMARK_TIMING] file={file_name} elapsed={_bt_elapsed:.6f} size_bytes={_bt_size}")
                        processed_files_count += 1
                        if args.generate_ner_data:
                            logging.info(f"NER data for '{file_name}' saved at: {output_file}")
                        else:
                            logging.info(f"Anonymized file for '{file_name}' saved at: {output_file}")
                    except ValueError as ve:
                        failed_files_count += 1
                        logging.error(f"Could not process '{file_full_path}': {ve}")
                    except Exception as e:
                        failed_files_count += 1
                        logging.error(f"Could not process '{file_full_path}': {e}", exc_info=args.log_level == "DEBUG")
            
            if processed_files_count == 0:
                raise ValueError(f"No files were processed in {args.file_path}. Check the file formats and errors above.")
            else:
                print(f"Processed {processed_files_count} file(s); skipped {skipped_files_count}; failed {failed_files_count}.")
            if failed_files_count:
                raise ValueError("Some files failed. The output is incomplete; correct the errors above and retry.")

        else:
            mode_str = "Generating NER data for" if args.generate_ner_data else "Processing"
            logging.info(f"{mode_str} file: {args.file_path}...")
            processor = ProcessorRegistry.get_processor(args.file_path, orchestrator, **processor_factory_args)
            if processor:
                output_file = processor.process()
                if args.generate_ner_data:
                    logging.info(f"NER data generation complete. Saved at: {output_file}")
                else:
                    logging.info(f"Anonymized file saved at: {output_file}")
            else:
                raise ValueError(f"Unsupported file: {args.file_path}. Use --help to see the available options.")

        logging.info("Processing complete.")

        # --- Final Output ---
        if not args.generate_ner_data and not args.no_report:
            elapsed_time = time.time() - start_time
            
            # Calculate file size and throughput
            try:
                if os.path.isfile(args.file_path):
                    file_size_bytes = os.path.getsize(args.file_path)
                elif os.path.isdir(args.file_path):
                    # Sum all files in directory
                    file_size_bytes = sum(
                        os.path.getsize(os.path.join(root, f))
                        for root, _, files in os.walk(args.file_path)
                        for f in files
                    )
                else:
                    file_size_bytes = 0
                
                file_size_kb = file_size_bytes / 1024
                file_size_mb = file_size_kb / 1024
                throughput_kbps = file_size_kb / elapsed_time if elapsed_time > 0 else 0
            except Exception:
                file_size_mb = 0
                throughput_kbps = 0
            
            print("\n" + "="*50)
            print("ANONYMIZATION STATISTICS")
            print("="*50)
            print(f"Total entities processed: {orchestrator.total_entities_processed}")
            if hasattr(orchestrator, 'entity_counts') and orchestrator.entity_counts:
                print("\nEntities by type:")
                for entity_type, count in sorted(orchestrator.entity_counts.items(), key=lambda x: x[1], reverse=True):
                    print(f"  {entity_type:30s}: {count:6,d}")
            
            print(f"\nPerformance:")
            print(f"  File size                     : {file_size_mb:8.2f} MB")
            print(f"  Processing time               : {elapsed_time:8.2f} seconds")
            print(f"  Average throughput            : {throughput_kbps:8.2f} KB/s")
            print("="*50 + "\n")
            write_report(args.file_path, start_time)

    except Exception as e:
        logging.error(f"Processing failed: {e}", exc_info=args.log_level == "DEBUG")
        sys.exit(1)
    finally:
        if db_context:
            db_context.shutdown()



if __name__ == "__main__":
    main()

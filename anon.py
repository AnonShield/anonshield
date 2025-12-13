import argparse
import warnings
import re
import logging
import os
import sys
import subprocess
import json
import torch
import spacy
import time
import csv
import signal
from pathlib import Path
from tqdm import tqdm


from src.anon.config import (
    ENTITY_MAPPING,
    SECRET_KEY,
    TRANSFORMER_MODEL,
    TRF_MODEL_PATH,
    ProcessingLimits,
    DefaultSizes,
    Global,
    LLM_CONFIG
)
from src.anon.database import DatabaseContext
from src.anon.engine import AnonymizationOrchestrator, load_custom_recognizers, SUPPORTED_LANGUAGES
from src.anon.processors import ProcessorRegistry
from src.anon.cache_manager import CacheManager
from src.anon.hash_generator import HashGenerator
from src.anon.entity_detector import EntityDetector
from src.anon.slm.client import OllamaClient
from src.anon.slm.prompts import PromptManager
from src.anon.slm.mappers.entity_mapper import SLMEntityMapper, EntityMapperExporter
from src.anon.slm.detectors.slm_detector import SLMEntityDetector
from src.anon.slm.anonymizers.slm_anonymizer import SLMAnonymizationStrategy, SLMFullAnonymizer

warnings.filterwarnings("ignore")


def _handle_slm_entity_mapping(args):
    """Orchestrates the SLM entity mapping process, writing results progressively."""
    logging.info("Starting SLM Entity Mapping process...")

    if not args.file_path or not os.path.exists(args.file_path):
        logging.error(f"File not found: {args.file_path}")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = Path(args.file_path).stem
    jsonl_output_path = output_dir / f"{base_name}_entity_map.jsonl"
    csv_output_path = output_dir / f"{base_name}_entity_map.csv"

    jsonl_file_handle = None
    csv_file_handle = None

    def graceful_shutdown(signum, frame):
        logging.warning(f"Interrupt signal ({signum}) received. Closing files and exiting.")
        if jsonl_file_handle and not jsonl_file_handle.closed:
            jsonl_file_handle.close()
        if csv_file_handle and not csv_file_handle.closed:
            csv_file_handle.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    try:
        jsonl_file_handle = open(jsonl_output_path, 'w', encoding='utf-8')
        csv_file_handle = open(csv_output_path, 'w', newline='', encoding='utf-8')
        csv_writer = csv.writer(csv_file_handle)
        csv_writer.writerow(["Text", "Entity Type", "Start", "End", "Confidence", "Reason", "Context"])

        ollama_config = LLM_CONFIG["ollama"]
        client = OllamaClient(
            model=ollama_config["model"], base_url=ollama_config["base_url"],
            timeout=300, temperature=ollama_config["temperature"], max_retries=5
        )
        prompt_manager = PromptManager(base_path="prompts")
        mapper = SLMEntityMapper(client, prompt_manager)

        file_extension = Path(args.file_path).suffix.lower()
        logging.info(f"Processing file '{args.file_path}'...")

        if file_extension == '.csv':
            try:
                import pandas as pd
                total_lines = sum(1 for _ in open(args.file_path, 'r', encoding='utf-8')) - 1
                chunk_iterator = pd.read_csv(args.file_path, chunksize=args.csv_chunk_size, on_bad_lines='skip', engine='python')
                
                with tqdm(total=total_lines, desc=f"Processing CSV {os.path.basename(args.file_path)}", unit="line") as pbar:
                    for chunk_df in chunk_iterator:
                        texts_to_map = [val for col in chunk_df.columns for val in chunk_df[col].dropna() if isinstance(val, str) and val.strip()]
                        if not texts_to_map:
                            pbar.update(len(chunk_df))
                            continue
                        
                        results_batch = mapper.batch_map(texts_to_map, language=args.lang, prompt_version=args.slm_prompt_version)
                        
                        for result in results_batch:
                            for entity in result.entities:
                                jsonl_file_handle.write(json.dumps(entity.to_dict()) + '\n')
                                csv_writer.writerow([
                                    entity.text, entity.entity_type, entity.start, 
                                    entity.end, entity.confidence, entity.reason, entity.context
                                ])
                        
                        jsonl_file_handle.flush()
                        csv_file_handle.flush()
                        pbar.update(len(chunk_df))

            except Exception as e:
                logging.error(f"Failed to process CSV file in chunks: {e}. All data will be loaded into memory.", exc_info=True)
                with open(args.file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                entity_stream = mapper.map_entities_stream(content, language=args.lang, prompt_version=args.slm_prompt_version)
                for entity in tqdm(entity_stream, desc="Processing file content"):
                    jsonl_file_handle.write(json.dumps(entity.to_dict()) + '\n')
                    csv_writer.writerow([
                        entity.text, entity.entity_type, entity.start, 
                        entity.end, entity.confidence, entity.reason, entity.context
                    ])
                    jsonl_file_handle.flush()
                    csv_file_handle.flush()
        else:
            with open(args.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            entity_stream = mapper.map_entities_stream(content, language=args.lang, prompt_version=args.slm_prompt_version)
            
            for entity in tqdm(entity_stream, desc="Mapping entities in file"):
                jsonl_file_handle.write(json.dumps(entity.to_dict()) + '\n')
                csv_writer.writerow([
                    entity.text, entity.entity_type, entity.start, 
                    entity.end, entity.confidence, entity.reason, entity.context
                ])
                jsonl_file_handle.flush()
                csv_file_handle.flush()

        logging.info(f"Progressive entity map (JSONL) saved to: {jsonl_output_path}")
        logging.info(f"Progressive entity map (CSV) saved to: {csv_output_path}")

    except Exception as e:
        logging.error(f"An error occurred during SLM entity mapping: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if jsonl_file_handle and not jsonl_file_handle.closed:
            jsonl_file_handle.close()
        if csv_file_handle and not csv_file_handle.closed:
            csv_file_handle.close()


def models_check(lang: str):
    """Downloads and verifies necessary spaCy and Transformer models."""
    import spacy.util
    from huggingface_hub import snapshot_download

    SPACY_MODEL_MAP = {"pt": "pt_core_news_lg", "en": "en_core_web_lg"}
    en_model = SPACY_MODEL_MAP["en"]
    requested = SPACY_MODEL_MAP.get(lang) or f"{lang}_core_news_lg"

    for model in (en_model, requested):
        if model and not spacy.util.is_package(model):
            logging.info(f"Spacy model '{model}' not found. Downloading...")
            try:
                subprocess.run(
                    [sys.executable, "-m", "spacy", "download", model],
                    check=True, capture_output=True, text=True,
                )
                logging.info(f"Successfully downloaded '{model}'.")
            except Exception as e:
                logging.error(f"Failed to download spaCy model '{model}': {e}")
                sys.exit(1)

    if not os.path.exists(TRF_MODEL_PATH):
        logging.info(f"Transformer model '{TRANSFORMER_MODEL}' not found. Downloading...")
        snapshot_download(repo_id=TRANSFORMER_MODEL, cache_dir=TRF_MODEL_PATH, max_workers=10)


def write_report(file_path, start_time):
    """Writes a simple performance report."""
    os.makedirs("logs", exist_ok=True)
    base_name = os.path.basename(file_path)
    report_file = os.path.join("logs", f"report_{base_name}.txt")
    with open(report_file, "w", encoding="utf-8") as report:
        report.write(f"Processed file: {file_path}\n")
        report.write(f"Total elapsed time: {time.time() - start_time:.2f} seconds\n")
    logging.info(f"Report saved at: {report_file}")


def get_supported_entities() -> list[str]:
    """Return a sorted list of supported entity names."""
    supported = set(ENTITY_MAPPING.values())
    try:
        for r in load_custom_recognizers(langs=['en']):
            supported.update(r.supported_entities)
    except Exception as exc:
        logging.warning(f"Failed to read custom recognizers: {exc}")
    return sorted(list(supported))


def _handle_list_entities():
    """Prints the list of supported entities and exits."""
    print("Supported entity types:")
    for entity in get_supported_entities():
        print(f" - {entity}")
    sys.exit(0)


def _parse_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Anonymize sensitive information or generate NER training data.")
    parser.add_argument("file_path", nargs='?', help="Path to the file or directory to be processed.")
    
    # Mode selection
    parser.add_argument("--generate-ner-data", action="store_true", help="Enable NER data generation mode instead of anonymizing.")

    # General options
    parser.add_argument("--list-entities", action="store_true", help="List all supported entity types and exit.")
    parser.add_argument("--list-languages", action="store_true", help="List all supported languages and exit.")
    parser.add_argument("--lang", type=str, default="en", help="Language of the document.")
    parser.add_argument("--output-dir", type=str, default="output", help="Directory to save output files. Default is 'output'.")
    parser.add_argument("--overwrite", action="store_true", help="Allow overwriting of existing output files.")
    parser.add_argument("--no-report", action="store_true", help="Disable the creation of a performance report in the 'logs' directory.")
    
    # Anonymization options
    parser.add_argument("--preserve-entities", type=str, default="", help="Comma-separated list of entity types to preserve.")
    parser.add_argument("--allow-list", type=str, default="", help="Comma-separated list of terms to allow.")
    parser.add_argument("--slug-length", type=int, default=None, help="Specify the length of the anonymized slug (0-64). If 0, only the entity type is used.")
    parser.add_argument("--anonymization-config", type=str, default=None, help="Path to a JSON file with advanced anonymization rules for structured files.")
    
    # Performance & Filtering options
    parser.add_argument("--preserve-row-context", action="store_true", help="For CSV/XLSX, process all values to preserve context instead of only unique values. Slower but more accurate.")
    parser.add_argument("--json-stream-threshold-mb", type=int, default=ProcessingLimits.JSON_STREAM_THRESHOLD_MB, help=f"JSON streaming threshold in MB. Files larger than this will be streamed from disk. Default: {ProcessingLimits.JSON_STREAM_THRESHOLD_MB}")
    parser.add_argument("--optimize", action="store_true", help="Enable all optimizations (fast strategy, cache, min-word-length=3, in-memory DB).")
    parser.add_argument("--use-cache", action="store_true", default=False, help="Enable in-memory caching for the run. Disabled by default.")
    parser.add_argument("--max-cache-size", type=int, default=ProcessingLimits.MAX_CACHE_SIZE, help=f"Maximum number of items to store in the in-memory cache. Default: {ProcessingLimits.MAX_CACHE_SIZE}")
    parser.add_argument("--min-word-length", type=int, default=0, help="Minimum character length for a word to be processed. Default is 0 (no limit).")
    parser.add_argument("--technical-stoplist", type=str, default="", help="Comma-separated list of custom words to add to the technical stoplist.")
    parser.add_argument("--skip-numeric", action="store_true", help="If set, numeric-only strings will not be anonymized. Default is to anonymize them if other rules permit.")
    parser.add_argument("--anonymization-strategy", type=str, default="presidio", choices=["presidio", "fast", "balanced", "slm"], help="Anonymization strategy ('presidio' for full analysis, 'fast' for an optimized path, 'balanced' for a mix of speed and accuracy, or 'slm' for end-to-end SLM anonymization).")
    parser.add_argument("--regex-priority", action="store_true", help="Give priority to custom regex recognizers over model-based ones.")
    parser.add_argument("--db-mode", type=str, default="persistent", choices=["persistent", "in-memory"], help="Database mode ('persistent' to save to disk, 'in-memory' for a temporary DB).")
    parser.add_argument("--db-dir", type=str, default="db", help="Directory for the database file.")
    parser.add_argument("--disable-gc", action="store_true", help="Disable automatic garbage collection during processing. May boost speed for single large files but increases memory usage.")
    parser.add_argument("--db-synchronous-mode", type=str, default=None, choices=["OFF", "NORMAL", "FULL", "EXTRA"], help="SQLite 'synchronous' PRAGMA mode. Overrides config file setting.")
    parser.add_argument("--log-level", type=str, default="WARNING", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Set the logging level (default: WARNING).")
    parser.add_argument("--force-large-xml", action="store_true", help="Force processing of XML files exceeding memory safety thresholds. Use with caution as it may lead to Out-of-Memory errors.")

    # SLM Options
    slm_group = parser.add_argument_group('SLM Options')
    slm_group.add_argument("--slm-map-entities", action="store_true", help="Use SLM to map potential entities for analysis (Task 1). Does not anonymize.")
    slm_group.add_argument("--slm-detector", action="store_true", help="Use SLM as an entity detector alongside traditional methods (Task 2).")
    slm_group.add_argument("--slm-detector-mode", type=str, default="hybrid", choices=["hybrid", "exclusive"], help="Mode for the SLM detector: 'hybrid' (default) merges with traditional NER, 'exclusive' uses only SLM results.")
    slm_group.add_argument("--slm-prompt-version", type=str, default="v1", help="Specify the prompt version to use for SLM tasks.")

    # Chunking & Batching Options
    chunk_group = parser.add_argument_group('Chunking and Batching')
    chunk_group.add_argument("--batch-size", type=int, default=DefaultSizes.BATCH_SIZE, help=f"Default batch size for processing text chunks. Default: {DefaultSizes.BATCH_SIZE}.")
    chunk_group.add_argument("--csv-chunk-size", type=int, default=DefaultSizes.CSV_CHUNK_SIZE, help=f"Chunk size for reading CSV files with pandas. Default: {DefaultSizes.CSV_CHUNK_SIZE}.")
    chunk_group.add_argument("--json-chunk-size", type=int, default=DefaultSizes.JSON_CHUNK_SIZE, help=f"Chunk size for streaming large JSON arrays. Default: {DefaultSizes.JSON_CHUNK_SIZE}.")
    chunk_group.add_argument("--ner-chunk-size", type=int, default=DefaultSizes.NER_CHUNK_SIZE, help=f"Max character size for text chunks in NER data generation. Default: {DefaultSizes.NER_CHUNK_SIZE}.")
    chunk_group.add_argument("--nlp-batch-size", type=int, default=DefaultSizes.NLP_BATCH_SIZE, help=f"Batch size for spaCy's nlp.pipe() processing. Default: {DefaultSizes.NLP_BATCH_SIZE}.")

    args = parser.parse_args()
    logging.debug(f"Parsed arguments: {args}")

    if args.list_entities:
        _handle_list_entities()

    if args.list_languages:
        _handle_list_languages()

    if args.slug_length is not None and not (0 <= args.slug_length <= 64):
        parser.error("--slug-length must be between 0 and 64.")

    if not args.file_path and not (args.list_entities or args.list_languages or args.slm_map_entities):
        parser.error("A file path must be provided.")

    # Handle the --optimize flag
    if args.optimize:
        logging.info("Optimization mode enabled: setting fast strategy, in-memory DB, cache, and min-word-length=3.")
        args.anonymization_strategy = "fast"
        args.db_mode = "in-memory"
        args.use_cache = True
        if args.min_word_length == 0:
            args.min_word_length = 3
    return args


def _handle_list_languages():
    """Prints the list of supported languages and exits."""
    print("Supported languages:")
    for lang_code, lang_name in SUPPORTED_LANGUAGES.items():
        print(f" - {lang_code}: {lang_name}")
    sys.exit(0)


def main():
    """Main function to orchestrate the anonymization or NER data generation process."""
    args = _parse_arguments()
    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {args.log_level}")
    logging.basicConfig(level=numeric_level, format='%(asctime)s - %(levelname)s - %(message)s', force=True)
    logging.debug(f"Resolved log level to: {numeric_level}")
    
    # --- Task 1: SLM Entity Mapping ---
    if args.slm_map_entities:
        _handle_slm_entity_mapping(args)
        sys.exit(0)

    logging.info("Starting anonymization process...")

    if not args.file_path or not os.path.exists(args.file_path):
        logging.critical(f"Input path not found: {args.file_path}")
        sys.exit(1)

    # --- Load Anonymization Config ---
    anonymization_config = None
    if args.anonymization_config:
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
    # Dynamically set LD_LIBRARY_PATH for CUDA libraries
    venv_python_path = os.path.dirname(sys.executable)
    venv_lib_path = os.path.join(os.path.dirname(venv_python_path), "lib")
    venv_python_version_path = next((d for d in os.listdir(venv_lib_path) if d.startswith("python") and os.path.isdir(os.path.join(venv_lib_path, d))), "python3.11")
    cuda_lib_path = os.path.join(venv_lib_path, venv_python_version_path, "site-packages", "nvidia", "cuda_runtime", "lib")
    
    if os.path.exists(cuda_lib_path):
        os.environ["LD_LIBRARY_PATH"] = f"{cuda_lib_path}:{os.environ.get('LD_LIBRARY_PATH', '')}"
        logging.info(f"LD_LIBRARY_PATH set to: {os.environ.get('LD_LIBRARY_PATH')}")
    else:
        logging.warning(f"CUDA library path not found: {cuda_lib_path}.")

    # --- GPU Activation ---
    logging.info("Verifying hardware...")
    if torch.cuda.is_available():
        try:
            spacy.require_gpu() # type: ignore
            logging.info(f"GPU activated successfully! (Device: {torch.cuda.get_device_name(0)})")
        except Exception as e:
            logging.warning(f"GPU detected, but failed to activate in Spacy: {e}")
    else:
        logging.info("CUDA not detected by PyTorch. Running on CPU.")

    # --- SECRET_KEY Validation (Early Exit) ---
    if not args.generate_ner_data and not SECRET_KEY:
        logging.error("ANON_SECRET_KEY or ANON_SECRET_KEY_FILE not set for anonymization.")
        sys.exit(1)

    start_time = time.time()
    
    db_context = None
    if not args.generate_ner_data:
        db_context = DatabaseContext(mode=args.db_mode, db_dir=args.db_dir)
        db_context.initialize(synchronous=args.db_synchronous_mode)
        logging.info(f"Database initialized in '{args.db_mode}' mode with synchronous PRAGMA set to '{args.db_synchronous_mode or 'NORMAL'}'.")

    # Update stoplist from CLI
    if args.technical_stoplist:
        new_stopwords = {term.strip().lower() for term in args.technical_stoplist.split(',') if term.strip()}
        if new_stopwords:
            Global.TECHNICAL_STOPLIST.update(new_stopwords)
            logging.info(f"Updated TECHNICAL_STOPLIST with {len(new_stopwords)} custom words.")

    models_check(args.lang)

    allow_list = [term.strip() for term in args.allow_list.split(',') if term]
    logging.debug(f"Allow list: {allow_list}")
    
    requested_preserve = [e.strip().upper() for e in args.preserve_entities.split(',') if e and e.strip()]
    logging.debug(f"Requested entities to preserve: {requested_preserve}")
    supported_entities_upper = {s.upper() for s in get_supported_entities()}
    unknown_entities = [e for e in requested_preserve if e not in supported_entities_upper]
    if unknown_entities:
        logging.warning(f"Unsupported entities will be ignored: {', '.join(unknown_entities)}")

    entities_to_preserve = [e for e in requested_preserve if e in supported_entities_upper]
    logging.debug(f"Effective entities to preserve: {entities_to_preserve}")

    try:
        engine_message = "NER detection engine" if args.generate_ner_data else "anonymization engine"
        logging.info(f"Initializing {engine_message} for language '{args.lang}'...")
        
        # Instantiate dependencies for injection
        cache_manager = CacheManager(
            use_cache=args.use_cache,
            max_cache_size=args.max_cache_size
        )
        hash_generator = HashGenerator()
        
        # --- Entity Detector Setup ---
        custom_recognizers = load_custom_recognizers([args.lang], regex_priority=args.regex_priority)
        compiled_patterns = []
        for recognizer in custom_recognizers:
            entity_type = recognizer.supported_entities[0]
            if entity_type in entities_to_preserve:
                continue
            for pattern in recognizer.patterns:
                try:
                    compiled_patterns.append({
                        "label": entity_type,
                        "regex": re.compile(pattern.regex, flags=re.DOTALL | re.IGNORECASE),
                        "score": pattern.score
                    })
                except re.error:
                    logging.warning(f"Invalid regex pattern skipped: {pattern.regex}")
        
        entity_detector = EntityDetector(
            compiled_patterns=compiled_patterns,
            entities_to_preserve=set(entities_to_preserve),
            allow_list=set(allow_list)
        )

        slm_detector_instance = None
        if args.slm_detector:
            logging.info("SLM detector enabled for hybrid mode (Task 2).")
            try:
                ollama_config = LLM_CONFIG["ollama"]
                client = OllamaClient(model=ollama_config["model"], base_url=ollama_config["base_url"])
                prompt_manager = PromptManager(base_path="prompts")
                slm_detector_instance = SLMEntityDetector(
                    slm_client=client,
                    prompt_manager=prompt_manager,
                    entities_to_preserve=set(entities_to_preserve),
                    allow_list=set(allow_list),
                    prompt_version=args.slm_prompt_version
                )
            except Exception as e:
                logging.error(f"Failed to initialize SLM detector, proceeding without it. Error: {e}")

        # --- Strategy Setup (SLM or Traditional) ---
        strategy_instance = None
        if args.anonymization_strategy == "slm":
            logging.info("Using 'slm' end-to-end anonymization strategy (Task 3).")
            try:
                ollama_config = LLM_CONFIG["ollama"]
                client = OllamaClient(model=ollama_config["model"], base_url=ollama_config["base_url"])
                prompt_manager = PromptManager(base_path="prompts")
                slm_anonymizer = SLMFullAnonymizer(
                    slm_client=client,
                    prompt_manager=prompt_manager
                )
                strategy_instance = SLMAnonymizationStrategy(
                    slm_anonymizer=slm_anonymizer,
                    lang=args.lang
                )
            except Exception as e:
                logging.critical(f"Failed to initialize SLM strategy. Error: {e}. Aborting.")
                sys.exit(1)
        
        # --- Orchestrator ---
        orchestrator = AnonymizationOrchestrator(
            lang=args.lang,
            db_context=db_context,
            allow_list=allow_list, 
            entities_to_preserve=entities_to_preserve,
            slug_length=args.slug_length,
            strategy=strategy_instance,
            strategy_name=args.anonymization_strategy,
            regex_priority=args.regex_priority,
            nlp_batch_size=args.nlp_batch_size,
            cache_manager=cache_manager,
            hash_generator=hash_generator,
            entity_detector=entity_detector,
            slm_detector=slm_detector_instance,
            slm_detector_mode=args.slm_detector_mode,
            ner_data_generation=args.generate_ner_data
        )
        
        # --- Processing ---
        processor_factory_args = {
            "ner_data_generation": args.generate_ner_data,
            "anonymization_config": anonymization_config,
            "min_word_length": args.min_word_length,
            "skip_numeric": args.skip_numeric,
            "output_dir": args.output_dir,
            "overwrite": args.overwrite,
            "disable_gc": args.disable_gc,
            "json_stream_threshold_mb": args.json_stream_threshold_mb,
            "preserve_row_context": args.preserve_row_context,
            "batch_size": args.batch_size,
            "csv_chunk_size": args.csv_chunk_size,
            "json_chunk_size": args.json_chunk_size,
            "ner_chunk_size": args.ner_chunk_size,
            "force_large_xml": args.force_large_xml,
        }
        logging.debug(f"Processor factory arguments: {processor_factory_args}")

        if os.path.isdir(args.file_path):
            mode_str = "Generating NER data from" if args.generate_ner_data else "Processing"
            logging.info(f"{mode_str} directory: {args.file_path}...")
            processed_files_count = 0
            
            for root, _, files in os.walk(args.file_path):
                for file_name in files:
                    file_full_path = os.path.join(root, file_name)
                    logging.debug(f"Attempting to get processor for file: {file_full_path}")
                    try:
                        processor = ProcessorRegistry.get_processor(file_full_path, orchestrator, **processor_factory_args)
                        if not processor: 
                            logging.debug(f"No suitable processor found for file: {file_full_path}. Skipping.")
                            continue
                        
                        output_file = processor.process()
                        processed_files_count += 1
                        if args.generate_ner_data:
                            logging.info(f"NER data for '{file_name}' saved at: {output_file}")
                        else:
                            logging.info(f"Anonymized file for '{file_name}' saved at: {output_file}")
                    except ValueError as ve:
                        logging.warning(f"Skipping file '{file_full_path}': {ve}")
                    except Exception as e:
                        logging.error(f"An error occurred processing file '{file_full_path}': {e}", exc_info=True)
            
            if processed_files_count == 0:
                logging.warning(f"No files were processed in the directory: {args.file_path}")
            else:
                logging.info(f"Finished processing {processed_files_count} files in directory: {args.file_path}")

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
                logging.warning(f"Skipping unsupported file: {args.file_path}")

        logging.info("Processing complete.")

        # --- Final Output ---
        if not args.generate_ner_data and not args.no_report:
            logging.info("\n--- Anonymization Stats ---")
            logging.info(f"Total entities processed: {orchestrator.total_entities_processed}")
            if hasattr(orchestrator, 'entity_counts') and orchestrator.entity_counts:
                logging.info("Entities by type:")
                for entity_type, count in sorted(orchestrator.entity_counts.items()):
                    logging.info(f"  - {entity_type}: {count}")
            logging.info("---------------------------\n")
            write_report(args.file_path, start_time)

    except Exception as e:
        logging.error(f"An error occurred during processing: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if db_context:
            db_context.shutdown()



if __name__ == "__main__":
    main()

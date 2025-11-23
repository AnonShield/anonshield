"""
Anonymization Command-Line Interface

This script provides a command-line interface to anonymize sensitive information in various file formats.
It orchestrates the process by parsing arguments, setting up the anonymization engine, 
and delegating the file processing to the appropriate processor.
"""

import argparse
import os
import subprocess
import sys
import time
import warnings
import spacy
import torch
import json

from src.anon.config import (
    ENTITY_MAPPING,
    SECRET_KEY,
    TRANSFORMER_MODEL,
    TRF_MODEL_PATH,
    initialize_db,
)
from src.anon.engine import AnonymizationOrchestrator, load_custom_recognizers, SUPPORTED_LANGUAGES
from src.anon.processors import get_processor

warnings.filterwarnings("ignore")


def models_check(lang: str):
    """Downloads and verifies necessary spaCy and Transformer models."""
    # This part remains as it is related to environment setup before engine initialization
    import spacy.util
    from huggingface_hub import snapshot_download

    spacy_model_map = {"pt": "pt_core_news_lg", "en": "en_core_web_lg"}
    en_model = spacy_model_map["en"]
    requested = spacy_model_map.get(lang) or f"{lang}_core_news_lg"

    for model in (en_model, requested):
        if model and not spacy.util.is_package(model):
            print(f"[+] Spacy model '{model}' not found. Downloading...")
            try:
                subprocess.run(
                    [sys.executable, "-m", "spacy", "download", model],
                    check=True, capture_output=True, text=True,
                )
                print(f"[*] Successfully downloaded '{model}'.")
            except Exception as e:
                print(f"[!] Failed to download spaCy model '{model}': {e}", file=sys.stderr)
                sys.exit(1)

    if not os.path.exists(TRF_MODEL_PATH):
        print(f"[!] Downloading Transformer model '{TRANSFORMER_MODEL}'...")
        snapshot_download(repo_id=TRANSFORMER_MODEL, cache_dir=TRF_MODEL_PATH, max_workers=10)


def write_report(file_path, start_time):
    """Writes a simple performance report."""
    os.makedirs("logs", exist_ok=True)
    base_name = os.path.basename(file_path)
    report_file = os.path.join("logs", f"report_{base_name}.txt")
    with open(report_file, "w", encoding="utf-8") as report:
        report.write(f"Processed file: {file_path}\n")
        report.write(f"Total elapsed time: {time.time() - start_time:.2f} seconds\n")
    print(f"Report saved at: {report_file}")


def get_supported_entities() -> list[str]:
    """Return a sorted list of supported entity names."""
    supported = set(ENTITY_MAPPING.values())
    try:
        for r in load_custom_recognizers(langs=['en']):
            supported.update(r.supported_entities)
    except Exception as exc:
        print(f"[!] Warning: failed to read custom recognizers: {exc}", file=sys.stderr)
    return sorted(list(supported))


def _handle_list_entities():
    """Prints the list of supported entities and exits."""
    print("[*] Supported entity types:")
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
    parser.add_argument("--slug-length", type=int, default=None, help="Specify the length of the anonymized slug (1-64).")
    parser.add_argument("--anonymization-config", type=str, default=None, help="Path to a JSON file with advanced anonymization rules for structured files.")
    
    # Performance & Filtering options
    parser.add_argument("--optimize", action="store_true", help="Enable all optimizations (fast strategy, cache, min-word-length=3, in-memory DB).")
    parser.add_argument("--use-cache", action="store_true", default=False, help="Enable in-memory caching for the run. Disabled by default.")
    parser.add_argument("--min-word-length", type=int, default=0, help="Minimum character length for a word to be processed. Default is 0 (no limit).")
    parser.add_argument("--technical-stoplist", type=str, default="", help="Comma-separated list of custom words to add to the technical stoplist.")
    parser.add_argument("--skip-numeric", action="store_true", help="If set, numeric-only strings will not be anonymized. Default is to anonymize them if other rules permit.")
    parser.add_argument("--anonymization-strategy", type=str, default="presidio", choices=["presidio", "fast"], help="Anonymization strategy ('presidio' for full analysis, 'fast' for an optimized path).")
    parser.add_argument("--regex-priority", action="store_true", help="Give priority to custom regex recognizers over model-based ones.")
    parser.add_argument("--db-mode", type=str, default="persistent", choices=["persistent", "in-memory"], help="Database mode ('persistent' to save to disk, 'in-memory' for a temporary DB).")
    parser.add_argument("--db-synchronous-mode", type=str, default=None, choices=["OFF", "NORMAL", "FULL", "EXTRA"], help="SQLite 'synchronous' PRAGMA mode. Overrides config file setting.")

    args = parser.parse_args()

    if args.list_entities:
        _handle_list_entities()

    if args.list_languages:
        _handle_list_languages()

    if args.slug_length is not None and not (1 <= args.slug_length <= 64):
        parser.error("--slug-length must be between 1 and 64.")

    if not args.file_path and not (args.list_entities or args.list_languages):
        parser.error("A file path must be provided.")

    # Handle the --optimize flag
    if args.optimize:
        args.anonymization_strategy = "fast"
        args.db_mode = "in-memory"
        args.use_cache = True
        if args.min_word_length == 0:
            args.min_word_length = 3


    return args


def _handle_list_languages():
    """Prints the list of supported languages and exits."""
    print("[*] Supported languages:")
    for lang_code, lang_name in SUPPORTED_LANGUAGES.items():
        print(f" - {lang_code}: {lang_name}")
    sys.exit(0)


def main():
    """Main function to orchestrate the anonymization or NER data generation process."""
    args = _parse_arguments()

    # --- Load Anonymization Config ---
    anonymization_config = None
    if args.anonymization_config:
        if not os.path.exists(args.anonymization_config):
            print(f"[!] Error: Anonymization config file not found at '{args.anonymization_config}'", file=sys.stderr)
            sys.exit(1)
        try:
            with open(args.anonymization_config, 'r', encoding='utf-8') as f:
                anonymization_config = json.load(f)
            print(f"[*] Loaded advanced anonymization rules from '{args.anonymization_config}'.")
        except json.JSONDecodeError:
            print(f"[!] Error: Could not decode JSON from '{args.anonymization_config}'. Please check the file format.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"[!] Error reading anonymization config file: {e}", file=sys.stderr)
            sys.exit(1)

    # --- Common Setup ---
    # Dynamically set LD_LIBRARY_PATH for CUDA libraries
    venv_python_path = os.path.dirname(sys.executable)
    venv_lib_path = os.path.join(os.path.dirname(venv_python_path), "lib")
    venv_python_version_path = next((d for d in os.listdir(venv_lib_path) if d.startswith("python") and os.path.isdir(os.path.join(venv_lib_path, d))), "python3.11")
    cuda_lib_path = os.path.join(venv_lib_path, venv_python_version_path, "site-packages", "nvidia", "cuda_runtime", "lib")
    
    if os.path.exists(cuda_lib_path):
        os.environ["LD_LIBRARY_PATH"] = f"{cuda_lib_path}:{os.environ.get('LD_LIBRARY_PATH', '')}"
        print(f"[*] LD_LIBRARY_PATH set to: {os.environ.get('LD_LIBRARY_PATH')}")
    else:
        print(f"[!] Warning: CUDA library path not found: {cuda_lib_path}.")

    # --- GPU Activation ---
    print("[*] Verifying hardware...")
    if torch.cuda.is_available():
        try:
            spacy.require_gpu()
            print(f"[+] GPU activated successfully! (Device: {torch.cuda.get_device_name(0)})")
        except Exception as e:
            print(f"[!] GPU detected, but failed to activate in Spacy: {e}")
    else:
        print("[!] CUDA not detected by PyTorch. Running on CPU.")

    if not args.generate_ner_data and not SECRET_KEY:
        print("[!] Error: ANON_SECRET_KEY environment variable not set for anonymization.", file=sys.stderr)
        sys.exit(1)

    start_time = time.time()
    if not args.generate_ner_data:
        initialize_db(mode=args.db_mode, synchronous=args.db_synchronous_mode)
    
    # Update stoplist from CLI
    if args.technical_stoplist:
        from src.anon.config import TECHNICAL_STOPLIST
        new_stopwords = {term.strip().lower() for term in args.technical_stoplist.split(',') if term.strip()}
        TECHNICAL_STOPLIST.update(new_stopwords)

    models_check(args.lang)

    allow_list = [term.strip() for term in args.allow_list.split(',') if term]
    
    requested_preserve = [e.strip().upper() for e in args.preserve_entities.split(',') if e and e.strip()]
    supported_entities_upper = {s.upper() for s in get_supported_entities()}
    unknown_entities = [e for e in requested_preserve if e not in supported_entities_upper]
    if unknown_entities:
        print(f"[!] Warning: Unsupported entities will be ignored: {', '.join(unknown_entities)}", file=sys.stderr)

    entities_to_preserve = [e for e in requested_preserve if e in supported_entities_upper]

    try:
        engine_message = "NER detection engine" if args.generate_ner_data else "anonymization engine"
        print(f"[+] Initializing {engine_message} for language '{args.lang}'...")
        
        orchestrator = AnonymizationOrchestrator(
            lang=args.lang, 
            allow_list=allow_list, 
            entities_to_preserve=entities_to_preserve,
            slug_length=args.slug_length,
            strategy=args.anonymization_strategy,
            use_cache=args.use_cache,
            regex_priority=args.regex_priority
        )
        
        # --- Processing ---
        processor_factory_args = {
            "ner_data_generation": args.generate_ner_data,
            "anonymization_config": anonymization_config,
            "min_word_length": args.min_word_length,
            "skip_numeric": args.skip_numeric,
            "output_dir": args.output_dir,
            "overwrite": args.overwrite,
        }

        if os.path.isdir(args.file_path):
            mode_str = "Generating NER data from" if args.generate_ner_data else "Processing"
            print(f"[+] {mode_str} directory: {args.file_path}...")
            processed_files = []
            
            for root, _, files in os.walk(args.file_path):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    try:
                        processor = get_processor(file_path, orchestrator, **processor_factory_args)
                        if not processor: continue # Skip unsupported files
                        output_file = processor.process()
                        processed_files.append(output_file)
                        if args.generate_ner_data:
                            print(f"[*] NER data for '{file_name}' saved at: {output_file}")
                        else:
                            print(f"[*] Anonymized file for '{file_name}' saved at: {output_file}")
                    except ValueError as ve:
                        print(f"[!] Skipping file '{file_path}': {ve}", file=sys.stderr)
                    except Exception as e:
                        print(f"[!] An error occurred processing file '{file_path}': {e}", file=sys.stderr)
            
            if not processed_files:
                print("[!] No files were processed in the directory.", file=sys.stderr)

        else:
            mode_str = "Generating NER data for" if args.generate_ner_data else "Processing"
            print(f"[+] {mode_str} file: {args.file_path}...")
            processor = get_processor(args.file_path, orchestrator, **processor_factory_args)
            output_file = processor.process()
            if args.generate_ner_data:
                print(f"\n[*] NER data generation complete. Saved at: {output_file}")
            else:
                 print(f"[*] Anonymized file saved at: {output_file}")


        # --- Final Output ---
        if not args.generate_ner_data and not args.no_report:
            print("\n--- Anonymization Stats ---")
            print(f"Total entities processed: {orchestrator.total_entities_processed}")
            if hasattr(orchestrator, 'entity_counts') and orchestrator.entity_counts:
                print("Entities by type:")
                for entity_type, count in sorted(orchestrator.entity_counts.items()):
                    print(f"  - {entity_type}: {count}")
            print("---------------------------\n")
            write_report(args.file_path, start_time)

    except Exception as e:
        print(f"[!] An error occurred during processing: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

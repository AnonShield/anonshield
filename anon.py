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
import threading
import queue
import pandas as pd


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
from src.anon.tqdm_handler import TqdmLoggingHandler

warnings.filterwarnings("ignore")


import threading
import queue


def _handle_sampling(args):
    """
    Orchestrates data sampling by file format.
    It groups files by format, samples from each file, and consolidates
    the samples into a single output file per format.
    """
    logging.info("Starting data sampling process (stratified by file, aggregated by format)...")

    if not args.file_path or not os.path.isdir(args.file_path):
        logging.error(f"Input path must be a directory for this sampling mode: {args.file_path}")
        sys.exit(1)

    if not args.sample_fraction and not args.sample_size:
        logging.error("Either --sample-fraction or --sample-size must be provided.")
        sys.exit(1)
        
    if args.sample_fraction and args.sample_size:
        logging.error("Please provide either --sample-fraction or --sample-size, not both.")
        sys.exit(1)

    if args.stratify_by:
        logging.warning("The --stratify-by argument is ignored. In this mode, stratification is done per file.")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    input_path = Path(args.file_path)

    # Group files by extension
    file_groups = {}
    for ext in ['csv', 'json', 'jsonl']:
        files = list(input_path.rglob(f'*.{ext}'))
        if files:
            file_groups[ext] = files

    if not file_groups:
        logging.warning(f"No compatible files (.csv, .json, .jsonl) found in {args.file_path}.")
        sys.exit(0)

    for ext, files in file_groups.items():
        logging.info(f"Processing {len(files)} file(s) for format '.{ext}'...")
        sampled_dfs = []

        try:
            if args.sample_fraction:
                for file_path in files:
                    logging.debug(f"Sampling {args.sample_fraction*100}% from {file_path.name}")
                    df = _read_dataframe(file_path)
                    if df is not None and not df.empty:
                        sampled_dfs.append(df.sample(frac=args.sample_fraction, random_state=args.random_seed))

            elif args.sample_size:
                # Proportional sampling based on file size
                file_infos = []
                total_rows = 0
                for file_path in files:
                    df = _read_dataframe(file_path)
                    if df is not None and not df.empty:
                        num_rows = len(df)
                        file_infos.append({'path': file_path, 'rows': num_rows, 'df': df})
                        total_rows += num_rows

                if total_rows > 0:
                    # Calculate proportional samples, ensuring total matches sample_size
                    target_sample = min(args.sample_size, total_rows)
                    samples_allocated = 0

                    for i, info in enumerate(file_infos):
                        proportion = info['rows'] / total_rows

                        # For the last file, allocate remaining samples to avoid rounding errors
                        if i == len(file_infos) - 1:
                            n_to_sample = target_sample - samples_allocated
                        else:
                            n_to_sample = round(target_sample * proportion)

                        # Ensure we don't sample more than available
                        n_to_sample = min(n_to_sample, info['rows'])

                        if n_to_sample > 0:
                            logging.debug(f"Sampling {n_to_sample} rows from {info['path'].name}")
                            sampled_dfs.append(info['df'].sample(n=n_to_sample, random_state=args.random_seed))
                            samples_allocated += n_to_sample

            if not sampled_dfs:
                logging.warning(f"No data was sampled for format '.{ext}'. This could be due to small file sizes or a small sample size.")
                continue

            # Consolidate and shuffle
            final_df = pd.concat(sampled_dfs, ignore_index=True)
            final_df = final_df.sample(frac=1, random_state=args.random_seed).reset_index(drop=True)

            # Save consolidated file
            output_filename = f"{input_path.name}_{ext}_sampled.{ext}"
            output_path = output_dir / output_filename
            
            if not args.overwrite and output_path.exists():
                logging.warning(f"Output file {output_path} already exists. Use --overwrite to replace it.")
                continue

            _write_dataframe(final_df, output_path)
            logging.info(f"Successfully saved consolidated sample for '.{ext}' to {output_path}")

        except Exception as e:
            logging.error(f"Failed to process format '.{ext}': {e}", exc_info=True)

    logging.info("Data sampling process finished.")


def _read_dataframe(file_path: Path) -> pd.DataFrame | None:
    """Reads a file into a pandas DataFrame based on its extension."""
    try:
        if file_path.suffix == '.csv':
            return pd.read_csv(file_path)
        elif file_path.suffix == '.jsonl':
            return pd.read_json(file_path, lines=True)
        elif file_path.suffix == '.json':
            # Assuming JSON contains a list of objects
            return pd.read_json(file_path)
        else:
            logging.warning(f"Unsupported file format: {file_path.suffix}")
            return None
    except Exception as e:
        logging.error(f"Could not read or parse {file_path}: {e}")
        return None

def _write_dataframe(df: pd.DataFrame, output_path: Path):
    """Writes a DataFrame to a file based on its extension."""
    ext = output_path.suffix
    if ext == '.csv':
        df.to_csv(output_path, index=False)
    elif ext == '.jsonl':
        df.to_json(output_path, orient='records', lines=True)
    elif ext == '.json':
        df.to_json(output_path, orient='records', indent=2)


def _extract_cve_id_from_json(json_data: dict) -> str | None:
    """Extracts CVE ID from a JSON file following the cvelistV5 format.
    
    Args:
        json_data: Parsed JSON object from a CVE file
        
    Returns:
        CVE ID string (e.g., 'CVE-2024-53009') or None if not found
    """
    try:
        # cvelistV5 format has cveMetadata.cveId
        if 'cveMetadata' in json_data and 'cveId' in json_data['cveMetadata']:
            return json_data['cveMetadata']['cveId']
    except (TypeError, KeyError):
        pass
    return None


def _load_cve_files_into_index(cve_directory: Path) -> dict:
    """Loads all CVE JSON files from cvelistV5 directory structure into a searchable index.
    
    Directory structure expected: /cves/YYYY/xxxx/CVE-YYYY-xxxxx.json
    
    Args:
        cve_directory: Path to the cves directory
        
    Returns:
        Dictionary mapping CVE IDs to file paths
    """
    cve_index = {}
    total_files = 0
    failed_files = 0
    
    logging.info(f"Indexing CVE files from {cve_directory}...")
    
    for json_file in cve_directory.rglob("*.json"):
        # Skip metadata files like delta.json, deltaLog.json
        if json_file.name in ["delta.json", "deltaLog.json"]:
            continue
            
        total_files += 1
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                cve_data = json.load(f)
                cve_id = _extract_cve_id_from_json(cve_data)
                if cve_id:
                    cve_index[cve_id] = json_file
                    if total_files % 10000 == 0:
                        logging.debug(f"Indexed {total_files} CVE files...")
        except (json.JSONDecodeError, IOError) as e:
            failed_files += 1
            logging.debug(f"Failed to parse CVE file {json_file.name}: {e}")
            
    logging.info(f"CVE indexing complete: {len(cve_index)} CVEs indexed, {failed_files} failed")
    return cve_index


def _generate_cve_dataset_with_distribution(args):
    """Generates a CVE dataset following the vulnerability distribution from CAIS data.
    
    This function:
    1. Reads CAIS anonymized data to extract vulnerability frequency distribution
    2. Loads random CVEs from cvelistV5 directory
    3. Assigns CAIS frequencies to random CVEs (maintaining distribution shape)
    4. Replicates CVEs according to assigned frequencies
    5. Outputs consolidated dataset in desired format
    
    The key insight: We preserve the DISTRIBUTION of frequencies (how many vulns appear 1x, 2x, etc.)
    but use random CVEs instead of the specific vulnerabilities from CAIS.
    
    Args:
        args: Argument namespace containing:
            - cais_file_path: Path to CAIS anonymized CSV/JSON file
            - cve_directory: Path to cvelistV5/cves directory
            - output_dir: Output directory for generated dataset
            - output_format: Format for output (json, jsonl, csv)
            - random_seed: Random seed for reproducibility
            - overwrite: Whether to overwrite existing output files
    """
    logging.info("Starting CVE dataset generation with CAIS distribution stratification...")
    
    # Validate inputs
    cais_path = Path(args.cais_file_path)
    if not cais_path.exists():
        logging.error(f"CAIS path not found: {cais_path}")
        sys.exit(1)
        
    cve_dir = Path(args.cve_directory)
    if not cve_dir.exists() or not (cve_dir / "2024").exists():
        logging.error(f"Invalid CVE directory structure: {cve_dir}")
        logging.error("Expected: <cve_directory>/YYYY/xxxx/CVE-*.json")
        sys.exit(1)
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Set random seed for reproducibility
    import random
    if args.random_seed is not None:
        random.seed(args.random_seed)
    
    # Step 1: Read CAIS data (file or directory) and extract vulnerability frequency distribution
    all_dataframes = []
    
    if cais_path.is_file():
        logging.info(f"Reading CAIS file: {cais_path}...")
        try:
            df = _read_dataframe(cais_path)
            if df is not None and not df.empty:
                # Normalize 'definition' column if it's a nested dict (from JSON files)
                if 'definition' in df.columns and not df['definition'].empty:
                    first_val = df['definition'].iloc[0]
                    if isinstance(first_val, dict):
                        logging.info(f"  Normalizing nested 'definition' column...")
                        df['definition.id'] = df['definition'].apply(
                            lambda x: x.get('id') if isinstance(x, dict) else None
                        )
                
                all_dataframes.append(df)
        except Exception as e:
            logging.error(f"Error reading CAIS file: {e}")
            sys.exit(1)
    elif cais_path.is_dir():
        logging.info(f"Reading all CAIS files from directory: {cais_path}...")
        # Process all supported files in directory
        for ext in ['csv', 'json', 'jsonl']:
            files = list(cais_path.rglob(f'*.{ext}'))
            for file_path in files:
                logging.info(f"  Reading {file_path.name}...")
                try:
                    df = _read_dataframe(file_path)
                    if df is not None and not df.empty:
                        # Normalize 'definition' column if it's a nested dict (from JSON files)
                        if 'definition' in df.columns and not df['definition'].empty:
                            first_val = df['definition'].iloc[0]
                            if isinstance(first_val, dict):
                                logging.info(f"    - Normalizing nested 'definition' column...")
                                df['definition.id'] = df['definition'].apply(
                                    lambda x: x.get('id') if isinstance(x, dict) else None
                                )
                        
                        all_dataframes.append(df)
                        logging.info(f"    - Loaded {len(df)} records")
                except Exception as e:
                    logging.warning(f"    - Failed to read {file_path.name}: {e}")
    
    if not all_dataframes:
        logging.error(f"No data could be read from {cais_path}")
        sys.exit(1)
    
    # Combine all dataframes
    logging.info(f"Combining {len(all_dataframes)} CAIS file(s)...")
    df_cais = pd.concat(all_dataframes, ignore_index=True)
    logging.info(f"Total combined records: {len(df_cais)}")
    
    # Determine vulnerability ID column - prioritize definition.id for complete coverage
    vuln_col = None
    if 'definition.id' in df_cais.columns:
        vuln_col = 'definition.id'
    elif 'definition.cve' in df_cais.columns:
        vuln_col = 'definition.cve'
    elif 'cve' in df_cais.columns:
        vuln_col = 'cve'
    else:
        logging.error(f"Could not find vulnerability column in CAIS data. Available columns: {df_cais.columns.tolist()}")
        sys.exit(1)
    
    # Count vulnerability frequencies - get the list of frequencies (not the specific vulns)
    vuln_frequency_counts = df_cais[vuln_col].value_counts()
    frequency_list = sorted(vuln_frequency_counts.tolist(), reverse=True)  # List of frequencies
    
    logging.info(f"CAIS distribution extracted:")
    logging.info(f"  - Total records: {len(df_cais)}")
    logging.info(f"  - Unique vulnerabilities: {len(frequency_list)}")
    logging.info(f"  - Frequency range: {min(frequency_list)} to {max(frequency_list)}")
    logging.info(f"  - Average frequency: {sum(frequency_list)/len(frequency_list):.2f}")
    
    # Step 2: Load CVE index
    logging.info("Building CVE file index...")
    cve_index = _load_cve_files_into_index(cve_dir)
    if not cve_index:
        logging.error(f"No CVE files found in {cve_dir}")
        sys.exit(1)
    
    # Check if we have enough CVEs
    if len(cve_index) < len(frequency_list):
        logging.warning(f"CVE repository has {len(cve_index)} CVEs, but CAIS has {len(frequency_list)} unique vulnerabilities.")
        logging.warning(f"Will use available CVEs with potential duplicates.")
    
    # Step 3: Randomly select CVEs and assign frequencies
    logging.info(f"Randomly assigning {len(frequency_list)} CVEs to match CAIS distribution...")
    
    # Get list of all available CVE IDs
    available_cve_ids = list(cve_index.keys())
    
    # Randomly sample CVEs (with replacement if needed)
    if len(available_cve_ids) >= len(frequency_list):
        # Sample without replacement
        selected_cve_ids = random.sample(available_cve_ids, len(frequency_list))
    else:
        # Sample with replacement
        selected_cve_ids = random.choices(available_cve_ids, k=len(frequency_list))
    
    # Pair each selected CVE with a frequency from CAIS
    cve_frequency_pairs = list(zip(selected_cve_ids, frequency_list))
    
    logging.info(f"Selected {len(selected_cve_ids)} random CVEs from repository")
    logging.info(f"Top 10 CVEs with highest frequencies:")
    for i, (cve_id, freq) in enumerate(cve_frequency_pairs[:10]):
        logging.info(f"  {i+1}. {cve_id}: {freq}x")
    
    # Step 4: Load CVE data and replicate according to frequencies
    logging.info("Loading CVE data and creating replicated dataset...")
    cve_data_list = []
    failed_loads = 0
    
    for cve_id, frequency in cve_frequency_pairs:
        cve_file = cve_index[cve_id]
        try:
            with open(cve_file, 'r', encoding='utf-8') as f:
                cve_json = json.load(f)
                # Replicate the CVE data according to its assigned frequency
                for _ in range(frequency):
                    cve_record = {
                        'cve_id': cve_id,
                        'cais_frequency': frequency,
                        'cve_data': cve_json
                    }
                    cve_data_list.append(cve_record)
        except (json.JSONDecodeError, IOError) as e:
            failed_loads += 1
            logging.warning(f"Could not load CVE file for {cve_id}: {e}")
    
    if failed_loads > 0:
        logging.warning(f"Failed to load {failed_loads} CVE files")
    
    if not cve_data_list:
        logging.error("No CVE data was loaded. Check CVE directory.")
        sys.exit(1)
    
    logging.info(f"Dataset creation complete:")
    logging.info(f"  - Total CVE records (with replications): {len(cve_data_list)}")
    logging.info(f"  - Unique CVEs: {len(set(r['cve_id'] for r in cve_data_list))}")
    logging.info(f"  - Failed loads: {failed_loads}")
    
    # Step 4: Create dataframe and shuffle
    logging.info(f"Creating dataset with {len(cve_data_list)} CVE records (including replications)...")
    df_dataset = pd.DataFrame(cve_data_list)
    
    # Shuffle with reproducible seed
    if args.random_seed is not None:
        df_dataset = df_dataset.sample(frac=1, random_state=args.random_seed).reset_index(drop=True)
    else:
        df_dataset = df_dataset.sample(frac=1).reset_index(drop=True)
    
    # Step 5: Save output
    output_format = getattr(args, 'output_format', 'jsonl')
    if output_format not in ['json', 'jsonl', 'csv']:
        output_format = 'jsonl'
    
    cais_base = cais_path.stem
    output_filename = f"cve_dataset_{cais_base}_stratified.{output_format}"
    output_path = output_dir / output_filename
    
    if output_path.exists() and not args.overwrite:
        logging.error(f"Output file already exists: {output_path}. Use --overwrite to replace.")
        sys.exit(1)
    
    logging.info(f"Saving dataset to {output_path}...")
    try:
        _write_dataframe(df_dataset, output_path)
        logging.info(f"Successfully created CVE dataset: {output_path}")
        logging.info(f"Dataset statistics:")
        logging.info(f"  - Total records: {len(df_dataset)}")
        logging.info(f"  - Unique CVEs: {df_dataset['cve_id'].nunique()}")
        logging.info(f"  - Frequency range: {df_dataset['cais_frequency'].min()} to {df_dataset['cais_frequency'].max()}")
    except Exception as e:
        logging.error(f"Failed to save dataset: {e}")
        sys.exit(1)
    
    logging.info("CVE dataset generation complete.")


def _handle_slm_entity_mapping(args):
    """Orchestrates the SLM entity mapping process with threaded, progressive writing."""
    logging.info("Starting SLM Entity Mapping process...")

    if not args.file_path or not os.path.exists(args.file_path):
        logging.error(f"File not found: {args.file_path}")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = Path(args.file_path).stem
    jsonl_output_path = output_dir / f"{base_name}_entity_map.jsonl"
    csv_output_path = output_dir / f"{base_name}_entity_map.csv"

    # 1. Setup Producer-Consumer Queue
    write_queue = queue.Queue()

    # 2. Define the Consumer (Writer) Thread
    def writer_worker(q, jsonl_path, csv_path):
        try:
            with open(jsonl_path, 'w', encoding='utf-8') as jf, \
                 open(csv_path, 'w', newline='', encoding='utf-8') as cf:
                
                csv_writer = csv.writer(cf)
                csv_writer.writerow(["Text", "Entity Type", "Start", "End", "Confidence", "Reason", "Context"])

                while True:
                    item = q.get()
                    if item is None:  # Sentinel value to stop the thread
                        break
                    
                    # Write to both files
                    jf.write(json.dumps(item.to_dict()) + '\n')
                    csv_writer.writerow([
                        item.text, item.entity_type, item.start, 
                        item.end, item.confidence, item.reason, item.context
                    ])
                    q.task_done()
        except Exception as e:
            logging.error(f"Error in writer thread: {e}", exc_info=True)

    # 3. Start the writer thread
    writer_thread = threading.Thread(target=writer_worker, args=(write_queue, jsonl_output_path, csv_output_path))
    writer_thread.daemon = True # Allows main thread to exit even if writer is blocked
    writer_thread.start()

    # 4. Graceful shutdown handler
    def graceful_shutdown(signum, frame):
        logging.warning(f"Interrupt signal ({signum}) received. Draining queue and exiting.")
        write_queue.put(None)  # Signal writer to stop
        writer_thread.join()   # Wait for writer to finish
        sys.exit(0)

    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    # 5. Main (Producer) Logic
    try:
        ollama_config = LLM_CONFIG["ollama"]
        client = OllamaClient(
            model=ollama_config["model"],
            base_url=ollama_config["base_url"],
            timeout=300,
            temperature=args.slm_temperature,
            max_retries=5,
            auto_manage=not args.no_auto_ollama,
            docker_image=args.ollama_docker_image,
            container_name=args.ollama_container_name,
            gpu_enabled=not args.ollama_no_gpu
        )
        prompt_manager = PromptManager(base_path="prompts")
        mapper = SLMEntityMapper(
            client, 
            prompt_manager,
            max_chunk_size=args.slm_chunk_size,
            confidence_threshold=args.slm_confidence_threshold,
            context_window=args.slm_context_window
        )

        logging.info(f"Processing file '{args.file_path}'...")
        with open(args.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # The stream is now the producer
        entity_stream = mapper.map_entities_stream(content, language=args.lang, prompt_version=args.slm_prompt_version)
        
        for entity in entity_stream:
            write_queue.put(entity)

        logging.info("Finished processing file. Waiting for writer to complete...")

    except Exception as e:
        logging.error(f"An error occurred during SLM entity mapping: {e}", exc_info=True)
    finally:
        # 6. Signal writer to finish and wait
        write_queue.put(None)
        writer_thread.join()
        logging.info(f"Progressive entity map (JSONL) saved to: {jsonl_output_path}")
        logging.info(f"Progressive entity map (CSV) saved to: {csv_output_path}")



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
    parser.add_argument("--ner-include-all", action="store_true", help="Include all texts in NER output, even those without detected entities. Useful for training models to recognize non-PII text.")
    parser.add_argument("--ner-aggregate-record", action="store_true", help="For JSON/JSONL files, aggregate each record into a single text line instead of extracting fields separately. Produces more contextual NER training data.")

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
    parser.add_argument("--slug-length", type=int, default=DefaultSizes.DEFAULT_SLUG_LENGTH, help=f"Specify the length of the anonymized slug (0-64). If 0, only the entity type is used. Default: {DefaultSizes.DEFAULT_SLUG_LENGTH}.")
    parser.add_argument("--anonymization-config", type=str, default=None, help="Path to a JSON file with advanced anonymization rules for structured files.")
    
    # Sampling Options
    sample_group = parser.add_argument_group('Sampling Options')
    sample_group.add_argument("--sample", action="store_true", help="Enable sampling mode to generate a random sample from a file or directory.")
    sample_group.add_argument("--sample-fraction", type=float, help="Fraction of items to sample (e.g., 0.1 for 10%%).")
    sample_group.add_argument("--sample-size", type=int, help="Fixed number of items to sample.")
    sample_group.add_argument("--stratify-by", type=str, help="Column or key to use for stratified sampling.")
    sample_group.add_argument("--random-seed", type=int, help="Random seed for reproducible sampling.")

    # CVE Dataset Generation Options
    cve_group = parser.add_argument_group('CVE Dataset Generation Options')
    cve_group.add_argument("--generate-cve-dataset", action="store_true", help="Generate a CVE dataset following CAIS vulnerability distribution (stratified sampling).")
    cve_group.add_argument("--cais-file-path", type=str, help="Path to CAIS anonymized CSV or JSON file containing vulnerability data and frequencies.")
    cve_group.add_argument("--cve-directory", type=str, default="/home/kapelinski/Downloads/cvelistV5-main/cves", 
                           help="Path to cvelistV5 cves directory containing CVE JSON files organized by year. Default: cvelistV5-main/cves")
    cve_group.add_argument("--output-format", type=str, default="jsonl", choices=["json", "jsonl", "csv"],
                           help="Output format for generated CVE dataset. Default: jsonl")

    # Performance & Filtering options
    parser.add_argument("--preserve-row-context", action="store_true", help="For CSV/XLSX, process all values to preserve context instead of only unique values. Slower but more accurate.")
    parser.add_argument("--json-stream-threshold-mb", type=int, default=ProcessingLimits.JSON_STREAM_THRESHOLD_MB, help=f"JSON streaming threshold in MB. Files larger than this will be streamed from disk. Default: {ProcessingLimits.JSON_STREAM_THRESHOLD_MB}")
    parser.add_argument("--optimize", action="store_true", help="Enable all optimizations (fast strategy, cache, min-word-length=3, in-memory DB).")
    parser.add_argument("--use-cache", action="store_true", default=True, help="Enable in-memory caching for the run. Enabled by default. Use --no-use-cache to disable.")
    parser.add_argument("--no-use-cache", action="store_false", dest="use_cache", help="Disable in-memory caching for the run.")
    parser.add_argument("--max-cache-size", type=int, default=ProcessingLimits.MAX_CACHE_SIZE, help=f"Maximum number of items to store in the in-memory cache. Default: {ProcessingLimits.MAX_CACHE_SIZE}")
    parser.add_argument("--min-word-length", type=int, default=DefaultSizes.DEFAULT_MIN_WORD_LENGTH, help=f"Minimum character length for a word to be processed. Default: {DefaultSizes.DEFAULT_MIN_WORD_LENGTH} (no limit).")
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
    slm_group.add_argument("--slm-chunk-size", type=int, default=DefaultSizes.SLM_MAPPER_CHUNK_SIZE, help=f"Max character size for chunks sent to the SLM mapper. Default: {DefaultSizes.SLM_MAPPER_CHUNK_SIZE}.")
    slm_group.add_argument("--slm-confidence-threshold", type=float, default=DefaultSizes.DEFAULT_SLM_CONFIDENCE_THRESHOLD, help=f"Minimum confidence score for entities from the SLM mapper. Default: {DefaultSizes.DEFAULT_SLM_CONFIDENCE_THRESHOLD}.")
    slm_group.add_argument("--slm-context-window", type=int, default=DefaultSizes.DEFAULT_SLM_CONTEXT_WINDOW, help=f"Character window size for context extraction in SLM mapper. Default: {DefaultSizes.DEFAULT_SLM_CONTEXT_WINDOW}.")
    slm_group.add_argument("--slm-temperature", type=float, default=LLM_CONFIG['ollama']['temperature'], help=f"Temperature for the SLM model. Default: {LLM_CONFIG['ollama']['temperature']}.")

    # Ollama Service Management Options
    ollama_group = parser.add_argument_group('Ollama Service Options')
    ollama_group.add_argument("--no-auto-ollama", action="store_true", help="Disable automatic Ollama Docker management. By default, the script will start/manage Ollama automatically.")
    ollama_group.add_argument("--ollama-docker-image", type=str, default="ollama/ollama:latest", help="Docker image for Ollama. Default: ollama/ollama:latest")
    ollama_group.add_argument("--ollama-container-name", type=str, default="ollama-anon", help="Docker container name for Ollama. Default: ollama-anon")
    ollama_group.add_argument("--ollama-no-gpu", action="store_true", help="Disable GPU support when starting Ollama Docker container.")

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

    if not args.file_path and not (args.list_entities or args.list_languages or args.slm_map_entities or args.sample or args.generate_cve_dataset):
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
    tqdm_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(tqdm_handler)
    
    logging.debug(f"Resolved log level to: {numeric_level} and configured TqdmLoggingHandler.")

    # --- Task: Sampling ---
    if args.sample:
        _handle_sampling(args)
        sys.exit(0)
    
    # --- Task: CVE Dataset Generation ---
    if args.generate_cve_dataset:
        if not args.cais_file_path:
            logging.error("--cais-file-path is required when using --generate-cve-dataset")
            sys.exit(1)
        _generate_cve_dataset_with_distribution(args)
        sys.exit(0)
        
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
    # Dynamically set LD_LIBRARY_PATH for all NVIDIA CUDA libraries
    venv_python_path = os.path.dirname(sys.executable)
    venv_lib_path = os.path.join(os.path.dirname(venv_python_path), "lib")
    venv_python_version_path = next((d for d in os.listdir(venv_lib_path) if d.startswith("python") and os.path.isdir(os.path.join(venv_lib_path, d))), "python3.11")
    nvidia_base_path = os.path.join(venv_lib_path, venv_python_version_path, "site-packages", "nvidia")

    if os.path.exists(nvidia_base_path):
        # Find all lib directories under nvidia packages
        cuda_lib_paths = []
        for package_dir in os.listdir(nvidia_base_path):
            lib_path = os.path.join(nvidia_base_path, package_dir, "lib")
            if os.path.isdir(lib_path):
                cuda_lib_paths.append(lib_path)

        if cuda_lib_paths:
            cuda_libs_str = ":".join(cuda_lib_paths)
            os.environ["LD_LIBRARY_PATH"] = f"{cuda_libs_str}:{os.environ.get('LD_LIBRARY_PATH', '')}"
            logging.info(f"CUDA libraries configured ({len(cuda_lib_paths)} paths added to LD_LIBRARY_PATH)")
    else:
        logging.warning(f"NVIDIA library path not found: {nvidia_base_path}.")

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
                client = OllamaClient(
                    model=ollama_config["model"],
                    base_url=ollama_config["base_url"],
                    auto_manage=not args.no_auto_ollama,
                    docker_image=args.ollama_docker_image,
                    container_name=args.ollama_container_name,
                    gpu_enabled=not args.ollama_no_gpu
                )
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
                client = OllamaClient(
                    model=ollama_config["model"],
                    base_url=ollama_config["base_url"],
                    auto_manage=not args.no_auto_ollama,
                    docker_image=args.ollama_docker_image,
                    container_name=args.ollama_container_name,
                    gpu_enabled=not args.ollama_no_gpu
                )
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

#!/usr/bin/env python3
"""
CVE Dataset Generator

Generates a CVE dataset following the vulnerability distribution from CAIS data.
Uses stratified sampling to maintain the distribution shape while using random CVEs.

Usage:
    python scripts/generate_cve_dataset.py --cais-path /path/to/cais_data.csv --cve-dir /path/to/cvelistV5/cves
    python scripts/generate_cve_dataset.py --cais-path /path/to/cais_dir --cve-dir /path/to/cves --format jsonl
"""
import argparse
import json
import logging
import random
import sys
from pathlib import Path

import pandas as pd

from .utils import read_dataframe, write_dataframe, setup_logging


def extract_cve_id_from_json(json_data: dict) -> str | None:
    """Extract CVE ID from a JSON file following the cvelistV5 format.
    
    Args:
        json_data: Parsed JSON object from a CVE file
        
    Returns:
        CVE ID string (e.g., 'CVE-2024-53009') or None if not found
    """
    try:
        if 'cveMetadata' in json_data and 'cveId' in json_data['cveMetadata']:
            return json_data['cveMetadata']['cveId']
    except (TypeError, KeyError):
        pass
    return None


def load_cve_index(cve_directory: Path) -> dict[str, Path]:
    """Load all CVE JSON files from cvelistV5 directory into a searchable index.
    
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
        # Skip metadata files
        if json_file.name in ["delta.json", "deltaLog.json"]:
            continue
        
        total_files += 1
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                cve_data = json.load(f)
                cve_id = extract_cve_id_from_json(cve_data)
                if cve_id:
                    cve_index[cve_id] = json_file
                    if total_files % 10000 == 0:
                        logging.debug(f"Indexed {total_files} CVE files...")
        except (json.JSONDecodeError, IOError) as e:
            failed_files += 1
            logging.debug(f"Failed to parse CVE file {json_file.name}: {e}")
    
    logging.info(f"CVE indexing complete: {len(cve_index)} CVEs indexed, {failed_files} failed")
    return cve_index


def load_cais_distribution(cais_path: Path) -> list[int]:
    """Load CAIS data and extract vulnerability frequency distribution.
    
    Args:
        cais_path: Path to CAIS file or directory
        
    Returns:
        List of frequencies sorted in descending order
    """
    all_dataframes = []
    
    if cais_path.is_file():
        logging.info(f"Reading CAIS file: {cais_path}...")
        df = read_dataframe(cais_path)
        if df is not None and not df.empty:
            # Normalize 'definition' column if it's a nested dict
            if 'definition' in df.columns and not df['definition'].empty:
                first_val = df['definition'].iloc[0]
                if isinstance(first_val, dict):
                    logging.info("Normalizing nested 'definition' column...")
                    df['definition.id'] = df['definition'].apply(
                        lambda x: x.get('id') if isinstance(x, dict) else None
                    )
            all_dataframes.append(df)
    elif cais_path.is_dir():
        logging.info(f"Reading all CAIS files from directory: {cais_path}...")
        for ext in ['csv', 'json', 'jsonl']:
            for file_path in cais_path.rglob(f'*.{ext}'):
                logging.info(f"  Reading {file_path.name}...")
                df = read_dataframe(file_path)
                if df is not None and not df.empty:
                    if 'definition' in df.columns and not df['definition'].empty:
                        first_val = df['definition'].iloc[0]
                        if isinstance(first_val, dict):
                            df['definition.id'] = df['definition'].apply(
                                lambda x: x.get('id') if isinstance(x, dict) else None
                            )
                    all_dataframes.append(df)
                    logging.info(f"    Loaded {len(df)} records")
    else:
        raise ValueError(f"CAIS path not found: {cais_path}")
    
    if not all_dataframes:
        raise ValueError(f"No data could be read from {cais_path}")
    
    # Combine all dataframes
    df_cais = pd.concat(all_dataframes, ignore_index=True)
    logging.info(f"Total combined records: {len(df_cais)}")
    
    # Determine vulnerability ID column
    vuln_col = None
    for col in ['definition.id', 'definition.cve', 'cve']:
        if col in df_cais.columns:
            vuln_col = col
            break
    
    if not vuln_col:
        raise ValueError(f"Could not find vulnerability column. Available: {df_cais.columns.tolist()}")
    
    # Extract frequency distribution
    frequency_list = sorted(df_cais[vuln_col].value_counts().tolist(), reverse=True)
    
    logging.info(f"CAIS distribution extracted:")
    logging.info(f"  - Total records: {len(df_cais)}")
    logging.info(f"  - Unique vulnerabilities: {len(frequency_list)}")
    logging.info(f"  - Frequency range: {min(frequency_list)} to {max(frequency_list)}")
    logging.info(f"  - Average frequency: {sum(frequency_list)/len(frequency_list):.2f}")
    
    return frequency_list


def generate_cve_dataset(
    cais_path: Path,
    cve_directory: Path,
    output_dir: Path,
    output_format: str = "jsonl",
    random_seed: int | None = None,
    overwrite: bool = False
) -> Path:
    """Generate a CVE dataset following CAIS vulnerability distribution.
    
    Args:
        cais_path: Path to CAIS anonymized CSV/JSON file or directory
        cve_directory: Path to cvelistV5/cves directory
        output_dir: Output directory for generated dataset
        output_format: Format for output (json, jsonl, csv)
        random_seed: Random seed for reproducibility
        overwrite: Whether to overwrite existing output files
        
    Returns:
        Path to the generated dataset file
    """
    # Validate inputs
    if not cve_directory.exists() or not (cve_directory / "2024").exists():
        raise ValueError(f"Invalid CVE directory structure: {cve_directory}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if random_seed is not None:
        random.seed(random_seed)
    
    # Step 1: Load CAIS distribution
    frequency_list = load_cais_distribution(cais_path)
    
    # Step 2: Load CVE index
    cve_index = load_cve_index(cve_directory)
    if not cve_index:
        raise ValueError(f"No CVE files found in {cve_directory}")
    
    if len(cve_index) < len(frequency_list):
        logging.warning(f"CVE repository has {len(cve_index)} CVEs, but CAIS has {len(frequency_list)} unique vulnerabilities.")
    
    # Step 3: Randomly select CVEs and assign frequencies
    logging.info(f"Randomly assigning {len(frequency_list)} CVEs to match CAIS distribution...")
    
    available_cve_ids = list(cve_index.keys())
    
    if len(available_cve_ids) >= len(frequency_list):
        selected_cve_ids = random.sample(available_cve_ids, len(frequency_list))
    else:
        selected_cve_ids = random.choices(available_cve_ids, k=len(frequency_list))
    
    cve_frequency_pairs = list(zip(selected_cve_ids, frequency_list))
    
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
                for _ in range(frequency):
                    cve_data_list.append({
                        'cve_id': cve_id,
                        'cais_frequency': frequency,
                        'cve_data': cve_json
                    })
        except (json.JSONDecodeError, IOError) as e:
            failed_loads += 1
            logging.warning(f"Could not load CVE file for {cve_id}: {e}")
    
    if failed_loads > 0:
        logging.warning(f"Failed to load {failed_loads} CVE files")
    
    if not cve_data_list:
        raise ValueError("No CVE data was loaded. Check CVE directory.")
    
    logging.info(f"Dataset creation complete:")
    logging.info(f"  - Total CVE records: {len(cve_data_list)}")
    logging.info(f"  - Unique CVEs: {len(set(r['cve_id'] for r in cve_data_list))}")
    
    # Step 5: Create dataframe and shuffle
    df_dataset = pd.DataFrame(cve_data_list)
    df_dataset = df_dataset.sample(frac=1, random_state=random_seed).reset_index(drop=True)
    
    # Step 6: Save output
    cais_base = cais_path.stem if cais_path.is_file() else cais_path.name
    output_filename = f"cve_dataset_{cais_base}_stratified.{output_format}"
    output_path = output_dir / output_filename
    
    if output_path.exists() and not overwrite:
        raise ValueError(f"Output file exists: {output_path}. Use --overwrite to replace.")
    
    logging.info(f"Saving dataset to {output_path}...")
    write_dataframe(df_dataset, output_path)
    
    logging.info(f"Successfully created CVE dataset: {output_path}")
    logging.info(f"  - Total records: {len(df_dataset)}")
    logging.info(f"  - Unique CVEs: {df_dataset['cve_id'].nunique()}")
    
    return output_path


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate a CVE dataset following CAIS vulnerability distribution.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate dataset from single CAIS file
  python scripts/generate_cve_dataset.py --cais-path data/cais_anonymized.csv --cve-dir /path/to/cves

  # Generate from directory with JSONL output
  python scripts/generate_cve_dataset.py --cais-path data/cais/ --cve-dir /path/to/cves --format jsonl
        """
    )
    
    parser.add_argument("--cais-path", type=str, required=True,
                        help="Path to CAIS anonymized CSV/JSON file or directory")
    parser.add_argument("--cve-dir", type=str, required=True,
                        help="Path to cvelistV5 cves directory")
    parser.add_argument("--output-dir", type=str, default="output",
                        help="Output directory (default: output)")
    parser.add_argument("--format", type=str, default="jsonl", choices=["json", "jsonl", "csv"],
                        help="Output format (default: jsonl)")
    parser.add_argument("--random-seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files")
    parser.add_argument("--log-level", type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Logging level")
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    setup_logging(args.log_level)
    
    logging.info("Starting CVE dataset generation...")
    
    try:
        output_path = generate_cve_dataset(
            cais_path=Path(args.cais_path),
            cve_directory=Path(args.cve_dir),
            output_dir=Path(args.output_dir),
            output_format=args.format,
            random_seed=args.random_seed,
            overwrite=args.overwrite
        )
        logging.info(f"CVE dataset generation complete: {output_path}")
        
    except ValueError as e:
        logging.error(str(e))
        sys.exit(1)
    except Exception as e:
        logging.error(f"Generation failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

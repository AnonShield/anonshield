#!/usr/bin/env python3
"""
Data Sampling Tool

Generates stratified samples from datasets, supporting CSV, JSON, and JSONL formats.
Samples are stratified by file and aggregated by format.

Usage:
    python scripts/sample.py /path/to/data --sample-fraction 0.1 --output-dir output/samples
    python scripts/sample.py /path/to/data --sample-size 1000 --random-seed 42
"""
import argparse
import logging
import sys
from pathlib import Path

from .utils import read_dataframe, write_dataframe, setup_logging


def sample_data(
    input_path: Path,
    output_dir: Path,
    sample_fraction: float | None = None,
    sample_size: int | None = None,
    random_seed: int | None = None,
    overwrite: bool = False
) -> list[Path]:
    """
    Sample data from files in a directory, stratified by file and aggregated by format.
    
    Args:
        input_path: Directory containing files to sample
        output_dir: Directory for output files
        sample_fraction: Fraction of items to sample (0.0-1.0)
        sample_size: Fixed number of items to sample
        random_seed: Random seed for reproducibility
        overwrite: Whether to overwrite existing output files
        
    Returns:
        List of output file paths created
    """
    if not input_path.is_dir():
        raise ValueError(f"Input path must be a directory: {input_path}")
    
    if not sample_fraction and not sample_size:
        raise ValueError("Either sample_fraction or sample_size must be provided")
    
    if sample_fraction and sample_size:
        raise ValueError("Provide either sample_fraction or sample_size, not both")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    output_files = []
    
    # Group files by extension
    file_groups = {}
    for ext in ['csv', 'json', 'jsonl']:
        files = list(input_path.rglob(f'*.{ext}'))
        if files:
            file_groups[ext] = files
    
    if not file_groups:
        logging.warning(f"No compatible files (.csv, .json, .jsonl) found in {input_path}")
        return output_files
    
    for ext, files in file_groups.items():
        logging.info(f"Processing {len(files)} file(s) for format '.{ext}'...")
        sampled_dfs = []
        
        try:
            if sample_fraction:
                for file_path in files:
                    logging.debug(f"Sampling {sample_fraction*100}% from {file_path.name}")
                    df = read_dataframe(file_path)
                    if df is not None and not df.empty:
                        sampled_dfs.append(df.sample(frac=sample_fraction, random_state=random_seed))
            
            elif sample_size:
                # Proportional sampling based on file size
                file_infos = []
                total_rows = 0
                for file_path in files:
                    df = read_dataframe(file_path)
                    if df is not None and not df.empty:
                        file_infos.append({'path': file_path, 'rows': len(df), 'df': df})
                        total_rows += len(df)
                
                if total_rows > 0:
                    target_sample = min(sample_size, total_rows)
                    samples_allocated = 0
                    
                    for i, info in enumerate(file_infos):
                        proportion = info['rows'] / total_rows
                        
                        # Last file gets remaining samples to avoid rounding errors
                        if i == len(file_infos) - 1:
                            n_to_sample = target_sample - samples_allocated
                        else:
                            n_to_sample = round(target_sample * proportion)
                        
                        n_to_sample = min(n_to_sample, info['rows'])
                        
                        if n_to_sample > 0:
                            logging.debug(f"Sampling {n_to_sample} rows from {info['path'].name}")
                            sampled_dfs.append(info['df'].sample(n=n_to_sample, random_state=random_seed))
                            samples_allocated += n_to_sample
            
            if not sampled_dfs:
                logging.warning(f"No data was sampled for format '.{ext}'")
                continue
            
            # Consolidate and shuffle
            import pandas as pd
            final_df = pd.concat(sampled_dfs, ignore_index=True)
            final_df = final_df.sample(frac=1, random_state=random_seed).reset_index(drop=True)
            
            # Save consolidated file
            output_filename = f"{input_path.name}_{ext}_sampled.{ext}"
            output_path = output_dir / output_filename
            
            if not overwrite and output_path.exists():
                logging.warning(f"Output file {output_path} exists. Use --overwrite to replace.")
                continue
            
            write_dataframe(final_df, output_path)
            output_files.append(output_path)
            logging.info(f"Saved consolidated sample for '.{ext}' to {output_path} ({len(final_df)} records)")
        
        except Exception as e:
            logging.error(f"Failed to process format '.{ext}': {e}", exc_info=True)
    
    return output_files


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate stratified samples from datasets.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sample 10% of all data
  python scripts/sample.py /path/to/data --sample-fraction 0.1

  # Sample exactly 1000 records with reproducible results
  python scripts/sample.py /path/to/data --sample-size 1000 --random-seed 42
        """
    )
    
    parser.add_argument("input_path", type=str, help="Directory containing files to sample")
    parser.add_argument("--output-dir", type=str, default="output/samples", help="Output directory (default: output/samples)")
    parser.add_argument("--sample-fraction", type=float, help="Fraction of items to sample (e.g., 0.1 for 10%%)")
    parser.add_argument("--sample-size", type=int, help="Fixed number of items to sample")
    parser.add_argument("--random-seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files")
    parser.add_argument("--log-level", type=str, default="INFO", 
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Logging level")
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    setup_logging(args.log_level)
    
    logging.info("Starting data sampling process...")
    
    try:
        output_files = sample_data(
            input_path=Path(args.input_path),
            output_dir=Path(args.output_dir),
            sample_fraction=args.sample_fraction,
            sample_size=args.sample_size,
            random_seed=args.random_seed,
            overwrite=args.overwrite
        )
        
        if output_files:
            logging.info(f"Sampling complete. Created {len(output_files)} file(s).")
        else:
            logging.warning("No files were created.")
            sys.exit(1)
            
    except ValueError as e:
        logging.error(str(e))
        sys.exit(1)
    except Exception as e:
        logging.error(f"Sampling failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

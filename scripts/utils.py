"""
Shared utility functions for CLI scripts.
"""
import logging
import pandas as pd
from pathlib import Path


def read_dataframe(file_path: Path) -> pd.DataFrame | None:
    """Reads a file into a pandas DataFrame based on its extension.
    
    Args:
        file_path: Path to the file (csv, json, or jsonl)
        
    Returns:
        DataFrame or None if reading fails
    """
    try:
        if file_path.suffix == '.csv':
            return pd.read_csv(file_path)
        elif file_path.suffix == '.jsonl':
            return pd.read_json(file_path, lines=True)
        elif file_path.suffix == '.json':
            return pd.read_json(file_path)
        else:
            logging.warning(f"Unsupported file format: {file_path.suffix}")
            return None
    except Exception as e:
        logging.error(f"Could not read or parse {file_path}: {e}")
        return None


def write_dataframe(df: pd.DataFrame, output_path: Path) -> None:
    """Writes a DataFrame to a file based on its extension.
    
    Args:
        df: DataFrame to write
        output_path: Path where to save (extension determines format)
    """
    ext = output_path.suffix
    if ext == '.csv':
        df.to_csv(output_path, index=False)
    elif ext == '.jsonl':
        df.to_json(output_path, orient='records', lines=True)
    elif ext == '.json':
        df.to_json(output_path, orient='records', indent=2)
    else:
        raise ValueError(f"Unsupported output format: {ext}")


def setup_logging(level: str = "INFO") -> None:
    """Configure logging with a standard format.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

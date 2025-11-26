"""
Configuration Loader Module

This module provides utilities for loading various configurations from external
files, supporting formats like YAML and JSON. This centralizes configuration
management and makes it easier to update settings without modifying code.
"""

import os
import json
import yaml
import logging
from typing import Set

class ConfigLoader:
    """
    Handles loading of configuration files, such as stop-lists.
    """

    def load_stoplist(self, file_path: str) -> Set[str]:
        """
        Loads a stoplist from a specified file.
        Supports JSON and YAML formats.
        The file should contain a list of strings.
        """
        if not os.path.exists(file_path):
            logging.warning(f"Stoplist file not found at '{file_path}'. Returning empty set.")
            return set()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.endswith('.json'):
                    data = json.load(f)
                elif file_path.endswith('.yaml') or file_path.endswith('.yml'):
                    data = yaml.safe_load(f)
                else:
                    logging.error(f"Unsupported stoplist file format for '{file_path}'. Must be .json or .yaml/.yml.")
                    return set()

            if isinstance(data, list):
                return {str(item).lower() for item in data}
            else:
                logging.error(f"Stoplist file '{file_path}' must contain a list of strings. Found: {type(data)}")
                return set()

        except (json.JSONDecodeError, yaml.YAMLError) as e:
            logging.error(f"Error parsing stoplist file '{file_path}': {e}")
            return set()
        except Exception as e:
            logging.error(f"An unexpected error occurred while loading stoplist from '{file_path}': {e}")
            return set()


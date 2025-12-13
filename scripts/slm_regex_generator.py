# scripts/slm_regex_generator.py
import argparse
import json
import pandas as pd
import logging
from pathlib import Path
import sys
import os
from tqdm import tqdm

# Add src to path to import from project files
# This allows the script to be run from the project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from src.anon.slm.client import OllamaClient
    from src.anon.config import LLM_CONFIG
    from src.anon.tqdm_handler import TqdmLoggingHandler
    ollama_client_available = True
except ImportError as e:
    print(f"Could not import project dependencies: {e}")
    print("Please ensure you are running this script from the project root and that the environment is set up.")
    ollama_client_available = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Prompt Template ---
REGEX_GENERATION_PROMPT_TEMPLATE = """
You are an expert in regular expressions. Your task is to analyze a list of examples for a specific entity type and do one of two things:

1.  **Generate a single, robust Python-compatible regex** that accurately matches all the provided examples. The regex should be as specific as possible to avoid capturing unintended text, but general enough to capture other similar examples.
2.  **Explain why it is not feasible** to create a single, reliable regex for the given examples. This is often the case for highly variable, non-structured data like personal names, company names, or general descriptions.

**Input:**
- Entity Type: {entity_type}
- Examples:
{examples}

**Output Format (JSON only):**
- If successful, return a JSON object with the "regex" key:
  {{"regex": "^your-regex-here$"}}
- If not feasible, return a JSON object with the "reason" key:
  {{"reason": "It is not feasible to create a regex for this entity type because..."}}

**CRITICAL INSTRUCTIONS:**
- **DO NOT** provide both a "regex" and a "reason". Pick one.
- The regex should be a valid JSON string, so escape backslashes (e.g., `\\d` instead of `\d`).
- Aim for non-capturing groups `(?:...)` unless necessary.
- If you generate a regex, do not provide any additional explanation in your response. Your response must be **ONLY** the JSON object.
- If the examples are clearly just random strings or names with no discernible pattern, state that it's not feasible.
"""

def get_slm_client():
    """Initializes and returns the OllamaClient."""
    if not ollama_client_available:
        return None
    try:
        ollama_config = LLM_CONFIG["ollama"]
        client = OllamaClient(
            model=ollama_config["model"],
            base_url=ollama_config["base_url"],
            timeout=120,  # Generous timeout for regex generation
        )
        logging.info(f"Successfully connected to Ollama at {ollama_config['base_url']}.")
        return client
    except Exception as e:
        logging.error(f"Failed to connect to Ollama SLM: {e}")
        return None

def generate_regex_from_slm(client: OllamaClient, entity_type: str, examples: list[str]) -> dict:
    """
    Sends examples to the SLM and asks for a regex or a reason for infeasibility.
    """
    examples_str = "\n".join(f"- {ex}" for ex in examples)
    prompt = REGEX_GENERATION_PROMPT_TEMPLATE.format(entity_type=entity_type, examples=examples_str)
    
    try:
        response_json = client.query_json(prompt=prompt)
        return response_json
    except Exception as e:
        logging.error(f"Failed to get response from SLM for entity '{entity_type}': {e}")
        return {"reason": f"SLM query failed: {e}"}


def process_entities(json_file: Path, output_file: Path, max_samples: int):
    """
    Reads an entity map file, groups entities, and uses an SLM to generate regexes.
    """
    logging.info(f"Reading entity map file: {json_file}")
    
    # Load data
    try:
        if json_file.suffix.lower() == '.jsonl':
            df = pd.read_json(json_file, lines=True)
        elif json_file.suffix.lower() == '.json':
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            df = pd.DataFrame(data.get('entities', []))
        else:
            logging.error(f"Unsupported file format: {json_file.suffix}")
            return
    except Exception as e:
        logging.error(f"Failed to read file {json_file}: {e}")
        return

    if df.empty:
        logging.warning("No entities found in the file.")
        return

    client = get_slm_client()
    if not client:
        logging.error("Ollama client not available. Aborting.")
        sys.exit(1)

    results = {}
    
    entity_groups = df.groupby('entity_type')
    
    progress_bar = tqdm(entity_groups, desc="Generating Regexes", unit="type")
    for entity_type, group in progress_bar:
        progress_bar.set_description(f"Processing {entity_type}")
        
        # Get unique samples, limit the number sent to SLM
        unique_texts = group['text'].unique().tolist()
        samples = unique_texts[:max_samples]
        
        logging.info(f"Sending {len(samples)} unique samples for '{entity_type}' to SLM...")
        
        slm_result = generate_regex_from_slm(client, entity_type, samples)
        
        results[entity_type] = {
            "total_occurrences": len(group),
            "unique_count": len(unique_texts),
            "samples_sent_to_slm": samples,
            "slm_response": slm_result
        }

    # Save the final report
    logging.info(f"Saving regex generation report to {output_file}")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logging.info("Processing complete.")


def main():
    parser = argparse.ArgumentParser(description="Use an SLM to generate regular expressions from an entity map file.")
    parser.add_argument("file_path", type=Path, help="Path to the entity map JSON or JSONL file.")
    parser.add_argument("--output-file", type=Path, default="slm_regex_report.json", help="Path to save the output JSON report.")
    parser.add_argument("--max-samples", type=int, default=50, help="Maximum number of unique entity samples to send to the SLM for each type.")
    
    args = parser.parse_args()

    # Configure logging to be tqdm-friendly
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    tqdm_handler = TqdmLoggingHandler()
    tqdm_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(tqdm_handler)

    if not args.file_path.exists():
        logging.error(f"Input file not found: {args.file_path}")
        sys.exit(1)

    process_entities(args.file_path, args.output_file, args.max_samples)

if __name__ == "__main__":
    if not ollama_client_available:
        sys.exit(1)
    main()

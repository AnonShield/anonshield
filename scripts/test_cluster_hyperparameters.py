# scripts/test_cluster_hyperparameters.py
import argparse
import subprocess
import sys
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_experiment(
    original_script: Path,
    file_path: Path,
    min_size: int,
    model_name: str,
    base_output_dir: Path,
    entity_types: list[str] | None,
    min_text_length: int,
    epsilon: float
):
    """
    Runs a single clustering experiment with a specific configuration.
    """
    # Sanitize model name for directory creation
    model_dir_name = model_name.replace('/', '_')
    
    # Create a unique, descriptive output directory for this specific run
    experiment_output_dir = base_output_dir / model_dir_name / f"min_size_{min_size}_eps_{epsilon}"
    experiment_output_dir.mkdir(parents=True, exist_ok=True)
    
    logging.info(f"--- Running Experiment: Model='{model_name}', Min Cluster Size={min_size}, Epsilon={epsilon} ---")
    logging.info(f"Output will be saved to: {experiment_output_dir}")

    # Construct the command to call the original clustering script
    command = [
        sys.executable,  # Use the same python interpreter that's running this script
        str(original_script),
        str(file_path),
        "--output-dir", str(experiment_output_dir),
        "--min-cluster-size", str(min_size),
        "--embedding-model", model_name,
        "--min-text-length", str(min_text_length),
        "--cluster-selection-epsilon", str(epsilon)
    ]
    
    # Add optional entity types if provided
    if entity_types:
        command.extend(["--entity-types", *entity_types])
        
    try:
        # We use subprocess.run and capture output to show progress and errors
        result = subprocess.run(
            command,
            check=True,        # Raises an exception for non-zero exit codes
            capture_output=True, # Captures stdout and stderr
            text=True,           # Decodes stdout/stderr as text
            encoding='utf-8'
        )
        logging.info(f"Successfully completed experiment for min_size={min_size}, model='{model_name}', epsilon={epsilon}.")
        # Log stdout from the subscript for more details (e.g., model loading, progress bars)
        if result.stdout:
            logging.debug(f"Sub-script output:\n{result.stdout}")

    except subprocess.CalledProcessError as e:
        logging.error(f"Experiment failed for min_size={min_size}, model='{model_name}', epsilon={epsilon}.")
        logging.error(f"Return Code: {e.returncode}")
        logging.error(f"Stdout:\n{e.stdout}")
        logging.error(f"Stderr:\n{e.stderr}")
    except FileNotFoundError:
        logging.error(f"Error: The script '{original_script}' was not found.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Run hyperparameter tests for the entity clustering script.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("file_path", type=Path, help="Path to the entity map JSON or JSONL file.")
    parser.add_argument(
        "--min-cluster-sizes",
        nargs='+',
        type=int,
        default=[2, 5, 10],
        help="A space-separated list of minimum cluster sizes to test."
    )
    parser.add_argument(
        "--embedding-models",
        nargs='+',
        type=str,
        default=["multi-qa-MiniLM-L6-cos-v1", "all-MiniLM-L6-v2"],
        help="A space-separated list of sentence-transformer models to test."
    )
    parser.add_argument(
        "--epsilons",
        nargs='+',
        type=float,
        default=[0.0],
        help="A space-separated list of cluster selection epsilon values to test. Smaller values lead to more clusters."
    )
    parser.add_argument(
        "--base-output-dir",
        type=Path,
        default=Path("output/cluster_experiments"),
        help="The base directory where all experiment results will be saved."
    )
    parser.add_argument("--entity-types", nargs='+', help="Optional: A space-separated list of specific entity types to filter by (passed to the clustering script).")
    parser.add_argument("--min-text-length", type=int, default=3, help="Minimum character length of entity text (passed to the clustering script).")

    args = parser.parse_args()

    original_script_path = Path(__file__).parent / "cluster_entities.py"
    if not original_script_path.exists():
        logging.error(f"The target script '{original_script_path}' does not exist. Make sure this script is in the same directory.")
        sys.exit(1)

    if not args.file_path.exists():
        logging.error(f"Input file not found: {args.file_path}")
        sys.exit(1)
        
    logging.info("Starting hyperparameter tuning for clustering...")
    logging.info(f"File to analyze: {args.file_path}")
    logging.info(f"Testing Min Cluster Sizes: {args.min_cluster_sizes}")
    logging.info(f"Testing Embedding Models: {args.embedding_models}")
    logging.info(f"Testing Epsilon Values: {args.epsilons}")

    for model in args.embedding_models:
        for size in args.min_cluster_sizes:
            for eps in args.epsilons:
                run_experiment(
                    original_script=original_script_path,
                    file_path=args.file_path,
                    min_size=size,
                    model_name=model,
                    base_output_dir=args.base_output_dir,
                    entity_types=args.entity_types,
                    min_text_length=args.min_text_length,
                    epsilon=eps
                )
            
    logging.info("All hyperparameter experiments are complete.")
    logging.info(f"Results are saved in: {args.base_output_dir}")

if __name__ == "__main__":
    main()

# scripts/cluster_entities.py
import argparse
import json
import pandas as pd
import logging
from pathlib import Path
import sys
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Dependency Checks ---
try:
    from sentence_transformers import SentenceTransformer
    sentence_transformers_available = True
except ImportError:
    logging.error("\`sentence-transformers\` library not found. Please install it with: uv pip install sentence-transformers")
    sentence_transformers_available = False

try:
    import hdbscan
    hdbscan_available = True
except ImportError:
    logging.error("`hdbscan` library not found. Please install it with: uv pip install hdbscan")
    hdbscan_available = False

def cluster_and_report(json_file: Path, output_dir: Path, min_cluster_size: int, entity_types: list[str] | None, min_text_length: int, model_name: str, cluster_selection_epsilon: float):
    """
    Loads entity data, clusters all entity texts globally to find semantic similarities
    across types, and generates a detailed markdown report.
    """
    if not sentence_transformers_available or not hdbscan_available:
        logging.error("Missing required libraries. Aborting.")
        return

    logging.info(f"Analyzing and clustering entities from: {json_file}")
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = json_file.stem.replace("_entity_map", "")
    report_path = output_dir / f"{base_name}_global_cluster_report.md"

    # --- Load Data ---
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

    # --- Initialize Model ---
    logging.info(f"Loading sentence transformer model: '{model_name}'...")
    try:
        model = SentenceTransformer(model_name, device='cuda' if 'torch' in sys.modules and sys.modules['torch'].cuda.is_available() else 'cpu')
        logging.info(f"Model loaded on device: {model.device}")
    except Exception as e:
        logging.error(f"Failed to load sentence transformer model '{model_name}'. Please ensure it's a valid model from HuggingFace. Error: {e}")
        return

    # --- Main Report Content ---
    report_content = f"# Global Entity Clustering Report for `{json_file.name}`\n\n"
    report_content += "This report groups all entity texts together, regardless of their original type, to find semantic similarities and potential mapping inconsistencies.\n\n"
    report_content += f"* **Clustering Algorithm:** HDBSCAN\n"
    report_content += f"* **Embedding Model:** `{model_name}`\n"
    report_content += f"* **Minimum Cluster Size:** `{min_cluster_size}`\n"
    report_content += f"* **Cluster Selection Epsilon:** `{cluster_selection_epsilon}`\n"
    report_content += f"* **Minimum Text Length:** `{min_text_length}`\n\n"
    
    # --- Filter for specific entity types if requested ---
    if entity_types:
        df = df[df['entity_type'].isin(entity_types)]
        report_content += f"* **Filtered to Entity Types:** `{', '.join(entity_types)}`\n\n"
        if df.empty:
            logging.warning(f"No entities found for specified types: {', '.join(entity_types)}")
            report_content += f"**Warning:** No entities found for the specified types.\n"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            return
            
    report_content += "---\n\n"

    # --- Prepare Data for Global Clustering ---
    # Filter by text length and get unique texts
    df_filtered = df[df['text'].str.len() >= min_text_length]
    unique_texts = df_filtered['text'].unique()

    if len(unique_texts) < min_cluster_size:
        report_content += f"Skipping clustering as there are fewer unique texts ({len(unique_texts)}) than the minimum cluster size ({min_cluster_size}).\n"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        return

    logging.info(f"Processing {len(unique_texts)} unique texts for global clustering...")

    # --- Generate Embeddings ---
    embeddings = model.encode(unique_texts, show_progress_bar=True, convert_to_numpy=True)

    # --- Perform Clustering ---
    logging.info("Running HDBSCAN clustering...")
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        cluster_selection_epsilon=cluster_selection_epsilon,
        gen_min_span_tree=True
    )
    clusterer.fit(embeddings)
    
    # --- Map clusters back to all original entities ---
    text_to_cluster_id = {text: label for text, label in zip(unique_texts, clusterer.labels_)}
    # Assign cluster ID to each row in the original filtered dataframe
    df_filtered['cluster_id'] = df_filtered['text'].map(text_to_cluster_id)
    
    # --- Format Results ---
    num_clusters = df_filtered['cluster_id'].nunique() - (1 if -1 in clusterer.labels_ else 0)
    num_outliers = (df_filtered['cluster_id'] == -1).sum()
    
    report_content += f"Found **{num_clusters} clusters** and **{num_outliers} outliers** across all entity types.\n\n"
    
    for cluster_id, cluster_group in df_filtered.groupby('cluster_id'):
        original_types = cluster_group['entity_type'].unique()
        
        if cluster_id == -1:
            report_content += "### Outliers (Not Clustered)\n"
        else:
            report_content += f"### Cluster {cluster_id + 1}\n"
        
        report_content += f"**Original Entity Types Found:** `{', '.join(original_types)}`\n\n"
        report_content += "**Members:**\n"
        report_content += "```\n"
        report_content += "\n".join(cluster_group['text'].unique())
        report_content += "\n```\n\n"
        report_content += "---\n\n"

    # --- Save Report ---
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    logging.info(f"Global clustering report saved to: {report_path}")

def main():
    parser = argparse.ArgumentParser(description="Cluster entity texts from an entity map file to find similar items.")
    parser.add_argument("file_path", type=Path, help="Path to the entity map JSON or JSONL file.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Directory to save the clustering report. If not provided, a default directory will be created inside 'output/'.")
    parser.add_argument("--min-cluster-size", type=int, default=2, help="The minimum number of samples in a group for it to be considered a cluster (for HDBSCAN).")
    parser.add_argument("--cluster-selection-epsilon", type=float, default=0.0, help="A distance threshold. Clusters below this distance will be merged. A smaller value leads to more, smaller clusters.")
    parser.add_argument("--entity-types", nargs='+', help="Optional: A space-separated list of specific entity types to filter by before clustering (e.g., HOSTNAME URL).")
    parser.add_argument("--min-text-length", type=int, default=3, help="Minimum character length of entity text to be included in clustering.")
    parser.add_argument("--embedding-model", type=str, default="multi-qa-MiniLM-L6-cos-v1", help="The sentence-transformer model to use for embeddings.")

    args = parser.parse_args()

    if not args.file_path.exists():
        logging.error(f"Input file not found: {args.file_path}")
        sys.exit(1)

    if not sentence_transformers_available or not hdbscan_available:
        sys.exit(1)
        
    output_dir = args.output_dir
    if output_dir is None:
        script_name = Path(__file__).stem
        base_name = args.file_path.stem.replace("_entity_map", "")
        output_dir = Path("output") / script_name / f"entity_cluster_report_{base_name}"
        logging.info(f"--output-dir not specified. Using generated directory: {output_dir}")

    cluster_and_report(
        args.file_path,
        output_dir,
        args.min_cluster_size,
        args.entity_types,
        args.min_text_length,
        args.embedding_model,
        args.cluster_selection_epsilon
    )

if __name__ == "__main__":
    main()

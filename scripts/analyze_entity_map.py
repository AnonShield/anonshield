# scripts/analyze_entity_map.py
import argparse
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sys
import logging
from pathlib import Path

# Try to import optional dependencies and provide helpful messages if they are missing.
try:
    from grex import RegExpBuilder
    grex_available = True
except ImportError:
    grex_available = False

try:
    from wordcloud import WordCloud
    wordcloud_available = True
except ImportError:
    wordcloud_available = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_grex_regex(texts: list[str]) -> str | None:
    """Generates a regex from a list of texts using the grex library."""
    if not grex_available:
        return None
    
    if not texts:
        return None
    
    try:
        return RegExpBuilder.from_test_cases(texts).build()
    except Exception as e:
        logging.error(f"grex library failed to generate regex: {e}")
        return None

def analyze_entity_map(json_file: Path, output_dir: Path, min_regex_samples: int = 5, top_n_examples: int = 10):
    """
    Analyzes an entity map JSON or JSONL file, generates charts and word clouds,
    and attempts to create regexes.
    """
    logging.info(f"Analyzing entity map file: {json_file}")

    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = json_file.stem.replace("_entity_map", "")

    # Load data based on file extension
    try:
        if json_file.suffix.lower() == '.jsonl':
            df = pd.read_json(json_file, lines=True)
        elif json_file.suffix.lower() == '.json':
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            df = pd.DataFrame(data.get('entities', []))
        else:
            logging.error(f"Unsupported file format: {json_file.suffix}. Please provide a .json or .jsonl file.")
            return

        if df.empty:
            logging.warning("No entities found in the file. Skipping analysis.")
            return
    except Exception as e:
        logging.error(f"Failed to read or parse file {json_file}: {e}", exc_info=True)
        return

    # --- Basic Statistics ---
    report_content = f"# Entity Map Analysis for: `{json_file.name}`\n\n"
    report_content += f"**Total Entities Detected:** {len(df)}\n\n"
    report_content += f"**Unique Entity Types:** {df['entity_type'].nunique()}\n\n"

    # --- Entity Type Distribution ---
    logging.info("Generating entity type distribution...")
    entity_type_counts = df['entity_type'].value_counts()
    report_content += "## Entity Type Distribution\n\n"
    report_content += entity_type_counts.to_frame(name="Count").to_markdown() + "\n\n"

    # Bar chart for entity types
    plt.figure(figsize=(12, max(7, len(entity_type_counts) * 0.4)))
    sns.barplot(x=entity_type_counts.values, y=entity_type_counts.index, orient='h')
    plt.title('Distribution of Entity Types')
    plt.xlabel('Count')
    plt.ylabel('Entity Type')
    plt.tight_layout()
    chart_path = output_dir / f"{base_name}_entity_dist.png"
    plt.savefig(chart_path)
    plt.close()
    report_content += f"![Entity Type Distribution]({chart_path.name})\n\n"
    logging.info(f"Saved entity type distribution chart to {chart_path}")

    # --- Confidence Score Distribution ---
    if 'confidence' in df.columns and not df['confidence'].isnull().all():
        logging.info("Analyzing confidence scores...")
        report_content += "## Confidence Score Distribution (Overall)\n\n"
        report_content += df['confidence'].describe().to_frame().to_markdown() + "\n\n"

        plt.figure(figsize=(10, 6))
        sns.histplot(df['confidence'], bins=20, kde=True)
        plt.title('Distribution of Confidence Scores')
        plt.xlabel('Confidence Score')
        plt.ylabel('Frequency')
        plt.tight_layout()
        confidence_chart_path = output_dir / f"{base_name}_confidence_dist.png"
        plt.savefig(confidence_chart_path)
        plt.close()
        report_content += f"![Confidence Score Distribution]({confidence_chart_path.name})\n\n"
        logging.info(f"Saved confidence score distribution chart to {confidence_chart_path}")

    # --- Detailed Analysis per Entity Type (Word Clouds, Examples, Regex) ---
    report_content += "## Detailed Analysis by Entity Type\n\n"
    
    for entity_type, group in df.groupby('entity_type'):
        report_content += f"### {entity_type}\n\n"
        unique_texts = group['text'].unique().tolist()
        
        # Word Cloud
        if wordcloud_available and not group.empty:
            logging.info(f"Generating word cloud for '{entity_type}'...")
            try:
                # Get frequencies of all occurrences, not just unique ones
                text_frequencies = group['text'].value_counts().to_dict()
                
                wordcloud = WordCloud(width=800, height=400, background_color='white', collocations=False)
                wordcloud.generate_from_frequencies(text_frequencies)

                wc_path = output_dir / f"{base_name}_{entity_type}_wordcloud.png"
                wordcloud.to_file(wc_path)
                report_content += f"![Word Cloud for {entity_type}]({wc_path.name})\n\n"
                logging.info(f"Saved word cloud for '{entity_type}' to {wc_path}")
            except Exception as e:
                logging.warning(f"Could not generate word cloud for '{entity_type}': {e}")
                report_content += "*Word cloud generation failed for this entity type.*\n\n"
        elif not wordcloud_available:
            report_content += "*`wordcloud` library not installed. Skipping word cloud generation.*\n\n"

        # Examples
        report_content += f"**Top {top_n_examples} Unique Examples:**\n"
        report_content += "```\n"
        report_content += "\n".join(unique_texts[:top_n_examples])
        report_content += "\n```\n\n"

        # Regex Generation
        report_content += "**Suggested Regex (via grex):**\n"
        if not grex_available:
            report_content += "*`grex` library not installed. Skipping regex generation.*\n\n"
        elif len(unique_texts) >= min_regex_samples:
            logging.info(f"Generating regex for '{entity_type}' with {len(unique_texts)} samples...")
            regex = generate_grex_regex(unique_texts)
            if regex:
                report_content += f"```regex\n{regex}\n```\n\n"
            else:
                report_content += "*Failed to generate regex.*\n\n"
        else:
            report_content += f"*Not enough unique samples ({len(unique_texts)} < {min_regex_samples}) to generate a reliable regex.*\n\n"
        
        report_content += "---\n\n"

    # Save full report
    report_path = output_dir / f"{base_name}_analysis_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    logging.info(f"Analysis report saved to {report_path}")

def main():
    parser = argparse.ArgumentParser(description="Analyze SLM entity map JSON or JSONL file and generate reports.")
    parser.add_argument("file_path", type=Path, help="Path to the entity map JSON or JSONL file.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Directory to save reports. If not provided, a default directory will be created inside 'output/'.")
    parser.add_argument("--min-regex-samples", type=int, default=5, help="Minimum number of unique entity samples required to attempt grex regex generation.")
    parser.add_argument("--top-n-examples", type=int, default=10, help="Number of unique examples to list for each entity type.")
    
    args = parser.parse_args()

    if not args.file_path.exists():
        logging.error(f"Input file not found: {args.file_path}")
        sys.exit(1)
        
    file_suffix = args.file_path.suffix.lower()
    if file_suffix not in ['.json', '.jsonl']:
        logging.error(f"Input file must be a JSON or JSONL file. Got: {file_suffix}")
        sys.exit(1)
    
    # Determine output directory
    output_dir = args.output_dir
    if output_dir is None:
        script_name = Path(__file__).stem
        base_name = args.file_path.stem.replace("_entity_map", "")
        output_dir = Path("output") / script_name / f"entity_analysis_report_{base_name}"
        logging.info(f"--output-dir not specified. Using generated directory: {output_dir}")

    if not grex_available:
        logging.warning("Python library 'grex' not found. Regex generation will be skipped. Install it with 'uv pip install grex'")
    if not wordcloud_available:
        logging.warning("Python library 'wordcloud' not found. Word cloud generation will be skipped. Install it with 'uv pip install wordcloud'")

    analyze_entity_map(args.file_path, output_dir, args.min_regex_samples, args.top_n_examples)

if __name__ == "__main__":
    main()
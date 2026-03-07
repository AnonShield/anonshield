# Utility Scripts Guide

This document provides a comprehensive overview of the utility scripts located in the `scripts/` directory. These scripts are designed to support analysis, evaluation, benchmarking, and database management tasks related to the main anonymization tool.

## Table of Contents
- [Analysis & Reporting Scripts](#analysis--reporting-scripts)
  - [`analyze_entity_map.py`](#analyze_entity_mappy)
  - [`cluster_entities.py`](#cluster_entitiespy)
  - [`slm_regex_generator.py`](#slm_regex_generatorpy)
- [Database & Core Function Scripts](#database--core-function-scripts)
  - [`deanonymize.py`](#deanonymizepy)
  - [`export_and_clear_db.py`](#export_and_clear_dbpy)
- [Benchmarking & Metrics Scripts](#benchmarking--metrics-scripts)
  - [`get_metrics.py`](#get_metricspy)
  - [`get_runs_metrics.py`](#get_runs_metricspy)
- [Data Counting Scripts](#data-counting-scripts)
  - [`get_ticket_count.py`](#get_ticket_countpy)
  - [`count_eng.py`](#count_engpy)

---

## Analysis & Reporting Scripts

These scripts are primarily used to analyze the output of the SLM-based features.

### `analyze_entity_map.py`

- **Purpose:** Performs a deep analysis of the output from the SLM entity mapping task (`--slm-map-entities`). It provides insights into the types and distribution of entities found by the SLM, generates visualizations, and attempts to create regex patterns for discovered entity types.
- **Dependencies (Optional):**
  - `grex`: For generating regex patterns from examples. Install with `uv pip install grex`.
  - `wordcloud`: For generating word cloud visualizations. Install with `uv pip install wordcloud`.
- **Arguments:**
  - `file_path`: (Required) Path to the entity map `.json` or `.jsonl` file to be analyzed.
  - `--output-dir`: Directory to save the report and charts. If not provided, a new directory named `entity_analysis_report_<file_stem>` is created.
  - `--min-regex-samples`: Minimum number of unique samples required to attempt regex generation with `grex`. Default: `5`.
  - `--top-n-examples`: The number of unique examples to list for each entity type in the report. Default: `10`.
- **Usage:**
  ```bash
  uv run scripts/analyze_entity_map.py output/my_entity_map.jsonl
  ```
- **Output:**
  - A detailed markdown report (`..._analysis_report.md`) containing statistics, distributions, and per-entity analysis.
  - Distribution charts (`..._entity_dist.png`, `..._confidence_dist.png`).
  - A word cloud image for each entity type (`..._WORDCLOUD.png`).

### `cluster_entities.py`

- **Purpose:** Groups entities based on their semantic meaning using sentence-transformer models and HDBSCAN clustering. This is useful for discovering related concepts across different entity types or identifying when the SLM may have miscategorized a similar group of entities.
- **Dependencies:**
  - `sentence-transformers`: For generating text embeddings. Install with `uv pip install sentence-transformers`.
  - `hdbscan`: For density-based clustering. Install with `uv pip install hdbscan`.
- **Arguments:**
  - `file_path`: (Required) Path to the entity map `.json` or `.jsonl` file.
  - `--output-dir`: Directory to save the clustering report. If not provided, a new directory named `entity_cluster_report_<file_stem>` is created.
  - `--min-cluster-size`: The minimum number of samples in a group for it to be considered a cluster. Default: `2`.
  - `--entity-types`: A space-separated list of specific entity types to filter by before clustering (e.g., `HOSTNAME URL`).
  - `--min-text-length`: Minimum character length of an entity's text to be included. Default: `3`.
  - `--embedding-model`: The name of the sentence-transformer model to use for embeddings. Default: `multi-qa-MiniLM-L6-cos-v1`.
- **Usage:**
  ```bash
  uv run scripts/cluster_entities.py output/my_entity_map.jsonl --entity-types HOSTNAME IP_ADDRESS
  ```
- **Output:**
  - A markdown report (`..._global_cluster_report.md`) showing the members of each semantic cluster.

### `slm_regex_generator.py`

- **Purpose:** Automates the creation of regular expressions. It takes an entity map file, groups entities by type, and queries a configured SLM to generate a regex for each type based on the examples found.
- **Arguments:**
  - `file_path`: (Required) Path to the entity map `.json` or `.jsonl` file.
  - `--output-file`: Path to save the output JSON report. Default: `slm_regex_report.json`.
  - `--max-samples`: The maximum number of unique examples to send to the SLM for each entity type. Default: `50`.
- **Usage:**
  ```bash
  uv run scripts/slm_regex_generator.py output/my_entity_map.jsonl --output-file my_regexes.json
  ```
- **Output:**
  - A JSON file containing the SLM's response for each entity type. The response includes either a suggested regex or a reason why regex generation is not feasible.

---

## Database & Core Function Scripts

These scripts interact directly with the anonymization engine's database or core logic.

### `deanonymize.py`

- **Purpose:** Reverses the anonymization for a single entity slug. It queries the `entities.db` database to find the original text corresponding to a given slug. This script requires the `ANON_SECRET_KEY` environment variable to be set, as it is used to derive the hash for the database lookup.
- **Arguments:**
  - `slug`: (Required) The anonymized slug to look up (e.g., `[PERSON_a1b2c3d4]`).
  - `--db-dir`: The directory where the `entities.db` file is located. Default: `db`.
- **Usage:**
  ```bash
  # Ensure ANON_SECRET_KEY is set first
  export ANON_SECRET_KEY='your-secret'
  uv run scripts/deanonymize.py "[PERSON_a1b2c3d4]"
  ```
- **Output:** Prints the original text, entity type, and first/last seen timestamps to the console.

### `export_and_clear_db.py`

- **Purpose:** A database management script that exports all records from the `entities.db` file into a single CSV file. It includes an option to wipe the database after a successful export.
- **Arguments:**
  - `--clear`: A flag that, if present, will delete all records from the `entities` table after the export is complete.
- **Usage:**
  ```bash
  # To export only
  uv run scripts/export_and_clear_db.py

  # To export and then clear the database
  uv run scripts/export_and_clear_db.py --clear
  ```
- **Output:**
  - Creates an `entities_export.csv` file in the `output/` directory.

---

## Benchmarking & Metrics Scripts

These scripts are used to measure and track the performance of the anonymization tool.

### `get_metrics.py`

- **Purpose:** Provides a quick, aggregated summary of performance across all anonymization runs. It works by parsing the `report_*.txt` files generated in the `logs/` directory.
- **Arguments:** None.
- **Usage:**
  ```bash
  uv run scripts/get_metrics.py
  ```
- **Output:** Prints aggregated statistics to the console, including total files and rows processed, average time per file, and the correlation between the number of rows and processing time.

### `get_runs_metrics.py`

- **Purpose:** A benchmarking tool designed to measure performance and consistency over multiple executions. It runs the main anonymization script `N` times against a specified directory of test files and records the performance metrics for each complete run into a CSV file.
- **Arguments:**
  - `tests_path`: (Required) A positional argument pointing to the directory of files to be processed on each run.
- **Usage:**
  ```bash
  uv run scripts/get_runs_metrics.py /path/to/my/test/data
  ```
- **Output:** Appends a new row for each completed run to `metrics_runs.csv`, recording the total time, total tickets, and average time per file/ticket for that run.

---

## Data Counting Scripts

These are simple helper scripts for data profiling.

### `get_ticket_count.py`

- **Purpose:** A simple utility to count the number of "tickets" in a directory. For tabular files (`.csv`, `.xlsx`), it counts the number of rows. For all other supported file types (e.g., `.pdf`, `.docx`, `.json`, images), it counts each file as a single ticket.
- **Arguments:**
  - `directory_path`: (Required) A positional argument pointing to the directory to be scanned.
- **Usage:**
  ```bash
  uv run scripts/get_ticket_count.py /path/to/data/
  ```
- **Output:** Prints a file-by-file count and a grand total to the console.

### `count_eng.py`

- **Purpose:** A linguistic utility script that scans all CSV files in a given directory and counts how many cells contain common English words. This can be useful for quickly assessing the language composition of a dataset. The script's own comments and output are in Portuguese.
- **Arguments:**
  - `caminho_da_pasta`: (Required) A positional argument pointing to the directory of CSV files.
- **Usage:**
  ```bash
  uv run scripts/count_eng.py /path/to/my/csv_files/
  ```
- **Output:** Prints a pandas DataFrame to the console showing the count of English snippets for each file, followed by a total sum.

---

## CVE Dataset Generation

The main `anon.py` script now includes a mode for generating CVE datasets that follow the vulnerability distribution from CAIS (Centro de Atendimento a Incidentes de Segurança) data.

### Purpose

This feature addresses the need to create training datasets that reflect real-world vulnerability distributions. Instead of uniform sampling, it uses **random CVEs** from the cvelistV5 repository but replicates them according to the **frequency distribution** found in production CAIS security incident data. This ensures that machine learning models trained on the dataset encounter vulnerabilities with realistic proportions without being tied to specific CAIS vulnerabilities.

**Key Concept**: The script preserves the *shape* of the distribution (how many vulnerabilities appear 1x, 2x, 3x, etc.) but uses randomly selected CVEs instead of the actual vulnerabilities from CAIS data.

### How It Works

1. **Reads CAIS Data**: Analyzes anonymized CAIS incident reports to extract vulnerability frequency distribution (e.g., one vulnerability appears 144 times, another 97 times, etc.)
2. **Indexes CVE Repository**: Builds an index of all CVE files from the cvelistV5 repository (~329k CVEs)
3. **Random CVE Selection**: Randomly selects CVEs from the repository (one CVE per unique vulnerability frequency in CAIS)
4. **Frequency Assignment**: Assigns each CAIS frequency to a randomly selected CVE
5. **Replicates CVEs**: Creates dataset entries by replicating each random CVE according to its assigned frequency
6. **Outputs Dataset**: Generates a stratified dataset in JSON, JSONL, or CSV format

**Example**: If CAIS has a vulnerability appearing 144 times, the dataset will have a random CVE (e.g., CVE-2018-20885) replicated 144 times.

### Architecture & Design Principles

This implementation follows SOLID principles and emphasizes:
- **Single Responsibility**: Each function has a clear, focused purpose (CVE ID extraction, file indexing, distribution mapping)
- **Separation of Concerns**: Data reading, indexing, mapping, and writing are isolated operations
- **Modularity**: Functions can be reused or extended independently
- **Error Handling**: Comprehensive exception handling with detailed logging at each step
- **Performance**: Efficient file indexing with progress tracking for large CVE repositories

### Usage

#### Single File Processing
```bash
python anon.py --generate-cve-dataset \
  --cais-file-path /path/to/cais_data.csv \
  --cve-directory /path/to/cvelistV5-main/cves \
  --output-dir output \
  --output-format jsonl \
  --random-seed 42 \
  --overwrite
```

#### Directory Processing (Multiple Files)
```bash
# Process all CSV, JSON, and JSONL files in a directory
python anon.py --generate-cve-dataset \
  --cais-file-path /path/to/cais_data_directory/ \
  --cve-directory /path/to/cvelistV5-main/cves \
  --output-dir output \
  --output-format csv \
  --random-seed 42 \
  --overwrite
```

### Arguments

- `--generate-cve-dataset`: Enable CVE dataset generation mode
- `--cais-file-path`: Path to CAIS data file **OR directory** containing multiple CAIS files (required)
  - If file: Processes single CSV, JSON, or JSONL file
  - If directory: Combines all CSV, JSON, and JSONL files found (recursively)
- `--cve-directory`: Path to cvelistV5 'cves' directory containing CVE JSON files organized by year (default: `/home/kapelinski/Downloads/cvelistV5-main/cves`)
- `--output-format`: Output format for generated CVE dataset - choices: `json`, `jsonl`, `csv` (default: `jsonl`)
- `--random-seed`: Random seed for reproducible shuffling (optional)
- `--overwrite`: Allow overwriting existing output files
- `--output-dir`: Directory to save output files (default: `output`)
- `--log-level`: Logging level for detailed execution information

### Input Data Requirements

**CAIS File Format:**
- **Supported formats**: CSV, JSON, JSONL
- **Single file or directory**: Can process individual files or combine all files in a directory
- **Required columns**:
  - `definition.id`: Vulnerability ID (primary, recommended for JSON files with nested structure)
  - OR `definition.cve`: CVE identifier (e.g., CVE-2024-12345)
  - OR `cve`: Direct CVE column

**Important**: The script automatically handles different data structures:
- **CSV files**: Columns are flat (e.g., `definition.id`)
- **JSON files**: The `definition` field may be a nested dictionary - the script automatically extracts `definition.id` from nested structures

**CVE Repository Structure:**
- Must follow cvelistV5 format: `YYYY/xxxx/CVE-YYYY-xxxxx.json`
- Each JSON file should contain cveMetadata with cveId

### Data Structure Normalization

The tool automatically normalizes different CAIS file formats:

**CSV Files** (flat structure):
```csv
id,definition.id,definition.cve,severity
1,59077,CVE-2012-2333,3
```

**JSON Files** (nested structure):
```json
[
  {
    "id": "uuid",
    "definition": {
      "id": 59077,
      "name": "OpenSSL Vulnerability",
      "cve": ["CVE-2012-2333"]
    }
  }
]
```

The script detects nested `definition` dictionaries in JSON files and automatically extracts `definition.id`, making all formats compatible for combined processing.

### Output Format

The generated dataset contains records with:
- `cve_id`: CVE identifier
- `cais_frequency`: Original frequency count from CAIS data
- `cve_data`: Complete CVE JSON structure from cvelistV5

Example JSONL output:
```json
{"cve_id": "CVE-2020-12243", "cais_frequency": 9, "cve_data": {...}}
{"cve_id": "CVE-2016-2183", "cais_frequency": 144, "cve_data": {...}}
```

### Example Workflow

#### Example 1: Single File Processing
```bash
# Step 1: Verify CAIS data structure
head -n 1 /path/to/cais_anonymized.csv

# Step 2: Generate dataset from single file
python anon.py --generate-cve-dataset \
  --cais-file-path /path/to/cais_anonymized.csv \
  --cve-directory /path/to/cvelistV5-main/cves \
  --output-dir datasets \
  --output-format jsonl \
  --random-seed 42

# Step 3: Verify output
wc -l datasets/cve_dataset_*_stratified.jsonl
```

#### Example 2: Directory Processing (Multiple Files Combined)
```bash
# Process all CAIS files in a directory (CSV + JSON + JSONL)
python anon.py --generate-cve-dataset \
  --cais-file-path /path/to/cais_data_directory/ \
  --cve-directory /path/to/cvelistV5-main/cves \
  --output-dir datasets \
  --output-format csv \
  --random-seed 42 \
  --overwrite

# The script will:
# - Find all .csv, .json, .jsonl files in the directory
# - Normalize nested structures automatically
# - Combine all files into one distribution
# - Generate unified dataset
```

#### Example 3: Analyzing Distribution
```bash
# For CSV output
python -c "
import pandas as pd
df = pd.read_csv('datasets/cve_dataset_cais_stratified.csv')
print(f'Total records: {len(df):,}')
print(f'Unique CVEs: {df[\"cve_id\"].nunique():,}')
print('\nTop 10 most frequent CVEs:')
print(df['cve_id'].value_counts().head(10))
"

# For JSONL output
python -c "
import pandas as pd
df = pd.read_json('datasets/cve_dataset_cais_stratified.jsonl', lines=True)
print(f'Total records: {len(df):,}')
print(f'Unique CVEs: {df[\"cve_id\"].nunique():,}')
print(df[\"cve_id\"].value_counts().head(10))
"
```

#### Example 4: Real-World Case - 70k+ Records from Multiple Sources
```bash
# Directory structure:
# cais_data/
#   ├── anon_CAIS-naoanonimizado_julho.csv       (15,187 records)
#   ├── anon_CAIS-naoanonimizado_junho.json      (12,705 records)
#   ├── anon_CAIS-naoanonimizado_julho.json      (15,177 records)
#   └── ... (other files)

# Single command processes all files
python anon.py --generate-cve-dataset \
  --cais-file-path cais_data/ \
  --cve-directory /home/user/Downloads/cvelistV5-main/cves \
  --output-dir output \
  --output-format csv \
  --random-seed 42 \
  --overwrite

# Result: 70,951 records with 2,771 unique CVEs
# Distribution perfectly preserved from combined sources
```

### Performance Considerations

- **Indexing Time**: Initial CVE indexing takes ~40-60 seconds for 300k+ CVE files
- **Memory Usage**: Moderate - index stores only CVE IDs and file paths
- **Output Size**: Depends on replication factor
  - Single file: ~15k records typically → ~50-100MB (CSV) / ~30-60MB (JSONL)
  - Combined directory: ~70k records → ~200-250MB (CSV) / ~150-200MB (JSONL)
- **Scalability**: Handles large CVE repositories efficiently with streaming I/O
- **Directory Processing**: Minimal overhead when combining multiple files (all loaded into memory at once)

### Edge Cases Handled

- **Missing CVE Mappings**: Logs unmatched vulnerabilities (up to 10 examples)
- **Malformed JSON**: Gracefully skips corrupted CVE files with error logging
- **Duplicate CVEs**: Maintains proper replication count even with duplicates
- **Empty Results**: Validates that at least some CVEs were matched before proceeding
- **Nested JSON Structures**: Automatically detects and normalizes `definition` dictionaries
- **Mixed File Formats**: Seamlessly combines CSV (flat) and JSON (nested) data structures
- **Missing Columns**: Falls back through column priority: `definition.id` → `definition.cve` → `cve`
- **Empty Files**: Skips empty dataframes with warnings, continues processing other files

### Quality Assurance

The implementation includes:
- **Distribution Validation**: Verifies that output frequency matches input distribution exactly
- **Data Integrity**: Ensures complete CVE data is preserved in output
- **Comprehensive Logging**: Tracks matched/unmatched vulnerabilities, processing stages, file counts
- **Reproducibility**: Random seed support for deterministic shuffling
- **Format Compatibility**: Automatically normalizes different data structures (CSV flat vs JSON nested)
- **Multi-File Consistency**: Validates combined distributions when processing directories

### Real-World Results

**Test Case**: Processing 5 CAIS files (1 CSV + 4 JSON) totaling 70,951 records

```
Input:
- anon_CAIS-naoanonimizado_julho.csv:    15,187 records (flat structure)
- anon_CAIS-naoanonimizado_junho.json:   12,705 records (nested structure)
- anon_CAIS-naoanonimizado_julho.json:   15,177 records (nested structure)
- ...additional JSON files

Output:
- Total records: 70,951 (100% coverage)
- Unique CVEs: 2,771
- Frequency range: 1 to 1,643 occurrences
- Average frequency: 25.60 per CVE
- File size: 248MB (CSV format)

Distribution Match: ✅ Perfect
- Min frequency: 1 (matches CAIS)
- Max frequency: 1,643 (matches CAIS)
- Mean frequency: 25.60 (matches CAIS)
```

### Use Cases

1. **Machine Learning Training**: Create training datasets that reflect production vulnerability distributions
2. **Security Research**: Analyze vulnerability patterns based on real-world incident data
3. **Benchmarking**: Generate realistic test datasets for security tools
4. **Educational Purposes**: Provide students with representative security datasets
5. **Data Consolidation**: Combine multiple CAIS data sources (different months, formats) into unified dataset
6. **Distribution Analysis**: Study real-world vulnerability frequency patterns without exposing actual incident data


#!/usr/bin/env bash
# extract_datasets.sh — Extract the D3 dataset from the bundled zip files
#
# D3 is distributed as two zip files tracked in git:
#   paper_data/datasets/D3_mock_cais_csv.zip  (~36 MB)
#   paper_data/datasets/D3_mock_cais_json.zip (~44 MB)
#
# This script extracts both into paper_data/datasets/D3_mock_cais/ and
# removes the zips afterwards to save disk space.
#
# Usage (from repo root):
#   ./paper_data/scripts/extract_datasets.sh
#
# D1 (~88 MB) is already tracked in git — no extraction needed.
# D1C is generated locally by scripts/convert_d1_to_d1c.py.
# D2 (CAIS/CTCiber) is private and cannot be redistributed.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DATASETS="$REPO_ROOT/paper_data/datasets"
D3_DIR="$DATASETS/D3_mock_cais"
CSV_ZIP="$DATASETS/D3_mock_cais_csv.zip"
JSON_ZIP="$DATASETS/D3_mock_cais_json.zip"

mkdir -p "$D3_DIR"

for zip in "$CSV_ZIP" "$JSON_ZIP"; do
    [[ -f "$zip" ]] || { echo "ERROR: $zip not found — is the repo fully cloned?"; exit 1; }
done

echo "==> Extracting D3 CSV (~248 MB)..."
unzip -o "$CSV_ZIP" -d "$DATASETS"
echo "    Removing $CSV_ZIP..."
rm "$CSV_ZIP"

echo ""
echo "==> Extracting D3 JSON (~445 MB)..."
unzip -o "$JSON_ZIP" -d "$DATASETS"
echo "    Removing $JSON_ZIP..."
rm "$JSON_ZIP"

echo ""
echo "==> Done. D3 dataset extracted to: $D3_DIR"
echo "    CSV:  $(du -sh "$D3_DIR/cve_dataset_anonimizados_stratified.csv"  | cut -f1)"
echo "    JSON: $(du -sh "$D3_DIR/cve_dataset_anonimizados_stratified.json" | cut -f1)"

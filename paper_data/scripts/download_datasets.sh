#!/usr/bin/env bash
# download_datasets.sh — Download public datasets required for full reproduction
#
# Usage:
#   ./paper_data/scripts/download_datasets.sh           # download D3 (default)
#   ./paper_data/scripts/download_datasets.sh --d3-only # same
#
# What this downloads:
#   D3 — Synthetic Mock CVE dataset (~693 MB total)
#       paper_data/datasets/D3_mock_cais/cve_dataset_anonimizados_stratified.csv  (247 MB)
#       paper_data/datasets/D3_mock_cais/cve_dataset_anonimizados_stratified.json (445 MB)
#
# D1 (~88 MB) is already tracked in git — no download needed.
# D2 (CAIS/CTCiber) is private and cannot be redistributed — contact the authors.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
D3_DIR="$REPO_ROOT/paper_data/datasets/D3_mock_cais"

# ---------------------------------------------------------------------------
# TODO: Replace these URLs with the actual hosting location after uploading D3
#       to Zenodo (https://zenodo.org) or GitHub Releases.
#
# Suggested approach:
#   1. Upload the two D3 files to a Zenodo deposit or GitHub Release.
#   2. Replace the placeholder URLs below with the direct download links.
#   3. Update README.md and paper_data/EXPERIMENTS.md with the DOI or release URL.
# ---------------------------------------------------------------------------
D3_CSV_URL="https://TODO_REPLACE_WITH_ACTUAL_URL/cve_dataset_anonimizados_stratified.csv"
D3_JSON_URL="https://TODO_REPLACE_WITH_ACTUAL_URL/cve_dataset_anonimizados_stratified.json"

echo "==> Creating output directory: $D3_DIR"
mkdir -p "$D3_DIR"

echo ""
echo "==> Downloading D3 CSV (~247 MB)..."
curl -fL --progress-bar -o "$D3_DIR/cve_dataset_anonimizados_stratified.csv" "$D3_CSV_URL"

echo ""
echo "==> Downloading D3 JSON (~445 MB)..."
curl -fL --progress-bar -o "$D3_DIR/cve_dataset_anonimizados_stratified.json" "$D3_JSON_URL"

echo ""
echo "==> Done. D3 dataset is at: $D3_DIR"
echo "    CSV:  $(du -sh "$D3_DIR/cve_dataset_anonimizados_stratified.csv" | cut -f1)"
echo "    JSON: $(du -sh "$D3_DIR/cve_dataset_anonimizados_stratified.json" | cut -f1)"

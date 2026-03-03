#!/bin/bash
# Script to run scientific analysis on all benchmark results in session folder
# Usage: 
#   ./run_all_analyses.sh              # Run standard analysis (no extended)
#   ./run_all_analyses.sh --extended   # Run with extended analyses (15-17)

SESSION_DIR="benchmark/orchestrated_results/session_20260208_005447"
OVERHEAD_DATA="$SESSION_DIR/02_overhead_calibration_10runs/benchmark_results.csv"

# Check if --extended flag was passed
EXTENDED_FLAG=""
if [[ "$1" == "--extended" ]]; then
    EXTENDED_FLAG="--extended"
    echo "Running with EXTENDED analyses (15-17)"
else
    echo "Running with STANDARD analyses (1-14 only)"
    echo "Use: $0 --extended to include extended analyses"
fi
echo ""

# Activate virtual environment
source /home/kapelinski/Documents/tool/.venv/bin/activate

# List of subdirectories to analyze
SUBDIRS=(
    "00_cve_dataset_v3_10runs_csv"
    "01_cve_dataset_v3_10runs_json"
    "01_consolidated_json_10runs"
    "02_consolidated_csv_10runs"
    "02_overhead_calibration_10runs"
    "03_regression_3runs"
    "04_full_single_file_1run"
    "05_full_directory_mode_1run"
    "01_ctciber_csv_cache200k"
    "02_ctciber_json_cache200k"
    "03_cve_csv_default"
    "04_cve_json_default"
)

echo "========================================================================"
echo "Running Scientific Analysis on All Benchmark Results"
echo "========================================================================"
echo ""

for SUBDIR in "${SUBDIRS[@]}"; do
    INPUT_CSV="$SESSION_DIR/$SUBDIR/benchmark_results.csv"
    OUTPUT_DIR="$SESSION_DIR/$SUBDIR/analysis"
    
    if [ -f "$INPUT_CSV" ]; then
        echo ""
        echo "--------------------------------------------------------------------"
        echo "Analyzing: $SUBDIR"
        echo "--------------------------------------------------------------------"
        
        # Run analysis with overhead data, PDF generation, and optional extended analyses
        python3 benchmark/analyze_benchmark_scientific.py \
            "$INPUT_CSV" \
            -o "$OUTPUT_DIR" \
            --overhead "$OVERHEAD_DATA" \
            --pdf \
            $EXTENDED_FLAG
        
        if [ $? -eq 0 ]; then
            echo "✅ SUCCESS: $SUBDIR"
        else
            echo "❌ FAILED: $SUBDIR"
        fi
    else
        echo "⚠️  SKIPPED: $SUBDIR (no benchmark_results.csv found)"
    fi
done

echo ""
echo "========================================================================"
echo "All analyses completed!"
echo "========================================================================"

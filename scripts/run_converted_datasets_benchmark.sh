#!/bin/bash
#
# run_converted_datasets_benchmark.sh
#
# Executa benchmark EM UM ÚNICO COMANDO nos datasets convertidos
# (XLSX, DOCX, JSON, PDF_IMAGES) com todas as versões e estratégias.
#
# Author: AnonShield Team
# Date: February 2026
#
# Usage: ./run_converted_datasets_benchmark.sh [--output-dir DIR]
#

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
BASE_DIR="benchmark/converted_datasets"
OUTPUT_DIR="${OUTPUT_DIR:-benchmark/results}"
RUNS="${RUNS:-2}"
VERSIONS="${VERSIONS:-1.0 2.0 3.0}"
STRATEGIES="${STRATEGIES:- presidio filtered hybrid standalone}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Runs benchmark on all converted datasets (XLSX, DOCX, JSON, PDF_IMAGES)"
            echo "across all versions (1.0, 2.0, 3.0) and strategies."
            echo ""
            echo "Options:"
            echo "  -o, --output-dir DIR   Output directory for results (default: benchmark/results)"
            echo "  -h, --help             Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  OUTPUT_DIR  Output directory (default: benchmark/results)"
            echo "  RUNS        Number of runs per configuration (default: 2)"
            echo "  VERSIONS    Versions to test (default: 1.0 2.0 3.0)"
            echo "  STRATEGIES  Strategies for AnonShield (default: filtered hybrid standalone)"
            echo ""
            echo "Examples:"
            echo "  # Run with defaults (output to benchmark/results)"
            echo "  $0"
            echo ""
            echo "  # Save to custom directory"
            echo "  $0 --output-dir benchmark/orchestrated_results/converted"
            echo ""
            echo "  # Using environment variable"
            echo "  OUTPUT_DIR=benchmark/run_\$(date +%Y%m%d) RUNS=3 $0"
            echo ""
            echo "Notes:"
            echo "  - Scans all files in benchmark/converted_datasets/ recursively"
            echo "  - Results are appended (never overwritten)"
            echo "  - Can resume from interruption (uses benchmark_state.json)"
            echo "  - Directory mode processes all files in one invocation"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

print_header() {
    echo -e "\n${BLUE}======================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}======================================================================${NC}\n"
}

print_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Main execution
main() {
    print_header "CONVERTED DATASETS BENCHMARK - SINGLE COMMAND"
    
    # Check if converted datasets exist
    if [ ! -d "$BASE_DIR" ]; then
        echo "Error: Converted datasets directory not found: $BASE_DIR"
        echo "Run: .venv/bin/python scripts/convert_dataset.py --all"
        exit 1
    fi
    
    # Check subdirectories
    local found_dirs=""
    [ -d "$BASE_DIR/xlsx" ] && found_dirs="$found_dirs xlsx"
    [ -d "$BASE_DIR/docx" ] && found_dirs="$found_dirs docx"
    [ -d "$BASE_DIR/json" ] && found_dirs="$found_dirs json"
    [ -d "$BASE_DIR/pdf_images" ] && found_dirs="$found_dirs pdf_images"
    
    if [ -z "$found_dirs" ]; then
        echo "Error: No converted datasets found in $BASE_DIR"
        exit 1
    fi
    
    # Show configuration
    print_info "Configuration:"
    echo "  Data directory: $BASE_DIR (contains:$found_dirs)"
    echo "  Output: $OUTPUT_DIR"
    echo "  Versions: $VERSIONS"
    echo "  Strategies (AnonShield): $STRATEGIES"
    echo "  Runs per config: $RUNS"
    echo ""
    
    # Confirm
    read -p "Proceed with benchmark? [Y/n] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]] && [[ ! -z $REPLY ]]; then
        echo "Cancelled"
        exit 0
    fi
    
    # Build command
    local cmd="python3 benchmark/benchmark.py \
        --benchmark \
        --data-dir $BASE_DIR \
        --runs $RUNS \
        --versions $VERSIONS \
        --strategies $STRATEGIES \
        --results-dir $OUTPUT_DIR --continue-on-error --verbose --show-output"
    
    print_header "EXECUTING BENCHMARK"
    print_info "Command:"
    echo "  $cmd"
    echo ""
    
    START_TIME=$(date +%s)
    
    # Execute
    if eval $cmd; then
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        
        print_header "BENCHMARK COMPLETE"
        print_success "All benchmarks completed successfully!"
        echo ""
        echo "Execution time: $(($DURATION / 60))m $(($DURATION % 60))s"
        echo ""
        echo "Results: $OUTPUT_DIR/"
        echo "  ├─ benchmark_results.csv"
        echo "  └─ benchmark_results.json"
        echo "  └─ benchmark_state.json (resumable)"
        
        exit 0
    else
        echo ""
        echo "Error: Benchmark failed"
        exit 1
    fi
}

# Execute main
main

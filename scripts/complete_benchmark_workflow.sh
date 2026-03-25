#!/bin/bash
#
# complete_benchmark_workflow.sh
#
# Automated workflow for dataset conversion, analysis, and benchmarking.
# Executes the complete pipeline for multi-format benchmark evaluation.
#
# Author: AnonShield Team
# Date: February 2026
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SOURCE_DIR="${SOURCE_DIR:-vulnnet_scans_openvas}"
OUTPUT_BASE="${OUTPUT_BASE:-benchmark/converted_datasets}"
STATS_DIR="${STATS_DIR:-benchmark/dataset_statistics}"
WORKERS="${WORKERS:-8}"
RUNS="${RUNS:-2}"
VERSIONS="${VERSIONS:-2.0 3.0}"  # v1.0 doesn't support directory mode well

# Functions
print_header() {
    echo -e "\n${BLUE}================================================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================================================================${NC}\n"
}

print_step() {
    echo -e "${GREEN}[STEP]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    print_step "Checking dependencies..."
    
    local missing_deps=()
    
    # Check Python packages
    python -c "import openpyxl" 2>/dev/null || missing_deps+=("openpyxl")
    python -c "import docx" 2>/dev/null || missing_deps+=("python-docx")
    python -c "import pdf2image" 2>/dev/null || missing_deps+=("pdf2image")
    
    # Check system packages
    command -v pdftoppm >/dev/null 2>&1 || missing_deps+=("poppler-utils")
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_error "Missing dependencies: ${missing_deps[*]}"
        echo ""
        echo "Install with:"
        echo "  pip install openpyxl python-docx pdf2image"
        echo "  sudo apt-get install poppler-utils  # Ubuntu/Debian"
        echo "  or"
        echo "  brew install poppler  # macOS"
        exit 1
    fi
    
    print_info "All dependencies satisfied ✓"
}

check_source_dir() {
    if [ ! -d "$SOURCE_DIR" ]; then
        print_error "Source directory not found: $SOURCE_DIR"
        exit 1
    fi
    
    local file_count=$(find "$SOURCE_DIR" -type f \( -name "*.csv" -o -name "*.xml" -o -name "*.pdf" \) | wc -l)
    print_info "Source directory: $SOURCE_DIR ($file_count files)"
}

show_disk_space() {
    print_info "Disk space:"
    df -h . | tail -1 | awk '{print "  Available: "$4" / Total: "$2" (Used: "$5")"}'
}

convert_datasets() {
    print_header "PHASE 1: DATASET CONVERSION"
    
    print_step "Converting to all formats (XLSX, DOCX, JSON, Images)..."
    python scripts/convert_dataset.py \
        --all \
        --source "$SOURCE_DIR" \
        --output "$OUTPUT_BASE" \
        --workers "$WORKERS" \
        --verbose
    
    print_info "Conversion complete ✓"
}

analyze_statistics() {
    print_header "PHASE 2: STATISTICAL ANALYSIS"
    
    # Collect all directories to analyze
    local dirs=("$SOURCE_DIR")
    
    for format in xlsx docx json images; do
        local dir="$OUTPUT_BASE/$format"
        if [ -d "$dir" ]; then
            dirs+=("$dir")
        fi
    done
    
    print_step "Analyzing statistics for ${#dirs[@]} directories..."
    print_info "Directories: ${dirs[*]}"
    
    python scripts/analyze_dataset.py \
        --dirs "${dirs[@]}" \
        --output "$STATS_DIR" \
        --verbose
    
    print_info "Statistics generated ✓"
    echo ""
    print_info "Reports available at:"
    echo "  - $STATS_DIR/dataset_statistics.csv"
    echo "  - $STATS_DIR/dataset_statistics.json"
    echo "  - $STATS_DIR/dataset_statistics.md"
    echo "  - $STATS_DIR/dataset_files_detailed.csv"
}

run_benchmarks() {
    print_header "PHASE 3: BENCHMARK EXECUTION"
    
    # Parse versions
    local versions_array=($VERSIONS)
    local versions_arg=""
    for v in "${versions_array[@]}"; do
        versions_arg="$versions_arg --versions $v"
    done
    
    # Benchmark 1: Original dataset (CSV, XML, TXT, PDF)
    print_step "Benchmark 1/5: Original dataset (CSV, XML, TXT, PDF)"
    python benchmark/benchmark.py \
        --benchmark \
        --directory-mode \
        --data-dir "$SOURCE_DIR" \
        --runs "$RUNS" \
        $versions_arg \
        --strategies filtered hybrid standalone
    
    # Benchmark 2: XLSX files
    if [ -d "$OUTPUT_BASE/xlsx" ]; then
        print_step "Benchmark 2/5: XLSX files"
        python benchmark/benchmark.py \
            --benchmark \
            --directory-mode \
            --data-dir "$OUTPUT_BASE/xlsx" \
            --runs "$RUNS" \
            $versions_arg \
            --strategies filtered hybrid standalone
    else
        print_info "Skipping XLSX benchmark (directory not found)"
    fi
    
    # Benchmark 3: DOCX files
    if [ -d "$OUTPUT_BASE/docx" ]; then
        print_step "Benchmark 3/5: DOCX files"
        python benchmark/benchmark.py \
            --benchmark \
            --directory-mode \
            --data-dir "$OUTPUT_BASE/docx" \
            --runs "$RUNS" \
            $versions_arg \
            --strategies filtered hybrid standalone
    else
        print_info "Skipping DOCX benchmark (directory not found)"
    fi
    
    # Benchmark 4: JSON files
    if [ -d "$OUTPUT_BASE/json" ]; then
        print_step "Benchmark 4/5: JSON files"
        python benchmark/benchmark.py \
            --benchmark \
            --directory-mode \
            --data-dir "$OUTPUT_BASE/json" \
            --runs "$RUNS" \
            $versions_arg \
            --strategies filtered hybrid standalone
    else
        print_info "Skipping JSON benchmark (directory not found)"
    fi
    
    # Benchmark 5: Images (OCR test)
    if [ -d "$OUTPUT_BASE/images" ]; then
        print_step "Benchmark 5/5: Images (OCR test - PNG from PDF)"
        python benchmark/benchmark.py \
            --benchmark \
            --directory-mode \
            --data-dir "$OUTPUT_BASE/images" \
            --runs "$RUNS" \
            $versions_arg \
            --strategies filtered hybrid standalone
    else
        print_info "Skipping Images benchmark (directory not found)"
    fi
    
    print_info "All benchmarks complete ✓"
}

show_summary() {
    print_header "WORKFLOW COMPLETE"
    
    echo "Generated artifacts:"
    echo ""
    echo "1. Converted Datasets:"
    echo "   └─ $OUTPUT_BASE/"
    for format in xlsx docx json images; do
        local dir="$OUTPUT_BASE/$format"
        if [ -d "$dir" ]; then
            local size=$(du -sh "$dir" | cut -f1)
            local count=$(find "$dir" -type f | wc -l)
            echo "      ├─ $format/ ($count files, $size)"
        fi
    done
    
    echo ""
    echo "2. Statistics Reports:"
    echo "   └─ $STATS_DIR/"
    if [ -d "$STATS_DIR" ]; then
        for report in dataset_statistics.csv dataset_statistics.json dataset_statistics.md dataset_files_detailed.csv; do
            if [ -f "$STATS_DIR/$report" ]; then
                local size=$(du -sh "$STATS_DIR/$report" | cut -f1)
                echo "      ├─ $report ($size)"
            fi
        done
    fi
    
    echo ""
    echo "3. Benchmark Results:"
    echo "   └─ benchmark/results/"
    if [ -f "benchmark/results/benchmark_results.csv" ]; then
        local lines=$(wc -l < benchmark/results/benchmark_results.csv)
        local size=$(du -sh benchmark/results/benchmark_results.csv | cut -f1)
        echo "      ├─ benchmark_results.csv ($lines rows, $size)"
    fi
    if [ -f "benchmark/results/benchmark_results.json" ]; then
        local size=$(du -sh benchmark/results/benchmark_results.json | cut -f1)
        echo "      └─ benchmark_results.json ($size)"
    fi
    
    echo ""
    print_info "Next steps:"
    echo "  1. Review statistics: cat $STATS_DIR/dataset_statistics.md"
    echo "  2. Analyze benchmark results: benchmark/analyze_benchmark_scientific.py"
    echo "  3. Generate visualizations: benchmark/visualization/"
}

# Main execution
main() {
    print_header "COMPLETE BENCHMARK WORKFLOW"
    
    echo "Configuration:"
    echo "  Source Directory: $SOURCE_DIR"
    echo "  Output Directory: $OUTPUT_BASE"
    echo "  Statistics Directory: $STATS_DIR"
    echo "  Workers: $WORKERS"
    echo "  Benchmark Runs: $RUNS"
    echo "  Versions: $VERSIONS"
    echo ""
    
    # Pre-flight checks
    check_dependencies
    check_source_dir
    show_disk_space
    
    # Allow user to cancel
    echo ""
    read -p "Proceed with complete workflow? [Y/n] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]] && [[ ! -z $REPLY ]]; then
        echo "Cancelled by user"
        exit 0
    fi
    
    # Execute phases
    convert_datasets
    analyze_statistics
    run_benchmarks
    
    # Summary
    show_summary
}

# Help
if [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    echo "Usage: $0 [options]"
    echo ""
    echo "Automated workflow for dataset conversion, analysis, and benchmarking."
    echo ""
    echo "Environment variables:"
    echo "  SOURCE_DIR    Source directory (default: vulnnet_scans_openvas)"
    echo "  OUTPUT_BASE   Output directory (default: benchmark/converted_datasets)"
    echo "  STATS_DIR     Statistics directory (default: benchmark/dataset_statistics)"
    echo "  WORKERS       Number of workers (default: 8)"
    echo "  RUNS          Benchmark runs per config (default: 2)"
    echo "  VERSIONS      Space-separated versions (default: '2.0 3.0')"
    echo ""
    echo "Examples:"
    echo "  # Run with defaults"
    echo "  $0"
    echo ""
    echo "  # Custom configuration"
    echo "  WORKERS=16 RUNS=3 $0"
    echo ""
    echo "  # Different source directory"
    echo "  SOURCE_DIR=/path/to/data $0"
    exit 0
fi

# Run main
main

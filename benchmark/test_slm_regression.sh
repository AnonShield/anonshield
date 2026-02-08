#!/bin/bash
#
# Teste de regressão apenas com SLM
#

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

python3 "$BASE_DIR/benchmark/benchmark.py" \
    --regression \
    --regression-dir "$BASE_DIR/vulnnet_scans_openvas" \
    --regression-max-file-mb 2 \
    --versions 3.0 \
    --strategies slm \
    --runs 1 \
    --results-dir "$BASE_DIR/benchmark/test_slm_regression" \
    --continue-on-error

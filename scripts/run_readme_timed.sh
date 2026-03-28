#!/usr/bin/env bash
set -u -o pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_BASE="$ROOT_DIR/benchmark/readme_timing"
INCLUDE_SETUP=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out-dir)
      OUT_BASE="$2"
      shift 2
      ;;
    --include-setup)
      INCLUDE_SETUP=1
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Uso:
  bash scripts/run_readme_timed.sh [--out-dir DIR] [--include-setup]

Opções:
  --out-dir DIR       Diretório base para salvar os resultados.
  --include-setup     Inclui comandos de setup do README (apt/curl/git/docker).
  -h, --help          Exibe esta ajuda.
EOF
      exit 0
      ;;
    *)
      echo "[erro] argumento desconhecido: $1" >&2
      exit 2
      ;;
  esac
done

mkdir -p "$OUT_BASE"
RUN_ID="$(date +%Y%m%d_%H%M%S)"
RUN_DIR="$OUT_BASE/$RUN_ID"
LOG_DIR="$RUN_DIR/logs"
mkdir -p "$LOG_DIR"

if [[ -z "${ANON_SECRET_KEY:-}" ]]; then
  export ANON_SECRET_KEY
  ANON_SECRET_KEY="$(openssl rand -hex 32)"
fi

HAS_GPU=0
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
  HAS_GPU=1
fi

capture_hardware() {
  {
    echo "timestamp=$(date -Iseconds)"
    echo "hostname=$(hostname)"
    echo "kernel=$(uname -srmo)"
    echo "cwd=$ROOT_DIR"
    echo "gpu_detected=$HAS_GPU"
    echo
    echo "[lscpu]"
    command -v lscpu >/dev/null 2>&1 && lscpu || echo "indisponível"
    echo
    echo "[mem]"
    free -h || true
    echo
    echo "[disk]"
    df -h "$ROOT_DIR" || true
    echo
    echo "[gpu]"
    if [[ "$HAS_GPU" -eq 1 ]]; then
      nvidia-smi || true
    else
      echo "NVIDIA GPU não detectada"
    fi
  } > "$RUN_DIR/hardware.txt"
}

escape_csv() {
  local value="$1"
  value="${value//\"/\"\"}"
  printf '"%s"' "$value"
}

declare -a LABELS
declare -a ESTS
declare -a TAGS
declare -a CMDS

add_step() {
  LABELS+=("$1")
  ESTS+=("$2")
  TAGS+=("$3")
  CMDS+=("$4")
}

# Ordem pragmática: respeita dependências e, quando possível, vai do mais rápido ao mais lento
add_step "Minimal Test: anonimizar exemplo" "10" "always" "uv run anon.py examples/teste-exemplo-artigo.txt"
add_step "Minimal Test: validar saída" "11" "always" "cat output/anon_teste-exemplo-artigo.txt"
add_step "Minimal Test: unittest" "240" "always" "uv run python -m unittest discover tests/"
add_step "Claim #3: extract_datasets" "30" "always" "./paper_data/scripts/extract_datasets.sh"
add_step "Claim #3: spot_check GPU" "80" "gpu" "./paper_data/scripts/spot_check_claim3.sh"
add_step "Claim #3: spot_check CPU" "490" "always" "./paper_data/scripts/spot_check_claim3.sh --cpu-only"
add_step "Claim #1: smoke GPU" "900" "gpu" "./paper_data/test_minimal/run_tests.sh --skip-d2"
add_step "Claim #1: smoke CPU" "1500" "always" "./paper_data/test_minimal/run_tests.sh --skip-d2 --cpu-only"
add_step "Claim #1: spot_check GPU" "1200" "gpu" "./paper_data/scripts/spot_check_claim1.sh"
add_step "Claim #1: spot_check CPU" "1200" "always" "./paper_data/scripts/spot_check_claim1.sh --cpu-only"
add_step "Claim #2: benchmark 3.0 4 strategies" "1200" "always" "python3 benchmark/benchmark.py --benchmark --file paper_data/evaluation/vulnnet_scans_openvas_compilado.csv --versions 3.0 --strategies filtered hybrid standalone presidio --transformer-model attack-vector/SecureModernBERT-NER --entities-to-preserve TOOL,PLATFORM,FILE_PATH,THREAT_ACTOR,SERVICE,REGISTRY_KEY,CAMPAIGN,MALWARE,SECTOR --anonymization-config paper_data/configs/anonymization_config_openvas.json"
add_step "Claim #1: full D3 reproduce" "14400" "always" "./paper_data/scripts/reproduce_all_runs.sh --skip-d1 --skip-d2"
add_step "Claim #1: full D3 analyze" "300" "always" "./paper_data/scripts/analyze_all.sh"

if [[ "$INCLUDE_SETUP" -eq 1 ]]; then
  add_step "Setup: apt update + deps" "180" "setup" "sudo apt update && sudo apt install -y python3-dev build-essential"
  add_step "Setup: install uv" "60" "setup" "curl -LsSf https://astral.sh/uv/install.sh | sh"
  add_step "Setup: apt tesseract" "120" "setup" "sudo apt install -y tesseract-ocr"
  add_step "Setup: docker pull CPU image" "600" "setup" "docker pull anonshield/anon:latest"
  add_step "Setup: docker run helper script" "20" "setup" "curl -fsSL https://raw.githubusercontent.com/AnonShield/runshanondocker/main/run.sh -o run.sh && chmod +x run.sh"
fi

capture_hardware

CSV_FILE="$RUN_DIR/times.csv"
MD_FILE="$RUN_DIR/summary.md"
ROWS_FILE="$RUN_DIR/summary_rows.md"
touch "$ROWS_FILE"
printf 'idx,label,tag,estimated_seconds,real_seconds,exit_code,status,started_at,ended_at,command\n' > "$CSV_FILE"

printf '\n[info] saída: %s\n' "$RUN_DIR"
printf '[info] gpu_detected=%s\n\n' "$HAS_GPU"

for i in "${!CMDS[@]}"; do
  idx=$((i + 1))
  label="${LABELS[$i]}"
  est="${ESTS[$i]}"
  tag="${TAGS[$i]}"
  cmd="${CMDS[$i]}"

  status="ok"
  exit_code=0
  real=""

  if [[ "$tag" == "gpu" && "$HAS_GPU" -ne 1 ]]; then
    status="skipped_no_gpu"
    start_iso="$(date -Iseconds)"
    end_iso="$start_iso"
    printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
      "$idx" "$(escape_csv "$label")" "$tag" "$est" "" "" "$status" \
      "$start_iso" "$end_iso" "$(escape_csv "$cmd")" >> "$CSV_FILE"
    printf '| %s | %s | %s | %s | %s | %s | %s |\n' \
      "$idx" "$label" "$tag" "$est" "" "" "$status" >> "$ROWS_FILE"
    printf '[%02d] skip (sem GPU): %s\n' "$idx" "$label"
    continue
  fi

  printf '[%02d] run: %s\n' "$idx" "$label"
  stdout_file="$LOG_DIR/${idx}_stdout.log"
  stderr_file="$LOG_DIR/${idx}_stderr.log"
  start_iso="$(date -Iseconds)"

  {
    /usr/bin/time -f "real_seconds=%e\nuser_seconds=%U\nsys_seconds=%S\nmax_rss_kb=%M" \
      bash -lc "cd '$ROOT_DIR' && $cmd"
  } > >(tee "$stdout_file") 2> >(tee "$stderr_file" >&2)
  exit_code=$?

  end_iso="$(date -Iseconds)"
  real="$(grep -E '^real_seconds=' "$stderr_file" | tail -n1 | cut -d'=' -f2)"

  if [[ "$exit_code" -ne 0 ]]; then
    status="failed"
  fi

  printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
    "$idx" "$(escape_csv "$label")" "$tag" "$est" "$real" "$exit_code" "$status" \
    "$start_iso" "$end_iso" "$(escape_csv "$cmd")" >> "$CSV_FILE"
  printf '| %s | %s | %s | %s | %s | %s | %s |\n' \
    "$idx" "$label" "$tag" "$est" "${real:-}" "$exit_code" "$status" >> "$ROWS_FILE"

done

{
  echo "# README command timings"
  echo
  echo "- Run ID: \`$RUN_ID\`"
  echo "- Hardware: [hardware.txt](hardware.txt)"
  echo "- Raw CSV: [times.csv](times.csv)"
  echo
  echo "| # | Label | Tag | Est. (s) | Real (s) | Exit | Status |"
  echo "|---:|---|---|---:|---:|---:|---|"
  cat "$ROWS_FILE"
} > "$MD_FILE"

printf '\n[ok] relatório pronto em: %s\n' "$MD_FILE"

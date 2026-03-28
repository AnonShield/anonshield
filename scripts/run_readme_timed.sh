#!/usr/bin/env bash
set -u -o pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_BASE="$ROOT_DIR/benchmark/readme_timing"
INCLUDE_SETUP=0
ENABLE_TESSERACT=1
UPDATE_README=0

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
  bash scripts/run_readme_timed.sh [--out-dir DIR] [--include-setup] [--no-tesseract] [--update-readme]

Opções:
  --out-dir DIR       Diretório base para salvar os resultados.
  --include-setup     Inclui comandos de setup do README (apt/curl/git/docker).
  --no-tesseract      Não instala nem usa Tesseract; pula runs que dependem de OCR.
  --update-readme     Atualiza automaticamente README.md com bloco de tempos medidos.
  -h, --help          Exibe esta ajuda.
EOF
      exit 0
      ;;
    --no-tesseract)
      ENABLE_TESSERACT=0
      shift
      ;;
    --update-readme)
      UPDATE_README=1
      shift
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

HAS_TESSERACT=0
if command -v tesseract >/dev/null 2>&1; then
  HAS_TESSERACT=1
fi

capture_hardware() {
  {
    echo "timestamp=$(date -Iseconds)"
    echo "hostname=$(hostname)"
    echo "kernel=$(uname -srmo)"
    echo "cwd=$ROOT_DIR"
    echo "gpu_detected=$HAS_GPU"
    echo "tesseract_enabled=$ENABLE_TESSERACT"
    echo "tesseract_installed=$HAS_TESSERACT"
    if [[ "$HAS_TESSERACT" -eq 1 ]]; then
      echo "tesseract_version=$(tesseract --version | head -n1)"
    fi
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
declare -a REALS
declare -a STATUSES

add_step() {
  LABELS+=("$1")
  ESTS+=("$2")
  TAGS+=("$3")
  CMDS+=("$4")
}

format_duration() {
  local secs="$1"
  if [[ -z "$secs" ]]; then
    printf "n/a"
    return
  fi
  awk -v s="$secs" 'BEGIN {
    if (s < 60) { printf "%.1f s", s; exit }
    if (s < 3600) { printf "%.1f min", s/60; exit }
    printf "%.2f h", s/3600
  }'
}

find_idx_by_label() {
  local wanted="$1"
  local i
  for i in "${!LABELS[@]}"; do
    if [[ "${LABELS[$i]}" == "$wanted" ]]; then
      printf "%s" "$i"
      return 0
    fi
  done
  return 1
}

# Ordem pragmática: respeita dependências e, quando possível, vai do mais rápido ao mais lento
add_step "Minimal Test: anonimizar exemplo" "10" "always" "uv run anon.py examples/teste-exemplo-artigo.txt"
add_step "Minimal Test: validar saída" "11" "always" "cat output/anon_teste-exemplo-artigo.txt"
add_step "Minimal Test: unittest" "240" "always" "uv run python -m unittest discover tests/"
add_step "Claim #3: extract_datasets" "30" "always" "./paper_data/scripts/extract_datasets.sh"
add_step "Claim #3: spot_check GPU" "80" "gpu" "./paper_data/scripts/spot_check_claim3.sh"
add_step "Claim #3: spot_check CPU" "490" "always" "./paper_data/scripts/spot_check_claim3.sh --cpu-only"
add_step "Claim #1: smoke GPU" "900" "gpu,tesseract" "./paper_data/test_minimal/run_tests.sh --skip-d2"
add_step "Claim #1: smoke CPU" "1500" "tesseract" "./paper_data/test_minimal/run_tests.sh --skip-d2 --cpu-only"
add_step "Claim #1: spot_check GPU" "1200" "gpu" "./paper_data/scripts/spot_check_claim1.sh"
add_step "Claim #1: spot_check CPU" "1200" "always" "./paper_data/scripts/spot_check_claim1.sh --cpu-only"
add_step "Claim #2: benchmark 3.0 4 strategies" "1200" "always" "python3 benchmark/benchmark.py --benchmark --file paper_data/evaluation/vulnnet_scans_openvas_compilado.csv --versions 3.0 --strategies filtered hybrid standalone presidio --transformer-model attack-vector/SecureModernBERT-NER --entities-to-preserve TOOL,PLATFORM,FILE_PATH,THREAT_ACTOR,SERVICE,REGISTRY_KEY,CAMPAIGN,MALWARE,SECTOR --anonymization-config paper_data/configs/anonymization_config_openvas.json"
add_step "Claim #1: full D3 reproduce" "14400" "always" "./paper_data/scripts/reproduce_all_runs.sh --skip-d1 --skip-d2"
add_step "Claim #1: full D3 analyze" "300" "always" "./paper_data/scripts/analyze_all.sh"

if [[ "$INCLUDE_SETUP" -eq 1 ]]; then
  add_step "Setup: apt update + deps" "180" "setup" "sudo apt update && sudo apt install -y python3-dev build-essential"
  add_step "Setup: install uv" "60" "setup" "curl -LsSf https://astral.sh/uv/install.sh | sh"
  if [[ "$ENABLE_TESSERACT" -eq 1 ]]; then
    add_step "Setup: apt tesseract" "120" "setup,tesseract" "sudo apt install -y tesseract-ocr"
  fi
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

  if [[ ",$tag," == *,gpu,* && "$HAS_GPU" -ne 1 ]]; then
    status="skipped_no_gpu"
    start_iso="$(date -Iseconds)"
    end_iso="$start_iso"
    printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
      "$idx" "$(escape_csv "$label")" "$tag" "$est" "" "" "$status" \
      "$start_iso" "$end_iso" "$(escape_csv "$cmd")" >> "$CSV_FILE"
    printf '| %s | %s | %s | %s | %s | %s | %s |\n' \
      "$idx" "$label" "$tag" "$est" "" "" "$status" >> "$ROWS_FILE"
    REALS[$i]=""
    STATUSES[$i]="$status"
    printf '[%02d] skip (sem GPU): %s\n' "$idx" "$label"
    continue
  fi

  if [[ ",$tag," == *,tesseract,* ]] && [[ "$ENABLE_TESSERACT" -eq 0 || "$HAS_TESSERACT" -ne 1 ]]; then
    status="skipped_no_tesseract"
    start_iso="$(date -Iseconds)"
    end_iso="$start_iso"
    printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
      "$idx" "$(escape_csv "$label")" "$tag" "$est" "" "" "$status" \
      "$start_iso" "$end_iso" "$(escape_csv "$cmd")" >> "$CSV_FILE"
    printf '| %s | %s | %s | %s | %s | %s | %s |\n' \
      "$idx" "$label" "$tag" "$est" "" "" "$status" >> "$ROWS_FILE"
    REALS[$i]=""
    STATUSES[$i]="$status"
    printf '[%02d] skip (sem Tesseract): %s\n' "$idx" "$label"
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
  REALS[$i]="$real"
  STATUSES[$i]="$status"

done

{
  echo "# README command timings"
  echo
  echo "- Run ID: \`$RUN_ID\`"
  echo "- Hardware: [hardware.txt](hardware.txt)"
  echo "- Raw CSV: [times.csv](times.csv)"
  if [[ "$ENABLE_TESSERACT" -eq 0 ]]; then
    echo "- OCR/Tesseract: desabilitado por flag \`--no-tesseract\`"
    echo "- Nota: runs com PDF imagem/OCR aparecem como \`skipped_no_tesseract\`."
  elif [[ "$HAS_TESSERACT" -ne 1 ]]; then
    echo "- OCR/Tesseract: não instalado neste host"
    echo "- Nota: runs com PDF imagem/OCR aparecem como \`skipped_no_tesseract\`."
  fi
  echo
  echo "| # | Label | Tag | Est. (s) | Real (s) | Exit | Status |"
  echo "|---:|---|---|---:|---:|---:|---|"
  cat "$ROWS_FILE"
} > "$MD_FILE"

SNIPPET_FILE="$RUN_DIR/readme_option_c_timing.md"
ALL_CLAIMS_FILE="$RUN_DIR/readme_claim_timings.md"
idx_extract="$(find_idx_by_label "Claim #3: extract_datasets" || true)"
idx_reproduce="$(find_idx_by_label "Claim #1: full D3 reproduce" || true)"
idx_analyze="$(find_idx_by_label "Claim #1: full D3 analyze" || true)"
idx_claim1_smoke_gpu="$(find_idx_by_label "Claim #1: smoke GPU" || true)"
idx_claim1_smoke_cpu="$(find_idx_by_label "Claim #1: smoke CPU" || true)"
idx_claim1_spot_gpu="$(find_idx_by_label "Claim #1: spot_check GPU" || true)"
idx_claim1_spot_cpu="$(find_idx_by_label "Claim #1: spot_check CPU" || true)"
idx_claim2="$(find_idx_by_label "Claim #2: benchmark 3.0 4 strategies" || true)"
idx_claim3_spot_gpu="$(find_idx_by_label "Claim #3: spot_check GPU" || true)"
idx_claim3_spot_cpu="$(find_idx_by_label "Claim #3: spot_check CPU" || true)"

extract_real="${REALS[$idx_extract]:-}"
reproduce_real="${REALS[$idx_reproduce]:-}"
analyze_real="${REALS[$idx_analyze]:-}"

extract_status="${STATUSES[$idx_extract]:-not_found}"
reproduce_status="${STATUSES[$idx_reproduce]:-not_found}"
analyze_status="${STATUSES[$idx_analyze]:-not_found}"

claim1_smoke_gpu_real="${REALS[$idx_claim1_smoke_gpu]:-}"
claim1_smoke_cpu_real="${REALS[$idx_claim1_smoke_cpu]:-}"
claim1_smoke_gpu_status="${STATUSES[$idx_claim1_smoke_gpu]:-not_found}"
claim1_smoke_cpu_status="${STATUSES[$idx_claim1_smoke_cpu]:-not_found}"

claim1_spot_gpu_real="${REALS[$idx_claim1_spot_gpu]:-}"
claim1_spot_cpu_real="${REALS[$idx_claim1_spot_cpu]:-}"
claim1_spot_gpu_status="${STATUSES[$idx_claim1_spot_gpu]:-not_found}"
claim1_spot_cpu_status="${STATUSES[$idx_claim1_spot_cpu]:-not_found}"

claim2_real="${REALS[$idx_claim2]:-}"
claim2_status="${STATUSES[$idx_claim2]:-not_found}"

claim3_spot_gpu_real="${REALS[$idx_claim3_spot_gpu]:-}"
claim3_spot_cpu_real="${REALS[$idx_claim3_spot_cpu]:-}"
claim3_spot_gpu_status="${STATUSES[$idx_claim3_spot_gpu]:-not_found}"
claim3_spot_cpu_status="${STATUSES[$idx_claim3_spot_cpu]:-not_found}"

option_c_total=""
if [[ "$extract_status" == "ok" && "$reproduce_status" == "ok" && "$analyze_status" == "ok" ]]; then
  option_c_total="$(awk -v a="$extract_real" -v b="$reproduce_real" -v c="$analyze_real" 'BEGIN { printf "%.2f", (a+b+c) }')"
fi

claim1_option_a_gpu_total=""
if [[ "$claim1_smoke_gpu_status" == "ok" ]]; then
  claim1_option_a_gpu_total="$claim1_smoke_gpu_real"
fi
claim1_option_a_cpu_total=""
if [[ "$claim1_smoke_cpu_status" == "ok" ]]; then
  claim1_option_a_cpu_total="$claim1_smoke_cpu_real"
fi

claim1_option_b_gpu_total=""
if [[ "$extract_status" == "ok" && "$claim1_spot_gpu_status" == "ok" ]]; then
  claim1_option_b_gpu_total="$(awk -v a="$extract_real" -v b="$claim1_spot_gpu_real" 'BEGIN { printf "%.2f", (a+b) }')"
fi
claim1_option_b_cpu_total=""
if [[ "$extract_status" == "ok" && "$claim1_spot_cpu_status" == "ok" ]]; then
  claim1_option_b_cpu_total="$(awk -v a="$extract_real" -v b="$claim1_spot_cpu_real" 'BEGIN { printf "%.2f", (a+b) }')"
fi

claim3_gpu_total=""
if [[ "$extract_status" == "ok" && "$claim3_spot_gpu_status" == "ok" ]]; then
  claim3_gpu_total="$(awk -v a="$extract_real" -v b="$claim3_spot_gpu_real" 'BEGIN { printf "%.2f", (a+b) }')"
fi
claim3_cpu_total=""
if [[ "$extract_status" == "ok" && "$claim3_spot_cpu_status" == "ok" ]]; then
  claim3_cpu_total="$(awk -v a="$extract_real" -v b="$claim3_spot_cpu_real" 'BEGIN { printf "%.2f", (a+b) }')"
fi

cpu_model="$(lscpu 2>/dev/null | awk -F: '/Model name/{gsub(/^ +/,"",$2); print $2; exit}')"
gpu_model="none"
if [[ "$HAS_GPU" -eq 1 ]]; then
  gpu_model="$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n1)"
  [[ -z "$gpu_model" ]] && gpu_model="detected"
fi

{
  echo "**Option C — Full D3 benchmark (reproduces paper Tables 6–8):**"
  echo "Resultado real nesta máquina (run id: \`$RUN_ID\`):"
  echo ""
  echo "- Hardware: CPU \`$cpu_model\` | GPU \`$gpu_model\`"
  echo "- \`./paper_data/scripts/extract_datasets.sh\`: $(format_duration "$extract_real") (status: \`$extract_status\`)"
  echo "- \`./paper_data/scripts/reproduce_all_runs.sh --skip-d1 --skip-d2\`: $(format_duration "$reproduce_real") (status: \`$reproduce_status\`)"
  echo "- \`./paper_data/scripts/analyze_all.sh\`: $(format_duration "$analyze_real") (status: \`$analyze_status\`)"
  if [[ -n "$option_c_total" ]]; then
    echo "- Tempo total Option C: **$(format_duration "$option_c_total")**"
  else
    echo "- Tempo total Option C: **n/a** (uma ou mais etapas não concluídas com status \`ok\`)"
  fi
  if [[ "$ENABLE_TESSERACT" -eq 0 || "$HAS_TESSERACT" -ne 1 ]]; then
    echo "- Nota OCR: esta execução foi feita sem Tesseract; etapas dependentes de PDF imagem/OCR aparecem como \`skipped_no_tesseract\`."
  fi
  echo ""
  echo '```bash'
  echo "./paper_data/scripts/extract_datasets.sh                     # extract D3 from bundled zips (~80 MB → ~700 MB)"
  echo "./paper_data/scripts/reproduce_all_runs.sh --skip-d1 --skip-d2"
  echo "./paper_data/scripts/analyze_all.sh"
  echo '```'
} > "$SNIPPET_FILE"

{
  echo "### Measured Runtime Examples (auto-generated)"
  echo ""
  echo "Resultados reais nesta máquina (run id: \`$RUN_ID\`):"
  echo ""
  echo "- Hardware: CPU \`$cpu_model\` | GPU \`$gpu_model\`"
  if [[ "$ENABLE_TESSERACT" -eq 0 || "$HAS_TESSERACT" -ne 1 ]]; then
    echo "- OCR/Tesseract: indisponível nesta execução; etapas OCR aparecem como \`skipped_no_tesseract\`."
  fi
  echo ""
  echo "**Claim #1**"
  echo "- Option A (smoke, GPU): $(format_duration "$claim1_option_a_gpu_total") (status: \`$claim1_smoke_gpu_status\`)"
  echo "- Option A (smoke, CPU): $(format_duration "$claim1_option_a_cpu_total") (status: \`$claim1_smoke_cpu_status\`)"
  echo "- Option B (extract + spot, GPU): $(format_duration "$claim1_option_b_gpu_total") (status spot: \`$claim1_spot_gpu_status\`)"
  echo "- Option B (extract + spot, CPU): $(format_duration "$claim1_option_b_cpu_total") (status spot: \`$claim1_spot_cpu_status\`)"
  echo "- Option C (extract + reproduce + analyze): $(format_duration "$option_c_total") (extract: \`$extract_status\`, reproduce: \`$reproduce_status\`, analyze: \`$analyze_status\`)"
  echo ""
  echo "**Claim #2**"
  echo "- Benchmark (3.0, 4 strategies): $(format_duration "$claim2_real") (status: \`$claim2_status\`)"
  echo ""
  echo "**Claim #3**"
  echo "- Spot check (extract + GPU): $(format_duration "$claim3_gpu_total") (extract: \`$extract_status\`, spot: \`$claim3_spot_gpu_status\`)"
  echo "- Spot check (extract + CPU): $(format_duration "$claim3_cpu_total") (extract: \`$extract_status\`, spot: \`$claim3_spot_cpu_status\`)"
} > "$ALL_CLAIMS_FILE"

if [[ "$UPDATE_README" -eq 1 ]]; then
  python3 - "$ROOT_DIR/README.md" "$ALL_CLAIMS_FILE" <<'PY'
import pathlib
import re
import sys

readme_path = pathlib.Path(sys.argv[1])
snippet = pathlib.Path(sys.argv[2]).read_text().rstrip()
start = "<!-- AUTO_TIMINGS_START -->"
end = "<!-- AUTO_TIMINGS_END -->"
block = f"{start}\n{snippet}\n{end}"

text = readme_path.read_text()

if start in text and end in text:
    pattern = re.compile(re.escape(start) + r"[\s\S]*?" + re.escape(end), re.M)
    text = pattern.sub(block, text, count=1)
else:
    marker = "## Experiments"
    if marker in text:
        text = text.replace(marker, marker + "\n\n" + block, 1)
    else:
        text = text.rstrip() + "\n\n" + block + "\n"

readme_path.write_text(text)
PY
fi

printf '\n[ok] relatório pronto em: %s\n' "$MD_FILE"
printf '[ok] snippet Option C: %s\n' "$SNIPPET_FILE"
printf '[ok] snippet todas claims: %s\n' "$ALL_CLAIMS_FILE"
if [[ "$UPDATE_README" -eq 1 ]]; then
  printf '[ok] README atualizado automaticamente com tempos medidos.\n'
fi

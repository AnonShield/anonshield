#!/bin/bash

# Script para executar anonimização com múltiplas estratégias
# Cada estratégia terá sua própria database e diretório de output

set -e  # Parar em caso de erro

# Configurações
INPUT_FILE="vulnnet_scans_openvas_compilado.csv"
TRANSFORMER_MODEL="attack-vector/SecureModernBERT-NER"
BASE_DB_DIR="/home/kapelinski/Documents/tool/vulnnet_database"
BASE_OUTPUT_DIR="/home/kapelinski/Documents/tool/vulnnet_output"

# Estratégias a serem testadas (excluindo standalone)
STRATEGIES=("presidio" "filtered" "hybrid" "slm")

# Cores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Anonimização Multi-Estratégias${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Arquivo: ${GREEN}${INPUT_FILE}${NC}"
echo -e "Modelo: ${GREEN}${TRANSFORMER_MODEL}${NC}"
echo -e "Estratégias: ${GREEN}${STRATEGIES[@]}${NC}"
echo ""

# Verificar se o arquivo de entrada existe
if [ ! -f "$INPUT_FILE" ]; then
    echo -e "${RED}Erro: Arquivo não encontrado: ${INPUT_FILE}${NC}"
    exit 1
fi

# Verificar se ANON_SECRET_KEY está definida
if [ -z "$ANON_SECRET_KEY" ]; then
    echo -e "${YELLOW}Aviso: ANON_SECRET_KEY não está definida!${NC}"
    echo -e "${YELLOW}Defina com: export ANON_SECRET_KEY='sua-chave-secreta'${NC}"
    exit 1
fi

# Criar diretórios base
mkdir -p "$BASE_DB_DIR"
mkdir -p "$BASE_OUTPUT_DIR"

# Contador de sucesso/falha
SUCCESS_COUNT=0
FAILED_COUNT=0
START_TIME=$(date +%s)

# Iterar sobre cada estratégia
for STRATEGY in "${STRATEGIES[@]}"; do
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}  Executando estratégia: ${YELLOW}${STRATEGY}${NC}"
    echo -e "${BLUE}========================================${NC}\n"

    # Criar diretórios específicos para cada estratégia
    DB_DIR="${BASE_DB_DIR}/${STRATEGY}"
    OUTPUT_DIR="${BASE_OUTPUT_DIR}/${STRATEGY}"

    mkdir -p "$DB_DIR"
    mkdir -p "$OUTPUT_DIR"

    echo -e "Database: ${GREEN}${DB_DIR}${NC}"
    echo -e "Output: ${GREEN}${OUTPUT_DIR}${NC}"
    echo ""

    # Timestamp de início
    STRATEGY_START=$(date +%s)

    # Executar comando de anonimização
    if uv run anon.py "$INPUT_FILE" \
        --anonymization-strategy "$STRATEGY" \
        --transformer-model "$TRANSFORMER_MODEL" \
        --db-dir "$DB_DIR" \
        --output-dir "$OUTPUT_DIR" \
        --db-mode persistent \
        --db-synchronous-mode OFF \
        --optimize \
        --batch-size 2000 \
        --csv-chunk-size 2000 \
        --nlp-batch-size 1000; then

        STRATEGY_END=$(date +%s)
        STRATEGY_DURATION=$((STRATEGY_END - STRATEGY_START))

        echo -e "\n${GREEN}✓ Estratégia '${STRATEGY}' concluída com sucesso!${NC}"
        echo -e "  Tempo: ${STRATEGY_DURATION}s"
        echo -e "  Database: ${DB_DIR}/entities.db"
        echo -e "  Output: ${OUTPUT_DIR}/anon_${INPUT_FILE}"

        ((SUCCESS_COUNT++))
    else
        echo -e "\n${RED}✗ Erro ao executar estratégia '${STRATEGY}'${NC}"
        ((FAILED_COUNT++))
    fi
done

# Resumo final
END_TIME=$(date +%s)
TOTAL_DURATION=$((END_TIME - START_TIME))

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}  Resumo Final${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Total de estratégias: ${#STRATEGIES[@]}"
echo -e "${GREEN}Sucesso: ${SUCCESS_COUNT}${NC}"
echo -e "${RED}Falhas: ${FAILED_COUNT}${NC}"
echo -e "Tempo total: ${TOTAL_DURATION}s ($(($TOTAL_DURATION / 60))m $(($TOTAL_DURATION % 60))s)"
echo ""

# Listar arquivos gerados
echo -e "${BLUE}Arquivos gerados:${NC}"
for STRATEGY in "${STRATEGIES[@]}"; do
    OUTPUT_FILE="${BASE_OUTPUT_DIR}/${STRATEGY}/anon_${INPUT_FILE}"
    DB_FILE="${BASE_DB_DIR}/${STRATEGY}/entities.db"

    if [ -f "$OUTPUT_FILE" ]; then
        SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
        echo -e "  ${GREEN}✓${NC} ${STRATEGY}: ${SIZE} - ${OUTPUT_FILE}"
    else
        echo -e "  ${RED}✗${NC} ${STRATEGY}: Arquivo não encontrado"
    fi

    if [ -f "$DB_FILE" ]; then
        DB_SIZE=$(du -h "$DB_FILE" | cut -f1)
        echo -e "      DB: ${DB_SIZE} - ${DB_FILE}"
    fi
done

echo ""
echo -e "${GREEN}Processo concluído!${NC}"

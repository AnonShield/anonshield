#!/usr/bin/env python3

"""
Calcula as métricas de acurácia (Precisão, Recall, F1-Score) para um
arquivo anonimizado, comparando-o com um arquivo de gabarito (ground truth).

Este script utiliza a lógica de avaliação presente nos testes do projeto para
fornecer uma ferramenta de linha de comando para a avaliação de acurácia.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Adiciona o diretório 'src' ao path para que possamos importar os módulos do anon
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

try:
    from src.anon.evaluation.metrics_calculator import MetricsCalculator
    from src.anon.evaluation.ground_truth import GroundTruth
except ImportError as e:
    print(f"Erro: Não foi possível importar os módulos de avaliação. Verifique se o script está no diretório 'scripts' e se o ambiente virtual está ativo.")
    print(f"Detalhes: {e}")
    sys.exit(1)


def setup_logging():
    """Configura o logging para o script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stdout,
    )

def main():
    """
    Função principal que orquestra a leitura dos arquivos, cálculo das métricas
    e exibição dos resultados.
    """
    parser = argparse.ArgumentParser(
        description="Calcula Precisão, Recall e F1-Score para um arquivo anonimizado.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--ground-truth-json",
        required=True,
        help="Caminho para o arquivo JSON de gabarito (ground truth)."
    )
    parser.add_argument(
        "--anonymized-file",
        required=True,
        help="Caminho para o arquivo de texto anonimizado que será avaliado."
    )
    parser.add_argument(
        "--db-path",
        required=True,
        help="Caminho para o arquivo de banco de dados (entities.db) usado na anonimização."
    )
    args = parser.parse_args()

    setup_logging()
    logging.info("Iniciando o processo de avaliação...")

    # --- Validação dos caminhos ---
    ground_truth_path = Path(args.ground_truth_json)
    anonymized_file_path = Path(args.anonymized_file)
    db_path = Path(args.db_path)

    if not ground_truth_path.exists():
        logging.error(f"Arquivo de gabarito não encontrado: {ground_truth_path}")
        sys.exit(1)
    if not anonymized_file_path.exists():
        logging.error(f"Arquivo anonimizado não encontrado: {anonymized_file_path}")
        sys.exit(1)
    if not db_path.exists():
        logging.warning(f"Arquivo de banco de dados não encontrado: {db_path}. A avaliação pode falhar se os hashes não forem encontrados.")

    # --- Execução da Avaliação ---
    try:
        # 1. Carregar o gabarito (Ground Truth)
        logging.info(f"Carregando gabarito de {ground_truth_path}...")
        ground_truth = GroundTruth.load(ground_truth_path)
        logging.info(f"Gabarito carregado com {ground_truth.get_total_entities()} entidades esperadas.")

        # 2. Inicializar a calculadora de métricas
        logging.info(f"Inicializando calculadora de métricas com o banco de dados: {db_path}...")
        calculator = MetricsCalculator(db_path=str(db_path))

        # 3. Ler o conteúdo do arquivo anonimizado
        logging.info(f"Lendo arquivo anonimizado de {anonymized_file_path}...")
        anonymized_text = anonymized_file_path.read_text(encoding="utf-8")

        # 4. Calcular as métricas
        logging.info("Calculando métricas...")
        metrics = calculator.calculate_metrics(ground_truth, anonymized_text)

        # 5. Exibir os resultados
        print("\n" + "="*50)
        print("RESULTADOS DA AVALIAÇÃO DE ACURÁCIA")
        print("="*50)
        print(f"  - Arquivo Avaliado: {anonymized_file_path.name}")
        print(f"  - Gabarito: {ground_truth_path.name}")
        print("-" * 50)
        print(f"  - Verdadeiros Positivos (TP): {metrics.true_positives}")
        print(f"  - Falsos Positivos (FP):     {metrics.false_positives}")
        print(f"  - Falsos Negativos (FN):     {metrics.false_negatives}")
        print("-" * 50)
        print(f"  - Precisão: {metrics.precision:.4f}")
        print(f"  - Recall:   {metrics.recall:.4f}")
        print(f"  - F1-Score: {metrics.f1_score:.4f}")
        print("="*50 + "\n")

        # Exibir detalhes sobre Falsos Positivos e Falsos Negativos
        if metrics.fp_details or metrics.fn_details:
            print("--- Detalhes ---")
            if metrics.fp_details:
                print(f"Falsos Positivos (entidades encontradas, mas não esperadas):")
                for entity, count in metrics.fp_details.items():
                    print(f"  - {entity} (encontrado {count}x)")
            if metrics.fn_details:
                print(f"Falsos Negativos (entidades esperadas, mas não encontradas):")
                for entity, count in metrics.fn_details.items():
                    print(f"  - {entity.original_text} ({entity.entity_type}) (esperado {count}x)")
            print("-" * 16 + "\n")


    except Exception as e:
        logging.error(f"Ocorreu um erro durante a avaliação: {e}", exc_info=True)
        sys.exit(1)

    logging.info("Avaliação concluída com sucesso.")


if __name__ == "__main__":
    main()

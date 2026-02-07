#!/usr/bin/env python3

"""
Cria um arquivo de gabarito (ground truth) em formato JSON a partir de um
arquivo de texto original, automatizando o processo de bootstrapping.

Este script utiliza o próprio motor do anon.py para gerar os dados de NER
(Named Entity Recognition), gera os hashes determinísticos e salva o arquivo
de gabarito pronto para ser usado pelo script 'evaluate.py'.
"""

import argparse
import logging
import os
import sys
import subprocess
import tempfile
from pathlib import Path

# Adiciona o diretório 'src' ao path para que possamos importar os módulos do anon
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

try:
    from src.anon.evaluation.ground_truth import GroundTruthManager
    from src.anon.config import SECRET_KEY
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
    Função principal que orquestra a criação do arquivo de gabarito.
    """
    parser = argparse.ArgumentParser(
        description="Cria um arquivo de gabarito (ground truth) JSON a partir de um arquivo de texto.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--input-file",
        required=True,
        help="Caminho para o arquivo de texto original."
    )
    parser.add_argument(
        "--output-json",
        required=True,
        help="Caminho onde o arquivo ground_truth.json será salvo."
    )
    parser.add_argument(
        "--lang",
        type=str,
        default="en",
        help="Idioma do documento (ex: 'pt', 'en'). Default: 'en'."
    )
    args = parser.parse_args()

    setup_logging()

    # --- Validação da chave secreta ---
    if not SECRET_KEY:
        logging.error("A variável de ambiente ANON_SECRET_KEY não está definida. Ela é necessária para gerar os hashes do gabarito.")
        sys.exit(1)

    input_path = Path(args.input_file)
    output_path = Path(args.output_json)

    if not input_path.exists():
        logging.error(f"Arquivo de entrada não encontrado: {input_path}")
        sys.exit(1)

    # Garante que o diretório de saída exista
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Usar um arquivo temporário para o output do NER
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".jsonl") as temp_ner_file:
        temp_ner_path = Path(temp_ner_file.name)

    try:
        # --- Passo 1: Gerar dados de NER usando anon.py ---
        logging.info(f"Executando 'anon.py --generate-ner-data' em '{input_path}'...")
        cmd = [
            "uv", "run", "python", str(project_root / "anon.py"),
            str(input_path),
            "--generate-ner-data",
            "--ner-aggregate-record", # Garante um formato compatível com Doccano
            "--output-dir", str(temp_ner_path.parent),
            "--lang", args.lang,
            "--overwrite" # Permite sobrescrever o output temporário
        ]
        
        # O nome do arquivo de saída do NER é previsível
        ner_output_filename = f"anon_{input_path.name}.jsonl"
        expected_ner_output_path = temp_ner_path.parent / ner_output_filename

        # Renomear o arquivo temporário para o nome esperado
        # para que o `anon.py` escreva nele.
        if expected_ner_output_path.exists():
            os.remove(expected_ner_output_path)
        os.rename(temp_ner_path, expected_ner_output_path)
        
        # Executa o subprocesso
        subprocess.run(cmd, check=True, capture_output=True, text=True)

        if not expected_ner_output_path.exists() or expected_ner_output_path.stat().st_size == 0:
            raise RuntimeError(f"A geração de dados NER falhou. O arquivo de saída '{expected_ner_output_path}' está vazio ou não foi criado.")
            
        logging.info(f"Dados de NER gerados com sucesso em: {expected_ner_output_path}")

        # --- Passo 2: Processar os dados de NER e criar o gabarito ---
        logging.info("Inicializando GroundTruthManager...")
        manager = GroundTruthManager(secret_key=SECRET_KEY)

        logging.info(f"Importando dados no formato Doccano de '{expected_ner_output_path}'...")
        manager.import_from_doccano(expected_ner_output_path)

        logging.info("Gerando gabarito (ground truth) com hashes determinísticos...")
        ground_truth = manager.generate_ground_truth()

        logging.info(f"Salvando o arquivo de gabarito final em '{output_path}'...")
        ground_truth.save(output_path)

        print("\n" + "="*50)
        print("GABARITO CRIADO COM SUCESSO")
        print("="*50)
        print(f"  - Arquivo de Entrada: {input_path.name}")
        print(f"  - Arquivo de Saída:   {output_path}")
        print(f"  - Entidades Encontradas: {ground_truth.get_total_entities()}")
        print("="*50 + "\n")
        logging.info(f"Processo concluído. O arquivo '{output_path}' está pronto para ser usado com 'evaluate.py'.")

    except subprocess.CalledProcessError as e:
        logging.error("Ocorreu um erro ao executar 'anon.py' para gerar os dados de NER.")
        logging.error(f"Output do erro:\n{e.stderr}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Ocorreu um erro durante a criação do gabarito: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # --- Limpeza ---
        if 'expected_ner_output_path' in locals() and expected_ner_output_path.exists():
            os.remove(expected_ner_output_path)
            logging.debug(f"Arquivo temporário de NER removido: {expected_ner_output_path}")

if __name__ == "__main__":
    main()

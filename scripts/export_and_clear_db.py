
import os
import csv
import logging
import argparse
from typing import List, Tuple

# --- Configuration ---
# Adiciona o diretório raiz do projeto ao sys.path para permitir importações de módulos locais
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.anon.repository import EntityRepository
from src.anon.config import DB_CONFIG

# ---

def export_entities_to_csv(entities: List[Tuple], output_path: str):
    """Escreve uma lista de entidades para um arquivo CSV."""
    if not entities:
        logging.info("Nenhuma entidade encontrada no banco de dados. Nada para exportar.")
        return

    logging.info(f"Exportando {len(entities)} entidades para '{output_path}'...")
    header = ["id", "entity_type", "original_name", "slug_name", "full_hash", "first_seen", "last_seen"]
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        writer.writerows(entities)
    logging.info(f"Exportação concluída com sucesso. Dados salvos em {output_path}")

def main():
    """
    Exporta todas as entidades do banco de dados para um arquivo CSV e, opcionalmente,
    limpa a tabela de entidades.
    """
    parser = argparse.ArgumentParser(description="Exportar entidades para CSV e, opcionalmente, limpar o banco de dados.")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Limpar todas as entidades do banco de dados após a exportação para CSV."
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    output_dir = os.path.join(PROJECT_ROOT, "output")
    csv_filename = "entities_export.csv"
    output_path = os.path.join(output_dir, csv_filename)

    if not os.path.exists(DB_CONFIG['db_path']):
        logging.error(f"Arquivo de banco de dados não encontrado em '{DB_CONFIG['db_path']}'. Certifique-se de que o banco de dados existe.")
        return

    repository = None
    try:
        # Inicializa o repositório que gerencia as conexões de banco de dados
        repository = EntityRepository(db_path=DB_CONFIG['db_path'])
        repository.initialize_schema() # Garante que o esquema está pronto
        
        logging.info(f"Conectado com sucesso ao banco de dados em '{DB_CONFIG['db_path']}'.")

        # 1. Busca todas as entidades usando o repositório
        logging.info("Buscando todas as entidades do banco de dados...")
        entities = repository.get_all_entities()

        # 2. Escreve para CSV
        export_entities_to_csv(entities, output_path)

        # 3. Limpa o banco de dados condicionalmente
        if args.clear:
            logging.info("Limpando todas as entidades do banco de dados, pois a flag --clear foi fornecida...")
            deleted_rows_count = repository.clear_all_entities()
            logging.info(f"Banco de dados limpo com sucesso. {deleted_rows_count} linhas foram deletadas.")
        else:
            logging.info("A limpeza do banco de dados foi ignorada. Para limpar o banco de dados, execute o script com a flag --clear.")

    except Exception as e:
        logging.error(f"Ocorreu um erro inesperado: {e}", exc_info=True)
    finally:
        if repository:
            repository.close_thread_connection()
            logging.info("Conexão com o banco de dados fechada.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Script para compilar todos os arquivos CSV das subpastas de vulnnet_scans_openvas
Versão corrigida que preserva campos com quebras de linha e caracteres especiais.
"""

import os
import csv
from pathlib import Path

def compile_csvs():
    base_dir = Path("/home/kapelinski/Documents/tool/vulnnet_scans_openvas")
    output_file = Path("/home/kapelinski/Documents/tool/vulnnet_scans_openvas_compilado.csv")

    # Encontrar todos os CSVs nas subpastas (mindepth 2)
    csv_files = []
    for root, dirs, files in os.walk(base_dir):
        # Ignorar arquivos na raiz (apenas em subpastas)
        if root == str(base_dir):
            continue
        for file in files:
            if file.endswith('.csv'):
                csv_files.append(os.path.join(root, file))

    csv_files.sort()  # Ordenar para consistência

    print(f"Encontrados {len(csv_files)} arquivos CSV nas subpastas")

    header_written = False
    total_rows = 0
    errors = []

    with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        writer = None

        for idx, csv_file in enumerate(csv_files, 1):
            print(f"Processando {idx}/{len(csv_files)}: {Path(csv_file).name}")

            try:
                with open(csv_file, 'r', newline='', encoding='utf-8') as infile:
                    # Usar csv.reader com configuração adequada para lidar com campos complexos
                    reader = csv.reader(infile,
                                       delimiter=',',
                                       quotechar='"',
                                       doublequote=True,
                                       skipinitialspace=True)

                    for row_idx, row in enumerate(reader):
                        # Primeira linha de cada arquivo é o cabeçalho
                        if row_idx == 0:
                            if not header_written:
                                # Escrever cabeçalho apenas uma vez
                                # Configurar writer com quoting adequado
                                writer = csv.writer(outfile,
                                                   delimiter=',',
                                                   quotechar='"',
                                                   quoting=csv.QUOTE_MINIMAL,
                                                   doublequote=True,
                                                   lineterminator='\n')
                                writer.writerow(row)
                                header_written = True
                            continue

                        # Escrever dados (ignorar linhas completamente vazias)
                        if writer and any(field.strip() for field in row):
                            writer.writerow(row)
                            total_rows += 1

            except Exception as e:
                error_msg = f"ERRO ao processar {csv_file}: {e}"
                print(f"  {error_msg}")
                errors.append(error_msg)
                continue

    print(f"\n✓ Compilação concluída!")
    print(f"  Arquivos processados: {len(csv_files)}")
    print(f"  Total de linhas de dados: {total_rows}")
    print(f"  Arquivo gerado: {output_file}")

    if errors:
        print(f"\n⚠ Erros encontrados: {len(errors)}")
        for error in errors:
            print(f"  - {error}")

if __name__ == "__main__":
    compile_csvs()

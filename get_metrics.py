#! /usr/bin/env python

"""
Printa métricas de agregação dos relatórios presentes na pasta `logs/`.
"""

import glob
import os
import re

import numpy as np


def parse_report(file_path):
    """
    Lê um relatório e extrai as métricas:
    - Número de linhas processadas
    - Tempo total gasto (em segundos)
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    num_lines = 0
    time_elapsed = 0.0

    for line in content.splitlines():
        if line.startswith("Number of processed rows:"):
            match = re.search(r"\d+", line)
            if match:
                num_lines = int(match.group())
        elif line.startswith("Total elapsed time:"):
            match = re.search(r"[\d.]+", line)
            if match:
                time_elapsed = float(match.group())

    return num_lines, time_elapsed


def aggregate_reports(log_folder):
    """
    Processa todos os relatórios na pasta 'logs/' e calcula estatísticas globais.
    """
    report_files = glob.glob(os.path.join(log_folder, "report_*.txt"))

    data = []

    for file in report_files:
        num_lines, time_elapsed = parse_report(file)
        data.append((num_lines, time_elapsed))

    # Caso não haja relatórios
    if not data:
        return None

    linhas, tempos = zip(*data)

    stats = {
        "total_files": len(data),
        "total_rows": sum(linhas),
        "avg_rows": np.mean(linhas),
        "std_rows": np.std(linhas),
        "avg_time": np.mean(tempos),
        "std_time": np.std(tempos),
        "total_time": sum(tempos),
        "correlation": np.corrcoef(linhas, tempos)[0, 1] if len(data) > 1 else None,
    }

    return stats


if __name__ == "__main__":
    log_folder = "logs"
    stats = aggregate_reports(log_folder)

    if stats:
        print("=== General Statistics ===")
        print(f"Processed files: {stats['total_files']}")
        print(f"Total processed rows: {stats['total_rows']}")
        print(
            f"Average rows per file: {stats['avg_rows']:.2f} ± {stats['std_rows']:.2f}"
        )
        print(f"Total elapsed time: {stats['total_time']:.2f} seconds")
        print(
            f"Average time per file: {stats['avg_time']:.2f} ± {stats['std_time']:.2f} seconds"
        )
        if stats["correlation"] is not None:
            print(
                f"Pearson correlation between processed rows and elapsed time: {stats['correlation']:.3f}"
            )

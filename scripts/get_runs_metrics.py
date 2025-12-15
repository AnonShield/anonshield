#!/usr/bin/env python3

"""
Coleta métricas de agregação do script principal ao longo de várias execuções.
Salva os resultados em um CSV com nome definido pela variável `CSV_OUT`.

Leva um argumento em linha de comando, salvo em `TEST_FILES`, com o caminho
dos arquivos de teste a serem processados.
"""

import csv
import glob
import os
import re
import subprocess
import time
import sys

# Quantidade de runs
NUM_RUNS = 10

# Diretório onde o anon.py grava os relatórios
REPORT_DIR = "logs"

# CSV de saída
script_name = os.path.splitext(os.path.basename(__file__))[0]
CSV_OUT = os.path.join("output", script_name, "metrics_runs.csv")


def collect_run_metrics(run_id, test_files, cmd_base):
    """
    Executa uma run completa (conjunto de teste), aguarda os relatórios,
    extrai tempo e tickets de cada relatório e retorna um dict com:
      - número da run
      - total de tickets
      - tempo total (s)
      - tempo médio por arquivo (s)
      - tempo médio por ticket (s)
    """
    print(f"\n=== Starting run {run_id}/{NUM_RUNS} ===")

    per_file_times = []
    total_tickets = 0

    for idx, file in enumerate(test_files, start=1):
        print(f"[Run {run_id}] Processing file {idx}/{len(test_files)}: {file}")
        # dispara o anon.py e deixa stdout/stderr no console
        try:
            subprocess.run(cmd_base + [file], check=True)
        except subprocess.CalledProcessError as e:
            print(f"[Run {run_id}] ⚠️ Error in {file}: {e}")

        # nome do relatório gerado
        base, ext = os.path.splitext(os.path.basename(file))
        report_file = os.path.join(REPORT_DIR, f"report_{base}_{ext[1:]}.txt")

        # espera até o relatório existir (timeout 10 min por arquivo)
        deadline = time.time() + 600
        while not os.path.exists(report_file) and time.time() < deadline:
            time.sleep(0.5)
        if not os.path.exists(report_file):
            print(f"[Run {run_id}] ⚠️ Report missing: {report_file}")
            # fallback: .docx = 1 ticket, 0s; outros = 0 ticket, 0s
            tickets = 1 if ext.lower() == ".docx" else 0
            per_file_times.append(0.0)
            total_tickets += tickets
            continue

        # lê e extrai métricas
        with open(report_file, encoding="utf-8") as f:
            content = f.read()
        m_lines = re.search(r"Number of processed rows:\s*(\d+)", content)
        m_time = re.search(r"Total elapsed time:\s*([\d.]+)", content)

        tickets = (
            int(m_lines.group(1)) if m_lines else (1 if ext.lower() == ".docx" else 0)
        )
        time_spent = float(m_time.group(1)) if m_time else 0.0

        per_file_times.append(time_spent)
        total_tickets += tickets

        print(f"[Run {run_id}] → tickets: {tickets}, time: {time_spent:.2f}s")

    # agrega métricas da run
    total_time = sum(per_file_times)
    avg_file = total_time / len(per_file_times) if per_file_times else 0.0
    avg_ticket = total_time / total_tickets if total_tickets else 0.0

    print(
        f"[Run {run_id}] ✔️ Completed: total_time={total_time:.2f}s, "
        f"total_tickets={total_tickets}, avg_file={avg_file:.2f}s, "
        f"avg_ticket={avg_ticket:.2f}s"
    )

    return {
        "run": run_id,
        "total_tickets": total_tickets,
        "total_time_s": round(total_time, 2),
        "avg_time_per_file": round(avg_file, 2),
        "avg_time_per_ticket": round(avg_ticket, 2),
    }


def main_logic(test_dir):
    """The main logic of the script."""
    # Arquivos de teste (sem a barra no final)
    test_files = glob.glob(f"{test_dir}/*")

    # Comando base para rodar o anon
    # Assumes CWD is project root
    cmd_base = ["uv", "run", "python", "anon.py"]

    # Garante que o diretório de saída exista
    os.makedirs(os.path.dirname(CSV_OUT), exist_ok=True)

    # Verifica se o CSV já existe
    first_time = not os.path.exists(CSV_OUT)

    # Abre em modo append
    with open(CSV_OUT, "a", newline="", encoding="utf-8") as csvf:
        writer = csv.DictWriter(
            csvf,
            fieldnames=[
                "Run",
                "Total Tickets",
                "Total Time (s)",
                "Average Time per File (s)",
                "Average Time per Ticket (s)",
            ],
        )
        # Se for a primeira vez, escreve o cabeçalho
        if first_time:
            writer.writeheader()

        # Executa as runs sequencialmente
        for run_id in range(1, NUM_RUNS + 1):
            metrics = collect_run_metrics(run_id, test_files, cmd_base)
            writer.writerow(
                {
                    "Run": metrics["run"],
                    "Total Tickets": metrics["total_tickets"],
                    "Total Time (s)": metrics["total_time_s"],
                    "Average Time per File (s)": metrics["avg_time_per_file"],
                    "Average Time per Ticket (s)": metrics["avg_time_per_ticket"],
                }
            )
            csvf.flush()
            print(f"[Main] Run {run_id} row added to CSV.")

    print(f"\n✅ All {NUM_RUNS} runs completed. Metrics in: {CSV_OUT}")

def main():
    """Parses arguments and runs the main logic."""
    if len(sys.argv) < 2:
        print("Use: python get_runs_metrics.py <tests_path>")
        sys.exit(1)

    test_dir = sys.argv[1].rstrip(os.sep)
    if not os.path.isdir(test_dir):
        print(f"Error: '{test_dir}' is not a valid directory.")
        sys.exit(1)
    
    main_logic(test_dir)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Script Automático de Geração de Relatório de Benchmarks

Gera documento MD completo com:
- Estatísticas de todos os datasets
- Estimativas de tempo
- Links para gráficos
- Overhead real + slope calculado

Uso:
    python generate_analysis_report.py [--session SESSION_DIR] [--output OUTPUT.md]
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
from scipy import stats

class BenchmarkReportGenerator:
    def __init__(self, session_dir: Path):
        self.session_dir = Path(session_dir)
        self.datasets = []
        self.overhead_real = {}
        self.slopes = {}

    def discover_datasets(self):
        """Descobre todos os datasets na sessão."""
        for dataset_dir in sorted(self.session_dir.iterdir()):
            if not dataset_dir.is_dir():
                continue

            csv_file = dataset_dir / "benchmark_results.csv"
            if not csv_file.exists():
                continue

            self.datasets.append({
                'name': dataset_dir.name,
                'path': dataset_dir,
                'csv': csv_file,
                'analysis': dataset_dir / "analysis"
            })

        print(f"✓ Encontrados {len(self.datasets)} datasets")

    def load_overhead_real(self):
        """Carrega overhead real do dataset de calibração."""
        for ds in self.datasets:
            if 'overhead' in ds['name'].lower() or 'calibration' in ds['name'].lower():
                df = pd.read_csv(ds['csv'])

                for version in df['version'].unique():
                    for strategy in df[df['version'] == version]['strategy'].unique():
                        data = df[(df['version'] == version) & (df['strategy'] == strategy)]
                        self.overhead_real[(version, strategy)] = data['wall_clock_time_sec'].mean()

                print(f"✓ Overhead real carregado: {len(self.overhead_real)} combinações")
                return

    def calculate_slopes(self):
        """Calcula slopes da regressão para cada versão/estratégia."""
        for ds in self.datasets:
            if 'regression' in ds['name'].lower():
                df = pd.read_csv(ds['csv'])

                for ext in df['file_extension'].unique():
                    df_format = df[df['file_extension'] == ext].copy()

                    for version in df_format['version'].unique():
                        for strategy in df_format[df_format['version'] == version]['strategy'].unique():
                            data = df_format[(df_format['version'] == version) &
                                           (df_format['strategy'] == strategy)]

                            if len(data) >= 3:
                                x = data['file_size_mb'].values
                                y = data['wall_clock_time_sec'].values

                                slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

                                key = (version, strategy, ext)
                                self.slopes[key] = {
                                    'slope': slope,
                                    'r2': r_value ** 2,
                                    'n': len(data)
                                }

                print(f"✓ Slopes calculados: {len(self.slopes)} combinações")
                return

    def estimate_time(self, version, strategy, ext, size_mb):
        """Estima tempo de processamento."""
        overhead_key = (version, strategy)
        slope_key = (version, strategy, ext)

        if overhead_key not in self.overhead_real or slope_key not in self.slopes:
            return None

        overhead = self.overhead_real[overhead_key]
        slope = self.slopes[slope_key]['slope']

        return overhead + (slope * size_mb)

    def generate_markdown(self, output_path: Path):
        """Gera o documento markdown completo."""
        lines = []

        # Cabeçalho
        lines.append("# Análise de Benchmarks - Relatório Automático")
        lines.append(f"\n**Gerado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Sessão:** {self.session_dir.name}")
        lines.append(f"**Total de Datasets:** {len(self.datasets)}")
        lines.append("\n---\n")

        # Sumário executivo
        lines.append("## 📋 Sumário Executivo\n")
        lines.append("| Dataset | Registros | Versões | Estratégias | Formatos | Gráficos |")
        lines.append("|---------|-----------|---------|-------------|----------|----------|")

        for ds in self.datasets:
            df = pd.read_csv(ds['csv'])
            n_graphs = len(list(ds['analysis'].glob("*.png"))) if ds['analysis'].exists() else 0

            versions = ', '.join(map(str, sorted(df['version'].unique())))
            strategies = df['strategy'].nunique() if 'strategy' in df.columns else 0
            formats = df['file_extension'].nunique() if 'file_extension' in df.columns else 0

            lines.append(f"| {ds['name'][:30]} | {len(df)} | {versions} | {strategies} | {formats} | {n_graphs} |")

        lines.append("\n---\n")

        # Datasets detalhados
        for idx, ds in enumerate(self.datasets, 1):
            lines.extend(self._generate_dataset_section(idx, ds))

        # Estimativas
        if self.overhead_real and self.slopes:
            lines.extend(self._generate_estimates_section())

        # Overhead e slopes
        lines.extend(self._generate_methodology_section())

        # Salvar
        output_path.write_text('\n'.join(lines))
        print(f"\n✓ Relatório gerado: {output_path}")
        print(f"  Total de linhas: {len(lines)}")

    def _generate_dataset_section(self, idx, ds):
        """Gera seção de um dataset."""
        lines = []
        df = pd.read_csv(ds['csv'])

        lines.append(f"## {idx}. {ds['name']}")
        lines.append(f"\n**Registros:** {len(df)}")
        lines.append(f"**Formato:** CSV")

        if 'version' in df.columns:
            lines.append(f"**Versões:** {', '.join(map(str, sorted(df['version'].unique())))}")
        if 'strategy' in df.columns:
            lines.append(f"**Estratégias:** {', '.join(sorted(df['strategy'].unique()))}")
        if 'file_extension' in df.columns:
            lines.append(f"**Formatos de arquivo:** {', '.join(sorted(df['file_extension'].unique()))}")

        # Estatísticas por versão e estratégia
        if 'version' in df.columns and 'strategy' in df.columns:
            lines.append("\n### Tempo de Execução por Versão e Estratégia\n")
            lines.append("| Versão | Estratégia | Tempo Médio (s) | Desvio | N |")
            lines.append("|--------|------------|-----------------|--------|---|")

            stats_df = df.groupby(['version', 'strategy']).agg({
                'wall_clock_time_sec': ['mean', 'std', 'count']
            }).round(2)

            for (v, s), row in stats_df.iterrows():
                mean = row[('wall_clock_time_sec', 'mean')]
                std = row[('wall_clock_time_sec', 'std')]
                count = int(row[('wall_clock_time_sec', 'count')])
                lines.append(f"| {v} | {s} | {mean:.2f} | {std:.2f} | {count} |")

        # Throughput por formato
        if 'file_extension' in df.columns and 'throughput_mb_per_sec' in df.columns:
            lines.append("\n### Throughput por Formato (KB/s)\n")

            if 'version' in df.columns and 'strategy' in df.columns:
                for version in sorted(df['version'].unique()):
                    lines.append(f"\n#### Versão {version}\n")

                    version_data = df[df['version'] == version]

                    for strategy in sorted(version_data['strategy'].unique()):
                        lines.append(f"\n**{strategy}:**\n")

                        strategy_data = version_data[version_data['strategy'] == strategy]
                        format_stats = strategy_data.groupby('file_extension').agg({
                            'throughput_mb_per_sec': 'mean'
                        })

                        for fmt, row in format_stats.iterrows():
                            kb_s = row['throughput_mb_per_sec'] * 1024
                            lines.append(f"- {fmt}: {kb_s:.2f} KB/s")

        # Links para gráficos
        if ds['analysis'].exists():
            graphs = sorted(ds['analysis'].glob("*.png"))
            if graphs:
                lines.append(f"\n### Visualizações ({len(graphs)} gráficos)\n")
                lines.append(f"**Localização:** `{ds['analysis'].relative_to(self.session_dir.parent.parent)}/`\n")

                for graph in graphs:
                    lines.append(f"- `{graph.name}`")

        lines.append("\n---\n")
        return lines

    def _generate_estimates_section(self):
        """Gera seção de estimativas."""
        lines = []
        lines.append("## 🎯 Estimativas de Tempo\n")
        lines.append("**Metodologia:** `tempo = overhead_real + (slope × tamanho)`\n")

        # Arquivos para estimar (hardcoded, pode ser parametrizado)
        targets = [
            ("vulnnet_scans_openvas_compilado.csv", 9.2, '.csv'),
            ("cve_dataset_anonimizados_stratified.csv", 248.0, '.csv'),
            ("cve_dataset_anonimizados_stratified.json", 445.0, '.json'),
        ]

        for filename, size_mb, ext in targets:
            lines.append(f"\n### {filename} ({size_mb} MB)\n")
            lines.append("| Versão | Estratégia | Overhead (s) | Slope (s/MB) | Tempo Estimado |")
            lines.append("|--------|------------|--------------|--------------|----------------|")

            for (v, s), overhead in sorted(self.overhead_real.items()):
                slope_key = (v, s, ext)
                if slope_key in self.slopes:
                    slope = self.slopes[slope_key]['slope']
                    time = overhead + (slope * size_mb)

                    if time < 3600:
                        time_str = f"{time:.1f}s ({time/60:.1f} min)"
                    else:
                        time_str = f"{time:.0f}s ({time/3600:.2f}h)"

                    lines.append(f"| {v} | {s} | {overhead:.2f} | {slope:.2f} | {time_str} |")

        lines.append("\n---\n")
        return lines

    def _generate_methodology_section(self):
        """Gera seção de metodologia."""
        lines = []
        lines.append("## 📐 Metodologia\n")

        lines.append("### Overhead Real (medido)\n")
        lines.append("| Versão | Estratégia | Overhead (s) |")
        lines.append("|--------|------------|--------------|")
        for (v, s), oh in sorted(self.overhead_real.items()):
            lines.append(f"| {v} | {s} | {oh:.3f} |")

        lines.append("\n### Slopes Calculados (regressão linear)\n")
        lines.append("| Versão | Estratégia | Formato | Slope (s/MB) | R² | N |")
        lines.append("|--------|------------|---------|--------------|----|----|")
        for (v, s, ext), data in sorted(self.slopes.items()):
            lines.append(f"| {v} | {s} | {ext} | {data['slope']:.2f} | {data['r2']:.3f} | {data['n']} |")

        lines.append("\n---\n")
        lines.append(f"\n**Gerado automaticamente em:** {datetime.now()}")

        return lines


def main():
    parser = argparse.ArgumentParser(description="Gera relatório automático de benchmarks")
    parser.add_argument(
        '--session',
        default='benchmark/orchestrated_results/session_20260208_005447',
        help='Diretório da sessão de benchmarks'
    )
    parser.add_argument(
        '--output',
        default='benchmark/ANALISE_BENCHMARKS_AUTO.md',
        help='Arquivo de saída'
    )

    args = parser.parse_args()

    print("="*70)
    print("🔧 GERADOR AUTOMÁTICO DE RELATÓRIO DE BENCHMARKS")
    print("="*70)

    generator = BenchmarkReportGenerator(args.session)

    print("\n1️⃣ Descobrindo datasets...")
    generator.discover_datasets()

    if not generator.datasets:
        print("❌ Nenhum dataset encontrado!")
        return 1

    print("\n2️⃣ Carregando overhead real...")
    generator.load_overhead_real()

    print("\n3️⃣ Calculando slopes...")
    generator.calculate_slopes()

    print("\n4️⃣ Gerando markdown...")
    output_path = Path(args.output)
    generator.generate_markdown(output_path)

    print("\n" + "="*70)
    print("✅ CONCLUÍDO!")
    print("="*70)
    print(f"\n📄 Relatório: {output_path}")
    print(f"📊 Datasets analisados: {len(generator.datasets)}")
    print(f"🔢 Overhead real: {len(generator.overhead_real)} combinações")
    print(f"📈 Slopes: {len(generator.slopes)} combinações")

    return 0


if __name__ == "__main__":
    sys.exit(main())

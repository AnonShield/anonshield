#!/usr/bin/env python3
"""
Análise Avançada de Benchmark - AnonShield Tool
Análise de nível senior com insights de performance, eficiência e custos
Segmentação por versão e estratégia (fast, balanced, presidio)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# Configuração de visualização
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10

class BenchmarkAnalyzer:
    """Analisador avançado de resultados de benchmark"""
    
    def __init__(self, csv_path: str):
        self.df = pd.read_csv(csv_path)
        self.df_success = self.df[self.df['status'] == 'SUCCESS'].copy()
        
        # Criar coluna combinada version_strategy para análises detalhadas
        self.df_success['version_strategy'] = self.df_success.apply(
            lambda row: f"v{row['version']}-{row['strategy']}" if pd.notna(row.get('strategy')) else f"v{row['version']}-default",
            axis=1
        )
        
        self.output_dir = Path('benchmark/results/analysis')
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
    def generate_executive_summary(self) -> str:
        """Gera sumário executivo com KPIs principais"""
        summary = []
        summary.append("=" * 80)
        summary.append("EXECUTIVE SUMMARY - BENCHMARK ANALYSIS")
        summary.append("=" * 80)
        summary.append("")
        
        # Overview geral
        total_runs = len(self.df)
        success_runs = len(self.df_success)
        skipped_runs = len(self.df[self.df['status'] == 'SKIPPED'])
        
        summary.append(f"📊 Total de Execuções: {total_runs}")
        summary.append(f"✅ Sucessos: {success_runs} ({success_runs/total_runs*100:.1f}%)")
        summary.append(f"⏭️  Skipped: {skipped_runs} ({skipped_runs/total_runs*100:.1f}%)")
        summary.append("")
        
        # Análise por versão e estratégia
        summary.append("🔍 PERFORMANCE POR VERSÃO E ESTRATÉGIA:")
        summary.append("-" * 80)
        
        for version in sorted(self.df_success['version'].unique()):
            v_data = self.df_success[self.df_success['version'] == version]
            summary.append(f"\n📌 Versão {version}:")
            summary.append(f"   ⏱️  Tempo médio: {v_data['wall_clock_time_sec'].mean():.2f}s (±{v_data['wall_clock_time_sec'].std():.2f}s)")
            summary.append(f"   💾 Memória pico média: {v_data['peak_memory_mb'].mean():.0f} MB")
            summary.append(f"   ⚡ Throughput médio: {v_data['throughput_mb_per_sec'].mean():.4f} MB/s")
            summary.append(f"   🖥️  CPU médio: {v_data['cpu_percent'].mean():.1f}%")
            
            # Análise por estratégia se existir
            if 'strategy' in v_data.columns and v_data['strategy'].notna().any():
                strategies = v_data['strategy'].unique()
                if len(strategies) > 1 or (len(strategies) == 1 and strategies[0] != 'default'):
                    summary.append(f"   📊 Estratégias:")
                    for strategy in sorted(strategies):
                        s_data = v_data[v_data['strategy'] == strategy]
                        summary.append(f"      • {strategy}: {s_data['wall_clock_time_sec'].mean():.2f}s, {s_data['peak_memory_mb'].mean():.0f}MB, {s_data['throughput_mb_per_sec'].mean():.4f}MB/s")
        
        summary.append("")
        summary.append("=" * 80)
        return "\n".join(summary)
    
    def analyze_version_comparison(self) -> pd.DataFrame:
        """Análise comparativa detalhada entre versões"""
        print("\n📊 ANÁLISE COMPARATIVA ENTRE VERSÕES")
        print("=" * 80)
        
        comparison = self.df_success.groupby('version').agg({
            'wall_clock_time_sec': ['mean', 'median', 'std', 'min', 'max'],
            'peak_memory_mb': ['mean', 'median', 'std', 'min', 'max'],
            'throughput_mb_per_sec': ['mean', 'median', 'std'],
            'cpu_percent': ['mean', 'max'],
            'file_name': 'count'
        }).round(2)
        
        comparison.columns = ['_'.join(col).strip() for col in comparison.columns.values]
        
        # Calcular melhorias relativas
        print("\n💡 INSIGHTS DE PERFORMANCE:")
        print("-" * 80)
        
        versions = sorted(self.df_success['version'].unique())
        for i, version in enumerate(versions):
            v_data = self.df_success[self.df_success['version'] == version]
            print(f"\n🔹 Versão {version}:")
            print(f"   Tempo médio: {v_data['wall_clock_time_sec'].mean():.2f}s")
            print(f"   Throughput: {v_data['throughput_mb_per_sec'].mean():.4f} MB/s")
            print(f"   Eficiência memória: {v_data['memory_per_kb_input'].mean():.0f} KB/KB")
            
            if i > 0:
                prev_version = versions[i-1]
                prev_data = self.df_success[self.df_success['version'] == prev_version]
                
                time_change = ((v_data['wall_clock_time_sec'].mean() - prev_data['wall_clock_time_sec'].mean()) 
                              / prev_data['wall_clock_time_sec'].mean() * 100)
                memory_change = ((v_data['peak_memory_mb'].mean() - prev_data['peak_memory_mb'].mean()) 
                                / prev_data['peak_memory_mb'].mean() * 100)
                
                print(f"   📈 vs v{prev_version}:")
                print(f"      Tempo: {time_change:+.1f}%")
                print(f"      Memória: {memory_change:+.1f}%")
        
        return comparison
    
    def analyze_strategy_performance(self):
        """Análise de performance por estratégia (todas as versões)"""
        print("\n\n🎯 ANÁLISE DETALHADA DE ESTRATÉGIAS")
        print("=" * 80)
        
        # Análise por version_strategy
        strategy_stats = self.df_success.groupby('version_strategy').agg({
            'wall_clock_time_sec': ['count', 'mean', 'std', 'min', 'max'],
            'peak_memory_mb': ['mean', 'std'],
            'throughput_mb_per_sec': ['mean', 'std'],
            'cpu_percent': ['mean', 'max'],
            'memory_per_kb_input': ['mean']
        }).round(2)
        
        strategy_stats.columns = ['_'.join(col).strip() for col in strategy_stats.columns.values]
        
        print("\n📊 Performance por Versão e Estratégia:")
        print(strategy_stats)
        
        # Análise específica v3.0
        v3_data = self.df_success[self.df_success['version'] == '3.0']
        
        if len(v3_data) > 0 and 'strategy' in v3_data.columns:
            print("\n\n🔍 ANÁLISE DETALHADA - VERSÃO 3.0")
            print("-" * 80)
            
            strategies = v3_data.groupby('strategy').agg({
                'wall_clock_time_sec': ['mean', 'std', 'min', 'max'],
                'peak_memory_mb': ['mean', 'std'],
                'throughput_mb_per_sec': ['mean', 'std'],
                'cpu_percent': ['mean', 'max'],
                'file_name': 'count'
            }).round(2)
            
            print("\n📊 Comparação de Estratégias v3.0:")
            print(strategies)
            
            # Comparação percentual entre estratégias
            print("\n\n📈 COMPARAÇÃO PERCENTUAL (v3.0):")
            print("-" * 80)
            
            strategies_list = sorted(v3_data['strategy'].unique())
            if len(strategies_list) > 1:
                base_strategy = strategies_list[0]
                base_data = v3_data[v3_data['strategy'] == base_strategy]
                
                for strategy in strategies_list[1:]:
                    s_data = v3_data[v3_data['strategy'] == strategy]
                    
                    time_diff = ((s_data['wall_clock_time_sec'].mean() - base_data['wall_clock_time_sec'].mean()) 
                                / base_data['wall_clock_time_sec'].mean() * 100)
                    mem_diff = ((s_data['peak_memory_mb'].mean() - base_data['peak_memory_mb'].mean()) 
                               / base_data['peak_memory_mb'].mean() * 100)
                    throughput_diff = ((s_data['throughput_mb_per_sec'].mean() - base_data['throughput_mb_per_sec'].mean()) 
                                      / base_data['throughput_mb_per_sec'].mean() * 100)
                    
                    print(f"\n'{strategy}' vs '{base_strategy}':")
                    print(f"  Tempo: {time_diff:+.1f}%")
                    print(f"  Memória: {mem_diff:+.1f}%")
                    print(f"  Throughput: {throughput_diff:+.1f}%")
            
            # Recomendações
            print("\n\n💡 RECOMENDAÇÕES POR CASO DE USO:")
            print("-" * 80)
            
            fastest = v3_data.groupby('strategy')['wall_clock_time_sec'].mean().idxmin()
            most_efficient_mem = v3_data.groupby('strategy')['peak_memory_mb'].mean().idxmin()
            highest_throughput = v3_data.groupby('strategy')['throughput_mb_per_sec'].mean().idxmax()
            lowest_cpu = v3_data.groupby('strategy')['cpu_percent'].mean().idxmin()
            
            print(f"\n🚀 Melhor velocidade: '{fastest}'")
            print(f"💾 Menor uso de memória: '{most_efficient_mem}'")
            print(f"⚡ Maior throughput: '{highest_throughput}'")
            print(f"🖥️  Menor uso de CPU: '{lowest_cpu}'")
        
    def analyze_file_type_performance(self):
        """Análise de performance por tipo de arquivo"""
        print("\n\n📄 ANÁLISE POR TIPO DE ARQUIVO")
        print("=" * 80)
        
        file_stats = self.df_success.groupby('file_extension').agg({
            'wall_clock_time_sec': ['mean', 'std', 'count'],
            'peak_memory_mb': ['mean'],
            'throughput_mb_per_sec': ['mean'],
            'file_size_mb': ['mean']
        }).round(3)
        
        file_stats.columns = ['_'.join(col).strip() for col in file_stats.columns.values]
        print("\n📊 Performance por Extensão:")
        print(file_stats.sort_values('wall_clock_time_sec_mean'))
        
        # Identificar arquivos problemáticos
        print("\n\n⚠️  ARQUIVOS MAIS CUSTOSOS:")
        print("-" * 80)
        slowest = self.df_success.nlargest(5, 'wall_clock_time_sec')[
            ['version', 'strategy', 'file_name', 'file_size_mb', 'wall_clock_time_sec', 'peak_memory_mb']
        ]
        print(slowest.to_string(index=False))
        
    def analyze_scaling_characteristics(self):
        """Análise de escalabilidade com tamanho de arquivo"""
        print("\n\n📈 ANÁLISE DE ESCALABILIDADE")
        print("=" * 80)
        
        # Correlação entre tamanho e tempo
        for version in sorted(self.df_success['version'].unique()):
            v_data = self.df_success[self.df_success['version'] == version]
            
            if len(v_data) > 3:
                corr_time = v_data['file_size_mb'].corr(v_data['wall_clock_time_sec'])
                corr_memory = v_data['file_size_mb'].corr(v_data['peak_memory_mb'])
                
                print(f"\n📌 Versão {version}:")
                print(f"   Correlação tamanho x tempo: {corr_time:.3f}")
                print(f"   Correlação tamanho x memória: {corr_memory:.3f}")
                
                # Eficiência por MB
                efficiency = v_data['wall_clock_time_sec'] / v_data['file_size_mb']
                print(f"   Tempo médio por MB: {efficiency.mean():.2f}s")
        
    def create_visualizations(self):
        """Cria visualizações avançadas"""
        print("\n\n📊 GERANDO VISUALIZAÇÕES...")
        print("=" * 80)
        
        # 1. Comparação de Performance por Versão e Estratégia
        fig, axes = plt.subplots(2, 2, figsize=(18, 12))
        fig.suptitle('Análise Comparativa de Performance - Por Versão e Estratégia', fontsize=16, fontweight='bold')
        
        # Tempo de execução
        self.df_success.boxplot(column='wall_clock_time_sec', by='version_strategy', ax=axes[0, 0])
        axes[0, 0].set_title('Tempo de Execução por Versão e Estratégia')
        axes[0, 0].set_xlabel('Versão-Estratégia')
        axes[0, 0].set_ylabel('Tempo (segundos)')
        plt.sca(axes[0, 0])
        plt.xticks(rotation=45, ha='right')
        
        # Memória pico
        self.df_success.boxplot(column='peak_memory_mb', by='version_strategy', ax=axes[0, 1])
        axes[0, 1].set_title('Memória Pico por Versão e Estratégia')
        axes[0, 1].set_xlabel('Versão-Estratégia')
        axes[0, 1].set_ylabel('Memória (MB)')
        plt.sca(axes[0, 1])
        plt.xticks(rotation=45, ha='right')
        
        # Throughput
        self.df_success.boxplot(column='throughput_mb_per_sec', by='version_strategy', ax=axes[1, 0])
        axes[1, 0].set_title('Throughput por Versão e Estratégia')
        axes[1, 0].set_xlabel('Versão-Estratégia')
        axes[1, 0].set_ylabel('Throughput (MB/s)')
        plt.sca(axes[1, 0])
        plt.xticks(rotation=45, ha='right')
        
        # CPU
        self.df_success.boxplot(column='cpu_percent', by='version_strategy', ax=axes[1, 1])
        axes[1, 1].set_title('Uso de CPU por Versão e Estratégia')
        axes[1, 1].set_xlabel('Versão-Estratégia')
        axes[1, 1].set_ylabel('CPU (%)')
        plt.sca(axes[1, 1])
        plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'version_strategy_comparison.png', dpi=300, bbox_inches='tight')
        print(f"✅ Salvo: {self.output_dir / 'version_strategy_comparison.png'}")
        
        # 2. Análise de Estratégias (v3.0)
        v3_data = self.df_success[self.df_success['version'] == '3.0']
        if len(v3_data) > 0:
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle('Análise de Estratégias - Versão 3.0', fontsize=16, fontweight='bold')
            
            v3_data.boxplot(column='wall_clock_time_sec', by='strategy', ax=axes[0, 0])
            axes[0, 0].set_title('Tempo por Estratégia')
            axes[0, 0].set_ylabel('Tempo (s)')
            
            v3_data.boxplot(column='peak_memory_mb', by='strategy', ax=axes[0, 1])
            axes[0, 1].set_title('Memória por Estratégia')
            axes[0, 1].set_ylabel('Memória (MB)')
            
            v3_data.boxplot(column='throughput_mb_per_sec', by='strategy', ax=axes[1, 0])
            axes[1, 0].set_title('Throughput por Estratégia')
            axes[1, 0].set_ylabel('Throughput (MB/s)')
            
            v3_data.boxplot(column='cpu_percent', by='strategy', ax=axes[1, 1])
            axes[1, 1].set_title('CPU por Estratégia')
            axes[1, 1].set_ylabel('CPU (%)')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'strategy_comparison.png', dpi=300, bbox_inches='tight')
            print(f"✅ Salvo: {self.output_dir / 'strategy_comparison.png'}")
        
        # 3. Escalabilidade - Tamanho vs Performance
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        fig.suptitle('Análise de Escalabilidade', fontsize=16, fontweight='bold')
        
        for version in sorted(self.df_success['version'].unique()):
            v_data = self.df_success[self.df_success['version'] == version]
            axes[0].scatter(v_data['file_size_mb'], v_data['wall_clock_time_sec'], 
                          alpha=0.6, s=100, label=f'v{version}')
            axes[1].scatter(v_data['file_size_mb'], v_data['peak_memory_mb'], 
                          alpha=0.6, s=100, label=f'v{version}')
        
        axes[0].set_xlabel('Tamanho do Arquivo (MB)')
        axes[0].set_ylabel('Tempo de Execução (s)')
        axes[0].set_title('Tamanho vs Tempo')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        axes[1].set_xlabel('Tamanho do Arquivo (MB)')
        axes[1].set_ylabel('Memória Pico (MB)')
        axes[1].set_title('Tamanho vs Memória')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'scalability_analysis.png', dpi=300, bbox_inches='tight')
        print(f"✅ Salvo: {self.output_dir / 'scalability_analysis.png'}")
        
        # 4. Heatmap de Eficiência por Versão-Estratégia
        fig, ax = plt.subplots(figsize=(16, 10))
        
        pivot_time = self.df_success.pivot_table(
            values='wall_clock_time_sec', 
            index='file_name', 
            columns='version_strategy', 
            aggfunc='mean'
        )
        
        sns.heatmap(pivot_time, annot=True, fmt='.1f', cmap='YlOrRd', ax=ax, cbar_kws={'label': 'Tempo (s)'})
        ax.set_title('Heatmap: Tempo de Execução por Arquivo, Versão e Estratégia', fontsize=14, fontweight='bold')
        ax.set_xlabel('Versão-Estratégia')
        ax.set_ylabel('Arquivo')
        plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'performance_heatmap.png', dpi=300, bbox_inches='tight')
        print(f"✅ Salvo: {self.output_dir / 'performance_heatmap.png'}")
        
        # 5. Throughput por tipo de arquivo e estratégia
        fig, ax = plt.subplots(figsize=(16, 8))
        
        throughput_by_ext = self.df_success.groupby(['file_extension', 'version_strategy'])['throughput_mb_per_sec'].mean().unstack()
        throughput_by_ext.plot(kind='bar', ax=ax, width=0.8)
        
        ax.set_title('Throughput Médio por Tipo de Arquivo, Versão e Estratégia', fontsize=14, fontweight='bold')
        ax.set_xlabel('Extensão do Arquivo')
        ax.set_ylabel('Throughput (MB/s)')
        ax.legend(title='Versão-Estratégia', bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3, axis='y')
        plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'throughput_by_filetype.png', dpi=300, bbox_inches='tight')
        print(f"✅ Salvo: {self.output_dir / 'throughput_by_filetype.png'}")
        
        # 6. Gráfico de barras comparativo - Estratégias v3.0
        v3_data = self.df_success[self.df_success['version'] == '3.0']
        if len(v3_data) > 0 and 'strategy' in v3_data.columns:
            fig, axes = plt.subplots(1, 3, figsize=(18, 6))
            fig.suptitle('Comparação de Estratégias - Versão 3.0', fontsize=16, fontweight='bold')
            
            strategy_summary = v3_data.groupby('strategy').agg({
                'wall_clock_time_sec': 'mean',
                'peak_memory_mb': 'mean',
                'throughput_mb_per_sec': 'mean'
            })
            
            strategy_summary['wall_clock_time_sec'].plot(kind='bar', ax=axes[0], color='steelblue')
            axes[0].set_title('Tempo Médio de Execução')
            axes[0].set_ylabel('Tempo (s)')
            axes[0].set_xlabel('Estratégia')
            axes[0].grid(True, alpha=0.3, axis='y')
            plt.setp(axes[0].xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            strategy_summary['peak_memory_mb'].plot(kind='bar', ax=axes[1], color='coral')
            axes[1].set_title('Memória Pico Média')
            axes[1].set_ylabel('Memória (MB)')
            axes[1].set_xlabel('Estratégia')
            axes[1].grid(True, alpha=0.3, axis='y')
            plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            strategy_summary['throughput_mb_per_sec'].plot(kind='bar', ax=axes[2], color='seagreen')
            axes[2].set_title('Throughput Médio')
            axes[2].set_ylabel('Throughput (MB/s)')
            axes[2].set_xlabel('Estratégia')
            axes[2].grid(True, alpha=0.3, axis='y')
            plt.setp(axes[2].xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            plt.tight_layout()
            plt.savefig(self.output_dir / 'v3_strategy_bars.png', dpi=300, bbox_inches='tight')
            print(f"✅ Salvo: {self.output_dir / 'v3_strategy_bars.png'}")
        
    def calculate_cost_analysis(self):
        """Análise de custo computacional"""
        print("\n\n💰 ANÁLISE DE CUSTO COMPUTACIONAL")
        print("=" * 80)
        
        # Assumindo custos hipotéticos de cloud (AWS/GCP/Azure)
        # CPU: $0.05/vCPU-hour
        # Memory: $0.005/GB-hour
        
        CPU_COST_PER_HOUR = 0.05
        MEMORY_COST_PER_GB_HOUR = 0.005
        
        print("\n📊 Estimativa de custo (cloud computing):")
        print("Premissas: CPU=$0.05/vCPU-hour, Memory=$0.005/GB-hour")
        print("-" * 80)
        
        for version in sorted(self.df_success['version'].unique()):
            v_data = self.df_success[self.df_success['version'] == version]
            
            # Calcular custo médio por execução
            avg_time_hours = v_data['wall_clock_time_sec'].mean() / 3600
            avg_memory_gb = v_data['peak_memory_mb'].mean() / 1024
            avg_cpu = v_data['cpu_percent'].mean() / 100  # vCPUs utilizados
            
            cpu_cost = avg_time_hours * avg_cpu * CPU_COST_PER_HOUR
            memory_cost = avg_time_hours * avg_memory_gb * MEMORY_COST_PER_GB_HOUR
            total_cost = cpu_cost + memory_cost
            
            print(f"\n📌 Versão {version}:")
            print(f"   Custo médio por execução: ${total_cost:.6f}")
            print(f"   CPU: ${cpu_cost:.6f}")
            print(f"   Memory: ${memory_cost:.6f}")
            print(f"   Custo por MB processado: ${total_cost / v_data['file_size_mb'].mean():.6f}/MB")
        
    def export_detailed_report(self):
        """Exporta relatório detalhado em CSV e texto"""
        print("\n\n📝 EXPORTANDO RELATÓRIOS DETALHADOS...")
        print("=" * 80)
        
        # Relatório por versão-estratégia
        version_strategy_report = self.df_success.groupby('version_strategy').agg({
            'wall_clock_time_sec': ['count', 'mean', 'std', 'min', 'max', 'median'],
            'peak_memory_mb': ['mean', 'std', 'min', 'max'],
            'throughput_mb_per_sec': ['mean', 'std', 'max'],
            'cpu_percent': ['mean', 'max'],
            'memory_per_kb_input': ['mean', 'std']
        }).round(3)
        
        version_strategy_report.to_csv(self.output_dir / 'version_strategy_summary.csv')
        print(f"✅ Salvo: {self.output_dir / 'version_strategy_summary.csv'}")
        
        # Relatório por versão (agregado)
        version_report = self.df_success.groupby('version').agg({
            'wall_clock_time_sec': ['count', 'mean', 'std', 'min', 'max', 'median'],
            'peak_memory_mb': ['mean', 'std', 'min', 'max'],
            'throughput_mb_per_sec': ['mean', 'std', 'max'],
            'cpu_percent': ['mean', 'max'],
            'memory_per_kb_input': ['mean', 'std']
        }).round(3)
        
        version_report.to_csv(self.output_dir / 'version_summary.csv')
        print(f"✅ Salvo: {self.output_dir / 'version_summary.csv'}")
        
        # Relatório por tipo de arquivo e estratégia
        filetype_report = self.df_success.groupby(['version_strategy', 'file_extension']).agg({
            'wall_clock_time_sec': ['mean', 'std'],
            'peak_memory_mb': ['mean'],
            'throughput_mb_per_sec': ['mean'],
            'file_size_mb': ['mean']
        }).round(3)
        
        filetype_report.to_csv(self.output_dir / 'filetype_strategy_summary.csv')
        print(f"✅ Salvo: {self.output_dir / 'filetype_strategy_summary.csv'}")
        
        # Relatório de estratégias (todas as versões)
        if 'strategy' in self.df_success.columns:
            strategy_full_report = self.df_success.groupby(['version', 'strategy']).agg({
                'wall_clock_time_sec': ['count', 'mean', 'std', 'min', 'max'],
                'peak_memory_mb': ['mean', 'std'],
                'throughput_mb_per_sec': ['mean', 'std'],
                'cpu_percent': ['mean', 'max']
            }).round(3)
            
            strategy_full_report.to_csv(self.output_dir / 'strategy_full_summary.csv')
            print(f"✅ Salvo: {self.output_dir / 'strategy_full_summary.csv'}")
        
    def run_complete_analysis(self):
        """Executa análise completa"""
        print("\n" + "🔬 INICIANDO ANÁLISE COMPLETA DE BENCHMARK" + "\n")
        
        # 1. Executive Summary
        summary = self.generate_executive_summary()
        print(summary)
        
        # 2. Comparação de versões
        version_comparison = self.analyze_version_comparison()
        
        # 3. Estratégias
        self.analyze_strategy_performance()
        
        # 4. Tipos de arquivo
        self.analyze_file_type_performance()
        
        # 5. Escalabilidade
        self.analyze_scaling_characteristics()
        
        # 6. Análise de custo
        self.calculate_cost_analysis()
        
        # 7. Visualizações
        self.create_visualizations()
        
        # 8. Exportar relatórios
        self.export_detailed_report()
        
        print("\n\n" + "=" * 80)
        print("✅ ANÁLISE COMPLETA FINALIZADA!")
        print(f"📁 Todos os arquivos salvos em: {self.output_dir}")
        print("=" * 80 + "\n")


def main():
    """Função principal"""
    csv_path = 'benchmark/results/benchmark_results.csv'
    
    try:
        analyzer = BenchmarkAnalyzer(csv_path)
        analyzer.run_complete_analysis()
        
    except FileNotFoundError:
        print(f"❌ Erro: Arquivo não encontrado: {csv_path}")
        print("Certifique-se de que o arquivo existe no caminho correto.")
    except Exception as e:
        print(f"❌ Erro durante a análise: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

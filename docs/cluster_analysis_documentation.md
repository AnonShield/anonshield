# Documentação: Análise e Otimização de Clusters de Entidades

Este documento detalha as ferramentas e a metodologia para analisar e otimizar o processo de clusterização de entidades, abordando o problema de granularidade dos clusters gerados.

## O Problema: Granularidade dos Clusters

O script `scripts/cluster_entities.py` utiliza o algoritmo HDBSCAN, que agrupa entidades com base na similaridade semântica de seus textos. No entanto, dependendo do modelo de embedding e da configuração dos parâmetros, os resultados podem ser:

1.  **Muito Granulares:** Muitos clusters pequenos são criados, separando conceitos que deveriam estar juntos (ex: `URL do Google` e `URL da AWS` em clusters diferentes, em vez de um único cluster `URL`).
2.  **Muito Genéricos:** Poucos clusters muito grandes são criados, agrupando entidades que não são semanticamente similares o suficiente.

Para resolver isso, foram implementadas ferramentas que permitem um ajuste fino através da experimentação com os hiperparâmetros do HDBSCAN.

## Hiperparâmetros de Ajuste

Existem dois parâmetros principais que controlam o comportamento da clusterização no script `cluster_entities.py`:

1.  `--min-cluster-size`:
    *   **O que faz:** Define o número mínimo de amostras (textos) que um agrupamento deve ter para ser considerado um cluster.
    *   **Efeito:** Valores maiores tendem a diminuir o número total de clusters, forçando-os a serem mais densos e significativos, ao custo de classificar mais pontos como *outliers* (ruído).

2.  `--cluster-selection-epsilon`:
    *   **O que faz:** Define uma distância de corte. Agrupamentos hierárquicos que se estendem por uma distância maior que este valor são divididos em clusters menores e mais densos.
    *   **Efeito:** É a ferramenta ideal para "quebrar" clusters grandes e esparsos. Um valor **menor** de epsilon resulta em uma divisão mais agressiva, criando **mais** clusters, porém mais específicos e coesos. Um valor de `0.0` (padrão) desativa efetivamente essa divisão baseada em distância.

## Ferramenta de Automação: `test_cluster_hyperparameters.py`

Para facilitar a busca pela configuração ideal, o script `scripts/test_cluster_hyperparameters.py` foi criado. Ele automatiza a execução do `cluster_entities.py` com múltiplas combinações de parâmetros.

### Uso do Script

O script é executado a partir da linha de comando e aceita os seguintes argumentos:

-   `file_path`: O caminho para o arquivo JSON ou JSONL contendo o mapa de entidades.
-   `--min-cluster-sizes`: (Opcional) Uma lista de um ou mais valores inteiros para testar o `min_cluster_size`. Padrão: `2 5 10`.
-   `--embedding-models`: (Opcional) Uma lista de um ou mais modelos da biblioteca `sentence-transformers` para testar. Padrão: `multi-qa-MiniLM-L6-cos-v1 all-MiniLM-L6-v2`.
-   `--epsilons`: (Opcional) Uma lista de um ou mais valores de ponto flutuante para testar o `cluster_selection_epsilon`. Padrão: `0.0`.
-   `--base-output-dir`: (Opcional) O diretório base onde os resultados dos experimentos serão salvos. Padrão: `output/cluster_experiments`.

### Exemplo de Execução

O comando abaixo executa uma bateria de testes no arquivo `meu_arquivo_local.jsonl`, testando `min_cluster_size` de 10 a 100 (em passos de 10) e usando apenas o modelo `all-MiniLM-L6-v2` (recomendado para similaridade geral).

```bash
python scripts/test_cluster_hyperparameters.py meu_arquivo_local.jsonl \
    --min-cluster-sizes 10 20 30 40 50 60 70 80 90 100 \
    --embedding-models all-MiniLM-L6-v2 \
    --epsilons 0.0
```

Para controlar a divisão de clusters grandes, pode-se executar:

```bash
python scripts/test_cluster_hyperparameters.py meu_arquivo_local.jsonl \
    --min-cluster-sizes 10 \
    --embedding-models all-MiniLM-L6-v2 \
    --epsilons 0.1 0.3 0.5
```

## Análise dos Resultados

Após a execução, o script criará uma estrutura de diretórios organizada para fácil comparação:

```
output/cluster_experiments/
└── <nome-do-modelo>/
    ├── min_size_<X>_eps_<Y>/
    │   └── <arquivo_de_relatorio>.md
    ├── min_size_<X>_eps_<Z>/
    │   └── <arquivo_de_relatorio>.md
    └── ...
```

Cada arquivo `.md` contém o relatório detalhado para uma combinação específica de parâmetros. A recomendação é analisar os relatórios gerados para identificar a configuração que melhor equilibra a granularidade e a coesão dos clusters para o seu conjunto de dados específico.

-----

# Anonimização de Incidentes de Segurança com Reidentificação Controlada

Ferramenta prática e inteligente para anonimizar tickets de incidentes de segurança, projetada para ser usada localmente por CSIRTs, garantindo que dados sensíveis possam ser utilizados para treinar modelos de IA (LLMs) com segurança.

-----

**Título*: Anonimização de Incidentes de Segurança com Reidentificação Controlada*

**Resumo*: Este trabalho aborda métodos de anonimização de dados presentes em incidentes de segurança, com o objetivo de alimentá-los em Large Language Models (LLMs). O objetivo é manter informações sensíveis não identificáveis e, ao mesmo tempo, potencializar o uso de inteligência artificial (IA), permitindo a classificação e correlação pelo modelo de eventos, pessoas e ocorrências. São estabelecidos requisitos de anonimização para a utilização de incidentes reais em uma LLM, a bibliografia é revisitada a fim de avaliar os métodos e ferramentas existentes para o caso proposto, e finalmente é apresentada uma ferramenta que usa uma abordagem híbrida para solucionar o problema especificado.*

-----

## Estrutura deste README

Esta documentação está organizada da seguinte maneira:

  - **Estrutura do Repositório:** Arquivos e diretórios presentes no projeto, com suas funções.
  - **Como a Ferramenta Funciona:** Uma visão geral do fluxo de anonimização.
  - **Selos Considerados:** Selos pretendidos pelo artefato (Disponível, Funcional e Sustentável).
  - **Pré-requisitos:** Requisitos de software/hardware para execução da ferramenta.
  - **Dependências:** Dependências de pacotes necessários para execução.
  - **Preocupações com Segurança:** Informações sobre a configuração da chave secreta.
  - **Instalação e Execução:** Passo a passo para baixar, instalar e executar a ferramenta.
  - **Exemplos de Uso:** Comandos de exemplo e um vídeo demonstrativo.
  - **Solução de Problemas Comuns:** Como resolver os erros mais frequentes.
  - **Ambiente de Testes:** Ambiente de hardware/software usado para desenvolvimento/testes.
  - **Experimentos:** Sobre coleta de métricas e exemplos de execução dos scripts auxiliares.
  - **LICENSE:** Informação sobre a licença do projeto.

-----

## Estrutura do Repositório

```
.
├── .gitignore                 # Arquivos ignorados pelo git
├── .python-version            # Versão do Python utilizada
├── anon.py                    # Script principal de anonimização
├── config.py                  # Arquivo de configuração (banco de dados, modelos)
├── deanonymize.py             # Script para reverter a anonimização de um slug
├── engine.py                  # Contém a lógica principal dos motores de anonimização
├── count_eng.py               # Script utilitário, conta trechos em inglês
├── get_metrics.py             # Script utilitário, coleta métricas de execução
├── get_runs_metrics.py        # Script utilitário, gera métricas ao longo de várias execuções
├── get_ticket_count.py        # Script utilitário, conta o número de tickets em um diretório
├── LICENSE                    # Licença do projeto
├── pyproject.toml             # Arquivo de configuração de dependências
├── README.md                  # Este arquivo
└── uv.lock                    # Cria o ambiente a partir do `pyproject.toml`
```

Obs.: Após a primeira execução, são gerados 4 diretórios:

```
.
├── db/       # Base de dados SQLite local, contendo as entidades detectadas
├── logs/     # Relatórios com estatísticas básicas de execuções
├── models/   # Modelos de Redes Neurais baixados
└── output/   # Diretório de saída com os arquivos anonimizados
```

-----

## Como a Ferramenta Funciona

O processo de anonimização segue um fluxo bem definido para garantir segurança e consistência:

1.  **Leitura e Extração**: O script `anon.py` lê o arquivo de entrada e detecta seu formato (e.g., `.txt`, `.pdf`, `.json`). Ele extrai todo o conteúdo textual. Para arquivos PDF, ele também utiliza **Tesseract OCR** para extrair texto de imagens incorporadas.
2.  **Carregamento dos Motores de IA**: Os motores de NLP da biblioteca **Presidio** são inicializados. A ferramenta utiliza um modelo spaCy (`pt_core_news_lg` ou `en_core_web_lg`) para tarefas gerais e um modelo Transformer (`Davlan/xlm-roberta-base-ner-hrl`) para um reconhecimento de entidades mais apurado. Os modelos são carregados de forma "lazy", ou seja, apenas na primeira vez que são necessários.
3.  **Análise e Detecção**: O texto extraído é processado pelo motor de análise, que identifica informações sensíveis (PII) como nomes de pessoas (`PERSON`), locais (`LOCATION`), organizações (`ORGANIZATION`), e-mails, etc. A ferramenta também utiliza reconhecedores personalizados para entidades como `CVE` e `IP_ADDRESS`.
4.  **Geração de Slug e Armazenamento**: Para cada entidade detectada, a ferramenta gera um "slug" anonimizado. Esse slug é um hash **HMAC-SHA256** do texto original, usando a `ANON_SECRET_KEY` como chave. A relação entre o texto original e seu hash é armazenada de forma segura em um banco de dados SQLite no diretório `db/`. Isso garante que a mesma entidade (e.g., o nome "João da Silva") sempre gere o mesmo slug, mantendo a consistência.
5.  **Substituição**: O texto original é substituído pelo slug anonimizado, no formato `[TIPO_DA_ENTIDADE_hash...]` (ex: `[PERSON_a1b2c3d4...]`).
6.  **Geração de Arquivos**: Um novo arquivo com o conteúdo anonimizado é salvo no diretório `output/`, e um relatório de execução é gerado em `logs/`.
7.  **Reidentificação**: O script `deanonymize.py` pode ser usado para consultar o banco de dados e encontrar o texto original correspondente a um slug, desde que a `ANON_SECRET_KEY` correta esteja configurada.

-----

## Selos Considerados

Os autores consideram os Selos Disponível, Funcional e Sustentável.

As requisições são baseadas nas informações providas neste repositório, contendo a documentação, título e resumo do trabalho - tornando o artefato disponível. Ademais, esta documentação busca explicitar ao máximo os passos necessários para a execução do programa, além de todas as dependências necessárias e com exemplos de uso, tornando o artefato funcional. Pelo cuidado tomado com documentação, legibilidade e modularidade do código, também é considerado sustentável.

-----

## Pré-requisitos

Componentes necessários para a execução da ferramenta:

1.  **Ferramenta `uv`**:

      - **Windows:**
        ```powershell
        powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
        ```
      - **Linux/macOS:**
        ```bash
        curl -LsSf https://astral.sh/uv/install.sh | sh
        ```

2.  **Tesseract OCR**:

      - A ferramenta de OCR Tesseract precisa estar instalada e acessível no `PATH` do seu sistema para processar imagens em PDFs.
      - **Ubuntu/Debian:**
        ```bash
        sudo apt update
        sudo apt install tesseract-ocr
        ```
      - **macOS (usando Homebrew):**
        ```bash
        brew install tesseract
        ```
      - **Windows:** Baixe o instalador oficial na [documentação do Tesseract](https://www.google.com/search?q=https://github.com/tesseract-ocr/tesseract%23installing-tesseract) e certifique-se de adicionar o caminho da instalação à variável de ambiente `PATH`.

3.  **Requisitos de Hardware**:

      - No mínimo **5GB** de espaço de armazenamento livre, devido ao tamanho das bibliotecas e dos modelos de redes neurais que serão baixados.

-----

## Dependências

As dependências são gerenciadas pelo `uv` através do arquivo `pyproject.toml`.

  - **Ferramentas Principais:**

| Ferramenta | Versão |
| :--- | :--- |
| `Python` | \>=3.11 |

  - **Dependências do Projeto:**

| Pacote | Versão |
| :--- | :--- |
| `email-validator` | \>=2.2.0 |
| `openpyxl` | \>=3.1.5 |
| `pandas` | \>=2.2.3 |
| `Pillow` | \>=10.4.0 |
| `pip` | \>=25.0.1 |
| `presidio-analyzer[transformers]`| \>=2.2.357 |
| `presidio-anonymizer` | \>=2.2.357 |
| `protobuf` | \>=6.30.1 |
| `PyMuPDF` | \>=1.24.9 |
| `pytesseract` | \>=0.3.10 |
| `python-docx` | \>=1.1.2 |
| `sentencepiece` | \>=0.2.0 |
| `transformers` | \>=4.49.0 |

-----

## Preocupações com Segurança

⚠️ **IMPORTANTE:** A segurança e a capacidade de reidentificação dos dados dependem de uma chave secreta (`HMAC SECRET KEY`). Esta chave **deve** ser configurada como uma variável de ambiente.

A variável de ambiente deve se chamar `ANON_SECRET_KEY`.

  - **No Linux/macOS** (adicione ao seu `.bashrc` ou `.zshrc` para persistência):
    ```bash
    export ANON_SECRET_KEY='sua-chave-super-secreta-e-longa-aqui'
    ```
  - **No Windows** (usando PowerShell):
    ```powershell
    $env:ANON_SECRET_KEY='sua-chave-super-secreta-e-longa-aqui'
    ```
    Para definir permanentemente, use as configurações de sistema do Windows ("Editar as variáveis de ambiente do sistema").

**Sem esta chave, a ferramenta não executará.**

-----

## Instalação e Execução

1.  **Clone o repositório:**

    ```bash
    git clone https://github.com/gt-rnp-lfi/anon.git
    cd anon
    ```

2.  **Crie o ambiente virtual e instale as dependências:**
    O `uv` cria um ambiente virtual (`.venv`) e instala os pacotes listados em `pyproject.toml` e `uv.lock`.

    ```bash
    uv sync
    ```

3.  **Configure a Chave Secreta:**
    Conforme a seção "Preocupações com Segurança", defina a variável de ambiente `ANON_SECRET_KEY`.

4.  **Execute o script de anonimização:**
    Use `uv run` para executar o script dentro do ambiente virtual, passando um arquivo como argumento.

    ```bash
    uv run anon.py <caminho/para/o/arquivo>
    ```

      - O arquivo processado será salvo no diretório `output/`.
      - Um relatório de execução será salvo em `logs/`.

-----

## Exemplos de Uso

> ⏳ **Nota sobre a primeira execução:** Na primeira vez que você executar o script, os modelos de IA necessários (spaCy e Transformer) serão baixados automaticamente. O processo pode levar alguns minutos.

**Execução Padrão (idioma português):**

```bash
uv run anon.py caminho/para/seu/arquivo.csv
```

**Especificando o idioma (inglês):**

```bash
uv run anon.py cve_report.json --lang en
```

**Preservando entidades (não anonimizar Localização e Organização):**

```bash
uv run anon.py relatorio.txt --preserve-entities "LOCATION,ORGANIZATION"
```

**Adicionando termos a uma lista de permissões:**

```bash
uv run anon.py logs_servidor.txt --allow-list "Servidor-01,Proxy-Interno"
```

**Revertendo a anonimização de um slug:**
Para descobrir o valor original de um slug gerado, use o script `deanonymize.py`.

```bash
uv run deanonymize.py "[PERSON_a1b2c3d4e5f6...]"
```

**Vídeo com exemplos de execução:**

\<a href="[https://asciinema.org/a/TC8KBxoPO5afHPqjIsSefNbCN](https://asciinema.org/a/TC8KBxoPO5afHPqjIsSefNbCN)" target="\_blank"\>\<img src="[https://asciinema.org/a/TC8KBxoPO5afHPqjIsSefNbCN.svg](https://asciinema.org/a/TC8KBxoPO5afHPqjIsSefNbCN.svg)" /\>\</a\>

-----

## Solução de Problemas Comuns

  - **Erro: `[!] Tesseract is not installed or not in your PATH...`**

      - **Causa**: O Tesseract OCR não foi encontrado no seu sistema.
      - **Solução**: Siga as instruções de instalação na seção **Pré-requisitos**. Se você já instalou (especialmente no Windows), verifique se o local da instalação foi adicionado à variável de ambiente `PATH`.

   - **Aviso: `[!] Tesseract is not installed or not in your PATH...`**

      - **Causa**: O Tesseract OCR não foi encontrado no seu sistema.
      - **Solução**: Siga as instruções de instalação na seção **Pré-requisitos**. Se você já instalou (especialmente no Windows), verifique se o local da instalação foi adicionado à variável de ambiente `PATH`.

  - **Erro: `[!] Error: ANON_SECRET_KEY environment variable not set.`**

      - **Causa**: A chave secreta não foi configurada.
      - **Solução**: Siga as instruções na seção **Preocupações com Segurança** para definir a variável de ambiente `ANON_SECRET_KEY`.

  - **Erro: `[!] An error occurred during processing: No matching recognizers were found...`**

      - **Causa**: Geralmente indica um problema interno onde o idioma do motor de análise não corresponde ao idioma solicitado para análise.
      - **Solução**: Este problema foi corrigido na versão modular. Se ocorrer, verifique se as alterações para passar o parâmetro `lang` nas funções `anonymize_text` (`engine.py`) e `anonymizer_func` (`anon.py`) foram aplicadas corretamente.

-----

## Ambiente de Testes

**Hardware:**

  - **Processador:** AMD Ryzen 3 3300X
  - **Memória RAM:** 16GB DDR4 @ 2666Hz
  - **Placa de Vídeo:** NVIDIA GeForce 1650

**Software:**

  - **Sistema Operacional:** Windows 10 22H2
  - **Sistema de Virtualização:** WSL2 com Ubuntu 20.04

-----

## Experimentos

### Coleta de métricas para 10 execuções

Para coletar métricas de performance ao longo de 10 *runs*, é possível usar o script auxiliar `get_runs_metrics.py`. Basta passar um diretório como único argumento de linha de comando:

```bash
uv run get_runs_metrics.py <diretório-com-conjunto-de-teste>
```

### Reivindicação 1:

```bash
uv run anon.py dataset-teste-anonimizado/anon_incidents_xlsx.csv
```

### Reivindicação 2:

```bash
uv run anon.py dataset-teste-anonimizado/anon_POP_-__-_RS_-__-_CERT-RS_\(Todo180_xlsx.csv
```

-----

## LICENSE

Esta ferramenta está licenciada sob a [GPL-3.0](https://www.google.com/search?q=./LICENSE).
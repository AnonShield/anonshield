# AnonLFI 2.0: Guia do Desenvolvedor

Este documento fornece uma visão aprofundada da arquitetura, componentes e fluxos de trabalho do AnonLFI 2.0. O objetivo é capacitar os desenvolvedores a entender, manter e estender o projeto de forma eficaz.

## Índice

- [Visão Geral da Arquitetura](#visão-geral-da-arquitetura)
  - [Princípios de Design](#princípios-de-design)
  - [Fluxo de Dados de Alto Nível](#fluxo-de-dados-de-alto-nível)
- [Mergulho nos Componentes Principais](#mergulho-nos-componentes-principais)
  - [1. Ponto de Entrada: `anon.py`](#1-ponto-de-entrada-anonpy)
  - [2. Orquestração Central: `AnonymizationOrchestrator`](#2-orquestração-central-anonymizationorchestrator)
  - [3. Estratégias de Anonimização: `strategies.py`](#3-estratégias-de-anonimização-strategiespy)
  - [4. Processadores de Arquivo: `processors.py`](#4-processadores-de-arquivo-processorspy)
  - [5. Detecção de Entidades: `entity_detector.py` e `engine.py`](#5-detecção-de-entidades-entitydetectorpy-e-enginepy)
  - [6. Camada de Persistência: `database.py` e `repository.py`](#6-camada-de-persistência-databasepy-e-repositorypy)
  - [7. Geração de Hash: `hash_generator.py`](#7-geração-de-hash-hashgeneratorpy)
  - [8. Gerenciamento de Cache: `cache_manager.py`](#8-gerenciamento-de-cache-cachemanagerpy)
- [Mecanismo de Anonimização e Hashing](#mecanismo-de-anonimização-e-hashing)
- [Sistema de Configuração](#sistema-de-configuração)
  - [Argumentos da Linha de Comando](#argumentos-da-linha-de-comando)
  - [Configuração Avançada (JSON)](#configuração-avançada-json)
- [Como Estender o AnonLFI 2.0](#como-estender-o-anonlfi-20)
  - [Adicionando um Novo Processador de Arquivo](#adicionando-um-novo-processador-de-arquivo)
  - [Adicionando um Novo Reconhecedor de Entidades (Recognizer)](#adicionando-um-novo-reconhecedor-de-entidades-recognizer)
- [Ambiente de Desenvolvimento e Testes](#ambiente-de-desenvolvimento-e-testes)
  - [Configuração do Ambiente](#configuração-do-ambiente)
  - [Executando os Testes](#executando-os-testes)

---

## Visão Geral da Arquitetura

O AnonLFI 2.0 é construído sobre uma arquitetura em camadas e modular, projetada para ser extensível, testável e de fácil manutenção.

### Princípios de Design

-   **Separação de Responsabilidades (SoC):** Cada componente tem um único propósito. O `AnonymizationOrchestrator` coordena, os `FileProcessors` lidam com a extração de texto, o `EntityDetector` encontra PII, e o `EntityRepository` lida com o banco de dados.
-   **Inversão de Dependência (DI):** As dependências (como `CacheManager`, `HashGenerator`, etc.) são injetadas no `AnonymizationOrchestrator` a partir da raiz de composição (`anon.py`), facilitando a substituição e o teste de componentes.
-   **Padrões de Projeto (Design Patterns):**
    -   **Strategy Pattern:** As diferentes lógicas de anonimização (`presidio`, `fast`, `balanced`) são encapsuladas em classes de estratégia intercambiáveis (`strategies.py`), permitindo que o orquestrador escolha a melhor abordagem em tempo de execução.
    -   **Template Method Pattern:** A classe base `FileProcessor` define o esqueleto do algoritmo de processamento de um arquivo (`extract -> process -> output`), e as subclasses implementam as etapas específicas para cada formato de arquivo.
    -   **Producer-Consumer:** O `DatabaseContext` usa uma fila e um thread em segundo plano para desacoplar as operações de escrita no banco de dados do fluxo principal de processamento, evitando que I/O de banco de dados se torne um gargalo.

### Fluxo de Dados de Alto Nível

O diagrama abaixo ilustra como um arquivo é processado desde a entrada do usuário até a saída anonimizada.

```mermaid
graph TD
    A[Usuário executa `anon.py`] --> B{`anon.py` (CLI)};
    B -- Argumentos --> C(Injeção de Dependência);
    C -- Cria instâncias de --> D(CacheManager, HashGenerator, EntityDetector);
    B -- Instancia --> E[AnonymizationOrchestrator];
    D -- Injeta em --> E;

    subgraph "Camada de Orquestração"
        E -- Seleciona --> F{ProcessorRegistry};
        F -- Dado o tipo do arquivo --> G[FileProcessor Específico];
    end

    subgraph "Camada de Processamento de Arquivo"
        G -- 1. Extrai textos --> H(Textos Brutos);
    end

    subgraph "Camada de Análise e Anonimização"
        H -- 2. Envia para --> E;
        E -- Delega para --> I{AnonymizationStrategy};
        I -- 3. Usa o EntityDetector --> J[Entidades PII Detectadas];
        J -- 4. Gera Hash Seguro --> K(HashGenerator);
        K -- Slugs --> L[Texto com Slugs];
        K -- Mapeamentos (Original, Hash) --> M(Fila do DB);
    end

    subgraph "Camada de Persistência (Assíncrona)"
        M -- Consumido por --> N(Database Writer Thread);
        N -- Salva em --> O[(entities.db)];
    end

    subgraph "Camada de Geração de Saída"
        L -- 5. Retorna para --> G;
        G -- 6. Reconstrói o arquivo --> P(Arquivo de Saída Anonimizado);
    end
```

---

## Mergulho nos Componentes Principais

### 1. Ponto de Entrada: `anon.py`

-   **Responsabilidade:** Atua como a **raiz de composição** da aplicação.
-   **Funções:**
    -   Analisar os argumentos da linha de comando usando `argparse`.
    -   Validar a configuração fornecida pelo usuário.
    -   Instanciar todas as dependências principais (`DatabaseContext`, `CacheManager`, `HashGenerator`, `EntityDetector`).
    -   Injetar essas dependências no `AnonymizationOrchestrator`.
    -   Invocar o `ProcessorRegistry` para obter o processador de arquivo correto e iniciar o processo.
    -   Gerenciar o ciclo de vida do `DatabaseContext` (inicialização e `shutdown`).

### 2. Orquestração Central: `AnonymizationOrchestrator`

-   **Localização:** `src/anon/engine.py`
-   **Responsabilidade:** Coordenar o processo de anonimização de alto nível.
-   **Funções:**
    -   Mantém as instâncias dos motores do Presidio (`AnalyzerEngine`, `AnonymizerEngine`).
    -   Utiliza o padrão **Strategy** para selecionar a lógica de anonimização (`presidio`, `fast`, `balanced`) com base na entrada do usuário, delegando o trabalho para o objeto de estratégia apropriado.
    -   Gerencia a lógica de fallback: se uma anonimização em lote falhar, ele aciona o `_safe_fallback_processing` para reprocessar os itens um a um, garantindo a integridade dos dados.
    -   Coleta estatísticas sobre as entidades anonimizadas para o relatório final.

### 3. Estratégias de Anonimização: `strategies.py`

-   **Localização:** `src/anon/strategies.py`
-   **Responsabilidade:** Encapsular os diferentes algoritmos de anonimização.
-   **Estratégias Implementadas:**
    1.  **`PresidioStrategy` (Abrangente):** Utiliza o pipeline completo do Presidio, com todos os reconhecedores disponíveis, para a máxima precisão de detecção. Usa tanto o AnalyzerEngine quanto o AnonymizerEngine do Presidio.
    2.  **`FastStrategy` (Otimizada):** Usa o AnalyzerEngine do Presidio com escopo filtrado de entidades (mesmo da Balanced) para detecção, mas implementa a substituição de texto manualmente em Python puro. Evita o overhead do AnonymizerEngine do Presidio.
    3.  **`BalancedStrategy` (Performance Ideal):** Usa o pipeline completo do Presidio (AnalyzerEngine + AnonymizerEngine), mas com um conjunto filtrado de reconhecedores. É a estratégia mais rápida devido à redução do escopo de detecção, sendo ideal para grandes volumes de dados onde a performance é crítica.

### 4. Processadores de Arquivo: `processors.py`

-   **Localização:** `src/anon/processors.py`
-   **Responsabilidade:** Extrair texto de diferentes formatos de arquivo e reconstruir o arquivo anonimizado.
-   **Padrão:** Template Method. A classe base `FileProcessor` define o fluxo `process()`, e as subclasses implementam os métodos abstratos `_extract_texts()` e `_get_output_extension()`.
-   **Processadores Notáveis:**
    -   **`PdfFileProcessor`:** Usa `PyMuPDF` para extrair texto e imagens. O texto é ordenado espacialmente para manter a ordem de leitura. Imagens embutidas são extraídas e processadas via OCR com `Pytesseract`.
    -   **`JsonFileProcessor`:** Um processador híbrido. Para arquivos `.jsonl`, ele processa linha a linha. Para arquivos `.json`, ele usa `orjson` para carregamento rápido em memória (arquivos pequenos) ou `ijson` para streaming de arrays JSON grandes, evitando o consumo excessivo de memória.
    -   **`CsvFileProcessor` / `XlsxFileProcessor`:** Usam `pandas` e `openpyxl` para processar dados tabulares. Por padrão, eles processam apenas os valores únicos por coluna para otimizar a performance, mas podem ser configurados para processar cada célula individualmente para manter o contexto da linha (`--preserve-row-context`).
    -   **`XmlFileProcessor`:** Usa `lxml` para parsear a árvore XML, rastreando o XPath de cada texto ou atributo para garantir que a estrutura do arquivo seja perfeitamente preservada após a anonimização.

### 5. Detecção de Entidades: `entity_detector.py` e `engine.py`

-   **Responsabilidade:** Identificar informações sensíveis (PII) no texto.
-   **Componentes:**
    -   **Motores Presidio (`AnalyzerEngine`):** O `engine.py` configura o `AnalyzerEngine` com um `TransformersNlpEngine`, que utiliza tanto modelos **spaCy** (para velocidade e entidades básicas) quanto um modelo **Transformer** (`xlm-roberta-base-ner-hrl`) para alta precisão em várias línguas.
    -   **Reconhecedores Customizados (`PatternRecognizer`):** Em `engine.py`, a função `load_custom_recognizers` define uma lista de reconhecedores baseados em **regex**, otimizados para detectar entidades técnicas comuns em CSIRTs (IPs, URLs, Hashes, CVEs, etc.).
    -   **`EntityDetector` (`entity_detector.py`):** Esta classe é usada pela `FastStrategy` para mesclar entidades sobrepostas. Contém a lógica de fusão customizada que prioriza entidades com maior pontuação (`score`) e comprimento. Note que a detecção em si é feita pelo `AnalyzerEngine` do Presidio.

### 6. Camada de Persistência: `database.py` e `repository.py`

-   **Responsabilidade:** Lidar com o armazenamento e recuperação de mapeamentos de entidades de forma segura e eficiente.
-   **Componentes:**
    -   **`DatabaseContext` (`database.py`):** Gerencia o ciclo de vida da conexão com o banco de dados e o thread de escrita. Ele implementa o padrão **Producer-Consumer**:
        -   O fluxo principal de anonimização (producer) coloca as entidades a serem salvas em uma `queue.Queue`.
        -   Um único thread em segundo plano (consumer) retira os itens da fila e os salva no banco de dados em lotes. Isso evita que as operações de escrita bloqueiem o processamento dos arquivos.
        -   O método `shutdown()` foi cuidadosamente projetado para garantir que a fila seja esvaziada e o thread finalizado de forma limpa, prevenindo a perda de dados.
    -   **`EntityRepository` (`repository.py`):** Implementa o **Repository Pattern**, encapsulando todas as consultas SQL. Ele gerencia as conexões de banco de dados usando `threading.local()`, o que garante que cada thread tenha sua própria conexão isolada, tornando as operações seguras para threads.

### 7. Geração de Hash: `hash_generator.py`

-   **Responsabilidade:** Criar pseudônimos seguros e consistentes.
-   **Funcionamento:**
    -   Utiliza **HMAC-SHA256** para gerar um hash de 64 caracteres para cada entidade única.
    -   A chave para o HMAC é fornecida pela variável de ambiente `ANON_SECRET_KEY`, garantindo que os hashes não possam ser recriados sem a chave secreta.
    -   Gera um "slug" (um prefixo do hash completo) de comprimento configurável para ser usado no texto de saída, melhorando a legibilidade.

### 8. Gerenciamento de Cache: `cache_manager.py`

-   **Responsabilidade:** Armazenar em memória os resultados da anonimização para acelerar o processamento de textos repetidos dentro da mesma execução.
-   **Funcionamento:**
    -   Implementa um cache **LRU (Least Recently Used)** usando `collections.OrderedDict`.
    -   Quando o cache está cheio, o item menos recentemente usado é removido.
    -   O cache é thread-safe, utilizando um `threading.RLock` para proteger as operações de leitura e escrita.

---

## Mecanismo de Anonimização e Hashing

O processo para substituir uma entidade PII detectada (ex: "John Doe") é o seguinte:

1.  **Normalização:** O texto da entidade é limpo para remover espaços extras (`" John  Doe  "` -> `"John Doe"`).
2.  **Geração de Hash:** O `HashGenerator` calcula o `HMAC-SHA256` do texto limpo usando a `ANON_SECRET_KEY`.
    -   **Hash Completo:** `hmac.new(key, "John Doe".encode(), sha256).hexdigest()` -> `a1b2c3d4e5f6...` (64 caracteres)
    -   **Slug:** Um prefixo do hash completo, ex: `a1b2c3d4` (comprimento 8).
3.  **Coleta para o Banco de Dados:** Uma tupla contendo `(entity_type, original_text, slug, full_hash)` é adicionada à fila de escrita do `DatabaseContext`.
4.  **Substituição no Texto:** O `CustomSlugAnonymizer` retorna o texto formatado `[PERSON_a1b2c3d4]`, que substitui "John Doe" no arquivo de saída.
5.  **Persistência:** O thread de banco de dados salva a tupla na tabela `entities`. A `UNIQUE` constraint na coluna `full_hash` garante que cada entidade original tenha apenas uma entrada no banco.

---

## Sistema de Configuração

### Argumentos da Linha de Comando

`anon.py` oferece uma vasta gama de argumentos para controlar o comportamento da ferramenta. Alguns dos mais importantes para desenvolvedores são:

-   `--log-level`: Controla a verbosidade dos logs (essencial para depuração).
-   `--anonymization-strategy`: Permite alternar entre `presidio`, `fast` e `balanced`.
-   `--db-mode`: Permite usar um banco de dados `in-memory` para execuções de teste rápidas.
-   `--use-cache`, `--optimize`: Flages para ativar otimizações de performance.

### Configuração Avançada (JSON)

Para arquivos estruturados (`.json`, `.xml`, `.csv`), um arquivo de configuração JSON pode ser fornecido via `--anonymization-config` para um controle granular:

-   `fields_to_exclude`: Lista de caminhos (dot-notation, ex: `"user.metadata.id"`) a serem completamente ignorados.
-   `fields_to_anonymize`: Ativa o **modo explícito**. Apenas os campos nesta lista serão analisados para detecção de PII.
-   `force_anonymize`: Ativa o **modo explícito** e força a anonimização de um campo com um tipo de entidade específico (ex: `{"user.id": {"entity_type": "CUSTOM_ID"}}`), ignorando a detecção de PII e outros filtros de texto.

---

## Como Estender o AnonLFI 2.0

### Adicionando um Novo Processador de Arquivo

Para adicionar suporte a um novo tipo de arquivo (ex: `.yaml`):

1.  **Crie a Classe do Processador:**
    -   Em `src/anon/processors.py`, crie uma nova classe que herde de `FileProcessor`.
    -   Ex: `class YamlFileProcessor(FileProcessor):`

2.  **Implemente os Métodos Abstratos:**
    -   `_get_output_extension(self) -> str:` Deve retornar a extensão do arquivo de saída (ex: `return ".yaml"`).
    -   `_extract_texts(self) -> Iterable[str]:` Se o objetivo for gerar um `.txt`, este método deve extrair todo o texto do arquivo e usar `yield` para retorná-lo.
    -   `_process_anonymization(self, output_path: str):` Se o objetivo for preservar a estrutura (altamente recomendado), você deve sobrescrever este método. Nele, você irá:
        1.  Parsear o arquivo (ex: usando `pyyaml`).
        2.  Coletar todos os textos que precisam de anonimização em um mapa ou lista.
        3.  Chamar `self.orchestrator.anonymize_texts()` para obter os textos anonimizados.
        4.  Construir um mapa de tradução (`original -> anonimizado`).
        5.  Reconstruir o arquivo de saída, substituindo os valores originais pelos anonimizados.

3.  **Registre o Processador:**
    -   No final de `src/anon/processors.py`, adicione o novo processador ao `ProcessorRegistry`.
    -   `ProcessorRegistry.register([".yaml", ".yml"], YamlFileProcessor)`
    -   Adicione também o mapeamento de MIME type em `FileTypeValidator` em `src/anon/security.py` para validação de tipo de arquivo.

### Adicionando um Novo Reconhecedor de Entidades (Recognizer)

Para detectar um novo tipo de PII (ex: `LICENSE_PLATE`):

1.  **Defina o Padrão Regex:**
    -   Crie um padrão de regex robusto que identifique a entidade.
    -   Ex: `license_plate_pattern = Pattern(name="License Plate", regex=r"\b[A-Z]{3}-\d{4}\b", score=0.8)`

2.  **Adicione o Reconhecedor:**
    -   Em `src/anon/engine.py`, na função `load_custom_recognizers`, adicione um novo `PatternRecognizer`.
    -   `PatternRecognizer(supported_entity="LICENSE_PLATE", patterns=[license_plate_pattern], supported_language=lang)`
    -   Adicione a nova entidade à lista de reconhecedores para cada idioma suportado.

3.  **Liste a Nova Entidade (Opcional):**
    -   Adicione `"LICENSE_PLATE"` à lista retornada por `get_supported_entities()` em `anon.py` para que ela apareça na ajuda (`--list-entities`).

---

## Ambiente de Desenvolvimento e Testes

### Configuração do Ambiente

1.  **Pré-requisitos:**
    -   Python 3.9+
    -   `uv` (instalador de pacotes e gerenciador de ambiente virtual).
    -   Tesseract OCR (para extração de texto de imagens).

2.  **Instalação:**
    ```bash
    # Clone o repositório
    git clone https://github.com/AnonShield/AnonLFI2.0.git
    cd AnonLFI2.0

    # Crie o ambiente virtual e instale as dependências
    uv sync
    ```

3.  **Chave Secreta:**
    -   Para executar a anonimização, uma chave secreta é obrigatória. Exporte-a como uma variável de ambiente:
    -   `export ANON_SECRET_KEY='uma-chave-super-secreta'`

### Executando os Testes

O projeto usa o módulo `unittest` do Python.

-   **Para executar todos os testes:**
    ```bash
    uv run python -m unittest discover tests/
    ```
-   **Para executar um arquivo de teste específico:**
    ```bash
    uv run python -m unittest tests/test_anon_integration.py
    ```

Os testes são cruciais para validar as correções de bugs e garantir que novas funcionalidades não quebrem o comportamento existente. É altamente recomendável escrever novos testes para qualquer código adicionado.

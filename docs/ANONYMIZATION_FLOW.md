# Fluxo de Anonimização: Um Mergulho Profundo

Este documento descreve em detalhes o fluxo de processamento para cada tipo de arquivo suportado pela ferramenta de anonimização. A arquitetura é baseada no padrão de projeto **Template Method**, onde uma classe base (`FileProcessor`) define o esqueleto do algoritmo, e as subclasses especializadas implementam os detalhes específicos de extração e reconstrução para cada formato.

## Arquitetura e Componentes Principais

O sistema é composto por três camadas principais que trabalham em conjunto.

```mermaid
graph TD
    A[Entrada: Arquivo] --> B{1. Camada de Processamento de Arquivo (processors.py)};
    B -- Extrai Textos --> C{2. Camada de Orquestração (engine.py)};
    C -- Detecta e Anonimiza PII --> D[3. Camada de Análise e Armazenamento (Presidio & DB)];
    C -- Retorna Texto Anonimizado --> B;
    B -- Reconstrói e Salva Arquivo --> E[Saída: Arquivo Anonimizado];

    subgraph "1. Processadores de Arquivo"
        B;
        direction LR;
        P_JSON(JsonFileProcessor);
        P_XML(XmlFileProcessor);
        P_CSV(CsvFileProcessor);
        P_PDF(PdfFileProcessor);
        P_DOCX(DocxFileProcessor);
        P_TXT(TextFileProcessor);
    end

    subgraph "2. Orquestrador e Estratégias"
        C;
        direction LR;
        S_Presidio(Estratégia Presidio);
        S_Balanced(Estratégia Balanced);
        S_Fast(Estratégia Fast);
        S_Forced(Estratégia Forçada);
    end
    
    subgraph "3. Análise e Persistência"
        D;
        direction LR;
        M_Spacy[Modelos spaCy];
        M_Trf[Modelo Transformer];
        M_Regex[Regex Customizadas];
        DB[(Banco de Dados)];
    end
```

1.  **`FileProcessor` (Classe Base):** Orquestra o fluxo principal. Sua responsabilidade é abrir o arquivo, chamar o método de extração, gerenciar o processamento em lotes (`batching`), e chamar o método de reconstrução/salvamento.
2.  **`AnonymizationOrchestrator`:** O cérebro da anonimização. Ele não sabe sobre arquivos, apenas sobre texto. Ele recebe lotes de texto, decide qual estratégia de anonimização usar (`presidio`, `fast`, `balanced`), e invoca os motores do Presidio para a detecção e substituição.
3.  **`CustomSlugAnonymizer`:** Um operador customizado do Presidio. Quando o `AnonymizerEngine` do Presidio encontra uma PII, ele chama este operador, que gera um "slug" seguro (ex: `[PERSON_a1b2c3]`) usando um hash HMAC-SHA256 do texto original. Isso garante que "João Silva" seja sempre substituído pelo mesmo slug, mantendo a consistência referencial. O hash completo é armazenado em um banco de dados SQLite para permitir a de-anonimização futura.

---

## O Coração do Processo: Lógica de Decisão e Anonimização

### A. O Porteiro: `_should_anonymize()`

Este método na classe `FileProcessor` atua como um porteiro, decidindo se um texto deve ser enviado para a custosa análise de PII. Para arquivos estruturados (JSON, XML), ele também recebe o "caminho" do dado (ex: `asset.tags[0].value`).

O fluxo de decisão é o seguinte:
1.  **Verificação de Exclusão (`fields_to_exclude`):** Se o caminho está na lista de exclusão, o processo para. **É a regra de maior prioridade.**
2.  **Verificação de Anonimização Forçada (`force_anonymize`):** Se o caminho está mapeado aqui, ele é marcado para anonimização com um tipo de entidade específico, ignorando os filtros de texto.
3.  **Filtros de Texto:** O texto é inspecionado (tamanho, conteúdo numérico, stop-words). Se falhar, o processo para.
4.  **Lógica de Modo (Explícito vs. Implícito):** No modo explícito (se `fields_to_anonymize` existe), um texto só continua se seu caminho estiver explicitamente listado. No modo implícito, todo texto que passa pelos filtros continua.

### B. O Orquestrador e Suas Estratégias

Uma vez que `_should_anonymize` dá o sinal verde, o `AnonymizationOrchestrator` assume, usando uma das três estratégias principais:

#### Estratégia `presidio` (A Completa)
- **Como funciona:** Usa o motor `AnalyzerEngine` do Presidio em sua capacidade total. Ele invoca **todos** os reconhecedores disponíveis: o pipeline **spaCy+Transformer**, as **Regex customizadas**, e **dezenas de reconhecedores internos do Presidio** (para passaportes, CNHs, etc.). Os resultados de todas essas fontes são então agregados por uma lógica sofisticada para resolver conflitos e determinar a melhor entidade.
- **Pró:** Máxima precisão e capacidade de detecção.
- **Contra:** Mais lenta devido ao grande número de reconhecedores e à complexa lógica de agregação.

#### Estratégia `fast` (A Rápida)
- **Como funciona:** Ignora completamente o `AnalyzerEngine`. Ela executa um pipeline manual e direto:
    1. Passa o texto pelo pipeline **spaCy+Transformer**.
    2. Em paralelo, passa o texto pelas **Regex customizadas**.
    3. Usa uma lógica de fusão (`_merge_overlapping_entities`) mais simples para combinar os resultados das duas fontes.
    4. Reconstrói o texto manualmente.
- **Pró:** Significativamente mais rápida por eliminar a sobrecarga do `AnalyzerEngine` e seus múltiplos reconhecedores internos.
- **Contra:** Menos robusta na resolução de conflitos de entidades e não utiliza os reconhecedores adicionais do Presidio.

#### Estratégia `balanced` (O Melhor de Dois Mundos) - **NOVO!**
- **Como funciona:** Esta estratégia é um meio-termo inteligente. Ela usa o `AnalyzerEngine` do Presidio (garantindo uma lógica de agregação de resultados mais robusta que a do modo `fast`), mas o invoca de forma seletiva. Em vez de usar todos os reconhecedores, ela o instrui a usar **apenas** o pipeline **spaCy+Transformer** e as **Regex customizadas**.
- **Pró:** Oferece um equilíbrio ideal, sendo mais rápida que a `presidio` (pois ignora os reconhecedores internos lentos) e mais robusta que a `fast` (pois usa a lógica de agregação superior do Presidio).
- **Contra:** Pode não detectar entidades muito específicas que apenas os reconhecedores internos do Presidio cobririam.

### C. Como o Texto Chega ao Transformer: O Processo de Tokenização

O modelo Transformer processa uma representação numérica do texto, criada através de um passo crucial chamado **tokenização**.

Imagine o texto: `"Meu nome é João e moro em São Paulo."`

1.  **Quebra em Tokens:** O texto é quebrado em "sub-palavras" (ex: "São Paulo" -> `['ĠS', 'ão', 'ĠPaulo']`), permitindo que o modelo lide com palavras desconhecidas.
2.  **Adição de Tokens Especiais:** Tokens como `<s>` (início) e `</s>` (fim) são adicionados.
3.  **Conversão para IDs:** Cada token é mapeado para um número inteiro do vocabulário do modelo.
4.  **Criação da Máscara de Atenção:** Uma lista de `1`s e `0`s indica ao modelo quais tokens são reais e devem ser considerados.

A estrutura numérica resultante (`input_ids` e `attention_mask`) é o que é efetivamente passado para a rede neural do Transformer.

---

## Fluxo Detalhado por Tipo de Arquivo

O fluxo geral de **Coleta -> Anonimização em Lote -> Reconstrução** se aplica a todos. A diferença está em como cada processador implementa a coleta e a reconstrução.

### 1. `TextFileProcessor` e `ImageFileProcessor`
- **Lógica:** Simples e direta. Extrai todo o texto (seja de linhas de um arquivo `.txt` ou via OCR de uma imagem) e o salva em um novo arquivo `.txt` anonimizado.

### 2. `DocxFileProcessor` e `PdfFileProcessor`
- **Lógica:** Extração complexa com reconstrução simples.
- **Desafio:** Extrair texto na ordem correta, especialmente de imagens embutidas (DOCX) e de layouts complexos (PDF).
- **Solução:** O `PdfFileProcessor` se destaca por sua **ordenação espacial**. Ele extrai o texto e as coordenadas de cada bloco e imagem, e depois os reordena de cima para baixo e da esquerda para a direita para simular a leitura humana antes de enviar para anonimização. O resultado é um único `.txt`.

### 3. `CsvFileProcessor` e `XlsxFileProcessor`
- **Lógica:** Preservação da estrutura tabular através de um mapa de tradução.
- **Fluxo:**
    1.  **Coleta e Deduplicação:** Coleta todos os valores de texto **únicos** do arquivo que precisam de anonimização.
    2.  **Criação do Mapa:** Os valores únicos são anonimizados, criando um dicionário que mapeia o original para o anonimizado: `{"João Silva": "[PERSON_...]"}`.
    3.  **Aplicação do Mapa:** Itera novamente sobre o arquivo, substituindo todas as ocorrências dos valores originais pelos seus correspondentes anonimizados no mapa.
    4.  Um novo arquivo CSV/XLSX é salvo, mantendo a estrutura intacta.

### 4. `XmlFileProcessor` e `JsonFileProcessor`
- **Lógica:** Preservação da hierarquia através da análise e reconstrução da árvore de dados.
- **Fluxo:**
    1.  **Parseamento e Coleta com Caminho:** O arquivo é parseado em uma árvore. O processador percorre a árvore e coleta todos os textos que precisam de anonimização, guardando não só o texto, mas também seu **caminho** (`.`-notation para JSON, XPath para XML).
    2.  **Agrupamento e Mapa de Tradução:** Os textos são agrupados (por caminho ou tipo forçado) e enviados para criar um mapa de tradução.
    3.  **Reconstrução do Objeto:** O código percorre a árvore original uma segunda vez, usando o mapa para substituir os valores nos locais exatos.
    4.  O novo objeto/árvore anonimizado é salvo, preservando perfeitamente a estrutura original.
- **Otimização (XML):** Para lidar com vários campos pequenos, o `XmlFileProcessor` coleta *todos* os textos relevantes de todo o documento em uma única lista e a envia como um único lote para anonimização.
- **Otimização (JSON):** Usa um **Modo Híbrido** para arquivos grandes (>100MB), processando-os em modo de streaming (`ijson` para arrays, linha por linha para `.jsonl`) para evitar o consumo excessivo de memória.

---

## Modos de Operação Especiais e Otimizações

### Modo de Geração de Dados NER (`--generate-ner-data`)
- **Objetivo:** Em vez de anonimizar, gera dados para treinar modelos de NLP.
- **Otimização:** Para analisar milhares de pequenos textos de forma eficiente, o método `_run_ner_pipeline` os **junta em uma única string gigante**, usando o delimitador ` . ||| . ` como "cola". Essa string única é processada de uma só vez pelo modelo, maximizando a performance. Esta técnica de concatenação é usada **exclusivamente** neste modo.
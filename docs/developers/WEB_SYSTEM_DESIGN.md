# AnonShield Web — System Design

**Stack:** SvelteKit · FastAPI · Celery · Redis · Nginx  
**Servidor:** On-premise, GPU disponível  
**Filosofia:** Zero persistência de dados de usuário. Zero acúmulo de disco. Interface que desaparece.

---

## 1. Constraints

| Constraint | Decisão |
|-----------|---------|
| Sem cloud/S3 | Filesystem local com TTL agressivo |
| Sem persistência de arquivos | Input deletado após leitura, output deletado após download |
| Sem salvar dados do usuário | Chave só em Redis (TTL 1h), nunca em disco |
| Limite sem chave | 1 MB |
| Limite com chave | 10 GB |
| Concorrência atual | 1 usuário simultâneo (demo) |
| GPU disponível | Fila dedicada para estratégias NER |
| ZIP support | Extrai → processa cada arquivo → reempacota → entrega |

---

## 2. Arquitetura — Visão Geral

```
┌─────────────────────────────────────────────────────────────────┐
│                         Seu servidor                            │
│                                                                 │
│   Browser                                                       │
│      │  HTTPS (443)                                             │
│      ▼                                                          │
│   ┌──────────────────────────────────┐                          │
│   │  Nginx (TLS termination)         │                          │
│   │  client_max_body_size off        │                          │
│   │  proxy_read_timeout 7200         │ ← 2h para arquivos 10GB  │
│   └────────┬──────────────┬──────────┘                          │
│            │ /            │ /api                                │
│            ▼              ▼                                     │
│   ┌──────────────┐  ┌──────────────────────────────────┐       │
│   │  SvelteKit   │  │  FastAPI (uvicorn, 4 workers)    │       │
│   │  (SSR/SPA)   │  │  Streaming upload · Job API      │       │
│   │  :3000       │  │  SSE status · Streaming download │       │
│   └──────────────┘  └──────────┬───────────────────────┘       │
│                                │                                │
│                     ┌──────────▼──────────┐                    │
│                     │  Redis :6379         │                    │
│                     │  127.0.0.1 only      │                    │
│                     │  appendonly no       │                    │
│                     │  • Celery broker     │                    │
│                     │  • job:{id}:key      │                    │
│                     │  • job:{id}:status   │                    │
│                     └──────────┬──────────┘                    │
│                                │                                │
│              ┌─────────────────┴─────────────────┐             │
│              ▼                                   ▼             │
│   ┌─────────────────────┐           ┌─────────────────────┐   │
│   │  Worker: fast        │           │  Worker: gpu         │   │
│   │  queue=fast          │           │  queue=gpu           │   │
│   │  concurrency=4       │           │  concurrency=1       │   │
│   │  strategy: regex     │           │  strategy: filtered  │   │
│   │  (CPU only)          │           │  standalone · hybrid │   │
│   └──────────┬──────────┘           └──────────┬──────────┘   │
│              └─────────────┬─────────────────────┘             │
│                            ▼                                    │
│                  /tmp/anon/jobs/{job_id}/                       │
│                  ├── input.{ext}   ← deletado após leitura      │
│                  └── output/       ← deletado após download     │
│                                                                 │
│   Celery Beat (a cada 15 min)                                   │
│   └── limpa jobs órfãos > 30 min                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Componentes

### 3.1 SvelteKit (Frontend)

- **Modo:** SSR habilitado (primeira carga rápida, SEO irrelevante mas sem custo extra)
- **Responsabilidades:**
  - UI de upload com drag-and-drop
  - Configuration Builder (perfis, entidades, regex)
  - Polling de status (SSE ou fetch a cada 2s)
  - Download via `<a href>` streaming
  - Import/export de perfis YAML

### 3.2 FastAPI (Backend API)

- **Responsabilidades:**
  - Receber upload em streaming (sem carregar em memória)
  - Validar tipo de arquivo e tamanho por tier
  - Criar job + enfileirar no Celery
  - Servir status e output em streaming
  - Endpoint `/api/entities` — lista dinâmica de entidades por estratégia + modelo

### 3.3 Celery Workers

| Worker | Fila | Estratégias | Concorrência |
|--------|------|-------------|-------------|
| `worker-fast` | `fast` | `regex` | 4 (CPU) |
| `worker-gpu` | `gpu` | `filtered`, `standalone`, `hybrid` | 1 (GPU) |

### 3.4 Redis

- Broker Celery
- `job:{id}:key` — chave do usuário, TTL 1h, deletada pelo worker após uso
- `job:{id}:status` — `queued` / `running:{pct}` / `done` / `error:{msg}`
- `job:{id}:meta` — nome do arquivo, tamanho, estratégia, TTL 2h

---

## 4. Ciclo de Vida de um Job (zero dado deixado para trás)

```
1. UPLOAD
   Browser → POST /api/jobs (multipart, streaming)
   FastAPI lê chunk a chunk → /tmp/anon/jobs/{id}/input.{ext}
   Se tamanho > limite do tier → aborta upload, deleta parcial, retorna 413

2. ENFILEIRAMENTO
   FastAPI → redis.setex("job:{id}:key", 3600, key)
   FastAPI → redis.hset("job:{id}:meta", ...)
   FastAPI → celery.send_task(queue=fila_por_estrategia)
   FastAPI → retorna 202 {"job_id": "...", "status": "queued"}

3. PROCESSAMENTO (Worker)
   Worker busca key: key = redis.get("job:{id}:key")
   Worker abre input.{ext} para leitura
   *** Worker deleta input.{ext} imediatamente após abrir ***
   Worker executa AnonymizationOrchestrator (db_mode=in-memory)
   Worker salva resultado em /tmp/anon/jobs/{id}/output/
   Worker deleta key do Redis: redis.delete("job:{id}:key")
   Worker atualiza status: redis.set("job:{id}:status", "done")

4. DOWNLOAD
   Browser → GET /api/jobs/{id}/download
   FastAPI abre output/ e faz StreamingResponse
   *** FastAPI deleta output/ ao finalizar o stream ***
   FastAPI atualiza status: "downloaded"

5. LIMPEZA (segurança)
   Celery Beat a cada 15 min:
   → deleta jobs com status != "done" e mtime > 30 min (processamento travado)
   → deleta jobs com status "done" e mtime > 2h (usuário não baixou)
```

### 4.1 Suporte a ZIP

```
Upload .zip → Worker extrai em /tmp/anon/jobs/{id}/extracted/
→ processa cada arquivo individualmente (mesmo pipeline)
→ reempacota em /tmp/anon/jobs/{id}/output/anon_{nome_original}.zip
→ entrega o zip ao usuário
→ deleta tudo
```

Arquivos suportados dentro do ZIP: os mesmos do CLI (txt, csv, json, pdf, docx, xlsx, xml, png, jpg…).  
Arquivos não suportados dentro do ZIP: ignorados com log no summary.

---

## 5. Gestão de Disco

**Constraint:** O servidor é compartilhado. Sem partição dedicada, sem modificações no SO.

```
Caminho configurável via variável de ambiente:
  ANON_JOBS_DIR=/home/user/anon-jobs   ← padrão se não definido: /tmp/anon/jobs

Worst case (demo, 1 usuário):
  input:  10 GB
  output: ~10 GB
  ZIP extract: + 10 GB
  Total peak: ~30 GB no diretório ANON_JOBS_DIR

Controle de disco — sem partição dedicada:
  1. Worker verifica espaço livre antes de aceitar job:
       shutil.disk_usage(ANON_JOBS_DIR).free < required_bytes → rejeita com 507
  2. Celery Beat limpa jobs > 2h a cada 15 min (nenhum arquivo acumula)
  3. Input deletado imediatamente após leitura
  4. Output deletado logo após o download
  5. Limite de 1 job simultâneo na fila gpu (concurrency=1) — sem sobreposição de picos
```

**Por que não tmpfs?** 10 GB em RAM não é viável — e tmpfs usaria RAM compartilhada do servidor. O diretório configurável via `ANON_JOBS_DIR` é a solução adequada para servidor compartilhado.

---

## 6. Gerenciamento de Chaves

```python
# FastAPI — recebe chave, NUNCA loga, NUNCA persiste em disco
@app.post("/api/jobs")
async def create_job(key: str = Form(default="")):
    job_id = str(uuid4())
    if key:
        redis.setex(f"job:{job_id}:key", 3600, key)  # TTL 1h

# Worker Celery — usa e deleta imediatamente
def process_job(job_id: str):
    key = redis.get(f"job:{job_id}:key") or ""
    redis.delete(f"job:{job_id}:key")  # deleta ANTES de processar
    env = {**os.environ, "ANON_SECRET_KEY": key}
    # chama AnonymizationOrchestrator com env
```

**Garantias:**
- Chave nunca vai para disco (Redis com `appendonly no`)
- Redis bind em `127.0.0.1` — não exposto na rede
- HTTPS obrigatório — chave nunca trafega em claro
- Chave nunca aparece em logs (FastAPI: `exclude_unset=True`, sem request logging do body)

---

## 7. API Contract

### `POST /api/jobs`
Upload + criação de job.

**Request:** `multipart/form-data`
```
file:     UploadFile   (obrigatório)
key:      str          (opcional — ativa tier 10 GB)
strategy: str          (filtered | standalone | regex | hybrid)
lang:     str          (en | pt | es | ...)
entities: str          (JSON array: ["EMAIL_ADDRESS", "CPF", ...])
config:   str          (YAML inline — perfil completo, opcional)
```

**Response 202:**
```json
{ "job_id": "abc-123", "status": "queued", "queue": "gpu" }
```

**Response 413:** arquivo maior que o limite do tier.

---

### `GET /api/jobs/{id}/status`
Polling de status.

```json
{ "status": "running", "progress": 45, "eta_seconds": 30 }
{ "status": "done", "output_size_bytes": 1048576 }
{ "status": "error", "message": "Unsupported file type inside ZIP" }
```

---

### `GET /api/jobs/{id}/download`
StreamingResponse do arquivo anonimizado. Deleta output após stream.

**Headers de resposta:**
```
Content-Disposition: attachment; filename="anon_relatorio.pdf"
Content-Type: application/octet-stream
X-Output-Size: 1048576
```

---

### `GET /api/entities`
Lista dinâmica de entidades disponíveis por estratégia + modelo.

**Query params:** `?strategy=filtered&model=Davlan/xlm-roberta-base-ner-hrl&lang=pt`

```json
{
  "groups": [
    {
      "label": "Identidade",
      "entities": [
        { "id": "PERSON",        "label": "Pessoa",         "example": "João Silva" },
        { "id": "EMAIL_ADDRESS", "label": "E-mail",         "example": "joao@example.com" },
        { "id": "PHONE_NUMBER",  "label": "Telefone",       "example": "+55 11 91234-5678" }
      ]
    },
    {
      "label": "Rede",
      "entities": [
        { "id": "IP_ADDRESS",    "label": "IP",             "example": "192.168.1.1" },
        { "id": "URL",           "label": "URL",             "example": "https://exemplo.com" }
      ]
    },
    {
      "label": "Documentos BR (custom)",
      "entities": [
        { "id": "CPF",           "label": "CPF",            "example": "123.456.789-09" },
        { "id": "CNPJ",          "label": "CNPJ",           "example": "12.345.678/0001-90" }
      ]
    }
  ]
}
```

---

### `POST /api/profiles/validate`
Valida um YAML de perfil antes de importar (sem executar nada).

```json
{ "valid": true, "entities_count": 5, "patterns_count": 3 }
{ "valid": false, "error": "Regex inválido na linha 12: padrão não compilável" }
```

---

## 8. UX / Interface

### 8.1 Filosofia

> A interface não é o produto. O arquivo anonimizado é o produto.  
> Cada pixel que não ajuda o usuário a chegar lá é ruído cognitivo.

**Princípios aplicados:**
- **Lei de Hick:** não apresentar escolhas antes de serem relevantes. Estratégia aparece *depois* do upload.
- **Lei de Fitts:** área de drop grande o suficiente para não exigir precisão.
- **Lei de Miller:** no máximo 7±2 entidades visíveis por grupo — usar grupos colapsáveis.
- **Gestalt (proximidade + similaridade):** entidades agrupadas por categoria, mesmo espaçamento interno.
- **Nielsen #1 (visibilidade do status):** progresso sempre visível, nunca tela em branco.
- **WCAG 2.1 AA:** contraste ≥ 4.5:1, foco visível, sem informação só por cor.

---

### 8.2 Fluxo de Telas

```
[TELA 1 — HOME]
┌─────────────────────────────────────────────────────────────────┐
│  AnonShield                              [Importar Perfil ↑]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                                                         │  │
│   │         ↑  Arraste seu arquivo aqui                    │  │
│   │         ou clique para selecionar                      │  │
│   │                                                         │  │
│   │   .txt .csv .json .pdf .docx .xlsx .xml .zip           │  │
│   │   PNG JPG TIFF BMP WEBP GIF                            │  │
│   │                                                         │  │
│   │   ── Sem chave: máx. 1 MB ── Com chave: máx. 10 GB ── │  │
│   └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│   Chave de anonimização (opcional)                              │
│   [••••••••••••••••••••] [👁]  ← toggle visibilidade           │
│   ℹ️  Sem chave: sem reversibilidade. Com chave: determinístico. │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
    ↓ após selecionar arquivo

[TELA 2 — CONFIGURAÇÃO]
┌─────────────────────────────────────────────────────────────────┐
│  ← Trocar arquivo    relatorio.pdf (2.3 MB)    [Usar Perfil ▾] │
├──────────────────────────┬──────────────────────────────────────┤
│                          │                                      │
│  ESTRATÉGIA              │  ENTIDADES                           │
│                          │                                      │
│  ○ Filtrada (padrão)     │  Buscar entidade...  [Todas] [Nenhuma]│
│  ○ Standalone (GPU)      │                                      │
│  ● Regex (mais rápida)   │  ▾ Identidade                       │
│  ○ Híbrida               │    ☑ Pessoa          ☑ E-mail        │
│                          │    ☑ Telefone        ☐ Organização   │
│  IDIOMA                  │                                      │
│  [Português (pt)    ▾]   │  ▾ Rede                             │
│                          │    ☑ IP Address      ☐ URL           │
│  MODELO NER              │    ☐ Hostname        ☐ MAC           │
│  [xlm-roberta       ▾]   │                                      │
│                          │  ▾ Documentos BR ✦ custom            │
│  SLUG LENGTH             │    ☑ CPF             ☑ CNPJ          │
│  [8 chars    ─────────]  │    ☐ CEP             ☐ RG            │
│                          │                                      │
├──────────────────────────┴──────────────────────────────────────┤
│  PADRÕES REGEX CUSTOMIZADOS                          [+ Adicionar]│
│                                                                 │
│  ┌───────────────────┬────────────────────────┬────────┬──────┐ │
│  │ Nome (tipo)       │ Padrão                 │ Score  │      │ │
│  ├───────────────────┼────────────────────────┼────────┼──────┤ │
│  │ BANK_ACCOUNT      │ \d{4}[\s-]?\d{4}...   │ 0.90   │ [×]  │ │
│  └───────────────────┴────────────────────────┴────────┴──────┘ │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Salvar como Perfil]           [Anonimizar →]                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

[TELA 3 — PROCESSANDO]
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                    relatorio.pdf                                │
│                                                                 │
│        ████████████████████░░░░░░░░░  62%                      │
│        Detectando entidades... ~18s restantes                   │
│                                                                 │
│                      [Cancelar]                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

[TELA 4 — CONCLUÍDO]
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│              ✓  Anonimização concluída                          │
│                                                                 │
│   47 entidades substituídas em 3.2s                             │
│   Pessoa: 12  ·  E-mail: 8  ·  CPF: 4  ·  IP: 23              │
│                                                                 │
│         [↓ Baixar anon_relatorio.pdf  (2.1 MB)]                │
│                                                                 │
│   ⚠️  Arquivo disponível por tempo limitado.                    │
│   Após o download, é removido do servidor.                      │
│                                                                 │
│                [Anonimizar outro arquivo]                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 8.3 Configuration Builder — Padrão de Interação

**Seleção de Entidades (por que chips/checkboxes em grupos, não text input):**

O usuário *nunca digita* um nome de entidade. O sistema chama `GET /api/entities?strategy=...&model=...` assim que estratégia ou modelo mudam e renderiza os grupos. Justificativa: elimina erro de digitação, torna o scope visível, reduz carga cognitiva (reconhecer > recordar — Nielsen #6).

**Regex Builder — modal:**
```
[+ Adicionar Padrão]
┌─────────────────────────────────────────────────────┐
│  Novo Padrão Regex                              [×]  │
│                                                     │
│  Nome (tipo de entidade)                            │
│  [BANK_ACCOUNT                                   ]  │
│                                                     │
│  Expressão Regular                                  │
│  [\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}       ]  │
│                                                     │
│  Confiança (score)                                  │
│  [──────────●──────────] 0.90                       │
│                                                     │
│  Testar padrão                                      │
│  [1234-5678-9012-3456                            ]  │
│   ✓  Match: "1234-5678-9012-3456"                  │
│                                                     │
│            [Cancelar]  [Adicionar]                  │
└─────────────────────────────────────────────────────┘
```

O campo "Testar padrão" valida o regex em tempo real (client-side, sem request). Feedback imediato: verde se match, vermelho se erro de compilação, cinza se sem match. Princípio: feedback imediato reduz erros e custo de correção (Nielsen #9).

---

### 8.4 Sistema de Perfis

**Objetivo:** usuário cria uma configuração uma vez (ex: "Cheques BR"), salva, baixa como YAML, e pode reusar em qualquer sessão futura ou via CLI diretamente.

**Download de perfil:**
```yaml
# Gerado pelo AnonShield Web
# Perfil: Cheques BR
# Criado: 2026-04-11

strategy: regex
lang: pt
slug_length: 8

entities:
  - CPF
  - CNPJ
  - EMAIL_ADDRESS
  - PHONE_NUMBER
  - BANK_ACCOUNT
  - CREDIT_CARD

custom_patterns:
  - entity_type: BANK_ACCOUNT
    pattern: '\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}'
    score: 0.90
  - entity_type: CHEQUE_ID
    pattern: 'CHQ-\d{8}'
    score: 0.95
```

**Import de perfil:** botão "Importar Perfil ↑" no header → file picker de .yaml/.json → `POST /api/profiles/validate` → se válido, popula toda a UI com as configs do perfil → usuário pode ajustar antes de processar.

**Perfis offline:** o arquivo YAML é exatamente o mesmo formato aceito pelo `--config` do CLI. Zero fricção entre web e linha de comando.

---

### 8.5 Suporte a ZIP — UX

Ao detectar `.zip` no upload, a UI mostra:

```
relatorio.zip (15.2 MB)
Contém 8 arquivos:
  ✓ relatorio_jan.pdf     ← suportado
  ✓ dados.csv             ← suportado
  ✓ scan001.png           ← suportado
  ✗ apresentacao.pptx     ← não suportado, será ignorado
  ✓ contratos.docx        ← suportado
  ...

Resultado: anon_relatorio.zip com os arquivos processados.
Os arquivos não suportados não serão incluídos.
```

A análise do conteúdo do ZIP acontece client-side (Web API `zip.js`) — sem upload apenas para inspecionar. Reduz round-trip, dá feedback instantâneo.

---

### 8.6 Design Tokens (base)

```css
/* Cores — WCAG AA garantido */
--color-surface:        #0f1117;   /* fundo */
--color-surface-raised: #1a1d27;   /* cards, painéis */
--color-border:         #2d3148;
--color-text-primary:   #e8eaf0;   /* contraste 13.5:1 */
--color-text-secondary: #8b90a8;   /* contraste 4.6:1 */
--color-accent:         #6c63ff;   /* ações primárias */
--color-accent-hover:   #8178ff;
--color-success:        #22c55e;
--color-error:          #ef4444;
--color-warning:        #f59e0b;

/* Tipografia */
--font-sans:    'Inter Variable', system-ui, sans-serif;
--font-mono:    'JetBrains Mono', monospace;  /* regex, exemplos */
--text-sm:      0.875rem;
--text-base:    1rem;
--text-lg:      1.125rem;
--line-height:  1.6;

/* Espaçamento (escala 4px) */
--space-1: 4px;   --space-2: 8px;   --space-3: 12px;
--space-4: 16px;  --space-6: 24px;  --space-8: 32px;

/* Animações — propósito único: comunicar estado */
--duration-fast:   100ms;   /* feedback hover/focus */
--duration-normal: 200ms;   /* transições de estado */
--duration-slow:   350ms;   /* entrada de modais */
--ease-out:  cubic-bezier(0.0, 0.0, 0.2, 1);
--ease-in:   cubic-bezier(0.4, 0.0, 1.0, 1);

/* Bordas */
--radius-sm: 6px;  --radius-md: 10px;  --radius-lg: 16px;
```

---

### 8.7 Motion — Regras

| Elemento | Animação | Duração | Por quê |
|---------|----------|---------|--------|
| Drop zone hover | `border-color` + `background` | 150ms ease-out | Confirma interatividade (feedback imediato) |
| Progress bar | `width` linear | contínuo | Comunica progresso real |
| Modal entrada | `opacity 0→1` + `translateY(8px→0)` | 250ms ease-out | Orienta atenção, evita pop-in abrupto |
| Checkbox entidade | `scale(0.8→1)` no check | 100ms | Confirma seleção sem ruído |
| Toast de erro | slide-in top | 200ms ease-out | Urgência sem susto |
| Status "concluído" | ✓ com `scale(0→1)` | 300ms spring | Recompensa — único momento de "alegria" |

**O que NÃO tem animação:** hover em links de texto, abertura de grupos de entidades, resize de painéis. Decoração = ruído.

---

### 8.8 Acessibilidade (WCAG 2.1 AA)

- Drop zone acessível via teclado (`role="button"`, `tabindex="0"`, `Enter`/`Space` abre file picker)
- Entidades selecionáveis com teclado (Tab + Space)
- Progress bar: `role="progressbar"` com `aria-valuenow`
- Modais: focus trap, `aria-modal="true"`, `Escape` fecha
- Mensagens de erro: `role="alert"` (lidas por screen reader imediatamente)
- Sem informação transmitida apenas por cor (ícone acompanha sempre)
- Contraste de todos os tokens verificado acima de 4.5:1

---

## 9. Estrutura de Projeto (Monorepo)

```
tool/                          ← repo existente (CLI)
├── anon.py
├── src/anon/
│
└── web/
    ├── frontend/              ← SvelteKit
    │   ├── src/
    │   │   ├── routes/
    │   │   │   ├── +page.svelte          ← home (upload)
    │   │   │   ├── +layout.svelte
    │   │   │   └── jobs/[id]/
    │   │   │       └── +page.svelte      ← status + download
    │   │   ├── lib/
    │   │   │   ├── components/
    │   │   │   │   ├── DropZone.svelte
    │   │   │   │   ├── EntitySelector.svelte
    │   │   │   │   ├── RegexBuilder.svelte
    │   │   │   │   ├── ProfilePanel.svelte
    │   │   │   │   ├── ProgressBar.svelte
    │   │   │   │   └── KeyInput.svelte
    │   │   │   ├── stores/
    │   │   │   │   ├── config.ts         ← estado da configuração
    │   │   │   │   └── job.ts            ← estado do job ativo
    │   │   │   └── api.ts                ← cliente tipado da API
    │   │   └── app.css                   ← design tokens CSS
    │   ├── package.json
    │   └── svelte.config.js
    │
    └── backend/               ← FastAPI
        ├── main.py
        ├── routers/
        │   ├── jobs.py        ← POST /api/jobs, GET /api/jobs/{id}/*
        │   └── entities.py    ← GET /api/entities
        ├── services/
        │   ├── job_service.py
        │   ├── storage.py     ← gestão de /tmp/anon/
        │   └── profile.py     ← validação de YAML
        ├── workers/
        │   ├── celery_app.py
        │   └── tasks.py       ← process_job()
        └── Dockerfile          ← uv sync --group web (deps via pyproject.toml)
```

---

## 10. Docker Compose

```yaml
# web/docker-compose.yml
services:

  nginx:
    image: nginx:alpine
    ports: ["443:443", "80:80"]
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on: [frontend, backend]

  frontend:
    build: ./frontend
    expose: ["3000"]
    environment:
      - PUBLIC_API_URL=https://seu-dominio.com/api

  backend:
    build: ./backend
    expose: ["8000"]
    volumes:
      - anon-tmp:/anon-jobs
    environment:
      - REDIS_URL=redis://redis:6379/0
      - ANON_JOBS_DIR=/anon-jobs   # diretório configurável — sem partição dedicada
    depends_on: [redis]

  worker-fast:
    build: ./backend
    command: celery -A workers.celery_app worker -Q fast --concurrency 4 --loglevel=warning
    volumes:
      - anon-tmp:/anon-jobs
      - ../../src:/app/src   # monta o código anon existente
    environment:
      - REDIS_URL=redis://redis:6379/0
      - ANON_JOBS_DIR=/anon-jobs
    depends_on: [redis]

  worker-gpu:
    build: ./backend
    command: celery -A workers.celery_app worker -Q gpu --concurrency 1 --pool=solo --loglevel=warning
    volumes:
      - anon-tmp:/anon-jobs
      - ../../src:/app/src
    environment:
      - REDIS_URL=redis://redis:6379/0
      - ANON_JOBS_DIR=/anon-jobs
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    depends_on: [redis]

  beat:
    build: ./backend
    command: celery -A workers.celery_app beat --loglevel=warning
    environment:
      - ANON_JOBS_DIR=/anon-jobs
    depends_on: [redis]

  redis:
    image: redis:7-alpine
    command: redis-server --bind 127.0.0.1 --save "" --appendonly no
    expose: ["6379"]

volumes:
  anon-tmp:
    # Volume Docker gerenciado — sem bind mount para /data/anon
    # Para servidor compartilhado: defina ANON_JOBS_DIR no .env
    # Exemplo: ANON_JOBS_DIR=/home/seuuser/anon-jobs
```

---

## 11. Nginx Config (pontos críticos)

```nginx
# web/nginx.conf (trechos críticos)

http {
  # Sem limite de body — FastAPI controla por tier
  client_max_body_size 0;

  # Timeout longo para uploads de 10 GB
  proxy_read_timeout    7200s;
  proxy_send_timeout    7200s;
  proxy_connect_timeout 60s;

  # Não bufferizar uploads — stream direto ao backend
  proxy_request_buffering off;

  # Não bufferizar downloads — stream direto ao browser
  proxy_buffering off;

  server {
    listen 443 ssl;
    server_name seu-dominio.com;

    ssl_certificate     /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;

    # SvelteKit
    location / {
      proxy_pass http://frontend:3000;
    }

    # FastAPI
    location /api/ {
      proxy_pass http://backend:8000;
      # Headers para SSE
      proxy_set_header Connection '';
      proxy_http_version 1.1;
      chunked_transfer_encoding on;
    }
  }

  # Redireciona HTTP → HTTPS
  server {
    listen 80;
    return 301 https://$host$request_uri;
  }
}
```

---

## 12. Path de Escalabilidade

### Demo (agora)
- 1 worker-fast, 1 worker-gpu
- Redis single instance
- SQLite não usado (db_mode=in-memory)
- 1 instância FastAPI
- 1 instância SvelteKit

### Produção (quando necessário — sem reescrever nada)

| Mudança | O que habilita |
|---------|---------------|
| Aumentar `--concurrency` no worker-fast | Mais jobs regex simultâneos |
| Adicionar instâncias worker-gpu | Mais jobs NER em paralelo |
| Nginx upstream com múltiplas instâncias backend | Requests concorrentes (upload + polling) |
| PostgreSQL para `job:{id}:meta` | Histórico, auditoria, admin panel |
| Redis Sentinel ou Cluster | Alta disponibilidade do broker |
| Rate limiting no Nginx | Proteção contra abuso |
| `/data/anon` em storage NFS | Múltiplos servidores compartilhando jobs |

---

## 13. Checklist de Segurança

- [ ] HTTPS obrigatório — redirecionar HTTP → HTTPS no Nginx
- [ ] Redis bind em `127.0.0.1` + senha (`requirepass`)
- [ ] `appendonly no` no Redis — chave nunca persiste em disco
- [ ] Validação de Content-Type no backend (não confiar no cliente)
- [ ] Path traversal: jobs isolados em `UUID/` — nunca aceitar `../`
- [ ] Chave nunca aparece em logs (configurar `log_config` do uvicorn)
- [ ] Headers de segurança no Nginx: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`
- [ ] Tamanho máximo verificado via streaming (não carregar arquivo inteiro para checar)
- [ ] ZIP: limitar profundidade de extração, limitar arquivos (proteção zip bomb)
- [ ] Celery Beat: limpar jobs > 2h sem download (disco não acumula)
- [ ] Monitoramento de disco: alerta se `/data/anon` > 80%
- [ ] Partição `/data/anon` separada do sistema (disco cheio não derruba o servidor)

<script lang="ts">
  import { onMount } from 'svelte';
  import { locale } from '$lib/i18n';

  // ── Client-side regex demo ────────────────────────────────────────────────
  const SAMPLE = `Meeting notes — Q4 Security Review
Attendees: Sarah Chen (sarah.chen@acme.com), Marcus Rodriguez
Phone: +1 (555) 234-5678  ·  Alt: (415) 900-2211

Action items:
  • Card on file: 4532 8901 2345 6789 (exp. 09/27)
  • Migrate server 192.168.1.45 → new host at 10.0.0.12
  • Patch CVE-2024-12345 before Friday
  • API token: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c3IifQ.abc
  • Leaked URL: https://internal.corp/api?key=s3cr3t_v4lu3
  • File hash: a3f5b2c1d4e67890123456789012345678901234abcdef0123456789`;

  const PATTERNS = [
    { type: 'EMAIL',       color: '#4ade80', rx: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/ },
    { type: 'PHONE',       color: '#fbbf24', rx: /(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}/ },
    { type: 'CREDIT_CARD', color: '#f87171', rx: /\b(?:\d{4}[-\s]?){3}\d{4}\b/ },
    { type: 'IP_ADDRESS',  color: '#c084fc', rx: /\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b/ },
    { type: 'CVE_ID',      color: '#f472b6', rx: /CVE-\d{4}-\d{4,7}/ },
    { type: 'AUTH_TOKEN',  color: '#38bdf8', rx: /\bBearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]*/ },
    { type: 'URL',         color: '#60a5fa', rx: /https?:\/\/[^\s<>'"]+/ },
    { type: 'HASH',        color: '#94a3b8', rx: /\b[a-f0-9]{32,64}\b/ },
  ] as const;

  interface Hit { start: number; end: number; type: string; color: string; raw: string; }

  function slugify(s: string, type: string): string {
    let h = type.length * 17;
    for (const c of s) h = (Math.imul(h, 31) + c.charCodeAt(0)) | 0;
    return Math.abs(h).toString(36).padStart(6, '0').slice(0, 6);
  }

  function esc(s: string): string {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function findHits(text: string): Hit[] {
    const hits: Hit[] = [];
    for (const { type, color, rx } of PATTERNS) {
      const re = new RegExp(rx.source, 'g');
      let m: RegExpExecArray | null;
      while ((m = re.exec(text)) !== null) {
        hits.push({ start: m.index, end: m.index + m[0].length, type, color, raw: m[0] });
      }
    }
    hits.sort((a, b) => a.start - b.start);
    const out: Hit[] = [];
    let cursor = 0;
    for (const h of hits) {
      if (h.start >= cursor) { out.push(h); cursor = h.end; }
    }
    return out;
  }

  function buildHtml(text: string, hits: Hit[]): string {
    let html = '';
    let pos = 0;
    for (const h of hits) {
      html += esc(text.slice(pos, h.start));
      const sl = slugify(h.raw, h.type);
      html += `<mark class="ent" style="color:${h.color};--c:${h.color}" title="${h.type}: ${esc(h.raw)}">[${h.type.replace(/_/g,'·')}-${sl}]</mark>`;
      pos = h.end;
    }
    html += esc(text.slice(pos));
    return html;
  }

  let input = $state(SAMPLE);
  let hits = $derived(findHits(input));
  let outputHtml = $derived(buildHtml(input, hits));
  let legend = $derived.by(() => {
    const m = new Map<string, { color: string; n: number }>();
    for (const h of hits) {
      const e = m.get(h.type) ?? { color: h.color, n: 0 };
      e.n++;
      m.set(h.type, e);
    }
    return [...m.entries()].sort((a, b) => b[1].n - a[1].n);
  });

  // ── Pipeline node detail popover ─────────────────────────────────────────
  let activeNode = $state<number | null>(null);
  function toggleNode(i: number) { activeNode = activeNode === i ? null : i; }

  function handlePipelineClick(e: MouseEvent) {
    if (activeNode === null) return;
    const target = e.target as HTMLElement;
    if (!target.closest('.pipe-node')) activeNode = null;
  }

  // ── Scroll-triggered counter animation ───────────────────────────────────
  let statsVisible = $state(false);
  let statsRef: HTMLElement;

  // ── Scroll-reveal for sections ────────────────────────────────────────────
  onMount(() => {
    // Stats counter observer — fire as soon as 10% is visible
    const statsObs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { statsVisible = true; statsObs.disconnect(); }
    }, { threshold: 0.1 });
    if (statsRef) statsObs.observe(statsRef);

    // General reveal observer — trigger on first pixel entering viewport
    const revealObs = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
          revealObs.unobserve(entry.target);
        }
      });
    }, { threshold: 0, rootMargin: '0px 0px 0px 0px' });

    document.querySelectorAll('.reveal').forEach(el => revealObs.observe(el));

    return () => { statsObs.disconnect(); revealObs.disconnect(); };
  });

  const pt = $derived($locale === 'pt');
</script>

<svelte:head>
  <title>AnonShield — On-premise PII anonymization</title>
  <meta name="description" content="Research-grade sensitive entities redaction. Zero cloud, zero persistence. Built at UNIPAMPA — published at SBSeg 2025, ERRC 2025, SBRC 2026." />
</svelte:head>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!-- HERO                                                                   -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->
<section class="hero">
  <div class="hero-inner">

    <h1 class="hero-title">
      <span class="brand">AnonShield</span>
      <span class="hero-rule">{pt ? 'Anonimização de entidades on-premise.' : 'On-premise entities anonymization.'}</span>
    </h1>
    <p class="hero-sub">
      {pt
        ? 'Redação de dados sensíveis de nível acadêmico. Zero nuvem, zero persistência. Publicado no SBSeg 2025, ERRC 2025 e SBRC 2026.'
        : 'Research-grade sensitive data redaction. Zero cloud, zero persistence. Published at SBSeg 2025, ERRC 2025, and SBRC 2026.'}
    </p>

    <!-- ── LIVE DEMO ── -->
    <div class="demo-wrap">
      <div class="demo-label">
        <span class="demo-live">
          <span class="live-dot"></span>
          {pt ? 'Demo ao vivo — edite o texto' : 'Live demo — edit the text'}
        </span>
        <span class="demo-hint">{pt ? 'executa no browser, sem servidor' : 'runs in-browser, no server'}</span>
      </div>

      <div class="editor">
        <div class="panel panel-in">
          <header class="panel-head">
            <span class="panel-label">input</span>
            <span class="panel-hint">editable</span>
          </header>
          <textarea
            class="panel-body"
            spellcheck="false"
            autocomplete="off"
            bind:value={input}
            aria-label="Input text"
          ></textarea>
        </div>

        <div class="divider" aria-hidden="true">
          <div class="flow-line">
            <div class="flow-dot d1"></div>
            <div class="flow-dot d2"></div>
            <div class="flow-dot d3"></div>
          </div>
        </div>

        <div class="panel panel-out">
          <header class="panel-head">
            <span class="panel-label">anonymized</span>
            <span class="panel-count" class:has-hits={hits.length > 0}>
              {hits.length} {hits.length === 1 ? (pt ? 'entidade' : 'entity') : (pt ? 'entidades' : 'entities')} {pt ? 'redigidas' : 'redacted'}
            </span>
          </header>
          <div class="panel-body output-body" aria-live="polite">
            <!-- eslint-disable-next-line svelte/no-at-html-tags -->
            {@html outputHtml}
          </div>
        </div>
      </div>

      {#if legend.length > 0}
        <div class="legend" role="list">
          {#each legend as [type, { color, n }]}
            <div class="legend-item" role="listitem" style="--c:{color}">
              <span class="legend-dot"></span>
              <span class="legend-type">{type}</span>
              <span class="legend-n">{n}</span>
            </div>
          {/each}
        </div>
      {/if}
    </div>

    <div class="hero-actions">
      <a href="/app" class="cta-primary">{pt ? 'Abrir AnonShield →' : 'Launch AnonShield →'}</a>
      <span class="hero-meta">{pt ? 'Sem cadastro. Sem nuvem. Self-hostable.' : 'No sign-up. No cloud. Self-hostable.'}</span>
    </div>
  </div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!-- PIPELINE ANIMATION                                                     -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->
<section class="pipeline" onclick={handlePipelineClick}>
  <!-- Decorative elements clipped to section bounds -->
  <div class="pipeline-deco" aria-hidden="true">
    <div class="scan-beam"></div>
    <div class="dot-grid"></div>
  </div>

  <div class="pipeline-inner">
    <p class="section-label">{pt ? 'Como funciona' : 'How it works'}</p>
    <h2 class="section-title pipe-heading">
      {pt ? 'Privacidade garantida.' : 'Privacy guaranteed.'}
      <span class="pipe-sub-head">{pt ? 'Processamos tudo — sem guardar nada.' : 'We process everything — without keeping anything.'}</span>
    </h2>

    <div class="pipe-flow">
      <!-- ── NODE 1: Input ── -->
      <div class="pipe-node n1" style="--nc:#60a5fa">
        <div class="node-halo" aria-hidden="true"></div>
        <button class="node-ring" onclick={() => toggleNode(1)} aria-expanded={activeNode === 1} aria-label="Input stage details">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="12" y1="18" x2="12" y2="12"/>
            <line x1="9" y1="15" x2="12" y2="12"/>
            <line x1="15" y1="15" x2="12" y2="12"/>
          </svg>
        </button>
        <span class="node-name">{pt ? 'Entrada' : 'Input'}</span>
        <span class="node-note">TXT · PDF · DOCX · ZIP</span>
        {#if activeNode === 1}
          <div class="node-detail">
            <div class="nd-header" style="--nc:#60a5fa">
              <span class="nd-icon" style="--nc:#60a5fa">↑</span>
              <span class="nd-title">{pt ? 'Entrada de arquivo' : 'File Input'}</span>
            </div>
            <div class="nd-stats">
              <span class="nd-stat">10+ {pt ? 'formatos' : 'formats'}</span>
              <span class="nd-stat">Streaming I/O</span>
              <span class="nd-stat">{pt ? 'Sem limite RAM' : 'No RAM limit'}</span>
            </div>
            <div class="nd-formats">
              {#each ['TXT','CSV','JSON','PDF','DOCX','XLSX','XML','ZIP','PNG','JPG'] as f}
                <span class="nd-fmt">{f}</span>
              {/each}
            </div>
            <p class="nd-desc">{pt ? 'Processamento incremental via streaming — arquivos de qualquer tamanho sem carregar na RAM.' : 'Incremental streaming — files of any size without loading into RAM.'}</p>
          </div>
        {/if}
      </div>

      <!-- connector 1→2 (blue → violet) -->
      <div class="pipe-connector" style="--ca:#60a5fa;--cb:#a78bfa">
        <div class="conn-track" aria-hidden="true"></div>
        <span class="conn-p cp1" style="--cd:0s"></span>
        <span class="conn-p cp2" style="--cd:.55s"></span>
        <span class="conn-p cp3" style="--cd:1.1s"></span>
        <span class="conn-p cp4" style="--cd:1.65s"></span>
      </div>

      <!-- ── NODE 2: Detect ── -->
      <div class="pipe-node n2" style="--nc:#a78bfa">
        <div class="node-halo" aria-hidden="true"></div>
        <button class="node-ring" onclick={() => toggleNode(2)} aria-expanded={activeNode === 2} aria-label="NER Detection stage details">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z"/>
            <circle cx="12" cy="12" r="3"/>
            <line x1="12" y1="5" x2="12" y2="3"/>
            <line x1="12" y1="21" x2="12" y2="19"/>
          </svg>
        </button>
        <span class="node-name">{pt ? 'Detecção NER' : 'NER Detection'}</span>
        <span class="node-note">{pt ? 'Transformer + regex' : 'Transformer + regex'}</span>
        {#if activeNode === 2}
          <div class="node-detail">
            <div class="nd-header" style="--nc:#a78bfa">
              <span class="nd-icon" style="--nc:#a78bfa">◎</span>
              <span class="nd-title">NER Detection</span>
            </div>
            <div class="nd-stats">
              <span class="nd-stat">50+ {pt ? 'entidades' : 'entities'}</span>
              <span class="nd-stat">GPU · LRU cache</span>
              <span class="nd-stat">21 regex</span>
            </div>
            <div class="nd-transform">
              <span class="nd-src">"John Doe"</span>
              <span class="nd-arrow">→</span>
              <span class="nd-tag" style="color:#a78bfa;border-color:rgba(167,139,250,0.3)">[PERSON]</span>
            </div>
            <div class="nd-transform">
              <span class="nd-src">CVE-2024-3400</span>
              <span class="nd-arrow">→</span>
              <span class="nd-tag" style="color:#f87171;border-color:rgba(248,113,113,0.3)">[CVE_ID]</span>
            </div>
            <p class="nd-desc">xlm-roberta multilingual + regex {pt ? 'para IPs, hashes, certificados e credenciais.' : 'for IPs, hashes, certs and credentials.'}</p>
          </div>
        {/if}
      </div>

      <!-- connector 2→3 (violet → amber) -->
      <div class="pipe-connector" style="--ca:#a78bfa;--cb:#fbbf24">
        <div class="conn-track" aria-hidden="true"></div>
        <span class="conn-p cp1" style="--cd:.2s"></span>
        <span class="conn-p cp2" style="--cd:.75s"></span>
        <span class="conn-p cp3" style="--cd:1.3s"></span>
        <span class="conn-p cp4" style="--cd:1.85s"></span>
      </div>

      <!-- ── NODE 3: Hash ── -->
      <div class="pipe-node n3" style="--nc:#fbbf24">
        <div class="node-halo" aria-hidden="true"></div>
        <button class="node-ring" onclick={() => toggleNode(3)} aria-expanded={activeNode === 3} aria-label="HMAC-SHA256 stage details">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
            <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
          </svg>
        </button>
        <span class="node-name">HMAC-SHA256</span>
        <span class="node-note">{pt ? 'Hash determinístico' : 'Deterministic hash'}</span>
        {#if activeNode === 3}
          <div class="node-detail">
            <div class="nd-header" style="--nc:#fbbf24">
              <span class="nd-icon" style="--nc:#fbbf24">⬡</span>
              <span class="nd-title">HMAC-SHA256</span>
            </div>
            <div class="nd-stats">
              <span class="nd-stat">0–256 bits</span>
              <span class="nd-stat">{pt ? 'Determinístico' : 'Deterministic'}</span>
              <span class="nd-stat">{pt ? 'Chave opcional' : 'Optional key'}</span>
            </div>
            <div class="nd-code">
              <span class="nd-code-line"><span class="nd-kw">key</span> + entity → <span class="nd-val">48624b5c</span></span>
              <span class="nd-code-line nd-muted">{pt ? 'sem chave → aleatório por run' : 'no key → random per run'}</span>
            </div>
            <p class="nd-desc">{pt ? 'Mesmo input + chave = mesmo token entre runs. Correlação entre documentos sem expor o dado original.' : 'Same input + key = same token across runs. Cross-document correlation without exposing raw data.'}</p>
          </div>
        {/if}
      </div>

      <!-- connector 3→4 (amber → emerald) -->
      <div class="pipe-connector" style="--ca:#fbbf24;--cb:#34d399">
        <div class="conn-track" aria-hidden="true"></div>
        <span class="conn-p cp1" style="--cd:.4s"></span>
        <span class="conn-p cp2" style="--cd:.95s"></span>
        <span class="conn-p cp3" style="--cd:1.5s"></span>
        <span class="conn-p cp4" style="--cd:2.05s"></span>
      </div>

      <!-- ── NODE 4: Shield ── -->
      <div class="pipe-node n4" style="--nc:#34d399">
        <div class="node-halo" aria-hidden="true"></div>
        <button class="node-ring" onclick={() => toggleNode(4)} aria-expanded={activeNode === 4} aria-label="Pseudonymization stage details">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
        </button>
        <span class="node-name">{pt ? 'Pseudonimização' : 'Pseudonymization'}</span>
        <span class="node-note">{pt ? 'Token HMAC substituído' : 'HMAC token replaced'}</span>
        {#if activeNode === 4}
          <div class="node-detail">
            <div class="nd-header" style="--nc:#34d399">
              <span class="nd-icon" style="--nc:#34d399">◈</span>
              <span class="nd-title">{pt ? 'Pseudonimização' : 'Pseudonymization'}</span>
            </div>
            <div class="nd-stats">
              <span class="nd-stat">50+ {pt ? 'tipos' : 'types'}</span>
              <span class="nd-stat">{pt ? 'Schema intacto' : 'Schema intact'}</span>
              <span class="nd-stat">6 {pt ? 'categorias' : 'categories'}</span>
            </div>
            <div class="nd-replace-demo">
              <div class="nd-replace-row">
                <span class="nd-replace-before">100.111.20.23</span>
                <span class="nd-replace-after">[IP_ADDRESS_<span style="color:#34d399">48624b</span>]</span>
              </div>
              <div class="nd-replace-row">
                <span class="nd-replace-before">john@corp.io</span>
                <span class="nd-replace-after">[EMAIL_ADDRESS_<span style="color:#34d399">9fc2a1</span>]</span>
              </div>
            </div>
            <p class="nd-desc">{pt ? 'Prefixo do tipo preservado. Estrutura XML/JSON/CSV mantida — só os valores mudam.' : 'Type prefix preserved. XML/JSON/CSV structure kept — only values change.'}</p>
          </div>
        {/if}
      </div>

      <!-- connector 4→5 (emerald → teal) -->
      <div class="pipe-connector" style="--ca:#34d399;--cb:#2dd4bf">
        <div class="conn-track" aria-hidden="true"></div>
        <span class="conn-p cp1" style="--cd:.6s"></span>
        <span class="conn-p cp2" style="--cd:1.15s"></span>
        <span class="conn-p cp3" style="--cd:1.7s"></span>
        <span class="conn-p cp4" style="--cd:2.25s"></span>
      </div>

      <!-- ── NODE 5: Output ── -->
      <div class="pipe-node n5" style="--nc:#2dd4bf">
        <div class="node-halo" aria-hidden="true"></div>
        <button class="node-ring" onclick={() => toggleNode(5)} aria-expanded={activeNode === 5} aria-label="Output stage details">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
        </button>
        <span class="node-name">{pt ? 'Saída' : 'Output'}</span>
        <span class="node-note">{pt ? 'Deletado após download' : 'Deleted after download'}</span>
        {#if activeNode === 5}
          <div class="node-detail">
            <div class="nd-header" style="--nc:#2dd4bf">
              <span class="nd-icon" style="--nc:#2dd4bf">↓</span>
              <span class="nd-title">{pt ? 'Saída' : 'Output'}</span>
            </div>
            <div class="nd-stats">
              <span class="nd-stat">{pt ? 'Download imediato' : 'Instant download'}</span>
              <span class="nd-stat">0 bytes {pt ? 'retidos' : 'retained'}</span>
            </div>
            <div class="nd-zero">
              <div class="nd-zero-row">
                <span class="nd-zero-label">{pt ? 'arquivo original' : 'original file'}</span>
                <span class="nd-zero-val nd-deleted">— {pt ? 'deletado' : 'deleted'}</span>
              </div>
              <div class="nd-zero-row">
                <span class="nd-zero-label">{pt ? 'arquivo anonimizado' : 'anonymized file'}</span>
                <span class="nd-zero-val nd-ok">↓ {pt ? 'baixar' : 'download'}</span>
              </div>
              <div class="nd-zero-row">
                <span class="nd-zero-label">{pt ? 'após download' : 'after download'}</span>
                <span class="nd-zero-val nd-deleted">— {pt ? 'deletado' : 'deleted'}</span>
              </div>
            </div>
            <p class="nd-desc">{pt ? 'Nada fica no servidor. 0 bytes de dados sensíveis em disco após o ciclo completo.' : 'Nothing stays on the server. 0 bytes of sensitive data on disk after the full cycle.'}</p>
          </div>
        {/if}
      </div>
    </div>

    <p class="pipe-note">
      {pt
        ? 'Chave nunca armazenada no servidor — usada apenas em memória para computar HMAC · Arquivo de saída deletado imediatamente após download'
        : 'Key never stored server-side — used only in-memory for HMAC computation · Output file deleted immediately after download'}
    </p>
  </div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!-- STATS                                                                  -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->
<section class="stats-section reveal" bind:this={statsRef}>
  <div class="stats-inner">
    <div class="stat-block">
      <span class="stat-val" class:animated={statsVisible}>738<span class="stat-unit">×</span></span>
      <span class="stat-desc">{pt ? 'mais rápido que AnonLFI v2.0' : 'faster than AnonLFI v2.0'}</span>
    </div>
    <div class="stat-block">
      <span class="stat-val" class:animated={statsVisible}>94.2<span class="stat-unit">%</span></span>
      <span class="stat-desc">F1 {pt ? 'em dataset OpenVAS' : 'on OpenVAS dataset'}</span>
    </div>
    <div class="stat-block">
      <span class="stat-val" class:animated={statsVisible}>96.7<span class="stat-unit">%</span></span>
      <span class="stat-desc">{pt ? 'recall (filtered/hybrid, OpenVAS)' : 'Recall (filtered/hybrid, OpenVAS)'}</span>
    </div>
    <div class="stat-block">
      <span class="stat-val" class:animated={statsVisible}>550<span class="stat-unit">MB</span></span>
      <span class="stat-desc">{pt ? 'em menos de 10 min (GPU)' : 'in under 10 min (GPU)'}</span>
    </div>
    <div class="stat-block">
      <span class="stat-val" class:animated={statsVisible}>0</span>
      <span class="stat-desc">{pt ? 'chamadas à nuvem' : 'cloud calls'}</span>
    </div>
    <div class="stat-block">
      <span class="stat-val" class:animated={statsVisible}>1<span class="stat-unit">MB</span></span>
      <span class="stat-desc">{pt ? 'limite demo (configurável)' : 'demo limit (configurable)'}</span>
    </div>
  </div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!-- FORMATS                                                                -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->
<div class="formats-bar reveal">
  <span class="formats-lbl">{pt ? 'Formatos suportados' : 'Supported formats'}</span>
  <div class="formats-tags">
    {#each ['TXT','CSV','JSON','JSONL','PDF','DOCX','XLSX','XML','ZIP','PNG','JPG','TIFF','BMP','WEBP'] as fmt}
      <code class="fmt-tag">{fmt}</code>
    {/each}
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!-- RESEARCH                                                               -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->
<section class="research reveal">
  <div class="research-inner">
    <p class="section-label">{pt ? 'Linha de pesquisa' : 'Research lineage'}</p>
    <h2 class="section-title">
      {pt ? '3 gerações. 738× mais rápido.' : '3 generations. 738× faster.'}
    </h2>
    <p class="research-sub">
      {pt
        ? 'AnonShield é a terceira geração de uma linha de pesquisa peer-reviewed sobre anonimização on-premise para CSIRTs, iniciada pelo AnonLFI v1.0.'
        : 'AnonShield is the third generation of a peer-reviewed research line on on-premise anonymization for CSIRTs, started by AnonLFI v1.0.'}
    </p>

    <div class="timeline">
      <!-- Gen 1 -->
      <div class="tl-item">
        <div class="tl-marker">
          <span class="tl-gen">1</span>
        </div>
        <div class="tl-connector"></div>
        <div class="paper-card">
          <div class="paper-venue-row">
            <span class="paper-venue">SBSeg 2025</span>
            <span class="paper-gen">AnonLFI v1.0</span>
          </div>
          <h3 class="paper-title">Anonimização de Incidentes de Segurança com Reidentificação Controlada</h3>
          <p class="paper-authors">C. T. Bandel, J. P. R. Esteves, K. P. Guerra, L. M. Bertholdo, D. Kreutz, R. S. Miani</p>
          <p class="paper-context">
            {pt
              ? 'Focado em incidentes de segurança (não vulnerabilidades). NER híbrido + RegEx. Validado em 763 incidentes reais.'
              : 'Focused on security incidents (not vulnerability data). Hybrid NER + RegEx. Validated on 763 real incidents.'}
          </p>
          <div class="paper-metrics">
            <span class="pm pm-good">100% Precision</span>
            <span class="pm pm-good">97.38% Recall</span>
            <span class="pm pm-info">763 {pt ? 'Incidentes' : 'Incidents'}</span>
            <span class="pm pm-info">On-premise</span>
          </div>
        </div>
      </div>

      <!-- Gen 2 -->
      <div class="tl-item">
        <div class="tl-marker">
          <span class="tl-gen">2</span>
        </div>
        <div class="tl-connector"></div>
        <div class="paper-card">
          <div class="paper-venue-row">
            <span class="paper-venue">WRSeg / ERRC 2025</span>
            <span class="paper-gen">AnonLFI v2.0</span>
          </div>
          <h3 class="paper-title">AnonLFI 2.0: Extensible Architecture for PII Pseudonymization in CSIRTs with OCR and Technical Recognizers</h3>
          <p class="paper-authors">C. Kapelinski, D. Lautert, B. Machado, D. Kreutz</p>
          <p class="paper-context">
            {pt
              ? 'PoC para dados de vulnerabilidades. Adicionou HMAC-SHA256, XML/JSON e OCR. F1 92.1% (XML).'
              : 'PoC for vulnerability data. Added HMAC-SHA256, XML/JSON and OCR. F1 92.1% (XML).'}
          </p>
          <div class="paper-metrics">
            <span class="pm pm-good">92.1% F1 (XML)</span>
            <span class="pm pm-info">On-premise</span>
          </div>
        </div>
      </div>

      <!-- Gen 3 -->
      <div class="tl-item tl-current">
        <div class="tl-marker current">
          <span class="tl-gen">3</span>
        </div>
        <div class="paper-card current-paper">
          <div class="paper-venue-row">
            <span class="paper-venue accent-venue">SBRC 2026</span>
            <span class="paper-gen accent-gen">AnonShield ← {pt ? 'você está aqui' : 'you are here'}</span>
          </div>
          <h3 class="paper-title">AnonShield: Scalable On-Premise Pseudonymization for CSIRT Vulnerability Data</h3>
          <p class="paper-authors">C. Kapelinski, D. Lautert, B. Machado, I. G. Ferrão, D. Kreutz · UNIPAMPA / UBO</p>
          <p class="paper-context">
            {pt
              ? 'GPU-NER acelerado + cache LRU + streaming I/O + anonymization_config. 70.951 registros (550 MB) em <10 min. 94.2% F1, 96.7% Recall.'
              : 'GPU-accelerated NER + LRU cache + streaming I/O + anonymization_config. 70,951 records (550 MB) in <10 min. 94.2% F1, 96.7% Recall.'}
          </p>
          <div class="paper-metrics">
            <span class="pm pm-good">94.2% F1</span>
            <span class="pm pm-good">96.7% Recall</span>
            <span class="pm pm-hero">738× {pt ? 'mais rápido' : 'faster'}</span>
            <span class="pm pm-hero">&lt;10 min / 550 MB</span>
            <span class="pm pm-info">70,951 {pt ? 'registros' : 'records'}</span>
            <span class="pm pm-info">On-premise</span>
          </div>
          <a href="https://github.com/AnonShield/tool" target="_blank" class="paper-link">GitHub ↗</a>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!-- TEAM                                                                   -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->
<section class="team reveal">
  <div class="team-inner">
    <p class="section-label">{pt ? 'Equipe' : 'Team'}</p>
    <h2 class="section-title">{pt ? 'Construído por pesquisadores' : 'Built by researchers'}</h2>

    <div class="members">
      <div class="member">
        <span class="member-name">Cristhian Kapelinski</span>
        <span class="member-role">UNIPAMPA</span>
      </div>
      <div class="member">
        <span class="member-name">Douglas Lautert</span>
        <span class="member-role">UNIPAMPA</span>
      </div>
      <div class="member">
        <span class="member-name">Beatriz Machado</span>
        <span class="member-role">UNIPAMPA</span>
      </div>
      <div class="member">
        <span class="member-name">Diego Kreutz</span>
        <span class="member-role">UNIPAMPA</span>
      </div>
      <div class="member">
        <span class="member-name">Isadora G. Ferrão</span>
        <span class="member-role">UBO</span>
      </div>
    </div>

    <p class="team-affil">
      Universidade Federal do Pampa (UNIPAMPA) · Université de Bretagne Occidentale (UBO)
    </p>
  </div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!-- CTA + CONTACT                                                          -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->
<section class="cta-section reveal">
  <div class="cta-inner">
    <h2 class="cta-title">{pt ? 'Pronto para começar?' : 'Ready to get started?'}</h2>
    <p class="cta-sub">{pt ? 'Sem cadastro, sem nuvem, auto-hospedável.' : 'No sign-up, no cloud, self-hostable.'}</p>
    <a href="/app" class="cta-btn">{pt ? 'Abrir AnonShield →' : 'Launch AnonShield →'}</a>
    <a href="mailto:anonshield@unipampa.edu.br" class="cta-email">anonshield@unipampa.edu.br</a>
  </div>
</section>

<style>
  /* ── Shared ── */
  .section-label {
    font-size: 0.68rem; font-weight: 700; letter-spacing: 0.12em;
    text-transform: uppercase; color: var(--color-accent);
    margin: 0 0 12px;
  }
  .section-title {
    margin: 0 0 48px; font-size: clamp(1.4rem, 3vw, 2rem);
    font-weight: 800; letter-spacing: -0.035em;
    color: var(--color-text-primary);
  }

  /* ══════════════ HERO ══════════════ */
  .hero {
    padding: 56px 24px 48px;
    background: radial-gradient(ellipse 80% 60% at 50% -20%, rgba(99,102,241,0.12) 0%, transparent 70%);
    border-bottom: 1px solid var(--color-border);
    overflow-x: hidden;
  }
  .hero-inner { max-width: 1200px; margin: 0 auto; display: flex; flex-direction: column; gap: 28px; }


  .hero-title {
    margin: 0; display: flex; flex-direction: column; gap: 4px;
    font-size: clamp(2rem, 5vw, 3.2rem); font-weight: 900;
    letter-spacing: -0.04em; line-height: 1.1;
  }
  .brand {
    background: linear-gradient(135deg, #fff 0%, #a5b4fc 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  .hero-rule { color: var(--color-text-secondary); font-weight: 600; font-size: 0.65em; }

  .hero-sub {
    margin: 0; max-width: 640px;
    font-size: 0.95rem; line-height: 1.7;
    color: var(--color-text-secondary);
  }

  /* ── Demo ── */
  .demo-wrap { display: flex; flex-direction: column; gap: 12px; }

  .demo-label {
    display: flex; align-items: center; justify-content: space-between;
    flex-wrap: wrap; gap: 8px;
  }
  .demo-live {
    display: flex; align-items: center; gap: 7px;
    font-size: 0.75rem; font-weight: 600; letter-spacing: 0.05em;
    text-transform: uppercase; color: var(--color-text-primary);
  }
  .live-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: #4ade80;
    animation: pulse-dot 1.5s ease-in-out infinite;
  }
  .demo-hint {
    font-size: 0.7rem; font-family: var(--font-mono);
    color: var(--color-text-secondary);
  }

  .editor {
    display: grid; grid-template-columns: 1fr 44px 1fr;
    min-height: 340px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    overflow: hidden;
  }

  .panel { display: flex; flex-direction: column; min-width: 0; }
  .panel-in  { background: #080a0e; }
  .panel-out { background: #0c0e16; }

  .panel-head {
    display: flex; align-items: center; justify-content: space-between;
    padding: 9px 14px;
    border-bottom: 1px solid var(--color-border);
    flex-shrink: 0;
  }
  .panel-label {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: var(--color-text-secondary);
    font-family: var(--font-mono);
  }
  .panel-hint { font-size: 0.65rem; color: var(--color-border); font-family: var(--font-mono); }
  .panel-count {
    font-size: 0.65rem; font-family: var(--font-mono);
    color: var(--color-text-secondary); transition: color 150ms;
  }
  .panel-count.has-hits { color: #4ade80; }

  .panel-body {
    flex: 1; padding: 14px;
    font-family: var(--font-mono); font-size: 0.78rem; line-height: 1.75;
    color: var(--color-text-secondary);
    white-space: pre-wrap; word-break: break-word; overflow-y: auto;
  }
  textarea.panel-body {
    border: none; outline: none; resize: none;
    background: transparent; width: 100%;
  }
  textarea.panel-body:focus { color: var(--color-text-primary); }
  .output-body { color: #4a4e6a; }

  :global(.ent) {
    background: color-mix(in srgb, var(--c) 12%, transparent);
    border: 1px solid color-mix(in srgb, var(--c) 35%, transparent);
    border-radius: 4px; padding: 0 4px; margin: 0 1px;
    font-style: normal; font-size: 0.75rem;
    white-space: nowrap; cursor: default;
    transition: background 100ms;
  }
  :global(.ent:hover) { background: color-mix(in srgb, var(--c) 22%, transparent); }

  /* Animated divider */
  .divider {
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
    border-left: 1px solid var(--color-border);
    border-right: 1px solid var(--color-border);
    background: #070910;
    position: relative; overflow: hidden;
  }
  .flow-line {
    position: absolute; top: 50%; left: 4px; right: 4px; height: 1px;
    background: color-mix(in srgb, var(--color-accent) 30%, transparent);
    transform: translateY(-50%);
  }
  .flow-dot {
    position: absolute; top: 50%; width: 5px; height: 5px;
    border-radius: 50%; background: var(--color-accent);
    transform: translateY(-50%);
    box-shadow: 0 0 6px var(--color-accent);
    animation: flow-right 1.8s linear infinite;
  }
  .d1 { animation-delay: 0s; }
  .d2 { animation-delay: 0.6s; }
  .d3 { animation-delay: 1.2s; }
  @keyframes flow-right {
    0%   { left: 0; opacity: 0; }
    10%  { opacity: 1; }
    90%  { opacity: 1; }
    100% { left: calc(100% - 5px); opacity: 0; }
  }

  @media (max-width: 680px) {
    .editor { grid-template-columns: 1fr; min-height: unset; }
    .panel-body { min-height: 140px; }
    .divider { height: 36px; width: auto; border: none; border-top: 1px solid var(--color-border); border-bottom: 1px solid var(--color-border); }
    .flow-line { top: 4px; bottom: 4px; left: 50%; right: auto; width: 1px; height: auto; transform: none; }
    .flow-dot { left: 50%; top: 0; transform: translateX(-50%); animation-name: flow-down; }
    @keyframes flow-down {
      0%   { top: 0; opacity: 0; }
      10%  { opacity: 1; }
      90%  { opacity: 1; }
      100% { top: calc(100% - 5px); opacity: 0; }
    }
    .hero { padding: 32px 16px 32px; }
  }

  /* Legend */
  .legend {
    display: flex; flex-wrap: wrap; gap: 6px 14px;
    padding: 2px 0;
  }
  .legend-item {
    display: flex; align-items: center; gap: 6px;
    font-size: 0.72rem; font-family: var(--font-mono);
  }
  .legend-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--c);
    box-shadow: 0 0 5px color-mix(in srgb, var(--c) 60%, transparent);
  }
  .legend-type { color: var(--color-text-secondary); }
  .legend-n {
    color: var(--c); font-weight: 700;
    padding: 0 5px;
    background: color-mix(in srgb, var(--c) 12%, transparent);
    border-radius: 999px;
  }

  /* Hero actions */
  .hero-actions { display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }
  .cta-primary {
    display: inline-flex; align-items: center;
    padding: 13px 32px;
    background: var(--color-accent); color: #fff;
    border-radius: 8px; font-size: 0.95rem; font-weight: 700;
    text-decoration: none; letter-spacing: -0.01em;
    transition: background 120ms, transform 100ms, box-shadow 120ms;
    box-shadow: 0 0 24px rgba(99,102,241,0.3);
  }
  .cta-primary:hover {
    background: var(--color-accent-hover); color: #fff;
    transform: translateY(-2px);
    box-shadow: 0 6px 32px rgba(99,102,241,0.45);
  }
  .hero-meta {
    font-size: 0.78rem; font-family: var(--font-mono);
    color: var(--color-text-secondary);
  }

  /* ══════════════ PIPELINE ══════════════ */
  .pipeline {
    padding: 100px 24px 80px;
    border-top: 1px solid var(--color-border);
    border-bottom: 1px solid var(--color-border);
    background: #050610;
    position: relative;
    /* overflow: visible so popovers aren't clipped */
    overflow: visible;
  }
  /* Clip decoratives without clipping popovers */
  .pipeline-deco {
    position: absolute; inset: 0;
    overflow: hidden; pointer-events: none; z-index: 0;
  }
  .pipeline-inner {
    max-width: 1200px; margin: 0 auto;
    position: relative; z-index: 1;
  }

  /* Scan beam that sweeps horizontally */
  .scan-beam {
    position: absolute; top: 0; bottom: 0;
    width: 120px;
    background: linear-gradient(90deg, transparent, rgba(99,102,241,0.06), transparent);
    animation: scan-sweep 6s ease-in-out infinite;
    pointer-events: none; z-index: 0;
  }
  @keyframes scan-sweep {
    0%   { left: -120px; }
    100% { left: calc(100% + 120px); }
  }

  /* Dot grid behind the flow */
  .dot-grid {
    position: absolute; inset: 0; z-index: 0; pointer-events: none;
    background-image: radial-gradient(circle, rgba(99,102,241,0.15) 1px, transparent 1px);
    background-size: 32px 32px;
    mask-image: radial-gradient(ellipse 80% 80% at 50% 50%, black 40%, transparent 100%);
  }

  .pipe-heading {
    margin-bottom: 16px !important;
    font-size: clamp(1.6rem, 4vw, 2.4rem) !important;
    display: flex; flex-direction: column; gap: 4px;
  }
  .pipe-sub-head {
    font-size: 0.55em; font-weight: 400; color: var(--color-text-secondary); letter-spacing: 0;
  }

  /* Flow layout */
  .pipe-flow {
    display: flex; align-items: center; flex-wrap: nowrap;
    gap: 0; justify-content: center;
    margin: 56px 0 40px;
    /* overflow: visible so node popovers aren't clipped */
    overflow: visible; padding: 16px 0;
  }

  /* ── Nodes ── */
  .pipe-node {
    display: flex; flex-direction: column; align-items: center; gap: 10px;
    padding: 24px 20px 20px;
    min-width: 128px; text-align: center;
    position: relative; flex-shrink: 0;
    cursor: default;
    /* Ensure active node pops above siblings */
    z-index: 1;
  }
  .pipe-node:has(.node-ring[aria-expanded="true"]) {
    z-index: 10;
  }

  /* Ambient glow halo behind each node */
  .node-halo {
    position: absolute; top: 50%; left: 50%;
    transform: translate(-50%, -60%);
    width: 80px; height: 80px; border-radius: 50%;
    background: radial-gradient(circle, color-mix(in srgb, var(--nc) 22%, transparent) 0%, transparent 70%);
    filter: blur(8px);
    animation: halo-pulse 3s ease-in-out infinite;
    pointer-events: none;
  }
  @keyframes halo-pulse {
    0%, 100% { opacity: 0.5; transform: translate(-50%, -60%) scale(1); }
    50%       { opacity: 1;   transform: translate(-50%, -60%) scale(1.25); }
  }

  /* Circular icon ring — now a button */
  .node-ring {
    width: 72px; height: 72px;
    display: flex; align-items: center; justify-content: center;
    border-radius: 50%;
    background: color-mix(in srgb, var(--nc) 8%, #0a0c18);
    border: 1.5px solid color-mix(in srgb, var(--nc) 40%, transparent);
    box-shadow: 0 0 24px color-mix(in srgb, var(--nc) 20%, transparent),
                inset 0 0 12px color-mix(in srgb, var(--nc) 8%, transparent);
    color: var(--nc);
    position: relative; z-index: 1;
    cursor: pointer;
    transition: border-color 300ms, box-shadow 300ms, background 300ms, transform 200ms;
    flex-shrink: 0;
  }
  .node-ring:hover, .node-ring[aria-expanded="true"] {
    border-color: var(--nc);
    box-shadow: 0 0 40px color-mix(in srgb, var(--nc) 50%, transparent),
                inset 0 0 20px color-mix(in srgb, var(--nc) 14%, transparent);
    background: color-mix(in srgb, var(--nc) 18%, #0a0c18);
    transform: scale(1.08);
  }

  /* ── Node detail popover ── */
  .node-detail {
    position: absolute;
    top: calc(100% + 20px);
    left: 50%; transform: translateX(-50%);
    width: 290px;
    background: #080b18;
    border: 1px solid color-mix(in srgb, var(--nc) 28%, #1e2240);
    border-top: 2px solid var(--nc);
    border-radius: 14px;
    overflow: hidden;
    box-shadow:
      0 24px 64px rgba(0,0,0,0.75),
      0 0 0 1px rgba(255,255,255,0.03),
      0 0 40px color-mix(in srgb, var(--nc) 10%, transparent);
    z-index: 500;
    animation: detail-in 220ms cubic-bezier(0.34,1.4,0.64,1) both;
    pointer-events: none;
    /* override inherited text-align: center from .pipe-node */
    text-align: left;
  }

  /* Arrow */
  .node-detail::before {
    content: '';
    position: absolute; top: -7px; left: 50%;
    width: 12px; height: 12px;
    background: #080b18;
    border-left: 1px solid color-mix(in srgb, var(--nc) 28%, #1e2240);
    border-top: 2px solid var(--nc);
    transform: translateX(-50%) rotate(45deg);
  }

  /* Header strip */
  .nd-header {
    display: flex; align-items: center; gap: 8px;
    padding: 12px 16px 10px;
    background: color-mix(in srgb, var(--nc) 7%, transparent);
    border-bottom: 1px solid color-mix(in srgb, var(--nc) 14%, transparent);
  }
  .nd-icon {
    font-size: 1rem; color: var(--nc);
    width: 24px; height: 24px;
    display: flex; align-items: center; justify-content: center;
    background: color-mix(in srgb, var(--nc) 14%, transparent);
    border-radius: 6px;
    flex-shrink: 0;
  }
  .nd-title {
    font-size: 0.78rem; font-weight: 700;
    color: #e8eaf0; letter-spacing: 0.01em;
  }

  /* Stat pills */
  .nd-stats {
    display: flex; flex-wrap: wrap; gap: 5px;
    padding: 10px 16px 8px;
  }
  .nd-stat {
    font-size: 0.66rem; font-weight: 600;
    padding: 2px 8px;
    border-radius: 100px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.09);
    color: #a0a4be;
    letter-spacing: 0.03em;
    white-space: nowrap;
  }

  /* Format tags (node 1) */
  .nd-formats {
    display: flex; flex-wrap: wrap; gap: 4px;
    padding: 2px 16px 10px;
  }
  .nd-fmt {
    font-size: 0.62rem; font-weight: 700;
    font-family: var(--font-mono);
    padding: 2px 6px;
    border-radius: 4px;
    background: color-mix(in srgb, #60a5fa 10%, transparent);
    border: 1px solid color-mix(in srgb, #60a5fa 22%, transparent);
    color: #60a5fa;
    letter-spacing: 0.04em;
  }

  /* Entity transform rows (node 2) */
  .nd-transform {
    display: flex; align-items: center; gap: 6px;
    padding: 3px 16px;
    font-family: var(--font-mono);
    font-size: 0.68rem;
  }
  .nd-src { color: #9498b0; }
  .nd-arrow { color: #4b5268; }
  .nd-tag {
    padding: 1px 6px; border-radius: 4px;
    border: 1px solid;
    font-weight: 600; font-size: 0.63rem;
  }

  /* Code block (node 3) */
  .nd-code {
    margin: 4px 16px 8px;
    background: rgba(0,0,0,0.4);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 8px;
    padding: 8px 10px;
    display: flex; flex-direction: column; gap: 4px;
  }
  .nd-code-line {
    font-family: var(--font-mono);
    font-size: 0.67rem; color: #c8cae0;
  }
  .nd-kw { color: #fbbf24; font-weight: 600; }
  .nd-val { color: #fbbf24; }
  .nd-muted { color: #5a5f7a; font-style: italic; }

  /* Before/after replace demo (node 4) */
  .nd-replace-demo {
    margin: 4px 16px 8px;
    background: rgba(0,0,0,0.3);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 8px;
    padding: 8px 10px;
    display: flex; flex-direction: column; gap: 6px;
  }
  .nd-replace-row {
    display: flex; flex-direction: column; gap: 2px;
  }
  .nd-replace-before {
    font-family: var(--font-mono);
    font-size: 0.67rem;
    color: #f87171;
    text-decoration: line-through;
    text-decoration-color: rgba(248,113,113,0.4);
  }
  .nd-replace-after {
    font-family: var(--font-mono);
    font-size: 0.67rem;
    color: #c8cae0;
  }

  /* Zero-retention table (node 5) */
  .nd-zero {
    margin: 4px 16px 8px;
    display: flex; flex-direction: column; gap: 4px;
  }
  .nd-zero-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 4px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    font-size: 0.67rem;
  }
  .nd-zero-row:last-child { border-bottom: none; }
  .nd-zero-label { color: #6b7099; font-family: var(--font-mono); }
  .nd-zero-val { font-weight: 600; font-family: var(--font-mono); }
  .nd-deleted { color: #f87171; }
  .nd-ok { color: #4ade80; }

  /* Description text */
  .nd-desc {
    margin: 0;
    padding: 8px 16px 14px;
    font-size: 0.7rem; line-height: 1.6;
    color: #6b7099;
    border-top: 1px solid rgba(255,255,255,0.04);
  }

  /* Description-only fallback (old style) */
  .node-detail > p:only-child {
    margin: 0;
    padding: 14px 16px;
    font-size: 0.72rem; line-height: 1.65;
    color: #9498b0;
    font-family: var(--font-mono);
  }
  @keyframes detail-in {
    from { opacity: 0; transform: translateX(-50%) translateY(-6px); }
    to   { opacity: 1; transform: translateX(-50%) translateY(0); }
  }
  /* hint to click */
  .pipe-node::after {
    content: '↕';
    position: absolute; bottom: -4px; right: -4px;
    font-size: 0.55rem; color: color-mix(in srgb, var(--nc) 60%, transparent);
    opacity: 0; transition: opacity 200ms;
    pointer-events: none;
  }
  .pipe-node:hover::after { opacity: 1; }

  .node-name {
    font-size: 0.78rem; font-weight: 700; color: var(--color-text-primary);
    letter-spacing: -0.01em; line-height: 1.3; position: relative; z-index: 1;
  }
  .node-note {
    font-size: 0.64rem; font-family: var(--font-mono);
    color: var(--color-text-secondary); position: relative; z-index: 1;
    line-height: 1.4;
  }

  /* ── Connectors ── */
  .pipe-connector {
    position: relative; width: 72px; height: 4px;
    flex-shrink: 0; align-self: center;
    margin-bottom: 20px; /* vertically align with node center (accounts for label below) */
  }
  .conn-track {
    position: absolute; top: 50%; left: 0; right: 0; height: 1.5px;
    transform: translateY(-50%);
    background: linear-gradient(90deg, var(--ca), var(--cb));
    opacity: 0.35;
    border-radius: 1px;
  }

  /* Particles */
  .conn-p {
    position: absolute; top: 50%; transform: translateY(-50%);
    width: 10px; height: 10px; border-radius: 50%;
    background: var(--ca);
    box-shadow: 0 0 10px 3px color-mix(in srgb, var(--ca) 60%, transparent),
                0 0 20px 6px color-mix(in srgb, var(--ca) 25%, transparent);
    animation: conn-flow 2.2s linear infinite;
    animation-delay: var(--cd);
  }
  @keyframes conn-flow {
    0%   { left: 0;               opacity: 0;   background: var(--ca); }
    6%   { opacity: 1; }
    50%  { background: color-mix(in srgb, var(--ca) 50%, var(--cb)); }
    94%  { opacity: 1; }
    100% { left: calc(100% - 10px); opacity: 0; background: var(--cb); }
  }

  .pipe-note {
    text-align: center; font-size: 0.72rem; font-family: var(--font-mono);
    color: var(--color-text-secondary); line-height: 1.8;
    max-width: 640px; margin: 0 auto;
    padding: 16px 24px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: rgba(255,255,255,0.02);
  }

  @media (max-width: 900px) {
    .pipe-flow {
      flex-direction: column; align-items: center;
      overflow-x: visible; margin: 40px 0 32px;
    }
    .pipe-connector {
      width: 4px; height: 48px; margin-bottom: 0; margin-right: 0;
    }
    .conn-track {
      top: 0; bottom: 0; left: 50%; right: auto;
      width: 1.5px; height: 100%; transform: none;
      background: linear-gradient(180deg, var(--ca), var(--cb));
    }
    .conn-p {
      left: 50%; transform: translateX(-50%);
      animation-name: conn-flow-down;
    }
    @keyframes conn-flow-down {
      0%   { top: 0;               opacity: 0;   background: var(--ca); }
      6%   { opacity: 1; }
      50%  { background: color-mix(in srgb, var(--ca) 50%, var(--cb)); }
      94%  { opacity: 1; }
      100% { top: calc(100% - 10px); opacity: 0; background: var(--cb); }
    }
    .pipe-node { padding: 16px 24px; }
  }

  /* ══════════════ STATS ══════════════ */
  .stats-section {
    border-bottom: 1px solid var(--color-border);
    padding: 0;
  }
  .stats-inner {
    max-width: 1200px; margin: 0 auto;
    display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    border-left: 1px solid var(--color-border);
  }
  .stat-block {
    display: flex; flex-direction: column; align-items: center; gap: 5px;
    padding: 36px 16px;
    border-right: 1px solid var(--color-border);
    border-bottom: 1px solid var(--color-border);
    text-align: center;
  }
  .stat-val {
    font-size: 2rem; font-weight: 900; letter-spacing: -0.05em;
    color: var(--color-text-primary);
    font-variant-numeric: tabular-nums;
    opacity: 1; transform: none;
    transition: none;
  }
  .stat-val.animated { opacity: 1; transform: none; }
  .stat-val:nth-child(1) { transition-delay: 0ms; }
  .stat-block:nth-child(2) .stat-val { transition-delay: 80ms; }
  .stat-block:nth-child(3) .stat-val { transition-delay: 160ms; }
  .stat-block:nth-child(4) .stat-val { transition-delay: 240ms; }
  .stat-block:nth-child(5) .stat-val { transition-delay: 320ms; }
  .stat-block:nth-child(6) .stat-val { transition-delay: 400ms; }
  .stat-unit { font-size: 1.1rem; font-weight: 600; opacity: 0.6; }
  .stat-desc {
    font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.06em;
    color: var(--color-text-secondary); max-width: 120px;
  }

  /* ══════════════ FORMATS BAR ══════════════ */
  .formats-bar {
    display: flex; align-items: center; gap: 20px; flex-wrap: wrap;
    padding: 20px 24px; max-width: 1200px; margin: 0 auto;
    border-bottom: 1px solid var(--color-border);
  }
  .formats-lbl {
    font-size: 0.68rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: var(--color-text-secondary);
    white-space: nowrap; flex-shrink: 0;
  }
  .formats-tags { display: flex; flex-wrap: wrap; gap: 5px; }
  .fmt-tag {
    font-family: var(--font-mono); font-size: 0.72rem;
    color: var(--color-text-secondary);
    border: 1px solid var(--color-border); border-radius: 4px;
    padding: 2px 8px; background: var(--color-surface-raised);
    transition: border-color 100ms, color 100ms;
  }
  .fmt-tag:hover { border-color: var(--color-accent); color: var(--color-text-primary); }

  /* ══════════════ RESEARCH ══════════════ */
  .research {
    padding: 80px 24px;
    border-bottom: 1px solid var(--color-border);
  }
  .research-inner { max-width: 900px; margin: 0 auto; }
  .research-sub {
    margin: -32px 0 48px; font-size: 0.88rem; line-height: 1.7;
    color: var(--color-text-secondary); max-width: 640px;
  }

  /* Timeline */
  .timeline { display: flex; flex-direction: column; gap: 0; overflow: visible; }

  .tl-item {
    display: grid; grid-template-columns: 48px 24px 1fr;
    gap: 0 16px; align-items: start;
    min-width: 0;
  }
  /* Gen 3 has no connector div — make its card span cols 2+3 */
  .tl-item.tl-current .paper-card {
    grid-column: 2 / -1;
  }

  .tl-marker {
    display: flex; align-items: center; justify-content: center;
    width: 36px; height: 36px; border-radius: 50%;
    border: 2px solid var(--color-border);
    background: var(--color-surface-raised);
    flex-shrink: 0; position: relative; z-index: 1;
    margin-top: 20px;
  }
  .tl-marker.current {
    border-color: var(--color-accent);
    background: color-mix(in srgb, var(--color-accent) 15%, var(--color-surface));
    box-shadow: 0 0 16px rgba(99,102,241,0.3);
    animation: pulse-glow 2s ease-in-out infinite;
  }
  @keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 16px rgba(99,102,241,0.3); }
    50%       { box-shadow: 0 0 28px rgba(99,102,241,0.55); }
  }
  .tl-gen {
    font-size: 0.75rem; font-weight: 800; font-family: var(--font-mono);
    color: var(--color-text-secondary);
  }
  .tl-marker.current .tl-gen { color: var(--color-accent); }

  .tl-connector {
    width: 2px; background: var(--color-border);
    margin-left: 17px; /* center on marker = 48/2 - 1 */
    min-height: 32px;
    align-self: stretch;
  }
  .tl-item:last-child .tl-connector { display: none; }

  .paper-card {
    padding: 20px 24px; border: 1px solid var(--color-border);
    border-radius: var(--radius-md); background: var(--color-surface-raised);
    display: flex; flex-direction: column; gap: 10px;
    margin-bottom: 24px;
    transition: border-color 200ms, box-shadow 200ms;
  }
  .paper-card:hover {
    border-color: color-mix(in srgb, var(--color-accent) 50%, transparent);
  }
  .current-paper {
    border-color: color-mix(in srgb, var(--color-accent) 40%, transparent);
    background: color-mix(in srgb, var(--color-accent) 4%, var(--color-surface-raised));
  }

  .paper-venue-row {
    display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  }
  .paper-venue {
    font-size: 0.65rem; font-weight: 800; letter-spacing: 0.1em;
    text-transform: uppercase; color: var(--color-accent);
    font-family: var(--font-mono);
  }
  .accent-venue { color: #a5b4fc; }
  .paper-gen {
    font-size: 0.65rem; font-family: var(--font-mono);
    color: var(--color-text-secondary); opacity: 0.7;
  }
  .accent-gen { color: var(--color-accent); opacity: 1; }

  .paper-title {
    margin: 0; font-size: 0.88rem; font-weight: 600;
    color: var(--color-text-primary); line-height: 1.4;
  }
  .paper-authors {
    margin: 0; font-size: 0.75rem; color: var(--color-text-secondary);
    font-family: var(--font-mono);
  }
  .paper-context {
    margin: 0; font-size: 0.8rem; color: var(--color-text-secondary);
    line-height: 1.6;
  }
  .paper-metrics {
    display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px;
  }
  .pm {
    font-size: 0.68rem; font-weight: 700; font-family: var(--font-mono);
    color: var(--color-text-secondary);
    border: 1px solid var(--color-border);
    border-radius: 4px; padding: 2px 8px;
    background: var(--color-surface);
  }
  .pm-good { color: #4ade80; border-color: rgba(74,222,128,0.3); background: rgba(74,222,128,0.06); }
  .pm-hero { color: #a5b4fc; border-color: rgba(165,180,252,0.3); background: rgba(165,180,252,0.08); font-size: 0.72rem; }
  .pm-info { color: #38bdf8; border-color: rgba(56,189,248,0.3); background: rgba(56,189,248,0.06); }

  .paper-link {
    font-size: 0.72rem; font-family: var(--font-mono); font-weight: 700;
    color: var(--color-accent); text-decoration: none;
    margin-top: 4px; width: fit-content;
    transition: color 150ms, transform 150ms;
    display: inline-block;
  }
  .paper-link:hover { color: var(--color-accent-hover); transform: translateX(3px); }


  /* ══════════════ TEAM ══════════════ */
  .team {
    padding: 80px 24px;
    border-bottom: 1px solid var(--color-border);
    background: var(--color-surface-raised);
  }
  .team-inner { max-width: 1200px; margin: 0 auto; }

  .members {
    display: flex; flex-wrap: wrap; gap: 12px;
    margin-bottom: 24px;
  }
  .member {
    display: flex; flex-direction: column; gap: 4px;
    padding: 16px 24px;
    border: 1px solid var(--color-border); border-radius: var(--radius-md);
    background: var(--color-surface);
    min-width: 180px;
    transition: border-color 200ms;
  }
  .member:hover { border-color: var(--color-accent); }
  .member-name {
    font-size: 0.9rem; font-weight: 600; color: var(--color-text-primary);
  }
  .member-role {
    font-size: 0.72rem; font-family: var(--font-mono);
    color: var(--color-accent);
  }
  .team-affil {
    margin: 0; font-size: 0.78rem; font-family: var(--font-mono);
    color: var(--color-text-secondary); line-height: 1.6;
  }

  /* ══════════════ CTA ══════════════ */
  .cta-section {
    padding: 80px 24px;
    text-align: center;
    background: radial-gradient(ellipse 60% 80% at 50% 100%, rgba(99,102,241,0.1) 0%, transparent 70%);
  }
  .cta-inner { max-width: 480px; margin: 0 auto; display: flex; flex-direction: column; align-items: center; gap: 16px; }
  .cta-title {
    margin: 0; font-size: clamp(1.4rem, 3vw, 2rem); font-weight: 800;
    letter-spacing: -0.035em; color: var(--color-text-primary);
  }
  .cta-sub {
    margin: 0; font-size: 0.85rem; font-family: var(--font-mono);
    color: var(--color-text-secondary);
  }
  .cta-btn {
    display: inline-flex; align-items: center;
    padding: 15px 40px;
    background: var(--color-accent); color: #fff;
    border-radius: 10px; font-size: 1rem; font-weight: 700;
    text-decoration: none; letter-spacing: -0.01em;
    transition: background 120ms, transform 100ms, box-shadow 120ms;
    box-shadow: 0 0 32px rgba(99,102,241,0.3);
  }
  .cta-btn:hover {
    background: var(--color-accent-hover); color: #fff;
    transform: translateY(-2px);
    box-shadow: 0 8px 40px rgba(99,102,241,0.45);
  }
  .cta-email {
    font-size: 0.82rem; font-family: var(--font-mono);
    color: var(--color-text-secondary); text-decoration: none;
    transition: color 150ms;
  }
  .cta-email:hover { color: var(--color-accent); }

  /* ══════════════ SCROLL REVEAL ══════════════ */
  /* Sections are always visible — animation is enhancement only */
  .reveal {
    opacity: 1;
    transform: none;
  }
  .reveal.revealed {
    opacity: 1;
    transform: none;
  }
  /* Stagger children inside revealed containers */
  .reveal.revealed .stat-block,
  .reveal.revealed .tl-item,
  .reveal.revealed .team-card {
    animation: stagger-up 0.5s cubic-bezier(0.22, 1, 0.36, 1) both;
  }
  .reveal.revealed .stat-block:nth-child(1) { animation-delay: 0ms; }
  .reveal.revealed .stat-block:nth-child(2) { animation-delay: 60ms; }
  .reveal.revealed .stat-block:nth-child(3) { animation-delay: 120ms; }
  .reveal.revealed .stat-block:nth-child(4) { animation-delay: 180ms; }
  .reveal.revealed .stat-block:nth-child(5) { animation-delay: 240ms; }
  .reveal.revealed .stat-block:nth-child(6) { animation-delay: 300ms; }
  .reveal.revealed .tl-item:nth-child(1) { animation-delay: 0ms; }
  .reveal.revealed .tl-item:nth-child(2) { animation-delay: 100ms; }
  .reveal.revealed .tl-item:nth-child(3) { animation-delay: 200ms; }

  @keyframes stagger-up {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  @media (prefers-reduced-motion: reduce) {
    .reveal { opacity: 1; transform: none; transition: none; }
    .reveal.revealed .stat-block,
    .reveal.revealed .tl-item { animation: none; }
  }
</style>

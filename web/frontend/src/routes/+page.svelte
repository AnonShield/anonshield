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

  // ── Scroll-triggered counter animation ───────────────────────────────────
  let statsVisible = $state(false);
  let statsRef: HTMLElement;

  onMount(() => {
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { statsVisible = true; obs.disconnect(); }
    }, { threshold: 0.3 });
    if (statsRef) obs.observe(statsRef);
    return () => obs.disconnect();
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
<section class="pipeline">
  <div class="pipeline-inner">
    <p class="section-label">{pt ? 'Como funciona' : 'How it works'}</p>
    <h2 class="section-title">{pt ? 'Privacidade garantida: processamos tudo sem salvar nada.' : 'Privacy guaranteed: we process everything without saving anything.'}</h2>

    <div class="pipe-flow">
      <!-- Node 1: Upload -->
      <div class="pipe-node n1">
        <div class="node-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
        </div>
        <span class="node-name">{pt ? 'Entrada' : 'Input'}</span>
        <span class="node-note">TXT PDF DOCX ZIP…</span>
      </div>

      <div class="pipe-connector">
        <div class="conn-line"></div>
        <div class="conn-particle p1"></div>
        <div class="conn-particle p2"></div>
        <div class="conn-particle p3"></div>
      </div>

      <!-- Node 2: Detect -->
      <div class="pipe-node n2">
        <div class="node-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
            <line x1="11" y1="8" x2="11" y2="14"/>
            <line x1="8" y1="11" x2="14" y2="11"/>
          </svg>
        </div>
        <span class="node-name">{pt ? 'Detecção NER' : 'NER Detection'}</span>
        <span class="node-note">{pt ? 'Transformer ou regex' : 'Transformer or regex'}</span>
      </div>

      <div class="pipe-connector">
        <div class="conn-line"></div>
        <div class="conn-particle p1" style="animation-delay:0.3s"></div>
        <div class="conn-particle p2" style="animation-delay:0.97s"></div>
        <div class="conn-particle p3" style="animation-delay:1.63s"></div>
      </div>

      <!-- Node 3: Hash -->
      <div class="pipe-node n3">
        <div class="node-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <line x1="4" y1="9" x2="20" y2="9"/>
            <line x1="4" y1="15" x2="20" y2="15"/>
            <line x1="10" y1="3" x2="8" y2="21"/>
            <line x1="16" y1="3" x2="14" y2="21"/>
          </svg>
        </div>
        <span class="node-name">HMAC-SHA256</span>
        <span class="node-note">{pt ? 'Hash determinístico' : 'Deterministic hash'}</span>
      </div>

      <div class="pipe-connector">
        <div class="conn-line"></div>
        <div class="conn-particle p1" style="animation-delay:0.6s"></div>
        <div class="conn-particle p2" style="animation-delay:1.27s"></div>
        <div class="conn-particle p3" style="animation-delay:1.93s"></div>
      </div>

      <!-- Node 4: Shield -->
      <div class="pipe-node n4">
        <div class="node-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
        </div>
        <span class="node-name">{pt ? 'Pseudonimização' : 'Pseudonymization'}</span>
        <span class="node-note">{pt ? 'Token HMAC substituído' : 'HMAC token replaced'}</span>
      </div>

      <div class="pipe-connector">
        <div class="conn-line"></div>
        <div class="conn-particle p1" style="animation-delay:0.9s"></div>
        <div class="conn-particle p2" style="animation-delay:1.57s"></div>
        <div class="conn-particle p3" style="animation-delay:2.23s"></div>
      </div>

      <!-- Node 5: Output -->
      <div class="pipe-node n5">
        <div class="node-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
        </div>
        <span class="node-name">{pt ? 'Saída' : 'Output'}</span>
        <span class="node-note">{pt ? 'Deletado após download' : 'Deleted after download'}</span>
      </div>
    </div>

    <p class="pipe-note">
      {pt
        ? 'Chave armazenada apenas no Redis (TTL 1h) · Deletada pelo worker imediatamente após o processamento'
        : 'Key stored only in Redis (1h TTL) · Deleted by worker immediately after processing'}
    </p>
  </div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!-- STATS                                                                  -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->
<section class="stats-section" bind:this={statsRef}>
  <div class="stats-inner">
    <div class="stat-block">
      <span class="stat-val" class:animated={statsVisible}>738<span class="stat-unit">×</span></span>
      <span class="stat-desc">{pt ? 'mais rápido que linha de base' : 'faster than baseline'}</span>
    </div>
    <div class="stat-block">
      <span class="stat-val" class:animated={statsVisible}>94.2<span class="stat-unit">%</span></span>
      <span class="stat-desc">F1 {pt ? 'em dataset CTI' : 'on CTI dataset'}</span>
    </div>
    <div class="stat-block">
      <span class="stat-val" class:animated={statsVisible}>96.7<span class="stat-unit">%</span></span>
      <span class="stat-desc">{pt ? 'recall médio' : 'mean recall'}</span>
    </div>
    <div class="stat-block">
      <span class="stat-val" class:animated={statsVisible}>550<span class="stat-unit">MB</span></span>
      <span class="stat-desc">{pt ? 'em menos de 10 min' : 'in under 10 min'}</span>
    </div>
    <div class="stat-block">
      <span class="stat-val" class:animated={statsVisible}>0</span>
      <span class="stat-desc">{pt ? 'chamadas à nuvem' : 'cloud calls'}</span>
    </div>
    <div class="stat-block">
      <span class="stat-val" class:animated={statsVisible}>10<span class="stat-unit">GB</span></span>
      <span class="stat-desc">{pt ? 'tamanho máx. de arquivo (com chave)' : 'max file size (with key)'}</span>
    </div>
  </div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!-- FORMATS                                                                -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->
<div class="formats-bar">
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
<section class="research">
  <div class="research-inner">
    <p class="section-label">{pt ? 'Validação acadêmica' : 'Academic validation'}</p>
    <h2 class="section-title">{pt ? 'Publicado em conferências peer-reviewed' : 'Published at peer-reviewed venues'}</h2>

    <div class="papers-grid">
      <!-- Paper 1: SBSeg 2025 -->
      <div class="paper-card">
        <div class="paper-venue">SBSeg 2025</div>
        <h3 class="paper-title">Anonimização de Incidentes de Segurança com Reidentificação Controlada</h3>
        <p class="paper-authors">C. Bandel, J. P. R. Esteves, K. P. Guerra, L. M. Bertholdo, D. Kreutz, R. S. Miani</p>
        <div class="paper-metrics">
          <span class="pm">100% Prec.</span>
          <span class="pm">97.38% Rec.</span>
          <span class="pm">763 Incidents</span>
        </div>
        <a href="https://doi.org/10.5753/sbseg.2025.11433" target="_blank" class="paper-link">DOI Link ↗</a>
      </div>

      <!-- Paper 2: ERRC 2025 -->
      <div class="paper-card">
        <div class="paper-venue">ERRC 2025 (WRSeg)</div>
        <h3 class="paper-title">AnonLFI 2.0: Extensible Architecture for PII Pseudonymization in CSIRTs with OCR and Technical Recognizers</h3>
        <p class="paper-authors">C. Kapelinski, D. Lautert, B. Machado, D. Kreutz</p>
        <div class="paper-metrics">
          <span class="pm">100% Precision</span>
          <span class="pm">92.1% F1 (XML)</span>
          <span class="pm">On-premise</span>
        </div>
        <a href="https://doi.org/10.5753/errc.2025.17784" target="_blank" class="paper-link">DOI Link ↗</a>
      </div>

      <!-- Paper 3: SBRC 2026 -->
      <div class="paper-card">
        <div class="paper-venue">SBRC 2026 (Salão de Ferramentas)</div>
        <h3 class="paper-title">AnonShield: Scalable On-Premise Pseudonymization for CSIRT Vulnerability Data</h3>
        <p class="paper-authors">C. Kapelinski, D. Lautert, B. Machado, I. G. Ferrão, D. Kreutz</p>
        <div class="paper-metrics">
          <span class="pm">94.2% F1</span>
          <span class="pm">96.7% Recall</span>
          <span class="pm">738× Speedup</span>
        </div>
        <a href="https://github.com/AnonShield/tool" target="_blank" class="paper-link">GitHub Repo ↗</a>
      </div>
    </div>

  </div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!-- TEAM                                                                   -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->
<section class="team">
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
<section class="cta-section">
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
  }
  .hero-inner { max-width: 1200px; margin: 0 auto; display: flex; flex-direction: column; gap: 28px; }

  .hero-badge {
    display: inline-flex; align-items: center; gap: 8px;
    font-size: 0.72rem; font-family: var(--font-mono);
    color: var(--color-text-secondary);
    border: 1px solid var(--color-border);
    border-radius: 999px; padding: 5px 14px;
    width: fit-content;
    background: var(--color-surface-raised);
  }
  .badge-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #4ade80;
    box-shadow: 0 0 8px #4ade80;
    animation: pulse-dot 2s ease-in-out infinite;
  }
  @keyframes pulse-dot {
    0%, 100% { opacity: 1; box-shadow: 0 0 8px #4ade80; }
    50% { opacity: 0.5; box-shadow: 0 0 2px #4ade80; }
  }

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
    .editor { grid-template-columns: 1fr; }
    .divider { height: 40px; width: auto; border: none; border-top: 1px solid var(--color-border); border-bottom: 1px solid var(--color-border); }
    .flow-line { top: 4px; bottom: 4px; left: 50%; right: auto; width: 1px; height: auto; transform: none; }
    .flow-dot { left: 50%; top: 0; transform: translateX(-50%); animation-name: flow-down; }
    @keyframes flow-down {
      0%   { top: 0; opacity: 0; }
      10%  { opacity: 1; }
      90%  { opacity: 1; }
      100% { top: calc(100% - 5px); opacity: 0; }
    }
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
    padding: 80px 24px;
    border-top: 1px solid var(--color-border);
    border-bottom: 1px solid var(--color-border);
    background: var(--color-surface-raised);
  }
  .pipeline-inner { max-width: 1200px; margin: 0 auto; }

  .pipe-flow {
    display: flex; align-items: center; flex-wrap: wrap;
    gap: 0; justify-content: center;
    margin-bottom: 40px;
  }

  .pipe-node {
    display: flex; flex-direction: column; align-items: center; gap: 8px;
    padding: 20px 24px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    min-width: 130px; text-align: center;
    transition: border-color 300ms, box-shadow 300ms;
    position: relative;
  }
  .pipe-node:hover {
    border-color: var(--color-accent);
    box-shadow: 0 0 20px rgba(99,102,241,0.15);
  }

  /* Node color accents */
  .n1 .node-icon { color: #60a5fa; }
  .n2 .node-icon { color: #c084fc; }
  .n3 .node-icon { color: #fbbf24; }
  .n4 .node-icon { color: #4ade80; }
  .n5 .node-icon { color: #34d399; }

  .node-icon {
    width: 44px; height: 44px;
    display: flex; align-items: center; justify-content: center;
    border-radius: 50%;
    background: color-mix(in srgb, currentColor 10%, transparent);
    border: 1px solid color-mix(in srgb, currentColor 30%, transparent);
    transition: background 300ms;
  }
  .pipe-node:hover .node-icon {
    background: color-mix(in srgb, currentColor 18%, transparent);
  }

  .node-name {
    font-size: 0.82rem; font-weight: 700; color: var(--color-text-primary);
    letter-spacing: -0.01em;
  }
  .node-note {
    font-size: 0.68rem; font-family: var(--font-mono);
    color: var(--color-text-secondary);
  }

  /* Connector with animated particles */
  .pipe-connector {
    position: relative; width: 60px; height: 2px;
    flex-shrink: 0;
  }
  .conn-line {
    position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: var(--color-border);
    top: 50%; transform: translateY(-50%);
  }
  .conn-particle {
    position: absolute; top: 50%; transform: translateY(-50%);
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--color-accent);
    box-shadow: 0 0 6px var(--color-accent);
    animation: particle-flow 2s linear infinite;
  }
  .p1 { animation-delay: 0s; }
  .p2 { animation-delay: 0.67s; }
  .p3 { animation-delay: 1.33s; }
  @keyframes particle-flow {
    0%   { left: 0; opacity: 0; }
    8%   { opacity: 1; }
    92%  { opacity: 1; }
    100% { left: calc(100% - 6px); opacity: 0; }
  }

  .pipe-note {
    text-align: center; font-size: 0.75rem; font-family: var(--font-mono);
    color: var(--color-text-secondary); line-height: 1.7;
    max-width: 640px; margin: 0 auto;
  }

  @media (max-width: 900px) {
    .pipe-flow { flex-direction: column; align-items: stretch; }
    .pipe-connector {
      width: 1px; height: 40px; margin: 0 auto;
    }
    .conn-line { top: 0; bottom: 0; left: 50%; right: auto; width: 1px; height: 100%; transform: none; }
    .conn-particle {
      left: 50%; top: 0; transform: translateX(-50%);
      animation-name: particle-down;
    }
    @keyframes particle-down {
      0%   { top: 0; opacity: 0; }
      8%   { opacity: 1; }
      92%  { opacity: 1; }
      100% { top: calc(100% - 6px); opacity: 0; }
    }
    .pipe-node { min-width: auto; }
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
    opacity: 0; transform: translateY(8px);
    transition: opacity 600ms ease, transform 600ms ease;
  }
  .stat-val.animated { opacity: 1; transform: translateY(0); }
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
  .research-inner { max-width: 1200px; margin: 0 auto; }

  .papers-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px; margin-bottom: 32px;
  }
  .paper-card {
    padding: 24px; border: 1px solid var(--color-border);
    border-radius: var(--radius-md); background: var(--color-surface-raised);
    display: flex; flex-direction: column; gap: 12px;
    transition: border-color 200ms, box-shadow 200ms;
  }
  .paper-card:hover {
    border-color: color-mix(in srgb, var(--color-accent) 60%, transparent);
    box-shadow: 0 0 20px rgba(99,102,241,0.08);
  }
  .paper-venue {
    font-size: 0.65rem; font-weight: 800; letter-spacing: 0.1em;
    text-transform: uppercase; color: var(--color-accent);
    font-family: var(--font-mono);
  }
  .paper-title {
    margin: 0; font-size: 0.88rem; font-weight: 600;
    color: var(--color-text-primary); line-height: 1.4;
  }
  .paper-authors {
    margin: 0; font-size: 0.78rem; color: var(--color-text-secondary);
    font-family: var(--font-mono);
  }
  .paper-metrics {
    display: flex; flex-wrap: wrap; gap: 6px; margin-top: auto;
  }
  .pm {
    font-size: 0.68rem; font-weight: 700; font-family: var(--font-mono);
    color: #4ade80;
    border: 1px solid rgba(74,222,128,0.3);
    border-radius: 4px; padding: 2px 8px;
    background: rgba(74,222,128,0.06);
  }

  .paper-link {
    font-size: 0.72rem; font-family: var(--font-mono); font-weight: 700;
    color: var(--color-accent); text-decoration: none;
    margin-top: 8px; display: inline-flex; align-items: center;
    gap: 4px; transition: color 150ms, transform 150ms;
  }
  .paper-link:hover {
    color: var(--color-accent-hover);
    transform: translateX(3px);
  }


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
</style>

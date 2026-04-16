<script lang="ts">
  import { onMount } from 'svelte';
  import { t } from '$lib/i18n';

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

  type Mode = 'pseudo' | 'anon';

  function buildHtml(text: string, hits: Hit[], mode: Mode): string {
    let html = '';
    let pos = 0;
    for (const h of hits) {
      html += esc(text.slice(pos, h.start));
      const label = h.type.replace(/_/g, '·');
      const body = mode === 'pseudo'
        ? `[${label}-<span class="ent-token">${slugify(h.raw, h.type)}</span>]`
        : `[${label}]`;
      html += `<mark class="ent ent-${mode}" style="color:${h.color};--c:${h.color}" title="${h.type}: ${esc(h.raw)}">${body}</mark>`;
      pos = h.end;
    }
    html += esc(text.slice(pos));
    return html;
  }

  let input = $state(SAMPLE);
  let mode = $state<Mode>('pseudo');
  let hits = $derived(findHits(input));
  let outputHtml = $derived(buildHtml(input, hits, mode));
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
      <span class="hero-rule">{$t('landing.hero.rule')}</span>
    </h1>
    <p class="hero-sub">{$t('landing.hero.sub')}</p>

    <!-- ── LIVE DEMO ── -->
    <div class="demo-wrap">
      <div class="demo-label">
        <span class="demo-live">
          <span class="live-dot"></span>
          {$t('landing.hero.demo.live')}
        </span>
        <span class="demo-hint">{$t('landing.hero.demo.hint')}</span>
      </div>

      <!-- ── MODE TOGGLE ── -->
      <div class="mode-toggle" role="radiogroup" aria-label={$t('landing.hero.mode.label')}>
        <span class="mode-label">{$t('landing.hero.mode.label')}</span>
        <div class="mode-switch" class:is-anon={mode === 'anon'}>
          <button
            type="button"
            role="radio"
            aria-checked={mode === 'pseudo'}
            class="mode-opt"
            class:active={mode === 'pseudo'}
            onclick={() => (mode = 'pseudo')}
          >
            <span class="mode-opt-title">{$t('landing.hero.mode.pseudo')}</span>
          </button>
          <button
            type="button"
            role="radio"
            aria-checked={mode === 'anon'}
            class="mode-opt"
            class:active={mode === 'anon'}
            onclick={() => (mode = 'anon')}
          >
            <span class="mode-opt-title">{$t('landing.hero.mode.anon')}</span>
          </button>
          <span class="mode-thumb" aria-hidden="true"></span>
        </div>
        <p class="mode-desc" aria-live="polite">
          {mode === 'pseudo' ? $t('landing.hero.mode.pseudo.desc') : $t('landing.hero.mode.anon.desc')}
        </p>
      </div>

      <div class="editor">
        <div class="panel panel-in">
          <header class="panel-head">
            <span class="panel-label">{$t('landing.hero.panel.input')}</span>
            <span class="panel-hint">{$t('landing.hero.panel.editable')}</span>
          </header>
          <textarea
            class="panel-body"
            spellcheck="false"
            autocomplete="off"
            bind:value={input}
            aria-label={$t('landing.hero.panel.input')}
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
            <span class="panel-label">{$t('landing.hero.panel.output')}</span>
            <span class="panel-count" class:has-hits={hits.length > 0}>
              {hits.length} {hits.length === 1 ? $t('landing.hero.panel.entity_sg') : $t('landing.hero.panel.entity_pl')} {$t('landing.hero.panel.redacted')}
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

      <!-- ── TRADEOFFS GRID ── -->
      <div class="tradeoffs" aria-label={$t('landing.hero.tradeoff.title')}>
        <h3 class="tradeoffs-title">{$t('landing.hero.tradeoff.title')}</h3>
        <div class="tradeoff-grid">
          <div class="tradeoff-row">
            <span class="tradeoff-axis">{$t('landing.hero.tradeoff.reversible')}</span>
            <span class="tradeoff-val val-neutral">
              {mode === 'pseudo' ? $t('landing.hero.tradeoff.yes_with_key') : $t('landing.hero.tradeoff.no')}
            </span>
          </div>
          <div class="tradeoff-row">
            <span class="tradeoff-axis">{$t('landing.hero.tradeoff.correlation')}</span>
            <span class="tradeoff-val val-neutral">
              {mode === 'pseudo' ? $t('landing.hero.tradeoff.preserved') : $t('landing.hero.tradeoff.broken')}
            </span>
          </div>
          <div class="tradeoff-row">
            <span class="tradeoff-axis">{$t('landing.hero.tradeoff.privacy')}</span>
            <span class="tradeoff-val val-pos">
              {mode === 'pseudo' ? $t('landing.hero.tradeoff.high') : $t('landing.hero.tradeoff.maximum')}
            </span>
          </div>
        </div>
      </div>
    </div>

    <div class="hero-actions">
      <a href="/app" class="cta-primary">{$t('landing.hero.cta')}</a>
      <span class="hero-meta">{$t('landing.hero.meta')}</span>
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
    <p class="section-label">{$t('landing.pipe.label')}</p>
    <h2 class="section-title pipe-heading">
      {$t('landing.pipe.title')}
      <span class="pipe-sub-head">{$t('landing.pipe.subtitle')}</span>
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
        <span class="node-name">{$t('landing.n1.name')}</span>
        <span class="node-note">{$t('landing.n1.note')}</span>
        {#if activeNode === 1}
          <div class="node-detail">
            <div class="nd-header" style="--nc:#60a5fa">
              <span class="nd-icon" style="--nc:#60a5fa">↑</span>
              <span class="nd-title">{$t('landing.n1.title')}</span>
            </div>
            <div class="nd-stats">
              <span class="nd-stat">{$t('landing.n1.stat.formats')}</span>
              <span class="nd-stat">{$t('landing.n1.stat.stream')}</span>
              <span class="nd-stat">{$t('landing.n1.stat.ram')}</span>
            </div>
            <div class="nd-formats">
              {#each ['TXT','CSV','JSON','PDF','DOCX','XLSX','XML','ZIP','PNG','JPG'] as f}
                <span class="nd-fmt">{f}</span>
              {/each}
            </div>
            <p class="nd-desc">{$t('landing.n1.desc')}</p>
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
        <span class="node-name">{$t('landing.n2.name')}</span>
        <span class="node-note">{$t('landing.n2.note')}</span>
        {#if activeNode === 2}
          <div class="node-detail">
            <div class="nd-header" style="--nc:#a78bfa">
              <span class="nd-icon" style="--nc:#a78bfa">◎</span>
              <span class="nd-title">{$t('landing.n2.title')}</span>
            </div>
            <div class="nd-stats">
              <span class="nd-stat">{$t('landing.n2.stat.entities')}</span>
              <span class="nd-stat">{$t('landing.n2.stat.cache')}</span>
              <span class="nd-stat">{$t('landing.n2.stat.regex')}</span>
            </div>
            <div class="nd-transform">
              <span class="nd-src">"John Doe"</span>
              <span class="nd-arrow">→</span>
              <span class="nd-tag" style="color:#a78bfa;border-color:color-mix(in srgb, #a78bfa 30%, transparent)">[PERSON]</span>
            </div>
            <div class="nd-transform">
              <span class="nd-src">CVE-2024-3400</span>
              <span class="nd-arrow">→</span>
              <span class="nd-tag" style="color:#f87171;border-color:color-mix(in srgb, #f87171 30%, transparent)">[CVE_ID]</span>
            </div>
            <p class="nd-desc">{$t('landing.n2.desc')}</p>
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
        <span class="node-name">{$t('landing.n3.name')}</span>
        <span class="node-note">{$t('landing.n3.note')}</span>
        {#if activeNode === 3}
          <div class="node-detail">
            <div class="nd-header" style="--nc:#fbbf24">
              <span class="nd-icon" style="--nc:#fbbf24">⬡</span>
              <span class="nd-title">{$t('landing.n3.title')}</span>
            </div>
            <div class="nd-stats">
              <span class="nd-stat">{$t('landing.n3.stat.bits')}</span>
              <span class="nd-stat">{$t('landing.n3.stat.det')}</span>
              <span class="nd-stat">{$t('landing.n3.stat.key')}</span>
            </div>
            <div class="nd-code">
              <span class="nd-code-line"><span class="nd-kw">key</span> + entity → <span class="nd-val">48624b5c</span></span>
              <span class="nd-code-line nd-muted">{$t('landing.n3.code_note')}</span>
            </div>
            <p class="nd-desc">{$t('landing.n3.desc')}</p>
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
        <span class="node-name">{$t('landing.n4.name')}</span>
        <span class="node-note">{$t('landing.n4.note')}</span>
        {#if activeNode === 4}
          <div class="node-detail">
            <div class="nd-header" style="--nc:#34d399">
              <span class="nd-icon" style="--nc:#34d399">◈</span>
              <span class="nd-title">{$t('landing.n4.title')}</span>
            </div>
            <div class="nd-stats">
              <span class="nd-stat">{$t('landing.n4.stat.types')}</span>
              <span class="nd-stat">{$t('landing.n4.stat.schema')}</span>
              <span class="nd-stat">{$t('landing.n4.stat.cats')}</span>
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
            <p class="nd-desc">{$t('landing.n4.desc')}</p>
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
        <span class="node-name">{$t('landing.n5.name')}</span>
        <span class="node-note">{$t('landing.n5.note')}</span>
        {#if activeNode === 5}
          <div class="node-detail">
            <div class="nd-header" style="--nc:#2dd4bf">
              <span class="nd-icon" style="--nc:#2dd4bf">↓</span>
              <span class="nd-title">{$t('landing.n5.title')}</span>
            </div>
            <div class="nd-stats">
              <span class="nd-stat">{$t('landing.n5.stat.instant')}</span>
              <span class="nd-stat">{$t('landing.n5.stat.retained')}</span>
            </div>
            <div class="nd-zero">
              <div class="nd-zero-row">
                <span class="nd-zero-label">{$t('landing.n5.zero.original')}</span>
                <span class="nd-zero-val nd-deleted">— {$t('landing.n5.zero.deleted')}</span>
              </div>
              <div class="nd-zero-row">
                <span class="nd-zero-label">{$t('landing.n5.zero.anon')}</span>
                <span class="nd-zero-val nd-ok">↓ {$t('landing.n5.zero.download')}</span>
              </div>
              <div class="nd-zero-row">
                <span class="nd-zero-label">{$t('landing.n5.zero.after')}</span>
                <span class="nd-zero-val nd-deleted">— {$t('landing.n5.zero.deleted')}</span>
              </div>
            </div>
            <p class="nd-desc">{$t('landing.n5.desc')}</p>
          </div>
        {/if}
      </div>
    </div>

    <p class="pipe-note">{$t('landing.pipe.note')}</p>
  </div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!-- STATS                                                                  -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->
<section class="stats-section reveal" bind:this={statsRef}>
  <div class="stats-inner">
    <div class="stat-block">
      <span class="stat-val" class:animated={statsVisible}>738<span class="stat-unit">×</span></span>
      <span class="stat-desc">{$t('landing.stat.faster')}</span>
    </div>
    <div class="stat-block">
      <span class="stat-val" class:animated={statsVisible}>94.2<span class="stat-unit">%</span></span>
      <span class="stat-desc">{$t('landing.stat.f1')}</span>
    </div>
    <div class="stat-block">
      <span class="stat-val" class:animated={statsVisible}>96.7<span class="stat-unit">%</span></span>
      <span class="stat-desc">{$t('landing.stat.recall')}</span>
    </div>
    <div class="stat-block">
      <span class="stat-val" class:animated={statsVisible}>550<span class="stat-unit">MB</span></span>
      <span class="stat-desc">{$t('landing.stat.throughput')}</span>
    </div>
    <div class="stat-block">
      <span class="stat-val" class:animated={statsVisible}>0</span>
      <span class="stat-desc">{$t('landing.stat.cloud')}</span>
    </div>
    <div class="stat-block">
      <span class="stat-val" class:animated={statsVisible}>1<span class="stat-unit">MB</span></span>
      <span class="stat-desc">{$t('landing.stat.demo_limit')}</span>
    </div>
  </div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!-- FORMATS                                                                -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->
<div class="formats-bar reveal">
  <span class="formats-lbl">{$t('landing.fmt.label')}</span>
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
    <p class="section-label">{$t('landing.research.label')}</p>
    <h2 class="section-title">{$t('landing.research.title')}</h2>
    <p class="research-sub">{$t('landing.research.sub')}</p>

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
          <p class="paper-context">{$t('landing.research.gen1.ctx')}</p>
          <div class="paper-metrics">
            <span class="pm pm-good">100% Precision</span>
            <span class="pm pm-good">97.38% Recall</span>
            <span class="pm pm-info">763 {$t('landing.research.gen1.incidents')}</span>
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
          <p class="paper-context">{$t('landing.research.gen2.ctx')}</p>
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
            <span class="paper-gen accent-gen">AnonShield ← {$t('landing.research.gen3.here')}</span>
          </div>
          <h3 class="paper-title">AnonShield: Scalable On-Premise Pseudonymization for CSIRT Vulnerability Data</h3>
          <p class="paper-authors">C. Kapelinski, D. Lautert, B. Machado, I. G. Ferrão, D. Kreutz · UNIPAMPA / UBO</p>
          <p class="paper-context">{$t('landing.research.gen3.ctx')}</p>
          <div class="paper-metrics">
            <span class="pm pm-good">94.2% F1</span>
            <span class="pm pm-good">96.7% Recall</span>
            <span class="pm pm-hero">738× {$t('landing.research.gen3.faster')}</span>
            <span class="pm pm-hero">&lt;10 min / 550 MB</span>
            <span class="pm pm-info">70,951 {$t('landing.research.gen3.records')}</span>
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
    <p class="section-label">{$t('landing.team.label')}</p>
    <h2 class="section-title">{$t('landing.team.title')}</h2>

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

    <p class="team-affil">{$t('landing.team.affil')}</p>
  </div>
</section>

<!-- ═══════════════════════════════════════════════════════════════════════ -->
<!-- CTA + CONTACT                                                          -->
<!-- ═══════════════════════════════════════════════════════════════════════ -->
<section class="cta-section reveal">
  <div class="cta-inner">
    <h2 class="cta-title">{$t('landing.cta.title')}</h2>
    <p class="cta-sub">{$t('landing.cta.sub')}</p>
    <a href="/app" class="cta-btn">{$t('landing.cta.btn')}</a>
    <a href="mailto:anonshield@unipampa.edu.br" class="cta-email">anonshield@unipampa.edu.br</a>
  </div>
</section>

<style>
  /* ── Shared ── */
  .section-label {
    font-size: var(--text-xs); font-weight: 700; letter-spacing: 0.12em;
    text-transform: uppercase; color: var(--color-accent);
    margin: 0 0 var(--space-3);
  }
  .section-title {
    margin: 0 0 var(--space-12); font-size: clamp(1.4rem, 3vw, 2rem);
    font-weight: 800; letter-spacing: -0.035em;
    color: var(--color-text-primary);
  }

  /* ══════════════ HERO ══════════════ */
  .hero {
    padding: 56px 24px 48px;
    background: radial-gradient(ellipse 80% 60% at 50% -20%,
      color-mix(in srgb, var(--color-accent) 12%, transparent) 0%,
      transparent 70%);
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
    font-size: var(--text-base); line-height: 1.7;
    color: var(--color-text-secondary);
  }

  /* ── Demo ── */
  .demo-wrap { display: flex; flex-direction: column; gap: var(--space-3); }

  .demo-label {
    display: flex; align-items: center; justify-content: space-between;
    flex-wrap: wrap; gap: var(--space-2);
  }
  .demo-live {
    display: flex; align-items: center; gap: var(--space-2);
    font-size: var(--text-xs); font-weight: 600; letter-spacing: 0.05em;
    text-transform: uppercase; color: var(--color-text-primary);
  }
  .live-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--color-success);
    animation: pulse-dot 1.5s ease-in-out infinite;
  }
  .demo-hint {
    font-size: var(--text-xs); font-family: var(--font-mono);
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
    font-size: var(--text-xs); font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: var(--color-text-secondary);
    font-family: var(--font-mono);
  }
  .panel-hint { font-size: var(--text-xs); color: var(--color-border); font-family: var(--font-mono); }
  .panel-count {
    font-size: var(--text-xs); font-family: var(--font-mono);
    color: var(--color-text-secondary); transition: color var(--duration-fast) var(--ease-out);
  }
  .panel-count.has-hits { color: var(--color-success); }

  .panel-body {
    flex: 1; padding: var(--space-4);
    font-family: var(--font-mono); font-size: var(--text-xs); line-height: 1.75;
    color: var(--color-text-secondary);
    white-space: pre-wrap; word-break: break-word; overflow-y: auto;
  }
  textarea.panel-body {
    border: none; outline: none; resize: none;
    background: transparent; width: 100%;
  }
  textarea.panel-body:focus { color: var(--color-text-primary); }
  .output-body {
    /* deliberately muted "ghost" tone — below --color-text-secondary to indicate non-primary output */
    color: color-mix(in srgb, var(--color-text-secondary) 55%, var(--color-surface));
  }

  :global(.ent) {
    background: color-mix(in srgb, var(--c) 12%, transparent);
    border: 1px solid color-mix(in srgb, var(--c) 35%, transparent);
    border-radius: var(--radius-sm); padding: 0 var(--space-1); margin: 0 1px;
    font-style: normal; font-size: var(--text-xs);
    white-space: nowrap; cursor: default;
    transition: background var(--duration-fast) var(--ease-out);
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

  /* Mode toggle — segmented control with sliding thumb (Fitts: large targets; Miller: 2 options)
     Thumb animates between positions to imply state change is causal, not magical. */
  .mode-toggle {
    display: grid;
    grid-template-columns: auto 1fr;
    grid-template-areas: 'label switch' 'desc desc';
    align-items: center;
    gap: var(--space-2) var(--space-3);
    padding: var(--space-2) 0;
  }
  .mode-label {
    grid-area: label;
    font-size: var(--text-xs);
    font-weight: 600;
    color: var(--color-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }
  .mode-switch {
    grid-area: switch;
    position: relative;
    display: inline-flex;
    padding: 3px;
    background: var(--color-surface-raised);
    border: 1px solid var(--color-border);
    border-radius: 999px;
    justify-self: start;
    isolation: isolate;
  }
  .mode-opt {
    position: relative;
    z-index: 2;
    padding: var(--space-2) var(--space-5);
    background: none;
    border: none;
    border-radius: 999px;
    color: var(--color-text-secondary);
    font-size: var(--text-sm);
    font-weight: 600;
    cursor: pointer;
    transition: color var(--duration-fast) var(--ease-out);
  }
  .mode-opt:hover { color: var(--color-text-primary); }
  .mode-opt.active { color: #fff; }
  .mode-opt:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
  .mode-thumb {
    position: absolute;
    z-index: 1;
    top: 3px; bottom: 3px; left: 3px;
    width: calc(50% - 3px);
    background: var(--color-accent);
    border-radius: 999px;
    box-shadow: 0 2px 8px color-mix(in srgb, var(--color-accent) 40%, transparent);
    transition: transform var(--duration-slow) var(--ease-out),
                background var(--duration-slow) var(--ease-out);
  }
  .mode-switch.is-anon .mode-thumb {
    transform: translateX(100%);
    background: #a78bfa;
    box-shadow: 0 2px 8px color-mix(in srgb, #a78bfa 50%, transparent);
  }
  .mode-desc {
    grid-area: desc;
    margin: 0;
    font-size: var(--text-sm);
    color: var(--color-text-secondary);
    animation: fade-up var(--duration-slow) var(--ease-out);
  }
  @keyframes fade-up {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
  }

  /* Token span inside .ent — dims the hashed slug slightly so the type label reads as primary */
  :global(.ent-token) {
    opacity: 0.72;
    font-weight: 500;
  }

  /* Tradeoffs — three-axis grid that re-renders on mode change.
     Axis labels stay constant (Gestalt: common region); values animate to cue the change. */
  .tradeoffs {
    display: flex; flex-direction: column; gap: var(--space-3);
    padding: var(--space-4) var(--space-5);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    background: color-mix(in srgb, var(--color-surface-raised) 40%, transparent);
  }
  .tradeoffs-title {
    margin: 0;
    font-size: var(--text-xs);
    font-weight: 700;
    color: var(--color-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }
  .tradeoff-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--space-4);
  }
  @media (max-width: 680px) {
    .tradeoff-grid { grid-template-columns: 1fr; gap: var(--space-2); }
  }
  .tradeoff-row {
    display: flex; flex-direction: column; gap: 2px;
    padding: var(--space-2) var(--space-3);
    border-left: 2px solid var(--color-border);
    transition: border-color var(--duration-fast) var(--ease-out);
  }
  .tradeoff-axis {
    font-size: var(--text-xs);
    color: var(--color-text-secondary);
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .tradeoff-val {
    font-size: var(--text-base);
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    animation: val-swap var(--duration-slow) var(--ease-out);
  }
  @keyframes val-swap {
    from { opacity: 0; transform: translateY(-3px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  .val-pos { color: var(--color-success); }
  .val-neg { color: var(--color-warning); }
  .val-neutral { color: var(--color-text); }
  .tradeoff-row:has(.val-pos) { border-left-color: var(--color-success); }
  .tradeoff-row:has(.val-neg) { border-left-color: var(--color-warning); }

  /* Legend — inline chip strip, monospaced for alignment */
  .legend {
    display: flex; flex-wrap: wrap; gap: var(--space-2) var(--space-4);
    padding: 2px 0;
  }
  .legend-item {
    display: flex; align-items: center; gap: var(--space-2);
    font-size: var(--text-xs); font-family: var(--font-mono);
  }
  .legend-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--c);
    box-shadow: 0 0 5px color-mix(in srgb, var(--c) 60%, transparent);
  }
  .legend-type { color: var(--color-text-secondary); }
  .legend-n {
    color: var(--c); font-weight: 700;
    padding: 0 var(--space-2);
    background: color-mix(in srgb, var(--c) 12%, transparent);
    border-radius: 999px;
  }

  /* Hero actions — primary CTA uses accent token; glow shadow derived from accent via color-mix
     so it stays in sync with the palette (no hex literal of 99,102,241). */
  .hero-actions { display: flex; align-items: center; gap: var(--space-5); flex-wrap: wrap; }
  .cta-primary {
    display: inline-flex; align-items: center;
    padding: var(--space-3) var(--space-8);
    background: var(--color-accent); color: #fff;
    border-radius: var(--radius-md);
    font-size: var(--text-base); font-weight: 700;
    text-decoration: none; letter-spacing: -0.01em;
    transition: background var(--duration-fast) var(--ease-out),
                transform var(--duration-fast) var(--ease-out),
                box-shadow var(--duration-fast) var(--ease-out);
    box-shadow: 0 0 24px color-mix(in srgb, var(--color-accent) 30%, transparent);
  }
  .cta-primary:hover {
    background: var(--color-accent-hover); color: #fff;
    transform: translateY(-2px);
    box-shadow: 0 6px 32px color-mix(in srgb, var(--color-accent) 45%, transparent);
  }
  .cta-primary:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 3px;
  }
  .hero-meta {
    font-size: var(--text-xs); font-family: var(--font-mono);
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
    background: linear-gradient(90deg,
      transparent,
      color-mix(in srgb, var(--color-accent) 6%, transparent),
      transparent);
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
    background-image: radial-gradient(circle,
      color-mix(in srgb, var(--color-accent) 15%, transparent) 1px,
      transparent 1px);
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
      0 24px 64px color-mix(in srgb, #000 75%, transparent),
      0 0 0 1px color-mix(in srgb, #fff 3%, transparent),
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
    font-size: var(--text-base); color: var(--nc);
    width: 24px; height: 24px;
    display: flex; align-items: center; justify-content: center;
    background: color-mix(in srgb, var(--nc) 14%, transparent);
    border-radius: var(--radius-sm);
    flex-shrink: 0;
  }
  .nd-title {
    font-size: var(--text-sm); font-weight: 700;
    color: var(--color-text-primary); letter-spacing: 0.01em;
  }

  /* Stat pills — neutral chips on tinted glass surface */
  .nd-stats {
    display: flex; flex-wrap: wrap; gap: var(--space-1);
    padding: var(--space-3) var(--space-4) var(--space-2);
  }
  .nd-stat {
    font-size: var(--text-xs); font-weight: 600;
    padding: 2px var(--space-2);
    border-radius: 100px;
    background: color-mix(in srgb, var(--color-text-primary) 5%, transparent);
    border: 1px solid color-mix(in srgb, var(--color-text-primary) 9%, transparent);
    color: color-mix(in srgb, var(--color-text-secondary) 80%, var(--color-text-primary));
    letter-spacing: 0.03em;
    white-space: nowrap;
  }

  /* Format tags (node 1) — syntax-coloured blue for "file format" domain */
  .nd-formats {
    display: flex; flex-wrap: wrap; gap: var(--space-1);
    padding: 2px var(--space-4) var(--space-3);
  }
  .nd-fmt {
    --fmt-blue: #60a5fa;
    font-size: var(--text-xs); font-weight: 700;
    font-family: var(--font-mono);
    padding: 2px var(--space-2);
    border-radius: var(--radius-sm);
    background: color-mix(in srgb, var(--fmt-blue) 10%, transparent);
    border: 1px solid color-mix(in srgb, var(--fmt-blue) 22%, transparent);
    color: var(--fmt-blue);
    letter-spacing: 0.04em;
  }

  /* Entity transform rows (node 2) */
  .nd-transform {
    display: flex; align-items: center; gap: var(--space-2);
    padding: 3px var(--space-4);
    font-family: var(--font-mono);
    font-size: var(--text-xs);
  }
  .nd-src { color: var(--color-text-secondary); }
  .nd-arrow { color: color-mix(in srgb, var(--color-text-secondary) 60%, var(--color-surface)); }
  .nd-tag {
    padding: 1px var(--space-2);
    border-radius: var(--radius-sm);
    border: 1px solid;
    font-weight: 600; font-size: var(--text-xs);
  }

  /* Code block (node 3) — darker recessed surface to feel like a terminal/code snippet */
  .nd-code {
    margin: var(--space-1) var(--space-4) var(--space-2);
    background: color-mix(in srgb, #000 40%, transparent);
    border: 1px solid color-mix(in srgb, var(--color-text-primary) 6%, transparent);
    border-radius: var(--radius-md);
    padding: var(--space-2) var(--space-3);
    display: flex; flex-direction: column; gap: var(--space-1);
  }
  .nd-code-line {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: color-mix(in srgb, var(--color-text-primary) 85%, var(--color-text-secondary));
  }
  /* Syntax highlight — keyword amber matches --color-warning; muted italics for comments */
  .nd-kw { color: var(--color-warning); font-weight: 600; }
  .nd-val { color: var(--color-warning); }
  .nd-muted {
    color: color-mix(in srgb, var(--color-text-secondary) 65%, var(--color-surface));
    font-style: italic;
  }

  /* Before/after replace demo (node 4) */
  .nd-replace-demo {
    margin: var(--space-1) var(--space-4) var(--space-2);
    background: color-mix(in srgb, #000 30%, transparent);
    border: 1px solid color-mix(in srgb, var(--color-text-primary) 5%, transparent);
    border-radius: var(--radius-md);
    padding: var(--space-2) var(--space-3);
    display: flex; flex-direction: column; gap: var(--space-2);
  }
  .nd-replace-row {
    display: flex; flex-direction: column; gap: 2px;
  }
  .nd-replace-before {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--color-error);
    text-decoration: line-through;
    text-decoration-color: color-mix(in srgb, var(--color-error) 40%, transparent);
  }
  .nd-replace-after {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: color-mix(in srgb, var(--color-text-primary) 85%, var(--color-text-secondary));
  }

  /* Zero-retention table (node 5) */
  .nd-zero {
    margin: var(--space-1) var(--space-4) var(--space-2);
    display: flex; flex-direction: column; gap: var(--space-1);
  }
  .nd-zero-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: var(--space-1) 0;
    border-bottom: 1px solid color-mix(in srgb, var(--color-text-primary) 4%, transparent);
    font-size: var(--text-xs);
  }
  .nd-zero-row:last-child { border-bottom: none; }
  .nd-zero-label {
    color: color-mix(in srgb, var(--color-text-secondary) 80%, var(--color-text-primary));
    font-family: var(--font-mono);
  }
  .nd-zero-val { font-weight: 600; font-family: var(--font-mono); }
  .nd-deleted { color: var(--color-error); }
  .nd-ok { color: var(--color-success); }

  /* Description text */
  .nd-desc {
    margin: 0;
    padding: var(--space-2) var(--space-4) var(--space-4);
    font-size: var(--text-xs); line-height: 1.6;
    color: color-mix(in srgb, var(--color-text-secondary) 80%, var(--color-text-primary));
    border-top: 1px solid color-mix(in srgb, var(--color-text-primary) 4%, transparent);
  }

  /* Description-only fallback (old style) */
  .node-detail > p:only-child {
    margin: 0;
    padding: var(--space-4);
    font-size: var(--text-xs); line-height: 1.65;
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
  }
  @keyframes detail-in {
    from { opacity: 0; transform: translateX(-50%) translateY(-6px); }
    to   { opacity: 1; transform: translateX(-50%) translateY(0); }
  }
  /* Affordance hint — shows on hover to signal interactivity without clutter */
  .pipe-node::after {
    content: '↕';
    position: absolute; bottom: -4px; right: -4px;
    font-size: var(--text-xs); color: color-mix(in srgb, var(--nc) 60%, transparent);
    opacity: 0; transition: opacity var(--duration-normal) var(--ease-out);
    pointer-events: none;
  }
  .pipe-node:hover::after { opacity: 1; }

  .node-name {
    font-size: var(--text-sm); font-weight: 700; color: var(--color-text-primary);
    letter-spacing: -0.01em; line-height: 1.3; position: relative; z-index: 1;
  }
  .node-note {
    font-size: var(--text-xs); font-family: var(--font-mono);
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
    text-align: center; font-size: var(--text-xs); font-family: var(--font-mono);
    color: var(--color-text-secondary); line-height: 1.8;
    max-width: 640px; margin: 0 auto;
    padding: var(--space-4) var(--space-6);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-text-primary) 3%, transparent);
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
  .stat-unit { font-size: var(--text-lg); font-weight: 600; opacity: 0.6; }
  .stat-desc {
    font-size: var(--text-xs); text-transform: uppercase; letter-spacing: 0.06em;
    color: var(--color-text-secondary); max-width: 120px;
  }

  /* ══════════════ FORMATS BAR ══════════════ */
  .formats-bar {
    display: flex; align-items: center; gap: var(--space-5); flex-wrap: wrap;
    padding: var(--space-5) var(--space-6);
    max-width: 1200px; margin: 0 auto;
    border-bottom: 1px solid var(--color-border);
  }
  .formats-lbl {
    font-size: var(--text-xs); font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: var(--color-text-secondary);
    white-space: nowrap; flex-shrink: 0;
  }
  .formats-tags { display: flex; flex-wrap: wrap; gap: var(--space-1); }
  .fmt-tag {
    font-family: var(--font-mono); font-size: var(--text-xs);
    color: var(--color-text-secondary);
    border: 1px solid var(--color-border); border-radius: var(--radius-sm);
    padding: 2px var(--space-2); background: var(--color-surface-raised);
    transition: border-color var(--duration-fast) var(--ease-out),
                color var(--duration-fast) var(--ease-out);
  }
  .fmt-tag:hover { border-color: var(--color-accent); color: var(--color-text-primary); }

  /* ══════════════ RESEARCH ══════════════ */
  .research {
    padding: var(--space-16) var(--space-6);
    border-bottom: 1px solid var(--color-border);
  }
  .research-inner { max-width: 900px; margin: 0 auto; }
  .research-sub {
    margin: calc(var(--space-8) * -1) 0 var(--space-12);
    font-size: var(--text-sm); line-height: 1.7;
    color: var(--color-text-secondary); max-width: 640px;
  }

  /* Timeline */
  .timeline { display: flex; flex-direction: column; gap: 0; overflow: visible; }

  .tl-item {
    display: grid; grid-template-columns: 48px 24px 1fr;
    gap: 0 var(--space-4); align-items: start;
    min-width: 0;
  }
  .tl-item.tl-current .paper-card { grid-column: 2 / -1; }

  .tl-marker {
    display: flex; align-items: center; justify-content: center;
    width: 36px; height: 36px; border-radius: 50%;
    border: 2px solid var(--color-border);
    background: var(--color-surface-raised);
    flex-shrink: 0; position: relative; z-index: 1;
    margin-top: var(--space-5);
  }
  .tl-marker.current {
    border-color: var(--color-accent);
    background: color-mix(in srgb, var(--color-accent) 15%, var(--color-surface));
    box-shadow: 0 0 16px color-mix(in srgb, var(--color-accent) 30%, transparent);
    animation: pulse-glow 2s ease-in-out infinite;
  }
  @keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 16px color-mix(in srgb, var(--color-accent) 30%, transparent); }
    50%       { box-shadow: 0 0 28px color-mix(in srgb, var(--color-accent) 55%, transparent); }
  }
  .tl-gen {
    font-size: var(--text-xs); font-weight: 800; font-family: var(--font-mono);
    color: var(--color-text-secondary);
  }
  .tl-marker.current .tl-gen { color: var(--color-accent); }

  .tl-connector {
    width: 2px; background: var(--color-border);
    margin-left: 17px;
    min-height: 32px;
    align-self: stretch;
  }
  .tl-item:last-child .tl-connector { display: none; }

  .paper-card {
    padding: var(--space-5) var(--space-6);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md); background: var(--color-surface-raised);
    display: flex; flex-direction: column; gap: var(--space-3);
    margin-bottom: var(--space-6);
    transition: border-color var(--duration-normal) var(--ease-out),
                box-shadow var(--duration-normal) var(--ease-out);
  }
  .paper-card:hover {
    border-color: color-mix(in srgb, var(--color-accent) 50%, transparent);
  }
  .current-paper {
    border-color: color-mix(in srgb, var(--color-accent) 40%, transparent);
    background: color-mix(in srgb, var(--color-accent) 4%, var(--color-surface-raised));
  }

  .paper-venue-row {
    display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap;
  }
  .paper-venue {
    font-size: var(--text-xs); font-weight: 800; letter-spacing: 0.1em;
    text-transform: uppercase; color: var(--color-accent);
    font-family: var(--font-mono);
  }
  .accent-venue { color: var(--color-accent-hover); }
  .paper-gen {
    font-size: var(--text-xs); font-family: var(--font-mono);
    color: var(--color-text-secondary); opacity: 0.7;
  }
  .accent-gen { color: var(--color-accent); opacity: 1; }

  .paper-title {
    margin: 0; font-size: var(--text-sm); font-weight: 600;
    color: var(--color-text-primary); line-height: 1.4;
  }
  .paper-authors {
    margin: 0; font-size: var(--text-xs); color: var(--color-text-secondary);
    font-family: var(--font-mono);
  }
  .paper-context {
    margin: 0; font-size: var(--text-sm); color: var(--color-text-secondary);
    line-height: 1.6;
  }
  .paper-metrics {
    display: flex; flex-wrap: wrap; gap: var(--space-2); margin-top: var(--space-1);
  }
  .pm {
    font-size: var(--text-xs); font-weight: 700; font-family: var(--font-mono);
    color: var(--color-text-secondary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm); padding: 2px var(--space-2);
    background: var(--color-surface);
  }
  .pm-good {
    color: var(--color-success);
    border-color: color-mix(in srgb, var(--color-success) 30%, transparent);
    background: color-mix(in srgb, var(--color-success) 6%, transparent);
  }
  .pm-hero {
    --hero-lilac: #a5b4fc;
    color: var(--hero-lilac);
    border-color: color-mix(in srgb, var(--hero-lilac) 30%, transparent);
    background: color-mix(in srgb, var(--hero-lilac) 8%, transparent);
    font-size: var(--text-xs);
  }
  .pm-info {
    --info-sky: #38bdf8;
    color: var(--info-sky);
    border-color: color-mix(in srgb, var(--info-sky) 30%, transparent);
    background: color-mix(in srgb, var(--info-sky) 6%, transparent);
  }

  .paper-link {
    font-size: var(--text-xs); font-family: var(--font-mono); font-weight: 700;
    color: var(--color-accent); text-decoration: none;
    margin-top: var(--space-1); width: fit-content;
    transition: color var(--duration-fast) var(--ease-out),
                transform var(--duration-fast) var(--ease-out);
    display: inline-block;
  }
  .paper-link:hover { color: var(--color-accent-hover); transform: translateX(3px); }
  .paper-link:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 3px;
    border-radius: var(--radius-sm);
  }


  /* ══════════════ TEAM ══════════════ */
  .team {
    padding: var(--space-16) var(--space-6);
    border-bottom: 1px solid var(--color-border);
    background: var(--color-surface-raised);
  }
  .team-inner { max-width: 1200px; margin: 0 auto; }

  .members {
    display: flex; flex-wrap: wrap; gap: var(--space-3);
    margin-bottom: var(--space-6);
  }
  .member {
    display: flex; flex-direction: column; gap: var(--space-1);
    padding: var(--space-4) var(--space-6);
    border: 1px solid var(--color-border); border-radius: var(--radius-md);
    background: var(--color-surface);
    min-width: 180px;
    transition: border-color var(--duration-normal) var(--ease-out);
  }
  .member:hover { border-color: var(--color-accent); }
  .member-name {
    font-size: var(--text-sm); font-weight: 600; color: var(--color-text-primary);
  }
  .member-role {
    font-size: var(--text-xs); font-family: var(--font-mono);
    color: var(--color-accent);
  }
  .team-affil {
    margin: 0; font-size: var(--text-xs); font-family: var(--font-mono);
    color: var(--color-text-secondary); line-height: 1.6;
  }

  /* ══════════════ CTA ══════════════ */
  .cta-section {
    padding: var(--space-16) var(--space-6);
    text-align: center;
    background: radial-gradient(ellipse 60% 80% at 50% 100%,
      color-mix(in srgb, var(--color-accent) 10%, transparent) 0%,
      transparent 70%);
  }
  .cta-inner {
    max-width: 480px; margin: 0 auto;
    display: flex; flex-direction: column; align-items: center; gap: var(--space-4);
  }
  .cta-title {
    margin: 0; font-size: clamp(1.4rem, 3vw, 2rem); font-weight: 800;
    letter-spacing: -0.035em; color: var(--color-text-primary);
  }
  .cta-sub {
    margin: 0; font-size: var(--text-sm); font-family: var(--font-mono);
    color: var(--color-text-secondary);
  }
  .cta-btn {
    display: inline-flex; align-items: center;
    padding: var(--space-4) var(--space-12);
    background: var(--color-accent); color: #fff;
    border-radius: var(--radius-md); font-size: var(--text-base); font-weight: 700;
    text-decoration: none; letter-spacing: -0.01em;
    transition: background var(--duration-fast) var(--ease-out),
                transform var(--duration-fast) var(--ease-out),
                box-shadow var(--duration-fast) var(--ease-out);
    box-shadow: 0 0 32px color-mix(in srgb, var(--color-accent) 30%, transparent);
  }
  .cta-btn:hover {
    background: var(--color-accent-hover); color: #fff;
    transform: translateY(-2px);
    box-shadow: 0 8px 40px color-mix(in srgb, var(--color-accent) 45%, transparent);
  }
  .cta-btn:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 3px;
  }
  .cta-email {
    font-size: var(--text-xs); font-family: var(--font-mono);
    color: var(--color-text-secondary); text-decoration: none;
    transition: color var(--duration-fast) var(--ease-out);
  }
  .cta-email:hover { color: var(--color-accent); }
  .cta-email:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 3px;
    border-radius: var(--radius-sm);
  }

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
    animation: stagger-up var(--duration-slow) var(--ease-out) both;
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
    .mode-thumb { transition: none; }
    .mode-desc, .tradeoff-val { animation: none; }
    .live-dot, .scan-beam, .halo, .flow-line,
    :global(.pm-hero) { animation: none !important; }
  }
</style>

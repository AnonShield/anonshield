<script lang="ts">
  import { t } from '$lib/i18n';
  import HtmlDeck from '$lib/components/HtmlDeck.svelte';
  import DeckScroll from '$lib/components/DeckScroll.svelte';

  let mode = $state<'deck' | 'scroll'>('deck');

  const papers = [
    { name: 'AnonShield: Scalable On-Premise Pseudonymization for CSIRT Network Vulnerability Data', venue: 'SBRC 2026', url: 'https://sol.sbc.org.br/index.php/sbrc_estendido/article/view/42580' },
    { name: 'AnonLFI v2.0: extensible pseudonymization for CSIRTs', venue: 'ERRC 2025', url: 'https://sol.sbc.org.br/index.php/errc/article/view/39186' },
    { name: 'AnonLFI v1.0: incident report anonymization', venue: 'SBSeg 2025', url: 'https://sol.sbc.org.br/index.php/sbseg/article/view/36614' },
    { name: 'Severo et al.: incident classification with LLMs and prompt engineering', venue: 'SBSeg 2025', url: 'https://doi.org/10.5753/sbseg_estendido.2025.12510' },
    { name: 'Almeida et al.: on-premise vs commercial LLMs for incident classification', venue: '2025', url: 'https://doi.org/10.48550/arXiv.2511.14908' },
  ];
  const tools = [
    { name: 'OpenVAS / Greenbone', venue: 'vulnerability scanner', url: 'https://www.greenbone.net/' },
    { name: 'Tenable', venue: 'vulnerability scanner', url: 'https://www.tenable.com/' },
    { name: 'VulnLab', venue: 'testbed, 130 containers', url: 'https://github.com/AnonShield/LabVulnerabilities' },
    { name: 'SBRC 2026 artifact evaluation', venue: 'official results', url: 'https://doc-artefatos.github.io/sbrc2026/results.html' },
    { name: 'CERT.br', venue: 'incident statistics', url: 'https://stats.cert.br/' },
    { name: 'NIST NVD', venue: 'vulnerability database', url: 'https://nvd.nist.gov/' },
  ];
</script>

<svelte:head>
  <title>Slides · AnonShield</title>
  <meta name="description" content="AnonShield presentation slides. Best Artifact at SBRC 2026." />
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap" />
</svelte:head>

<section class="slides-page">
  <header class="s-head">
    <p class="section-label">{$t('slides.label')}</p>
    <h1 class="s-title">{$t('slides.title')}</h1>
  </header>

  <div class="mode-switch" role="tablist" aria-label={$t('slides.label')}>
    <button
      class="mode-btn" class:active={mode === 'deck'}
      role="tab" aria-selected={mode === 'deck'}
      onclick={() => (mode = 'deck')}
    >▤ {$t('slides.mode.deck')}</button>
    <button
      class="mode-btn" class:active={mode === 'scroll'}
      role="tab" aria-selected={mode === 'scroll'}
      onclick={() => (mode = 'scroll')}
    >☰ {$t('slides.mode.scroll')}</button>
  </div>

  {#if mode === 'deck'}
    <HtmlDeck pdf="/slides/AnonShield-slides.pdf" />
    <p class="s-hint">{$t('slides.hint')}</p>
  {:else}
    <DeckScroll />
    <p class="s-hint">{$t('slides.scroll_hint')}</p>
  {/if}

  <section class="refs">
    <h2 class="section-title">{$t('slides.refs.title')}</h2>
    <p class="refs-sub">{$t('slides.refs.sub')}</p>
    <div class="refs-grid">
      <div class="refs-col">
        <h3 class="refs-h">{$t('slides.refs.papers')}</h3>
        {#each papers as r (r.url)}
          <a class="ref" href={r.url} target="_blank" rel="noopener noreferrer">
            <span class="ref-name">{r.name}</span>
            <span class="ref-venue">{r.venue} ↗</span>
          </a>
        {/each}
      </div>
      <div class="refs-col">
        <h3 class="refs-h">{$t('slides.refs.tools')}</h3>
        {#each tools as r (r.url)}
          <a class="ref" href={r.url} target="_blank" rel="noopener noreferrer">
            <span class="ref-name">{r.name}</span>
            <span class="ref-venue">{r.venue} ↗</span>
          </a>
        {/each}
      </div>
    </div>
  </section>
</section>

<style>
  .slides-page {
    max-width: 960px; margin: 0 auto;
    padding: var(--space-12) var(--space-6) var(--space-16);
    display: flex; flex-direction: column; gap: var(--space-6);
  }

  .s-head { text-align: center; }
  .section-label {
    font-size: var(--text-xs); font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase;
    color: var(--color-accent); margin: 0 0 var(--space-2);
  }
  .s-title {
    font-size: var(--text-2xl); font-weight: 800; letter-spacing: -0.02em;
    margin: 0 0 var(--space-2); color: var(--color-text-primary);
  }
  .s-sub { margin: 0 auto; max-width: 60ch; color: var(--color-text-secondary); }

  .s-hint {
    text-align: center; font-size: var(--text-xs); color: var(--color-text-secondary);
    margin: calc(var(--space-2) * -1) 0 0;
  }

  .mode-switch {
    display: inline-flex; align-self: center; gap: 2px;
    padding: 3px; border: 1px solid var(--color-border); border-radius: var(--radius-md);
    background: var(--color-surface-raised);
  }
  .mode-btn {
    display: inline-flex; align-items: center; gap: var(--space-2);
    padding: var(--space-2) var(--space-4);
    border: none; border-radius: var(--radius-sm); background: transparent;
    color: var(--color-text-secondary);
    font-size: var(--text-sm); font-weight: 600; cursor: pointer;
    transition: background var(--duration-fast) var(--ease-out),
                color var(--duration-fast) var(--ease-out);
  }
  .mode-btn:hover { color: var(--color-text-primary); }
  .mode-btn.active { background: var(--color-accent); color: #fff; }
  .mode-btn:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
  @media (prefers-reduced-motion: reduce) { .mode-btn { transition: none; } }

  .refs { margin-top: var(--space-8); }
  .section-title {
    font-size: var(--text-xl); font-weight: 700; letter-spacing: -0.01em;
    margin: 0 0 var(--space-1); color: var(--color-text-primary);
  }
  .refs-sub { margin: 0 0 var(--space-5); color: var(--color-text-secondary); font-size: var(--text-sm); }
  .refs-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-6); }
  .refs-h {
    font-size: var(--text-xs); font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase;
    color: var(--color-text-secondary); margin: 0 0 var(--space-3);
  }
  .ref {
    display: flex; flex-direction: column; gap: 2px;
    padding: var(--space-3);
    border: 1px solid var(--color-border); border-radius: var(--radius-sm);
    background: var(--color-surface-raised);
    text-decoration: none; margin-bottom: var(--space-2);
    transition: border-color var(--duration-fast) var(--ease-out),
                transform var(--duration-fast) var(--ease-out);
  }
  .ref:hover { border-color: var(--color-accent); transform: translateY(-1px); }
  .ref:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
  .ref-name { color: var(--color-text-primary); font-size: var(--text-sm); font-weight: 500; }
  .ref-venue { color: var(--color-text-secondary); font-size: var(--text-xs); font-family: var(--font-mono); }

  @media (max-width: 640px) { .refs-grid { grid-template-columns: 1fr; } }
  @media (prefers-reduced-motion: reduce) { .ref { transition: none; } }
</style>

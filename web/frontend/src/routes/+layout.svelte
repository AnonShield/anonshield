<script lang="ts">
  import '../app.css';
  import { t, locale, LOCALES, LOCALE_NAMES } from '#lib/i18n.js';
  import { page } from '$app/state';

  let { children } = $props();

  let isApp       = $derived(page.url.pathname.startsWith('/app'));
  let isMetrics   = $derived(page.url.pathname === '/app/metrics');
  let appClass    = $derived(
    isApp
      ? (isMetrics ? 'app-main metrics-main' : 'app-main')
      : '',
  );
</script>

<svelte:head>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" />
</svelte:head>

<header class:app-header={isApp}>
  <div class="header-inner">
    <a href="/" class="logo">
      <span class="logo-mark">⬡</span>
      AnonShield
    </a>

    <nav class="nav">
      {#if !isApp}
        <a href="/slides" class="nav-link nav-slides">{$t('nav.slides')}</a>
        <a href="/app" class="nav-cta">{$t('nav.app')}</a>
      {:else}
        <a href="/" class="nav-link">← Home</a>
        {#if !isMetrics}
          <a href="/app/metrics" class="nav-link metrics-link">Metrics</a>
        {/if}
      {/if}
      <div class="lang-switch" role="group" aria-label={$t('nav.lang_label')}>
        {#each LOCALES as l (l)}
          <button
            type="button"
            class="lang-opt"
            data-lang={l}
            lang={l}
            aria-label={LOCALE_NAMES[l]}
            aria-pressed={$locale === l}
            onclick={() => locale.set(l)}
          >{l.toUpperCase()}</button>
        {/each}
      </div>
    </nav>
  </div>
</header>

<main class={appClass}>
  {@render children()}
</main>

<style>
  header {
    display: flex;
    align-items: center;
    padding: 0 var(--space-8);
    height: 56px;
    border-bottom: 1px solid var(--color-border);
    position: sticky; top: 0;
    /* Translucent sticky chrome: 85% of surface token + 15% transparent
       so the backdrop-filter blur reads through. */
    background: color-mix(in srgb, var(--color-surface) 85%, transparent);
    backdrop-filter: blur(12px);
    z-index: 100;
  }

  .header-inner {
    display: flex; align-items: center; justify-content: space-between;
    width: 100%; max-width: 960px; margin: 0 auto;
  }

  .logo {
    display: flex; align-items: center; gap: var(--space-2);
    font-weight: 700; font-size: var(--text-base);
    color: var(--color-text-primary);
    text-decoration: none;
    letter-spacing: -0.02em;
  }
  .logo:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 3px;
    border-radius: var(--radius-sm);
  }
  .logo-mark { color: var(--color-accent); font-size: var(--text-lg); }

  .nav { display: flex; align-items: center; gap: var(--space-3); }

  .nav-link {
    font-size: var(--text-sm); color: var(--color-text-secondary);
    text-decoration: none;
    transition: color var(--duration-fast) var(--ease-out);
  }
  .nav-link:hover { color: var(--color-text-primary); }
  .nav-link:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 3px;
    border-radius: var(--radius-sm);
  }
  .metrics-link {
    padding: var(--space-1) var(--space-2);
    border: 1px solid var(--color-border); border-radius: var(--radius-sm);
    font-size: var(--text-xs);
    transition: border-color var(--duration-fast) var(--ease-out),
                color var(--duration-fast) var(--ease-out);
  }
  .metrics-link:hover { border-color: var(--color-accent); color: var(--color-text-primary); }

  .nav-cta {
    padding: var(--space-2) var(--space-4);
    background: var(--color-accent); color: #fff;
    border-radius: var(--radius-sm);
    font-size: var(--text-sm); font-weight: 600;
    text-decoration: none;
    transition: background var(--duration-fast) var(--ease-out);
  }
  .nav-cta:hover { background: var(--color-accent-hover); color: #fff; }
  .nav-cta:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 3px;
  }

  .lang-switch {
    display: flex; gap: 2px; padding: 2px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
  }
  .lang-opt {
    min-width: 28px;
    padding: var(--space-1) 6px;
    border: none; border-radius: 4px;
    background: transparent;
    color: var(--color-text-secondary);
    font-size: var(--text-xs); font-weight: 600; line-height: 1.4;
    cursor: pointer;
    transition: background var(--duration-fast) var(--ease-out),
                color var(--duration-fast) var(--ease-out);
  }
  .lang-opt:hover { color: var(--color-text-primary); }
  .lang-opt[aria-pressed='true'] {
    background: color-mix(in srgb, var(--color-accent) 30%, transparent);
    box-shadow: inset 0 0 0 1px var(--color-accent);
    color: var(--color-text-primary);
  }
  .lang-opt:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 1px;
  }

  /* App page: more compact main container */
  main {
    padding: 0;
  }

  .app-main {
    max-width: 960px;
    margin: 0 auto;
    padding: var(--space-8);
  }
  :global(.metrics-main) {
    max-width: 1200px !important;
  }
  /* Phone width: room for the three languages next to the logo. The home page
     keeps its own slides button. */
  @media (max-width: 520px) {
    .nav { gap: var(--space-2); }
    .nav-slides { display: none; }
    .lang-switch { gap: 0; padding: 1px; }
    .lang-opt { min-width: 24px; padding: var(--space-1) 4px; }
  }
  @media (max-width: 480px) {
    header { padding: 0 var(--space-4); }
    .app-main { padding: var(--space-6) var(--space-4); }
  }
</style>

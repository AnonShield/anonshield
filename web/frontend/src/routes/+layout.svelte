<script lang="ts">
  import '../app.css';
  import favicon from '$lib/assets/favicon.svg';
  import { t, toggleLocale } from '$lib/i18n';
  import { page } from '$app/state';

  let { children } = $props();

  let isApp       = $derived(page.url.pathname.startsWith('/app'));
  let isMetrics   = $derived(page.url.pathname === '/app/metrics');
  let isBenchmark = $derived(page.url.pathname === '/app/benchmark');
  let appClass    = $derived(
    isApp
      ? (isMetrics || isBenchmark ? 'app-main metrics-main' : 'app-main')
      : '',
  );
</script>

<svelte:head>
  <link rel="icon" href={favicon} />
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
        <a href="/app" class="nav-cta">{$t('nav.app')}</a>
      {:else}
        <a href="/" class="nav-link">← Home</a>
        {#if !isMetrics}
          <a href="/app/metrics" class="nav-link metrics-link">Metrics</a>
        {/if}
        {#if !isBenchmark}
          <a href="/app/benchmark" class="nav-link metrics-link">Benchmark</a>
        {/if}
      {/if}
      <button class="lang-btn" onclick={toggleLocale} aria-label="Switch language">
        {$t('nav.lang_toggle')}
      </button>
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

  .lang-btn {
    padding: var(--space-1) var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--color-text-secondary);
    font-size: var(--text-xs); font-weight: 600;
    cursor: pointer;
    transition: border-color var(--duration-fast) var(--ease-out),
                color var(--duration-fast) var(--ease-out);
  }
  .lang-btn:hover { border-color: var(--color-accent); color: var(--color-text-primary); }
  .lang-btn:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
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
</style>

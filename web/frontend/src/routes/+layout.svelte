<script lang="ts">
  import '../app.css';
  import favicon from '$lib/assets/favicon.svg';
  import { t, toggleLocale } from '$lib/i18n';
  import { page } from '$app/state';

  let { children } = $props();

  let isApp     = $derived(page.url.pathname.startsWith('/app'));
  let isMetrics = $derived(page.url.pathname === '/app/metrics');
  let appClass  = $derived(isApp ? (isMetrics ? 'app-main metrics-main' : 'app-main') : '');
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
    background: rgba(8, 9, 13, 0.85);
    backdrop-filter: blur(12px);
    z-index: 100;
  }

  .header-inner {
    display: flex; align-items: center; justify-content: space-between;
    width: 100%; max-width: 960px; margin: 0 auto;
  }

  .logo {
    display: flex; align-items: center; gap: 8px;
    font-weight: 700; font-size: 1rem;
    color: var(--color-text-primary);
    text-decoration: none;
    letter-spacing: -0.02em;
  }
  .logo-mark { color: var(--color-accent); font-size: 1.1rem; }

  .nav { display: flex; align-items: center; gap: 12px; }

  .nav-link {
    font-size: var(--text-sm); color: var(--color-text-secondary);
    text-decoration: none;
    transition: color var(--duration-fast);
  }
  .nav-link:hover { color: var(--color-text-primary); }
  .metrics-link {
    padding: 5px 10px;
    border: 1px solid var(--color-border); border-radius: 6px;
    font-size: 0.75rem;
    transition: border-color var(--duration-fast), color var(--duration-fast);
  }
  .metrics-link:hover { border-color: var(--color-accent); color: var(--color-text-primary); }

  .nav-cta {
    padding: 7px 16px;
    background: var(--color-accent); color: #fff;
    border-radius: 8px; font-size: var(--text-sm); font-weight: 600;
    text-decoration: none;
    transition: background var(--duration-fast);
  }
  .nav-cta:hover { background: var(--color-accent-hover); color: #fff; }

  .lang-btn {
    padding: 6px 12px;
    border: 1px solid var(--color-border);
    border-radius: 8px;
    background: transparent;
    color: var(--color-text-secondary);
    font-size: 0.78rem; font-weight: 600;
    cursor: pointer;
    transition: border-color var(--duration-fast), color var(--duration-fast);
  }
  .lang-btn:hover { border-color: var(--color-accent); color: var(--color-text-primary); }

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

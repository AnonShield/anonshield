<script lang="ts">
  import '../app.css';
  import favicon from '$lib/assets/favicon.svg';

  let { children } = $props();
</script>

<svelte:head>
  <link rel="icon" href={favicon} />
  <title>AnonShield</title>
</svelte:head>

<header>
  <a href="/" class="logo">AnonShield</a>
</header>

<main>
  {@render children()}
</main>

<style>
  header {
    display: flex;
    align-items: center;
    padding: var(--space-4) var(--space-8);
    border-bottom: 1px solid var(--color-border);
    position: sticky;
    top: 0;
    background: var(--color-surface);
    z-index: 10;
  }

  .logo {
    font-weight: 700;
    font-size: var(--text-lg);
    color: var(--color-text-primary);
    text-decoration: none;
    letter-spacing: -0.02em;
  }

  main {
    max-width: 960px;
    margin: 0 auto;
    padding: var(--space-8);
  }
</style>

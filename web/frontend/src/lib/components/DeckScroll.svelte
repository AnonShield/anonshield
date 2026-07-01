<script lang="ts">
  import { SLIDES } from '$lib/deck';
  import DeckStage from './DeckStage.svelte';

  const VIDEO: Record<number, string> = {
    2: '/deck/bombeiros.mp4',
    3: '/deck/rede.mp4',
    4: '/deck/incidentes.mp4',
  };
</script>

<div class="scroll">
  {#each SLIDES as s (s.n)}
    <div class="page">
      <span class="page-num" aria-hidden="true">{s.n}</span>
      <DeckStage slide={s} video={VIDEO[s.n] ?? ''} />
    </div>
  {/each}
</div>

<style>
  .scroll { display: flex; flex-direction: column; gap: var(--space-5); }
  .page {
    position: relative;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    overflow: hidden;
    box-shadow: 0 4px 24px color-mix(in srgb, #000 25%, transparent);
  }
  .page-num {
    position: absolute; z-index: 2; top: var(--space-2); left: var(--space-3);
    padding: 2px 8px; border-radius: 999px;
    background: color-mix(in srgb, #110e09 60%, transparent);
    color: #fff; font: 600 var(--text-xs) / 1 var(--font-mono);
  }
</style>

<script lang="ts">
  let { progress = 0, label = '', indeterminate = false }: { progress?: number; label?: string; indeterminate?: boolean } = $props();
</script>

<div class="progress-wrap">
  <div class="bar-track"
    role="progressbar"
    aria-valuenow={indeterminate ? undefined : progress}
    aria-valuemin={0}
    aria-valuemax={100}
    aria-label={label || (indeterminate ? undefined : `${progress}%`)}
  >
    <div class="bar-fill" class:indeterminate style={indeterminate ? '' : `width: ${progress}%`}></div>
  </div>
  {#if label}
    <p class="label">{label}</p>
  {/if}
</div>

<style>
  .progress-wrap { display: flex; flex-direction: column; gap: var(--space-2); }
  .bar-track { height: 8px; background: var(--color-border); border-radius: 999px; overflow: hidden; }
  .bar-fill { height: 100%; background: var(--color-accent); border-radius: 999px; transition: width 500ms linear; }
  /* Work is running but no share is measured yet: a moving segment, not 0%. */
  .bar-fill.indeterminate { width: 30%; animation: slide 1.4s ease-in-out infinite; }
  @keyframes slide { from { transform: translateX(-100%); } to { transform: translateX(340%); } }
  @media (prefers-reduced-motion: reduce) { .bar-fill.indeterminate { animation: none; width: 100%; opacity: 0.35; } }
  .label { margin: 0; font-size: var(--text-sm); color: var(--color-text-secondary); text-align: center; }
</style>

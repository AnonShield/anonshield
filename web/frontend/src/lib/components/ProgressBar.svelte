<script lang="ts">
  let { progress = 0, label = '' }: { progress?: number; label?: string } = $props();
</script>

<div class="progress-wrap">
  <div class="bar-track"
    role="progressbar"
    aria-valuenow={progress}
    aria-valuemin={0}
    aria-valuemax={100}
    aria-label={label || `${progress}%`}
  >
    <div class="bar-fill" style="width: {progress}%"></div>
  </div>
  {#if label}
    <p class="label">{label}</p>
  {/if}
</div>

<style>
  .progress-wrap { display: flex; flex-direction: column; gap: var(--space-2); }
  .bar-track { height: 8px; background: var(--color-border); border-radius: 999px; overflow: hidden; }
  .bar-fill { height: 100%; background: var(--color-accent); border-radius: 999px; transition: width 500ms linear; }
  .label { margin: 0; font-size: var(--text-sm); color: var(--color-text-secondary); text-align: center; }
</style>

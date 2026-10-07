<script lang="ts">
  import { config, type CustomPattern } from '#lib/stores/config.js';
  import { patternError, previewRegex } from '#lib/pyRegex.js';
  import { t } from '#lib/i18n.js';
  import { onMount } from 'svelte';

  let { onclose }: { onclose?: () => void } = $props();

  let entityType = $state('');
  let pattern = $state('');
  let score = $state(0.9);
  let testInput = $state('');

  // Focus moves into the builder when it opens, as in any modal; otherwise Esc
  // reached the Advanced dialog behind it and closed both.
  let typeInput: HTMLInputElement;
  onMount(() => typeInput.focus());

  // Python's `re` decides whether a pattern is valid (the server compiles it
  // the same way the job will), asked a moment after typing stops. The answer
  // is kept with the pattern it is about, so a slow reply never applies to a
  // newer pattern.
  let check = $state<{ pattern: string; error: string } | null>(null);
  const current = $derived(pattern.trim());
  const checked = $derived(check !== null && check.pattern === current);
  const errorMsg = $derived(checked ? check!.error : '');
  $effect(() => {
    const p = current;
    if (!p) return;
    const timer = setTimeout(async () => {
      let error: string;
      try {
        error = await patternError(p);
      } catch {
        // Server unreachable: fall back to what the browser can tell.
        error = previewRegex(p) ? '' : $t('regex.unchecked');
      }
      check = { pattern: p, error };
    }, 300);
    return () => clearTimeout(timer);
  });

  const preview = $derived(current ? previewRegex(current) : null);
  type MatchState = 'none' | 'match' | 'nopreview';
  let matchResult: MatchState = $derived.by(() => {
    if (!current || !testInput || errorMsg) return 'none';
    if (!preview) return 'nopreview';
    return preview.test(testInput) ? 'match' : 'none';
  });

  const canAdd = $derived(!!entityType.trim() && !!current && checked && !errorMsg);

  function add() {
    if (!canAdd) return;
    const p: CustomPattern = { entity_type: entityType.trim().toUpperCase(), pattern: current, score };
    config.update(c => ({ ...c, custom_patterns: [...c.custom_patterns, p] }));
    onclose?.();
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      // Close only the builder, not the Advanced dialog it sits in.
      e.preventDefault();
      e.stopPropagation();
      onclose?.();
    }
  }
</script>

<div class="overlay" role="dialog" aria-modal="true" aria-label={$t('regex.dialog')} onkeydown={handleKeydown} tabindex="-1">
  <div class="modal card">
    <div class="modal-header">
      <h2>{$t('regex.title')}</h2>
      <button class="close" type="button" aria-label={$t('regex.close')} onclick={onclose}>×</button>
    </div>

    <label>{$t('regex.type')}
      <input type="text" bind:this={typeInput} bind:value={entityType} placeholder="BANK_ACCOUNT" spellcheck="false" />
    </label>

    <label>{$t('regex.pattern')} <span class="lang-badge">Python re</span>
      <input type="text" bind:value={pattern} placeholder={'\\d{4}[\\s-]?\\d{4}'} class="mono"
        spellcheck="false" class:has-error={!!errorMsg} aria-invalid={!!errorMsg} />
      {#if errorMsg}
        <span class="error-msg" role="alert">{errorMsg}</span>
      {:else if current && !checked}
        <span class="hint">{$t('regex.checking')}</span>
      {/if}
      <span class="hint">{$t('regex.hint')}</span>
    </label>

    <label>{$t('regex.score', { score: score.toFixed(2) })}
      <input type="range" min="0" max="1" step="0.05" bind:value={score} />
    </label>

    <label>{$t('regex.test')}
      <input type="text" bind:value={testInput} placeholder={$t('regex.test_placeholder')} class="mono" />
      {#if testInput && current && !errorMsg}
        <span class="feedback" class:match={matchResult === 'match'}>
          {matchResult === 'match' ? $t('regex.match') : matchResult === 'nopreview' ? $t('regex.no_preview') : $t('regex.no_match')}
        </span>
      {/if}
    </label>

    <div class="actions">
      <button class="btn btn-ghost" type="button" onclick={onclose}>{$t('regex.cancel')}</button>
      <button class="btn btn-primary" type="button" disabled={!canAdd} onclick={add}>
        {$t('regex.add')}
      </button>
    </div>
  </div>
</div>

<style>
  .overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.6);
    display: flex; align-items: center; justify-content: center; z-index: 100;
    animation: fade-in var(--duration-slow) var(--ease-out);
  }
  @keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }
  .modal { width: min(480px, 95vw); animation: slide-in var(--duration-slow) var(--ease-out); }
  @keyframes slide-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
  .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-6); }
  h2 { margin: 0; font-size: var(--text-lg); }
  .close { background: none; border: none; font-size: 1.5rem; color: var(--color-text-secondary); cursor: pointer; }
  label { display: flex; flex-direction: column; gap: var(--space-1); font-size: var(--text-sm); color: var(--color-text-secondary); margin-bottom: var(--space-4); }
  label input[type='range'] { accent-color: var(--color-accent); }
  .mono { font-family: var(--font-mono); font-size: var(--text-sm); }
  .has-error { border-color: var(--color-error) !important; }
  .error-msg { color: var(--color-error); font-size: 0.75rem; }
  .feedback { font-size: 0.75rem; color: var(--color-text-secondary); }
  .feedback.match { color: var(--color-success); }
  .actions { display: flex; justify-content: flex-end; gap: var(--space-2); margin-top: var(--space-4); }

  .lang-badge {
    display: inline-block;
    font-size: 0.68rem;
    padding: 1px 6px;
    border-radius: 4px;
    background: color-mix(in srgb, var(--color-accent) 15%, transparent);
    border: 1px solid color-mix(in srgb, var(--color-accent) 40%, transparent);
    color: var(--color-accent);
    font-weight: 600;
    letter-spacing: 0.03em;
    margin-left: var(--space-2);
    vertical-align: middle;
  }

  .hint {
    font-size: 0.72rem;
    color: var(--color-text-secondary);
    margin-top: 2px;
  }
</style>

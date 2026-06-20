<script lang="ts">
  import { config, type CustomPattern } from '$lib/stores/config';

  let { onclose }: { onclose?: () => void } = $props();

  let entityType = $state('');
  let pattern = $state('');
  let score = $state(0.9);
  let testInput = $state('');

  type MatchState = 'none' | 'match' | 'error';
  let matchResult: MatchState = $derived.by(() => {
    if (!pattern) return 'none';
    try {
      const rx = new RegExp(pattern, 'i');
      return testInput ? (rx.test(testInput) ? 'match' : 'none') : 'none';
    } catch {
      return 'error';
    }
  });

  let errorMsg = $derived.by(() => {
    if (!pattern) return '';
    try { new RegExp(pattern, 'i'); return ''; }
    catch (e) { return (e as Error).message; }
  });

  function add() {
    if (!entityType.trim() || !pattern.trim() || matchResult === 'error') return;
    const p: CustomPattern = { entity_type: entityType.trim().toUpperCase(), pattern: pattern.trim(), score };
    config.update(c => ({ ...c, custom_patterns: [...c.custom_patterns, p] }));
    onclose?.();
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') onclose?.();
  }
</script>

<div class="overlay" role="dialog" aria-modal="true" aria-label="Add custom pattern" onkeydown={handleKeydown} tabindex="-1">
  <div class="modal card">
    <div class="modal-header">
      <h2>New Custom Pattern</h2>
      <button class="close" type="button" aria-label="Close" onclick={onclose}>×</button>
    </div>

    <label>Entity type name
      <input type="text" bind:value={entityType} placeholder="BANK_ACCOUNT" spellcheck="false" />
    </label>

    <label>Regular expression <span class="lang-badge">Python re</span>
      <input type="text" bind:value={pattern} placeholder="\d{4}[\s-]?\d{4}" class="mono"
        spellcheck="false" class:has-error={matchResult === 'error'} />
      {#if matchResult === 'error'}
        <span class="error-msg">{errorMsg}</span>
      {/if}
      <span class="hint">Python <code>re</code> syntax. Quantifiers: <code>\d+</code> <code>\w*</code> <code>[A-Z]</code>. Case-insensitive: <code>(?i)</code>.</span>
    </label>

    <label>Confidence score: {score.toFixed(2)}
      <input type="range" min="0" max="1" step="0.05" bind:value={score} />
    </label>

    <label>Test input
      <input type="text" bind:value={testInput} placeholder="Paste a sample value here..." class="mono" />
      {#if testInput && matchResult !== 'error'}
        <span class="feedback" class:match={matchResult === 'match'}>
          {matchResult === 'match' ? '✓ Match' : '○ No match'}
        </span>
      {/if}
    </label>

    <div class="actions">
      <button class="btn btn-ghost" type="button" onclick={onclose}>Cancel</button>
      <button class="btn btn-primary" type="button"
        disabled={!entityType || !pattern || matchResult === 'error'} onclick={add}>
        Add Pattern
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
  .hint code {
    font-family: var(--font-mono);
    font-size: 0.72rem;
    background: var(--color-border);
    padding: 1px 4px;
    border-radius: 3px;
    color: var(--color-text-primary);
  }
</style>

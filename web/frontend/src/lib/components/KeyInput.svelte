<script lang="ts">
  import { config } from '$lib/stores/config';
  import { t } from '$lib/i18n';
  let visible = $state(false);
</script>

<div class="key-field">
  <label for="secret-key">
    {$t('key.label', { opt: $t('key.optional') })}
  </label>
  <div class="input-wrap">
    <input
      id="secret-key"
      type={visible ? 'text' : 'password'}
      bind:value={$config.key}
      placeholder={$t('key.placeholder')}
      autocomplete="off"
      spellcheck="false"
    />
    <button class="toggle" type="button" aria-label={visible ? 'Hide key' : 'Show key'}
      onclick={() => (visible = !visible)}>{visible ? '🙈' : '👁'}</button>
  </div>
  <p class="hint">
    {#if $config.key}
      <span class="hint-good">{$t('key.hint_deterministic').split(/: (.*)/s)[0]}</span>: {$t('key.hint_deterministic').split(/: (.*)/s)[1]}
    {:else}
      {$t('key.hint_random')}
    {/if}
  </p>
</div>

<style>
  .key-field { display: flex; flex-direction: column; gap: var(--space-2); }
  label { font-size: var(--text-sm); color: var(--color-text-secondary); font-weight: 500; }
  .optional { font-weight: 400; }
  .input-wrap { display: flex; gap: var(--space-2); }
  .input-wrap input { flex: 1; font-family: var(--font-mono); font-size: var(--text-sm); }
  .toggle {
    background: var(--color-surface-raised);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    padding: var(--space-2) var(--space-3);
    cursor: pointer;
  }
  .hint { margin: 0; font-size: 0.75rem; color: var(--color-text-secondary); line-height: 1.5; }
  .hint-good { color: #4ade80; font-weight: 600; }
  .hint-warn { color: #fbbf24; font-weight: 600; }
</style>

<!--
  FieldSelector: refactored into a Modal-based Schema Configurator.
  Includes compact summary bar and high-fidelity modal overlay.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { PUBLIC_API_URL } from '$env/static/public';
  import { t } from '$lib/i18n';
  import type { EntityGroup } from '$lib/api';
  import type { AnonymizationConfig } from '$lib/stores/config';

  const API_BASE = PUBLIC_API_URL ?? '/api';

  let {
    file,
    entityGroups = [],
    onchange,
  }: {
    file: File;
    entityGroups: EntityGroup[];
    onchange?: (config: AnonymizationConfig | null) => void;
  } = $props();

  type FieldMode = 'all' | 'targeted';
  type RuleType = 'auto' | 'force' | 'exclude';

  interface FieldRule {
    name: string;
    type: RuleType;
    forcedEntity?: string;
  }

  let mode = $state<FieldMode>('all');
  let fields = $state<string[]>([]);
  let rules = $state<Record<string, FieldRule>>({});
  let loading = $state(true);
  let error = $state('');
  let showModal = $state(false);

  const ext = $derived(file.name.split('.').pop()?.toLowerCase() ?? '');
  const supported = $derived(['csv', 'tsv', 'json', 'jsonl', 'ndjson', 'xlsx'].includes(ext));
  const flatEntities = $derived(entityGroups.flatMap(g => g.entities));
  const activeRulesCount = $derived(Object.values(rules).filter(r => r.type !== 'auto').length);

  async function detectFields() {
    if (!supported) { loading = false; return; }
    try {
      const fd = new FormData();
      fd.append('file', file);
      const r = await fetch(`${API_BASE}/analyze-fields`, { method: 'POST', body: fd });
      if (r.ok) {
        const data = await r.json();
        const cols: string[] = (data.fields ?? []).map((f: { name: string }) => f.name);
        if (cols.length > 0) {
          fields = cols;
          const initialRules: Record<string, FieldRule> = {};
          for (const f of cols) initialRules[f] = { name: f, type: 'auto' };
          rules = initialRules;
        }
      } else {
        error = 'Could not read file columns.';
      }
    } catch {
      error = 'Could not detect fields.';
    }
    loading = false;
  }

  onMount(detectFields);

  function setRuleType(fieldName: string, type: RuleType) {
    rules[fieldName].type = type;
    if (type === 'force' && !rules[fieldName].forcedEntity) {
      rules[fieldName].forcedEntity = 'PERSON';
    }
    emit();
  }

  function setForcedEntity(fieldName: string, entity: string) {
    rules[fieldName].forcedEntity = entity;
    emit();
  }

  function emit() {
    if (mode === 'all') { onchange?.(null); return; }
    const config: AnonymizationConfig = { force_anonymize: {}, fields_to_anonymize: [], fields_to_exclude: [] };
    let hasRules = false;
    for (const f of fields) {
      const rule = rules[f];
      if (rule.type === 'force' && rule.forcedEntity) {
        config.force_anonymize![f] = { entity_type: rule.forcedEntity };
        hasRules = true;
      } else if (rule.type === 'auto') {
        config.fields_to_anonymize!.push(f);
        hasRules = true;
      } else if (rule.type === 'exclude') {
        config.fields_to_exclude!.push(f);
        hasRules = true;
      }
    }
    if (!hasRules) onchange?.(null);
    else onchange?.(config);
  }

  function resetAllToAuto() {
    for (const f of fields) rules[f].type = 'auto';
    emit();
  }

  // Handle ESC key to close modal
  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') showModal = false;
  }
</script>

{#if supported}
  <!-- TRIGGER BAR -->
  <!-- ── TRIGGER BAR (SIMPLIFIED UX) ── -->
  <div 
    class="schema-trigger" 
    class:is-loading={loading} 
    onclick={() => !loading && (showModal = true)}
    role="button"
    tabindex="0"
    onkeydown={(e) => e.key === 'Enter' && !loading && (showModal = true)}
  >
    <div class="st-info">
      <div class="st-text">
        <span class="st-title">{$t('fields.title')}</span>
        <span class="st-hint">
          {mode === 'all' ? 'Global Analysis Active' : $t('fields.hint_n', { n: activeRulesCount })}
        </span>
      </div>
    </div>
    <div class="st-action">
      <button class="btn btn-primary btn-sm" disabled={loading} tabindex="-1">
        {loading ? '...' : $t('fields.pick')}
      </button>
    </div>
  </div>

  <!-- MODAL OVERLAY -->
  {#if showModal}
    <div class="modal-overlay" onkeydown={handleKeydown} tabindex="-1">
      <div class="modal-backdrop" onclick={() => showModal = false}></div>
      
      <div class="modal-content card">
        <div class="modal-header">
          <div class="mh-left">
            <span class="cp-badge">Schema Config</span>
            <h2>{$t('fields.title')}</h2>
          </div>
          <button class="close-btn" onclick={() => showModal = false}>&times;</button>
        </div>

        <div class="modal-tabs">
          <button class:active={mode === 'all'} onclick={() => mode = 'all'}>
            {$t('fields.all')}
          </button>
          <button class:active={mode === 'targeted'} onclick={() => mode = 'targeted'}>
            {$t('fields.pick')}
          </button>
        </div>

        <div class="modal-body">
          {#if mode === 'all'}
            <div class="mode-all-view">
              <div class="shield-icon">🛡️</div>
              <h3>{$t('fields.all')}</h3>
              <p>{$t('fields.hint_none')}</p>
              <button class="btn btn-ghost mt-4" onclick={() => mode = 'targeted'}>
                {$t('fields.pick')}
              </button>
            </div>
          {:else if fields.length > 0}
            <div class="table-container">
              <table class="field-table">
                <thead>
                  <tr>
                    <th>Field Name</th>
                    <th>Action</th>
                    <th>Mapping / Force Type</th>
                  </tr>
                </thead>
                <tbody>
                  {#each fields as f}
                    <tr class:row-excluded={rules[f].type === 'exclude'}>
                      <td class="td-name"><code>{f}</code></td>
                      <td class="td-actions">
                        <div class="segmented-control">
                          <button 
                            class:active={rules[f].type === 'auto'} 
                            onclick={() => setRuleType(f, 'auto')}
                            title={$t('fields.mode.auto.desc')}
                          >
                            Auto
                          </button>
                          <button 
                            class:active={rules[f].type === 'force'} 
                            onclick={() => setRuleType(f, 'force')}
                            title={$t('fields.mode.force.desc')}
                          >
                            Force
                          </button>
                          <button 
                            class:active={rules[f].type === 'exclude'} 
                            onclick={() => setRuleType(f, 'exclude')}
                            title={$t('fields.mode.exclude.desc')}
                          >
                            Skip
                          </button>
                        </div>
                      </td>
                      <td class="td-config">
                        {#if rules[f].type === 'force'}
                          <div class="force-input-group">
                            <input 
                              list="entity-suggestions-{f}"
                              class="force-input"
                              value={rules[f].forcedEntity} 
                              oninput={(e) => setForcedEntity(f, e.currentTarget.value.toUpperCase())}
                              placeholder="ENTITY_TYPE"
                            />
                            <datalist id="entity-suggestions-{f}">
                              {#each flatEntities as ent}
                                <option value={ent.id}>{ent.label}</option>
                              {/each}
                            </datalist>
                          </div>
                        {:else if rules[f].type === 'exclude'}
                          <span class="skip-label">Excluded from scan</span>
                        {:else}
                          <span class="auto-label">AI Scanning Active</span>
                        {/if}
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {:else}
            <p class="empty-msg">{$t('fields.empty')}</p>
          {/if}
        </div>

        <div class="modal-footer">
          <div class="mf-left">
            {#if mode === 'targeted'}
               <span class="rule-count">{$t('fields.hint_n', { n: activeRulesCount })}</span>
               <button class="btn-link" onclick={resetAllToAuto}>{$t('fields.clear')}</button>
            {/if}
          </div>
          <button class="btn btn-primary" onclick={() => showModal = false}>Done</button>
        </div>
      </div>
    </div>
  {/if}
{/if}

<style>
  /* ── Trigger Bar (Vertical Stack UX) ── */
  .schema-trigger {
    margin-top: 1.5rem;
    padding: 1.25rem;
    background: var(--color-surface-raised);
    border: 1px solid var(--color-border);
    border-radius: 12px;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
    cursor: pointer;
    transition: all 200ms ease;
  }
  .schema-trigger:hover {
    border-color: var(--color-accent);
    background: color-mix(in srgb, var(--color-surface-raised), white 2%);
  }

  .st-info {
    display: flex;
    flex-direction: column;
    gap: 4px;
    width: 100%;
  }

  .st-title {
    font-size: 0.75rem;
    font-weight: 800;
    color: var(--color-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }
  .st-hint {
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--color-text-primary);
    line-height: 1.4;
  }

  .st-action {
    width: 100%;
  }
  .st-action :global(.btn) {
    width: 100%;
    justify-content: center;
  }

  /* Modal Overlay (Industrial Glass) */
  .modal-overlay {
    position: fixed; inset: 0; z-index: 1000;
    display: flex; align-items: center; justify-content: center;
    padding: 2rem;
  }
  .modal-backdrop {
    position: absolute; inset: 0;
    background: rgba(0,0,0,0.7);
    backdrop-filter: blur(8px);
  }
  .modal-content {
    position: relative; width: 100%; max-width: 860px;
    display: flex; flex-direction: column;
    max-height: 90vh; overflow: hidden;
    animation: modal-pop 250ms cubic-bezier(0.16, 1, 0.3, 1);
  }
  @keyframes modal-pop {
    from { opacity: 0; transform: scale(0.95) translateY(10px); }
    to { opacity: 1; transform: scale(1) translateY(0); }
  }

  .modal-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 1.25rem 1.5rem; border-bottom: 1px solid var(--color-border);
  }
  .mh-left { display: flex; flex-direction: column; gap: 4px; }
  .mh-left h2 { margin: 0; font-size: 1.25rem; font-weight: 800; letter-spacing: -0.02em; }
  .cp-badge {
    display: inline-block; width: fit-content;
    background: var(--color-accent); color: #fff; font-size: 0.6rem; font-weight: 800;
    padding: 1px 5px; border-radius: 4px; text-transform: uppercase;
  }
  .close-btn { background: none; border: none; font-size: 2rem; color: var(--color-text-secondary); cursor: pointer; }

  .modal-tabs {
    display: flex; gap: 1rem; padding: 1rem 1.5rem;
    background: rgba(255,255,255,0.02);
  }
  .modal-tabs button {
    background: none; border: none; padding: 0.5rem 1rem;
    font-size: 0.85rem; font-weight: 700; color: var(--color-text-secondary);
    cursor: pointer; border-radius: 8px; transition: 150ms;
  }
  .modal-tabs button.active { background: var(--color-accent); color: #fff; }

  .modal-body { flex: 1; overflow-y: auto; padding: 0.5rem 1.5rem; }

  .mode-all-view {
    padding: 4rem 2rem; text-align: center;
  }
  .shield-icon { font-size: 3rem; margin-bottom: 1rem; }
  .mode-all-view h3 { margin: 0 0 0.5rem; }

  .table-container { margin-bottom: 1rem; }
  .field-table { width: 100%; border-collapse: collapse; text-align: left; }
  .field-table th {
    position: sticky; top: 0; background: var(--color-surface);
    padding: 0.75rem 1rem; font-size: 0.72rem; font-weight: 700;
    text-transform: uppercase; color: var(--color-text-secondary);
    border-bottom: 1px solid var(--color-border);
  }
  .field-table td { padding: 1rem; border-bottom: 1px dashed var(--color-border); }
  .td-name { font-family: var(--font-mono); font-size: 0.85rem; color: var(--color-accent); }
  .row-excluded { opacity: 0.6; }

  .segmented-control {
    display: flex; background: rgba(0,0,0,0.3); padding: 3px; border-radius: 8px; width: fit-content;
  }
  .segmented-control button {
    background: none; border: none; padding: 4px 12px;
    font-size: 0.72rem; font-weight: 700; color: var(--color-text-secondary);
    border-radius: 6px; cursor: pointer; text-transform: uppercase; transition: 150ms;
  }
  .segmented-control button.active { background: rgba(255,255,255,0.1); color: var(--color-accent); }
  
  .force-input-group { width: 100%; max-width: 280px; }
  .force-input {
    width: 100%;
    background: var(--color-surface-raised); border: 1px solid var(--color-border);
    color: var(--color-accent); padding: 8px 12px; border-radius: 8px;
    font-size: 0.8rem; outline: none; transition: 150ms;
    font-family: var(--font-mono); font-weight: 600;
  }
  .force-input:focus { border-color: var(--color-accent); box-shadow: 0 0 0 2px rgba(96, 165, 250, 0.2); }
  .force-input::placeholder { color: var(--color-text-secondary); opacity: 0.5; font-family: var(--font-sans); font-weight: 400; }
  .skip-label { color: var(--color-text-secondary); font-size: 0.75rem; font-style: italic; }
  .auto-label { color: #4ade80; font-size: 0.75rem; font-weight: 600; }

  .modal-footer {
    display: flex; justify-content: space-between; align-items: center;
    padding: 1.25rem 1.5rem; border-top: 1px solid var(--color-border);
    background: rgba(255,255,255,0.01);
  }
  .mf-left { display: flex; align-items: center; gap: 1.5rem; }
  .rule-count { font-size: 0.8rem; font-weight: 600; color: var(--color-text-secondary); }
  .btn-link { background: none; border: none; color: var(--color-accent); text-decoration: underline; cursor: pointer; font-size: 0.8rem; }
  
  .mt-4 { margin-top: 1rem; }
  .card { border-radius: 16px; background: var(--color-surface); border: 1px solid var(--color-border); box-shadow: 0 10px 40px rgba(0,0,0,0.4); }
</style>

<script lang="ts">
  import type { EntityGroup } from '$lib/api';
  import { config } from '$lib/stores/config';
  import { t } from '$lib/i18n';

  let { groups = [] }: { groups: EntityGroup[] } = $props();

  let search = $state('');
  let expanded: Record<string, boolean> = $state({});

  let filtered = $derived(
    groups.map(g => ({
      ...g,
      entities: g.entities.filter(e =>
        !search ||
        e.label.toLowerCase().includes(search.toLowerCase()) ||
        e.id.toLowerCase().includes(search.toLowerCase())
      ),
    })).filter(g => g.entities.length > 0)
  );

  /** null = all selected; new Set() = none; Set(ids) = specific */
  function isChecked(id: string): boolean {
    return $config.selected_entities === null || $config.selected_entities.has(id);
  }

  function selectAll() {
    config.update(c => ({ ...c, selected_entities: null }));
  }

  function selectNone() {
    config.update(c => ({ ...c, selected_entities: new Set<string>() }));
  }

  function toggle(id: string) {
    config.update(c => {
      if (c.selected_entities === null) {
        // All currently selected → deselect just this one
        const all = groups.flatMap(g => g.entities.map(e => e.id));
        const s = new Set(all);
        s.delete(id);
        return { ...c, selected_entities: s };
      }
      const s = new Set(c.selected_entities);
      if (s.has(id)) {
        s.delete(id);
      } else {
        s.add(id);
        // If everything is now selected, normalize to null
        const total = groups.reduce((n, g) => n + g.entities.length, 0);
        if (s.size === total) return { ...c, selected_entities: null };
      }
      return { ...c, selected_entities: s };
    });
  }

  function toggleGroup(label: string) {
    expanded[label] = !expanded[label];
  }

  // Groups considered "cybersecurity-relevant" for the Cyber preset
  const CYBER_GROUPS = new Set(["Security", "Cybersecurity", "Network", "System"]);

  let cyberIds = $derived(
    groups.filter(g => CYBER_GROUPS.has(g.label)).flatMap(g => g.entities.map(e => e.id))
  );

  // True when ALL cyber entities are currently selected (regardless of what else is selected)
  let allCyberOn = $derived(
    cyberIds.length > 0 && (
      $config.selected_entities === null ||
      cyberIds.every(id => ($config.selected_entities as Set<string>).has(id))
    )
  );

  function selectCyber() {
    config.update(c => {
      const sel = c.selected_entities;
      if (allCyberOn) {
        // Deselect cyber entities only — keep everything else intact
        if (sel === null) {
          // Currently all selected → make explicit set without cyber entities
          const allIds = groups.flatMap(g => g.entities.map(e => e.id));
          const s = new Set(allIds);
          cyberIds.forEach(id => s.delete(id));
          return { ...c, selected_entities: s };
        }
        const s = new Set(sel);
        cyberIds.forEach(id => s.delete(id));
        return { ...c, selected_entities: s };
      } else {
        // Select cyber entities — keep everything else intact
        if (sel === null) return c; // already all selected
        const s = new Set(sel);
        cyberIds.forEach(id => s.add(id));
        const total = groups.reduce((n, g) => n + g.entities.length, 0);
        if (s.size === total) return { ...c, selected_entities: null };
        return { ...c, selected_entities: s };
      }
    });
  }

  let isAllSelected = $derived($config.selected_entities === null);
  let isNoneSelected = $derived(
    $config.selected_entities !== null && $config.selected_entities.size === 0
  );
</script>

<div class="entity-selector">
  <div class="toolbar">
    <input
      class="search"
      type="search"
      placeholder={$t('app.search')}
      bind:value={search}
      aria-label="Search entities"
    />
    <button
      class="btn-chip"
      class:active={isAllSelected}
      type="button"
      onclick={selectAll}
    >{$t('app.all')}</button>
    <button
      class="btn-chip btn-chip-cyber"
      class:active={allCyberOn}
      type="button"
      onclick={selectCyber}
      title="Security · Cybersecurity · Network · System"
    >Cyber</button>
    <button
      class="btn-chip"
      class:active={isNoneSelected}
      type="button"
      onclick={selectNone}
    >{$t('app.none')}</button>
  </div>

  <div class="groups" role="group" aria-label="Entity selection">
    {#each filtered as group}
      {@const isOpen = expanded[group.label] !== false}
      <div class="group">
        <button
          class="group-header"
          type="button"
          aria-expanded={isOpen}
          onclick={() => toggleGroup(group.label)}
        >
          <span class="chevron" class:open={isOpen}>›</span>
          {group.label}
          <span class="count">{group.entities.length}</span>
        </button>
        {#if isOpen}
          <div class="entity-grid">
            {#each group.entities as entity}
              <label class="entity-chip" title={entity.example || entity.id}>
                <input
                  type="checkbox"
                  checked={isChecked(entity.id)}
                  onchange={() => toggle(entity.id)}
                  aria-label={entity.label}
                />
                <span class="chip-label">{entity.label}</span>
              </label>
            {/each}
          </div>
        {/if}
      </div>
    {/each}
    {#if filtered.length === 0 && search}
      <p class="empty">No entities match "{search}"</p>
    {/if}
  </div>
</div>

<style>
  .entity-selector { display: flex; flex-direction: column; gap: var(--space-3); }

  .toolbar { display: flex; gap: var(--space-2); align-items: center; }
  .search { flex: 1; font-size: var(--text-sm); }

  .btn-chip {
    padding: var(--space-1) var(--space-3);
    border-radius: 999px;
    border: 1px solid var(--color-border);
    background: transparent;
    color: var(--color-text-secondary);
    font-size: var(--text-sm);
    cursor: pointer;
    transition: border-color var(--duration-fast) var(--ease-out),
                color var(--duration-fast) var(--ease-out),
                background var(--duration-fast) var(--ease-out);
  }
  .btn-chip:hover { border-color: var(--color-accent); color: var(--color-text-primary); }
  .btn-chip.active {
    border-color: var(--color-accent);
    background: color-mix(in srgb, var(--color-accent) 15%, transparent);
    color: var(--color-text-primary);
  }

  .btn-chip-cyber { border-color: #3b82f6; color: #3b82f6; }
  .btn-chip-cyber:hover { border-color: #60a5fa; color: #60a5fa; background: color-mix(in srgb, #3b82f6 10%, transparent); }
  .btn-chip-cyber.active {
    border-color: #3b82f6;
    background: color-mix(in srgb, #3b82f6 18%, transparent);
    color: #93c5fd;
  }

  .groups { display: flex; flex-direction: column; gap: var(--space-1); overflow-y: auto; }
  .group { border-radius: var(--radius-sm); }

  .group-header {
    width: 100%; display: flex; align-items: center; gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    background: transparent; border: none;
    color: var(--color-text-secondary);
    font-size: var(--text-sm); font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.05em;
    cursor: pointer;
    transition: color var(--duration-fast) var(--ease-out);
  }
  .group-header:hover { color: var(--color-text-primary); }

  .chevron { display: inline-block; transition: transform var(--duration-fast) var(--ease-out); }
  .chevron.open { transform: rotate(90deg); }
  .count {
    margin-left: auto;
    font-size: 0.72rem;
    background: var(--color-border);
    border-radius: 999px;
    padding: 1px 7px;
    color: var(--color-text-secondary);
  }

  .entity-grid {
    display: flex; flex-wrap: wrap; gap: var(--space-2);
    padding: var(--space-2) var(--space-3) var(--space-3);
  }

  .entity-chip {
    display: flex; align-items: center; gap: var(--space-1);
    padding: var(--space-1) var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: 999px;
    font-size: var(--text-sm);
    cursor: pointer;
    transition: border-color var(--duration-fast) var(--ease-out),
                background var(--duration-fast) var(--ease-out);
  }
  .entity-chip:has(input:checked) {
    border-color: var(--color-accent);
    background: color-mix(in srgb, var(--color-accent) 12%, transparent);
  }
  .entity-chip input {
    appearance: none; width: 14px; height: 14px;
    border: 2px solid var(--color-border);
    border-radius: 3px;
    background: transparent;
    cursor: pointer;
    flex-shrink: 0;
  }
  .entity-chip input:checked {
    background: var(--color-accent);
    border-color: var(--color-accent);
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 10 10'%3E%3Cpath d='M1.5 5.5 L4 8 L8.5 2' stroke='white' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: center;
  }
  .chip-label { color: var(--color-text-primary); }
  .empty { padding: var(--space-4); text-align: center; color: var(--color-text-secondary); font-size: var(--text-sm); margin: 0; }
</style>

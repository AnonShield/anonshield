<script lang="ts">
  import DropZone from '$lib/components/DropZone.svelte';
  import KeyInput from '$lib/components/KeyInput.svelte';
  import EntitySelector from '$lib/components/EntitySelector.svelte';
  import RegexBuilder from '$lib/components/RegexBuilder.svelte';
  import ProgressBar from '$lib/components/ProgressBar.svelte';
  import { config, toYaml, fromYaml } from '$lib/stores/config';
  import { activeJob, clearJob } from '$lib/stores/job';
  import { createJob, fetchEntities, validateProfile, downloadUrl, pollStatus, cancelJob } from '$lib/api';
  import type { EntityGroup } from '$lib/api';
  import { onDestroy } from 'svelte';

  type Screen = 'home' | 'config' | 'processing' | 'done' | 'error';
  let screen: Screen = $state('home');
  let selectedFile: File | null = $state(null);
  let groups: EntityGroup[] = $state([]);
  let showRegexBuilder = $state(false);
  let errorMsg = $state('');

  async function onFile(e: CustomEvent<File>) {
    selectedFile = e.detail;
    screen = 'config';
    const resp = await fetchEntities($config.strategy, $config.model, $config.lang).catch(() => ({ groups: [] }));
    groups = resp.groups;
  }

  $effect(() => {
    if (screen === 'config') {
      fetchEntities($config.strategy, $config.model, $config.lang)
        .then(r => (groups = r.groups))
        .catch(() => {});
    }
  });

  async function submit() {
    if (!selectedFile) return;
    screen = 'processing';
    clearJob();
    errorMsg = '';

    try {
      const entities = $config.selected_entities.size > 0 ? [...$config.selected_entities] : undefined;
      const yamlConfig = $config.custom_patterns.length > 0
        ? toYaml($config, groups.flatMap(g => g.entities))
        : undefined;

      const job = await createJob(selectedFile, {
        key:      $config.key || undefined,
        strategy: $config.strategy,
        lang:     $config.lang,
        entities,
        config:   yamlConfig,
      });

      activeJob.set({ id: job.job_id, filename: selectedFile!.name, status: null, pollInterval: null });

      const interval = setInterval(async () => {
        try {
          const status = await pollStatus(job.job_id);
          activeJob.update(j => j ? { ...j, status } : j);
          if (status.status === 'done') {
            clearInterval(interval);
            screen = 'done';
          } else if (status.status === 'error') {
            clearInterval(interval);
            errorMsg = status.message ?? 'Unknown error';
            screen = 'error';
          }
        } catch {
          clearInterval(interval);
          errorMsg = 'Lost connection to server.';
          screen = 'error';
        }
      }, 2000);

      activeJob.update(j => j ? { ...j, pollInterval: interval } : j);
    } catch (e: unknown) {
      const msg = (e as Error).message;
      errorMsg = msg === 'FILE_TOO_LARGE'
        ? `File too large. ${$config.key ? 'Max 10 GB.' : 'Without a key, max is 1 MB.'}`
        : msg === 'INSUFFICIENT_STORAGE'
        ? 'Server is temporarily out of disk space. Try again in a few minutes.'
        : `Error: ${msg}`;
      screen = 'error';
    }
  }

  async function cancel() {
    if ($activeJob?.id) await cancelJob($activeJob.id).catch(() => {});
    clearJob();
    screen = 'home';
    selectedFile = null;
  }

  async function importProfile(e: Event) {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (!file) return;
    const text = await file.text();
    const result = await validateProfile(text);
    if (!result.valid) { alert(`Invalid profile: ${result.error}`); return; }
    fromYaml(text);
  }

  function exportProfile() {
    const yaml = toYaml($config, groups.flatMap(g => g.entities));
    const blob = new Blob([yaml], { type: 'text/yaml' });
    const a = Object.assign(document.createElement('a'), {
      href: URL.createObjectURL(blob),
      download: 'anonshield-profile.yaml',
    });
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function removePattern(i: number) {
    config.update(c => ({ ...c, custom_patterns: c.custom_patterns.filter((_, idx) => idx !== i) }));
  }

  onDestroy(() => clearJob());

  let progress = $derived($activeJob?.status?.progress ?? 0);
  let outputSize = $derived($activeJob?.status?.output_size_bytes ?? 0);
  let entityCount = $derived(($activeJob?.status?.result as Record<string, unknown> | undefined)?.entity_count as number | undefined);
</script>

{#if screen === 'home'}
  <div class="home">
    <div class="header-row">
      <h1>Anonymize your file</h1>
      <label class="btn btn-ghost">
        Import profile ↑
        <input type="file" accept=".yaml,.yml,.json" class="visually-hidden" onchange={importProfile} />
      </label>
    </div>
    <DropZone hasKey={!!$config.key} onfile={onFile} />
    <div class="card"><KeyInput /></div>
  </div>

{:else if screen === 'config'}
  <div class="config-layout">
    <div class="config-top">
      <button class="btn btn-ghost" onclick={() => { screen = 'home'; selectedFile = null; }}>← Change file</button>
      <span class="filename">{selectedFile?.name}</span>
      <div class="profile-actions">
        <label class="btn btn-ghost">
          Use profile ▾
          <input type="file" accept=".yaml,.yml" class="visually-hidden" onchange={importProfile} />
        </label>
        <button class="btn btn-ghost" onclick={exportProfile}>Save profile ↓</button>
      </div>
    </div>

    <div class="two-col">
      <section class="card settings-panel">
        <h2 class="section-title">Strategy</h2>
        <div class="radio-group" role="radiogroup">
          {#each [
            {v:'filtered',   l:'Filtered (default)'},
            {v:'standalone', l:'Standalone (GPU)'},
            {v:'regex',      l:'Regex only (fastest)'},
            {v:'hybrid',     l:'Hybrid'},
          ] as opt}
            <label class="radio-label">
              <input type="radio" name="strategy" value={opt.v} bind:group={$config.strategy} />
              {opt.l}
            </label>
          {/each}
        </div>

        <h2 class="section-title mt">Language</h2>
        <select bind:value={$config.lang}>
          <option value="en">English (en)</option>
          <option value="pt">Portuguese (pt)</option>
          <option value="es">Spanish (es)</option>
          <option value="fr">French (fr)</option>
          <option value="de">German (de)</option>
        </select>

        {#if $config.strategy !== 'regex'}
          <h2 class="section-title mt">NER model</h2>
          <select bind:value={$config.model}>
            <option value="Davlan/xlm-roberta-base-ner-hrl">xlm-roberta (default)</option>
            <option value="attack-vector/SecureModernBERT-NER">SecureModernBERT (cybersec)</option>
          </select>
        {/if}

        <h2 class="section-title mt">Slug length — {$config.slug_length} chars</h2>
        <input type="range" min="4" max="16" bind:value={$config.slug_length} style="width:100%;accent-color:var(--color-accent)" />
      </section>

      <section class="card entity-panel">
        <h2 class="section-title">Entities to anonymize</h2>
        <EntitySelector {groups} />
      </section>
    </div>

    <section class="card patterns-panel">
      <div class="patterns-header">
        <h2 class="section-title">Custom regex patterns</h2>
        <button class="btn btn-ghost" onclick={() => (showRegexBuilder = true)}>+ Add</button>
      </div>
      {#if $config.custom_patterns.length > 0}
        <table class="patterns-table">
          <thead><tr><th>Entity type</th><th>Pattern</th><th>Score</th><th></th></tr></thead>
          <tbody>
            {#each $config.custom_patterns as p, i}
              <tr>
                <td class="mono">{p.entity_type}</td>
                <td class="mono truncate">{p.pattern}</td>
                <td>{p.score.toFixed(2)}</td>
                <td><button class="remove-btn" onclick={() => removePattern(i)} aria-label="Remove">×</button></td>
              </tr>
            {/each}
          </tbody>
        </table>
      {:else}
        <p class="empty-patterns">No custom patterns. Use "+ Add" to define domain-specific detectors.</p>
      {/if}
    </section>

    <div class="submit-row">
      <button class="btn btn-primary large" onclick={submit}>Anonymize →</button>
    </div>
  </div>

{:else if screen === 'processing'}
  <div class="centered card">
    <h2>{$activeJob?.filename ?? selectedFile?.name}</h2>
    <ProgressBar {progress} label={progress > 0 ? `${progress}% complete` : 'Processing…'} />
    <button class="btn btn-ghost mt" onclick={cancel}>Cancel</button>
  </div>

{:else if screen === 'done'}
  <div class="centered card">
    <div class="success-icon" aria-hidden="true">✓</div>
    <h2>Anonymization complete</h2>
    {#if entityCount !== undefined}
      <p class="stats">{entityCount} entities replaced</p>
    {/if}
    <a
      class="btn btn-primary large"
      href={downloadUrl($activeJob!.id)}
      download
      onclick={() => setTimeout(() => { screen = 'home'; clearJob(); selectedFile = null; }, 3000)}
    >
      ↓ Download anon_{$activeJob?.filename}
      {#if outputSize > 0}({(outputSize / 1024 / 1024).toFixed(1)} MB){/if}
    </a>
    <p class="warning">File will be deleted from the server after download.</p>
    <button class="btn btn-ghost mt" onclick={() => { screen = 'home'; clearJob(); selectedFile = null; }}>
      Anonymize another file
    </button>
  </div>

{:else if screen === 'error'}
  <div class="centered card">
    <div role="alert" class="error-box">
      <strong>Error</strong>
      <p>{errorMsg}</p>
    </div>
    <button class="btn btn-ghost mt" onclick={() => { screen = 'home'; clearJob(); selectedFile = null; errorMsg = ''; }}>
      Try again
    </button>
  </div>
{/if}

{#if showRegexBuilder}
  <RegexBuilder onclose={() => (showRegexBuilder = false)} />
{/if}

<style>
  .home { display: flex; flex-direction: column; gap: var(--space-6); }
  .header-row { display: flex; align-items: center; justify-content: space-between; }
  h1 { margin: 0; font-size: 1.5rem; }

  .config-layout { display: flex; flex-direction: column; gap: var(--space-6); }
  .config-top { display: flex; align-items: center; gap: var(--space-4); flex-wrap: wrap; }
  .filename { flex: 1; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .profile-actions { display: flex; gap: var(--space-2); }

  .two-col { display: grid; grid-template-columns: 280px 1fr; gap: var(--space-6); }
  @media (max-width: 680px) { .two-col { grid-template-columns: 1fr; } }

  .section-title { margin: 0 0 var(--space-3); font-size: var(--text-sm); text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-text-secondary); }
  .mt { margin-top: var(--space-6); }

  .radio-group { display: flex; flex-direction: column; gap: var(--space-2); }
  .radio-label { display: flex; align-items: center; gap: var(--space-2); font-size: var(--text-sm); cursor: pointer; }
  .radio-label input { accent-color: var(--color-accent); }
  select { width: 100%; }

  .patterns-panel { display: flex; flex-direction: column; gap: var(--space-4); }
  .patterns-header { display: flex; justify-content: space-between; align-items: center; }
  .patterns-table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
  .patterns-table th { text-align: left; color: var(--color-text-secondary); font-weight: 500; padding: var(--space-2); border-bottom: 1px solid var(--color-border); }
  .patterns-table td { padding: var(--space-2); }
  .mono { font-family: var(--font-mono); }
  .truncate { max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .remove-btn { background: none; border: none; color: var(--color-error); font-size: 1.1rem; cursor: pointer; }
  .empty-patterns { margin: 0; font-size: var(--text-sm); color: var(--color-text-secondary); }
  .submit-row { display: flex; justify-content: flex-end; }

  .centered { max-width: 480px; margin: var(--space-8) auto; text-align: center; display: flex; flex-direction: column; align-items: center; gap: var(--space-4); }
  h2 { margin: 0; }
  .large { padding: var(--space-3) var(--space-6); font-size: var(--text-base); }

  .success-icon {
    width: 56px; height: 56px;
    background: color-mix(in srgb, var(--color-success) 15%, transparent);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.5rem; color: var(--color-success);
    animation: pop 350ms cubic-bezier(0.34, 1.56, 0.64, 1);
  }
  @keyframes pop { from { transform: scale(0); opacity: 0; } to { transform: scale(1); opacity: 1; } }

  .stats { margin: 0; color: var(--color-text-secondary); font-size: var(--text-sm); }
  .warning { margin: 0; font-size: var(--text-sm); color: var(--color-warning); }

  .error-box {
    background: color-mix(in srgb, var(--color-error) 10%, transparent);
    border: 1px solid var(--color-error);
    border-radius: var(--radius-sm);
    padding: var(--space-4); width: 100%; text-align: left;
  }
  .error-box p { margin: var(--space-2) 0 0; color: var(--color-text-secondary); font-size: var(--text-sm); }
  .mt { margin-top: var(--space-2); }
</style>

<script lang="ts">
  import DropZone from '$lib/components/DropZone.svelte';
  import KeyInput from '$lib/components/KeyInput.svelte';
  import EntitySelector from '$lib/components/EntitySelector.svelte';
  import RegexBuilder from '$lib/components/RegexBuilder.svelte';
  import ProgressBar from '$lib/components/ProgressBar.svelte';
  import Tutorial from '$lib/components/Tutorial.svelte';
  import { config, toYaml, fromYaml } from '$lib/stores/config';
  import { activeJob, clearJob } from '$lib/stores/job';
  import { createJob, fetchEntities, validateProfile, downloadUrl, pollStatus, cancelJob } from '$lib/api';
  import type { EntityGroup } from '$lib/api';
  import { t } from '$lib/i18n';
  import { onDestroy } from 'svelte';

  type Screen = 'home' | 'config' | 'processing' | 'done' | 'error';
  let screen: Screen = $state('home');
  let selectedFile: File | null = $state(null);
  let groups: EntityGroup[] = $state([]);
  let showRegexBuilder = $state(false);
  let errorMsg = $state('');

  // ── Entity fetch — re-run on strategy/lang only (entity list is model-independent) ──
  let entityFetchKey = $derived(`${$config.strategy}||${$config.lang}`);

  $effect(() => {
    if (screen !== 'config') return;
    const key = entityFetchKey;
    const [strategy, lang] = key.split('||');
    fetchEntities(strategy, $config.model, lang)
      .then(r => { groups = r.groups; })
      .catch(() => {});
  });

  async function onFile(file: File) {
    selectedFile = file;
    screen = 'config';
  }

  async function submit() {
    if (!selectedFile) return;
    screen = 'processing';
    clearJob();
    errorMsg = '';

    try {
      // null = all selected (no entity filter sent to backend)
      const sel = $config.selected_entities;
      const entities = (sel !== null && sel.size > 0) ? [...sel] : undefined;

      const yamlConfig = $config.custom_patterns.length > 0
        ? toYaml($config, groups)
        : undefined;

      const job = await createJob(selectedFile, {
        key:      $config.key || undefined,
        strategy: $config.strategy,
        lang:     $config.lang,
        entities,
        config:   yamlConfig,
      });

      activeJob.set({ id: job.job_id, filename: selectedFile.name, status: null, pollInterval: null });

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
    const yaml = toYaml($config, groups);
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
  let result = $derived($activeJob?.status?.result as Record<string, unknown> | undefined);
  let entityCount = $derived(result?.entity_count as number | undefined);
  let entityCounts = $derived(result?.entity_counts as Record<string, number> | undefined);


  const STRATEGIES = [
    { v: 'filtered',   lk: 'strategy.filtered',   dk: 'strategy.filtered.desc'   },
    { v: 'standalone', lk: 'strategy.standalone',  dk: 'strategy.standalone.desc' },
    { v: 'regex',      lk: 'strategy.regex',       dk: 'strategy.regex.desc'      },
    { v: 'hybrid',     lk: 'strategy.hybrid',      dk: 'strategy.hybrid.desc'     },
    { v: 'presidio',   lk: 'strategy.presidio',    dk: 'strategy.presidio.desc'   },
  ] as const;

  const MODELS = [
    { v: 'Davlan/xlm-roberta-base-ner-hrl',                  lk: 'model.xlm'       },
    { v: 'attack-vector/SecureModernBERT-NER',               lk: 'model.smbert'    },
    { v: 'dslim/bert-base-NER',                              lk: 'model.bert_fast' },
    { v: 'Jean-Baptiste/roberta-large-ner-english',          lk: 'model.roberta_en'},
    { v: 'obi/deid_roberta_i2b2',                            lk: 'model.clinical'  },
    { v: 'd4data/biomedical-ner-all',                        lk: 'model.bio'       },
    { v: 'Davlan/distilbert-base-multilingual-cased-ner-hrl',lk: 'model.distil'    },
  ] as const;

  const LANGS = [
    { v: 'en', lk: 'lang.en' },
    { v: 'pt', lk: 'lang.pt' },
    { v: 'es', lk: 'lang.es' },
    { v: 'fr', lk: 'lang.fr' },
    { v: 'de', lk: 'lang.de' },
  ] as const;
</script>

<svelte:head>
  <title>AnonShield — App</title>
</svelte:head>

<!-- Tutorial fires on first visit -->
<Tutorial />

{#if screen === 'home'}
  <div class="page-home">
    <div class="home-header">
      <div>
        <h1 class="home-title">{$t('app.title')}</h1>
      </div>
      <label class="btn btn-ghost">
        {$t('app.import_profile')}
        <input type="file" accept=".yaml,.yml,.json" class="visually-hidden" onchange={importProfile} />
      </label>
    </div>

    <div data-tut="dropzone">
      <DropZone hasKey={!!$config.key} onfile={onFile} />
    </div>

    <div data-tut="key" class="card key-card">
      <KeyInput />
    </div>
  </div>

{:else if screen === 'config'}
  <div class="page-config">
    <div class="config-top">
      <button class="btn btn-ghost" onclick={() => { screen = 'home'; selectedFile = null; }}>
        {$t('app.change_file')}
      </button>
      <span class="filename" title={selectedFile?.name}>{selectedFile?.name}</span>
      <div class="profile-actions">
        <label class="btn btn-ghost">
          {$t('app.use_profile')}
          <input type="file" accept=".yaml,.yml" class="visually-hidden" onchange={importProfile} />
        </label>
        <button class="btn btn-ghost" onclick={exportProfile}>{$t('app.save_profile')}</button>
      </div>
    </div>

    <div class="config-grid">
      <!-- Settings panel -->
      <div class="config-sidebar">
        <section class="card" data-tut="strategy">
          <h2 class="panel-title">{$t('app.strategy')}</h2>
          <div class="strategy-list">
            {#each STRATEGIES as s}
              <label class="strategy-option" class:selected={$config.strategy === s.v}>
                <input type="radio" name="strategy" value={s.v} bind:group={$config.strategy} />
                <div class="strategy-text">
                  <span class="strategy-name">{$t(s.lk)}</span>
                  <span class="strategy-desc">{$t(s.dk)}</span>
                </div>
              </label>
            {/each}
          </div>
        </section>

        <section class="card">
          <h2 class="panel-title">{$t('app.language')}</h2>
          <select bind:value={$config.lang}>
            {#each LANGS as l}
              <option value={l.v}>{$t(l.lk)}</option>
            {/each}
          </select>
        </section>

        {#if $config.strategy !== 'regex'}
          <section class="card">
            <h2 class="panel-title">{$t('app.ner_model')}</h2>
            <select bind:value={$config.model}>
              {#each MODELS as m}
                <option value={m.v}>{$t(m.lk)}</option>
              {/each}
            </select>
          </section>
        {/if}

        <section class="card">
          <h2 class="panel-title">{$t('app.slug_length', { n: $config.slug_length })}</h2>
          <input
            type="range" min="0" max="64"
            bind:value={$config.slug_length}
            style="width:100%;accent-color:var(--color-accent)"
          />
          <p class="slug-mode">
            {#if $config.slug_length === 0}
              <span class="slug-anon">Anonymization</span> — non-reversible, no token stored
            {:else}
              <span class="slug-pseudo">Pseudonymization</span> — HMAC-SHA256, {$config.slug_length * 4} bits entropy
            {/if}
          </p>
        </section>
      </div>

      <!-- Entity panel -->
      <section class="card entity-panel" data-tut="entities">
        <h2 class="panel-title">{$t('app.entities')}</h2>
        {#if groups.length > 0}
          <EntitySelector {groups} />
        {:else}
          <p class="loading-hint">Loading entities…</p>
        {/if}
      </section>
    </div>

    <!-- Custom patterns -->
    <section class="card patterns-card">
      <div class="patterns-header">
        <h2 class="panel-title">{$t('app.custom_patterns')}</h2>
        <button class="btn btn-ghost" onclick={() => (showRegexBuilder = true)}>
          {$t('app.add_pattern')}
        </button>
      </div>
      {#if $config.custom_patterns.length > 0}
        <table class="patterns-table">
          <thead>
            <tr>
              <th>{$t('app.pattern_type')}</th>
              <th>{$t('app.pattern_regex')}</th>
              <th>{$t('app.pattern_score')}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {#each $config.custom_patterns as p, i}
              <tr>
                <td class="mono">{p.entity_type}</td>
                <td class="mono truncate">{p.pattern}</td>
                <td>{p.score.toFixed(2)}</td>
                <td>
                  <button class="remove-btn" onclick={() => removePattern(i)} aria-label="Remove">×</button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      {:else}
        <p class="empty-hint">{$t('app.no_patterns')}</p>
      {/if}
    </section>

    <div class="submit-row">
      <button class="btn btn-primary submit-btn" onclick={submit}>
        {$t('app.anonymize')}
      </button>
    </div>
  </div>

{:else if screen === 'processing'}
  <div class="centered-card card">
    <div class="processing-icon" aria-hidden="true">
      <div class="spinner"></div>
    </div>
    <h2>{$activeJob?.filename ?? selectedFile?.name}</h2>
    <p class="status-label">{$t('status.processing')}</p>
    <ProgressBar {progress} label={progress > 0 ? `${progress}%` : ''} />
    <button class="btn btn-ghost mt" onclick={cancel}>{$t('status.cancel')}</button>
  </div>

{:else if screen === 'done'}
  <div class="done-wrap">
    <div class="centered-card card">
      <div class="success-icon" aria-hidden="true">✓</div>
      <h2>{$t('status.done')}</h2>
      {#if entityCount !== undefined}
        <p class="stats-label">
          {$t('status.entities_replaced', { n: entityCount })}
        </p>
      {/if}
      <a
        class="btn btn-primary download-btn"
        href={downloadUrl($activeJob!.id)}
        download
        onclick={() => setTimeout(() => { screen = 'home'; clearJob(); selectedFile = null; }, 3000)}
      >
        {$t('status.download')} — anon_{$activeJob?.filename}
        {#if outputSize > 0}<span class="file-size">({(outputSize / 1024 / 1024).toFixed(1)} MB)</span>{/if}
      </a>
      <p class="delete-warning">{$t('status.delete_warning')}</p>
      <button class="btn btn-ghost mt" onclick={() => { screen = 'home'; clearJob(); selectedFile = null; }}>
        {$t('status.anonymize_another')}
      </button>
    </div>

    {#if entityCounts && Object.keys(entityCounts).length > 0}
      {@const sorted = Object.entries(entityCounts).sort((a, b) => b[1] - a[1]).slice(0, 12)}
      {@const max = sorted[0][1]}
      {@const CHART_COLORS = ['#4ade80','#fbbf24','#f87171','#c084fc','#f472b6','#38bdf8','#60a5fa','#fb923c','#a3e635','#e879f9','#2dd4bf','#f9a8d4']}
      <div class="entity-chart card">
        <h3 class="chart-title">Entities by type</h3>
        <div class="chart-bars">
          {#each sorted as [type, count], i}
            <div class="bar-row">
              <span class="bar-label">{type.replace(/_/g, ' ')}</span>
              <div class="bar-track">
                <div
                  class="bar-fill"
                  style="--w:{(count/max*100).toFixed(1)}%;--c:{CHART_COLORS[i % CHART_COLORS.length]};--delay:{i * 60}ms"
                ></div>
              </div>
              <span class="bar-count" style="color:{CHART_COLORS[i % CHART_COLORS.length]}">{count}</span>
            </div>
          {/each}
        </div>
      </div>
    {/if}
  </div>

{:else if screen === 'error'}
  <div class="centered-card card">
    <div class="error-icon" aria-hidden="true">✕</div>
    <h2>{$t('status.error')}</h2>
    <div class="error-box" role="alert">
      <p>{errorMsg}</p>
    </div>
    <button class="btn btn-ghost mt" onclick={() => { screen = 'home'; clearJob(); selectedFile = null; errorMsg = ''; }}>
      {$t('status.try_again')}
    </button>
  </div>
{/if}

{#if showRegexBuilder}
  <RegexBuilder onclose={() => (showRegexBuilder = false)} />
{/if}

<style>
  /* ── Home ── */
  .page-home {
    display: flex; flex-direction: column; gap: var(--space-6);
    max-width: 640px; margin: 0 auto;
  }
  .home-header { display: flex; align-items: center; justify-content: space-between; }
  .home-title { margin: 0; font-size: 1.4rem; font-weight: 700; letter-spacing: -0.02em; }

  /* ── Config ── */
  .page-config { display: flex; flex-direction: column; gap: var(--space-6); }
  .config-top {
    display: flex; align-items: center; gap: var(--space-4); flex-wrap: wrap;
  }
  .filename {
    flex: 1; font-weight: 500; overflow: hidden;
    text-overflow: ellipsis; white-space: nowrap;
    color: var(--color-text-secondary);
    font-size: var(--text-sm);
  }
  .profile-actions { display: flex; gap: var(--space-2); }

  .config-grid {
    display: grid; grid-template-columns: 280px 1fr; gap: var(--space-6); align-items: start;
  }
  @media (max-width: 720px) { .config-grid { grid-template-columns: 1fr; } }

  .config-sidebar { display: flex; flex-direction: column; gap: var(--space-4); }

  .panel-title {
    margin: 0 0 var(--space-3);
    font-size: 0.72rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.07em;
    color: var(--color-text-secondary);
  }

  /* Strategy cards */
  .strategy-list { display: flex; flex-direction: column; gap: var(--space-2); }
  .strategy-option {
    display: flex; align-items: flex-start; gap: var(--space-3);
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: border-color var(--duration-fast) var(--ease-out),
                background var(--duration-fast) var(--ease-out);
  }
  .strategy-option:hover { border-color: var(--color-accent); }
  .strategy-option.selected {
    border-color: var(--color-accent);
    background: color-mix(in srgb, var(--color-accent) 8%, transparent);
  }
  .strategy-option input { accent-color: var(--color-accent); margin-top: 2px; flex-shrink: 0; }
  .strategy-text { display: flex; flex-direction: column; gap: 2px; }
  .strategy-name { font-size: var(--text-sm); font-weight: 500; color: var(--color-text-primary); }
  .strategy-desc { font-size: 0.75rem; color: var(--color-text-secondary); }

  select { width: 100%; }

  .entity-panel { min-height: 200px; max-height: 600px; overflow-y: auto; }
  .loading-hint { color: var(--color-text-secondary); font-size: var(--text-sm); margin: 0; }

  /* Patterns */
  .patterns-card { display: flex; flex-direction: column; gap: var(--space-4); }
  .patterns-header { display: flex; justify-content: space-between; align-items: center; }
  .patterns-table {
    width: 100%; border-collapse: collapse;
    font-size: var(--text-sm);
  }
  .patterns-table th {
    text-align: left; color: var(--color-text-secondary);
    font-weight: 500; padding: var(--space-2);
    border-bottom: 1px solid var(--color-border);
  }
  .patterns-table td { padding: var(--space-2); }
  .mono { font-family: var(--font-mono); }
  .truncate { max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .remove-btn { background: none; border: none; color: var(--color-error); font-size: 1.1rem; cursor: pointer; }
  .empty-hint { margin: 0; font-size: var(--text-sm); color: var(--color-text-secondary); }

  /* Slug mode */
  .slug-mode {
    margin: 8px 0 0; font-size: 0.72rem;
    color: var(--color-text-secondary); line-height: 1.5;
  }
  .slug-anon { color: #f87171; font-weight: 600; }
  .slug-pseudo { color: #4ade80; font-weight: 600; }

  .submit-row { display: flex; justify-content: flex-end; }
  .submit-btn { padding: var(--space-3) var(--space-8); font-size: var(--text-base); }

  /* ── Done layout ── */
  .done-wrap {
    display: flex; flex-direction: column; align-items: center;
    gap: var(--space-6);
  }

  /* Entity chart */
  .entity-chart {
    width: 100%; max-width: 560px;
  }
  .chart-title {
    margin: 0 0 var(--space-4); font-size: 0.72rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.07em;
    color: var(--color-text-secondary);
  }
  .chart-bars { display: flex; flex-direction: column; gap: 10px; }
  .bar-row {
    display: grid; grid-template-columns: 140px 1fr 40px;
    align-items: center; gap: 10px;
  }
  .bar-label {
    font-size: 0.72rem; font-family: var(--font-mono);
    color: var(--color-text-secondary);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    text-transform: uppercase; letter-spacing: 0.04em;
  }
  .bar-track {
    height: 8px; border-radius: 4px;
    background: var(--color-border); overflow: hidden;
  }
  .bar-fill {
    height: 100%; border-radius: 4px;
    background: var(--c);
    width: 0;
    animation: grow-bar 600ms cubic-bezier(0.16,1,0.3,1) forwards;
    animation-delay: var(--delay);
    box-shadow: 0 0 8px color-mix(in srgb, var(--c) 50%, transparent);
  }
  @keyframes grow-bar { to { width: var(--w); } }
  .bar-count {
    font-size: 0.75rem; font-weight: 700; font-family: var(--font-mono);
    text-align: right;
  }

  /* ── Centered states ── */
  .centered-card {
    max-width: 480px; margin: var(--space-8) auto;
    text-align: center; display: flex; flex-direction: column;
    align-items: center; gap: var(--space-4);
  }
  h2 { margin: 0; font-size: 1.25rem; font-weight: 700; letter-spacing: -0.02em; }

  /* Spinner */
  .processing-icon {
    width: 56px; height: 56px; display: flex; align-items: center; justify-content: center;
  }
  .spinner {
    width: 40px; height: 40px;
    border: 3px solid var(--color-border);
    border-top-color: var(--color-accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .status-label { margin: 0; color: var(--color-text-secondary); font-size: var(--text-sm); }

  /* Success */
  .success-icon {
    width: 56px; height: 56px;
    background: color-mix(in srgb, var(--color-success) 15%, transparent);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.5rem; color: var(--color-success);
    animation: pop 350ms cubic-bezier(0.34, 1.56, 0.64, 1);
  }
  @keyframes pop { from { transform: scale(0); opacity: 0; } to { transform: scale(1); opacity: 1; } }

  .stats-label { margin: 0; color: var(--color-text-secondary); font-size: var(--text-sm); }
  .download-btn { padding: var(--space-3) var(--space-6); font-size: var(--text-base); text-decoration: none; }
  .file-size { opacity: 0.7; }
  .delete-warning { margin: 0; font-size: var(--text-sm); color: var(--color-warning); }

  /* Error */
  .error-icon {
    width: 56px; height: 56px;
    background: color-mix(in srgb, var(--color-error) 15%, transparent);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.5rem; color: var(--color-error);
    animation: pop 350ms cubic-bezier(0.34, 1.56, 0.64, 1);
  }
  .error-box {
    background: color-mix(in srgb, var(--color-error) 8%, transparent);
    border: 1px solid color-mix(in srgb, var(--color-error) 40%, transparent);
    border-radius: var(--radius-sm);
    padding: var(--space-4); width: 100%; text-align: left;
  }
  .error-box p { margin: 0; color: var(--color-text-secondary); font-size: var(--text-sm); }

  .mt { margin-top: var(--space-2); }
</style>

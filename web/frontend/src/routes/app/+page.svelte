<script lang="ts">
  import DropZone from '$lib/components/DropZone.svelte';
  import KeyInput from '$lib/components/KeyInput.svelte';
  import EntitySelector from '$lib/components/EntitySelector.svelte';
  import RegexBuilder from '$lib/components/RegexBuilder.svelte';
  import ProgressBar from '$lib/components/ProgressBar.svelte';
  import Tutorial from '$lib/components/Tutorial.svelte';
  import FieldSelector from '$lib/components/FieldSelector.svelte';
  import { config, toYaml, fromYaml } from '$lib/stores/config';
  import { activeJob, clearJob } from '$lib/stores/job';
  import { createJob, fetchEntities, validateProfile, downloadUrl, pollStatus, cancelJob } from '$lib/api';
  import type { EntityGroup } from '$lib/api';
  import { t } from '$lib/i18n';
  import { onDestroy, onMount } from 'svelte';

  type Screen = 'configure' | 'processing' | 'done' | 'error';
  let screen: Screen = $state('configure');
  let showAdvanced = $state(false);
  let selectedFile: File | null = $state(null);
  let groups: EntityGroup[] = $state([]);
  let showRegexBuilder = $state(false);
  let errorMsg = $state('');
  let profileToast = $state<'ok' | 'err' | null>(null);
  let profileToastMsg = $state('');
  let profileToastTimer: ReturnType<typeof setTimeout> | null = null;

  // ── File size limits fetched from /api/config ────────────────────────────
  let limitMb = $state(1); // default 1 MB until config loads
  onMount(async () => {
    try {
      const r = await fetch('/api/config');
      if (r.ok) {
        const cfg = await r.json();
        limitMb = cfg.limit_no_key_mb ?? 1;
      }
    } catch { /* use default */ }
  });
  let limitBytes = $derived(limitMb * 1024 * 1024);
  let fileTooLarge = $derived(selectedFile !== null && (selectedFile as File).size > limitBytes);

  // ── Entity fetch — re-run when strategy, model, or lang changes ──
  let entityFetchKey = $derived(`${$config.strategy}||${$config.model}||${$config.lang}`);

  $effect(() => {
    if (screen !== 'configure') return;
    const key = entityFetchKey; // subscribe only to this derived
    const [strategy, model, lang] = key.split('||');
    groups = []; // clear while loading
    fetchEntities(strategy, model, lang)
      .then(r => { groups = r.groups; })
      .catch(() => {});
  });

  function onFile(file: File) {
    selectedFile = file;
    // stay on configure screen — file chip appears in-place
  }

  function clearFile() {
    selectedFile = null;
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
        key:        $config.key || undefined,
        strategy:   $config.strategy,
        lang:       $config.lang,
        entities,
        config:     yamlConfig,
        ocr_engine: $config.ocr_engine !== 'tesseract' ? $config.ocr_engine : undefined,
        anonymization_config: $config.anonymization_config,
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
        ? 'File too large. Demo limit is 1 MB.'
        : msg === 'INSUFFICIENT_STORAGE'
        ? 'Server is temporarily out of disk space. Try again in a few minutes.'
        : `Error: ${msg}`;
      screen = 'error';
    }
  }

  async function cancel() {
    if ($activeJob?.id) await cancelJob($activeJob.id).catch(() => {});
    clearJob();
    screen = 'configure';
    selectedFile = null;
  }

  function showToast(kind: 'ok' | 'err', msg: string) {
    profileToast = kind;
    profileToastMsg = msg;
    if (profileToastTimer) clearTimeout(profileToastTimer);
    profileToastTimer = setTimeout(() => { profileToast = null; }, 3500);
  }

  async function importProfile(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = ''; // reset so same file can be re-imported
    if (!file) return;
    try {
      const text = await file.text();
      const result = await validateProfile(text);
      if (!result.valid) { showToast('err', result.error ?? 'Invalid profile'); return; }
      fromYaml(text);
      showToast('ok', `Profile loaded — ${result.entities_count ?? 0} entities, ${result.patterns_count ?? 0} patterns`);
    } catch {
      showToast('err', 'Could not read profile file');
    }
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

  // ── Realistic ETA estimation ──────────────────────────────────────────────
  // Throughput estimates in KB/s per strategy (conservative lower bound from paper)
  const STRATEGY_KB_S: Record<string, number> = {
    regex:      34341,  // schema-aware config on D2
    filtered:   1250,   // baseline D2 standalone
    standalone: 1250,
    hybrid:     1250,
    presidio:   732,
  };

  let processingStart = $state(0);
  let elapsedMs = $state(0);
  let elapsedInterval: ReturnType<typeof setInterval> | null = null;

  $effect(() => {
    if ($activeJob?.status?.status === 'running' || $activeJob?.status?.status === 'queued') {
      if (!processingStart) {
        processingStart = Date.now();
        elapsedInterval = setInterval(() => { elapsedMs = Date.now() - processingStart; }, 500);
      }
    } else {
      if (elapsedInterval) { clearInterval(elapsedInterval); elapsedInterval = null; }
      processingStart = 0; elapsedMs = 0;
    }
  });

  let etaLabel = $derived.by(() => {
    const fileSizeKb = (selectedFile?.size ?? 0) / 1024;
    if (!fileSizeKb) return '';
    const strategy = $config.strategy || 'filtered';
    const kbPerSec = STRATEGY_KB_S[strategy] ?? 1250;
    const totalMs = (fileSizeKb / kbPerSec) * 1000;
    const remainMs = Math.max(0, totalMs - elapsedMs);
    if (remainMs < 1000) return 'almost done…';
    if (remainMs < 60000) return `~${Math.ceil(remainMs / 1000)}s remaining`;
    return `~${(remainMs / 60000).toFixed(1)} min remaining`;
  });


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

  const OCR_ENGINES = [
    { v: 'tesseract', name: 'Tesseract', badge_key: 'default' },
    { v: 'easyocr',   name: 'EasyOCR',   badge_key: 'gpu'     },
    { v: 'paddleocr', name: 'PaddleOCR', badge_key: 'tables'  },
    { v: 'doctr',     name: 'DocTR',     badge_key: 'docs'    },
  ] as const;

  // ── Batch queue (task #8) ─────────────────────────────────────────────────
  interface BatchItem {
    file: File;
    id: string;
    status: 'pending' | 'processing' | 'done' | 'error';
    jobId?: string;
    downloadHref?: string;
    entityCount?: number;
    errorMsg?: string;
  }
  let batchQueue = $state<BatchItem[]>([]);
  let batchRunning = $state(false);

  function addToBatch(f: File) {
    if (batchQueue.some(b => b.file.name === f.name && b.file.size === f.size)) return;
    batchQueue = [...batchQueue, { file: f, id: crypto.randomUUID(), status: 'pending' }];
  }

  function removeFromBatch(id: string) {
    batchQueue = batchQueue.filter(b => b.id !== id);
  }

  async function runBatch() {
    batchRunning = true;
    for (const item of batchQueue) {
      if (item.status !== 'pending') continue;
      batchQueue = batchQueue.map(b => b.id === item.id ? { ...b, status: 'processing' } : b);
      try {
        const sel = $config.selected_entities;
        const entities = (sel !== null && sel.size > 0) ? [...sel] : undefined;
        const yamlConfig = $config.custom_patterns.length > 0 ? toYaml($config, groups) : undefined;
        const job = await createJob(item.file, {
          key: $config.key || undefined, strategy: $config.strategy,
          lang: $config.lang, entities, config: yamlConfig,
          ocr_engine: $config.ocr_engine !== 'tesseract' ? $config.ocr_engine : undefined,
          anonymization_config: $config.anonymization_config,
        });
        // poll until done
        await new Promise<void>((resolve) => {
          const iv = setInterval(async () => {
            const s = await pollStatus(job.job_id);
            if (s.status === 'done') {
              clearInterval(iv);
              const ec = (s.result as any)?.entity_count as number | undefined;
              batchQueue = batchQueue.map(b => b.id === item.id
                ? { ...b, status: 'done', jobId: job.job_id, downloadHref: downloadUrl(job.job_id), entityCount: ec }
                : b);
              resolve();
            } else if (s.status === 'error') {
              clearInterval(iv);
              batchQueue = batchQueue.map(b => b.id === item.id
                ? { ...b, status: 'error', errorMsg: s.message ?? 'Error' }
                : b);
              resolve();
            }
          }, 2000);
        });
      } catch (e) {
        batchQueue = batchQueue.map(b => b.id === item.id
          ? { ...b, status: 'error', errorMsg: (e as Error).message }
          : b);
      }
    }
    batchRunning = false;
  }

  // Detect file type for conditional OCR engine visibility
  let fileExt = $derived((selectedFile as File | null)?.name.split('.').pop()?.toLowerCase() ?? '');
  let isImageOrPdf = $derived(['pdf','png','jpg','jpeg','tiff','bmp','webp','gif'].includes(fileExt));
  // csv/tsv/json/jsonl/xlsx — same set FieldSelector supports
  let isStructured = $derived(['csv','tsv','json','jsonl','ndjson','xlsx'].includes(fileExt));
  let useBatch = $state(false);
</script>

<svelte:head>
  <title>AnonShield — App</title>
</svelte:head>

<!-- Tutorial fires on first visit — spotlights dropzone, key, strategy, entities in-place -->
<Tutorial />

{#if screen === 'configure'}
  <!-- Profile import toast -->
  {#if profileToast}
    <div class="profile-toast" class:toast-ok={profileToast === 'ok'} class:toast-err={profileToast === 'err'} role="status">
      {profileToastMsg}
    </div>
  {/if}

  <div class="page-configure">
    <!-- Top bar: title + profile actions -->
    <div class="configure-top">
      <h1 class="configure-title">{$t('app.title')}</h1>
      <div class="profile-actions">
        <div class="profile-help-box">
          {$t('app.blueprint_help')}
        </div>
        <div class="profile-btn-wrap">
          <label class="btn btn-ghost" title="Load a saved YAML blueprint to restore strategy, entities, and patterns">
            {$t('app.import_blueprint')}
            <input type="file" accept=".yaml,.yml,.json" class="visually-hidden" onchange={importProfile} />
          </label>
        </div>
        <button class="btn btn-ghost" title="Save current configuration as a reusable YAML blueprint" onclick={exportProfile}>{$t('app.save_blueprint')}</button>
      </div>
    </div>

    <div class="configure-layout">
      <!-- Left: file + settings -->
      <div class="settings-col">
        <!-- File drop -->
        <div data-tut="dropzone">
          <DropZone
            limitMb={limitMb}
            onfile={onFile}
            file={selectedFile}
            onclear={clearFile}
          />
          {#if fileTooLarge}
            <p class="file-too-large">
              File is {(selectedFile!.size / 1024 / 1024).toFixed(1)} MB — demo limit is {limitMb} MB.
            </p>
          {/if}

          <!-- Field selector for CSV/JSON/JSONL/XLSX -->
          {#if selectedFile && isStructured}
            <FieldSelector
              file={selectedFile}
              entityGroups={groups}
              onchange={(conf) => config.update(c => ({ ...c, anonymization_config: conf }))}
            />
          {/if}

          <!-- Batch toggle -->
          <div class="batch-toggle">
            <label class="batch-label">
              <input type="checkbox" bind:checked={useBatch} />
              <span>{useBatch ? $t('app.batch_queue') : $t('app.batch_add')}</span>
            </label>
          </div>

          <!-- Batch queue -->
          {#if useBatch}
            <div class="batch-drop">
              <DropZone
                limitMb={limitMb}
                multiple={true}
                onfile={(f) => addToBatch(f)}
                onfiles={(fs) => fs.forEach(f => addToBatch(f))}
              />
            </div>
            {#if batchQueue.length > 0}
              <div class="batch-list">
                {#each batchQueue as item}
                  <div class="batch-item" class:bi-done={item.status === 'done'} class:bi-err={item.status === 'error'} class:bi-proc={item.status === 'processing'}>
                    <div class="bi-info">
                      <span class="bi-name">{item.file.name}</span>
                      <span class="bi-meta">
                        {(item.file.size / 1024).toFixed(0)} KB ·
                        {#if item.status === 'done'}
                          {item.entityCount ?? 0} entities
                        {:else if item.status === 'error'}
                          {item.errorMsg}
                        {:else if item.status === 'processing'}
                          processing…
                        {:else}
                          queued
                        {/if}
                      </span>
                    </div>
                    <div class="bi-actions">
                      {#if item.status === 'done' && item.downloadHref}
                        <a class="bi-dl" href={item.downloadHref} download>↓</a>
                      {/if}
                      {#if item.status === 'pending'}
                        <button class="bi-rm" onclick={() => removeFromBatch(item.id)}>×</button>
                      {/if}
                    </div>
                  </div>
                {/each}
              </div>
            {/if}
          {/if}
        </div>

        <!-- Key -->
        <div data-tut="key" class="card">
          <KeyInput />
        </div>

        <!-- Strategy -->
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

        <!-- Advanced toggle -->
        <button class="advanced-toggle" onclick={() => (showAdvanced = !showAdvanced)}>
          <span class="advanced-toggle-label">{$t('app.advanced')}</span>
          <span class="advanced-toggle-arrow">{showAdvanced ? '▴' : '▾'}</span>
        </button>

        {#if showAdvanced}
          <div class="advanced-section">
            <!-- Language -->
            <section class="card">
              <h2 class="panel-title">{$t('app.language')}</h2>
              <select bind:value={$config.lang}>
                {#each LANGS as l}
                  <option value={l.v}>{$t(l.lk)}</option>
                {/each}
              </select>
            </section>

            <!-- NER model (hidden for regex strategy) -->
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

            <!-- OCR Engine -->
            <section class="card">
              <h2 class="panel-title">OCR Engine</h2>
              <select bind:value={$config.ocr_engine}>
                {#each OCR_ENGINES as e}
                  <option value={e.v}>{e.name} — {$t(`ocr.desc.${e.v}` as any)}</option>
                {/each}
              </select>
              <p class="ocr-hint">{$t(`ocr.badge.${OCR_ENGINES.find(e => e.v === $config.ocr_engine)?.badge_key ?? 'default'}` as any)}</p>
            </section>

            <!-- Slug length -->
            <section class="card">
              <h2 class="panel-title">{$t('app.slug_length', { n: $config.slug_length })}</h2>
              <input
                type="range" min="0" max="64" step="1"
                bind:value={$config.slug_length}
                class="slug-slider"
              />
              <p class="slug-mode">
                {#if $config.slug_length === 0}
                  <span class="slug-anon">Anonymization</span> — non-reversible, no token stored
                {:else}
                  <span class="slug-pseudo">Pseudonymization</span> — HMAC-SHA256, {$config.slug_length * 4} bits entropy
                {/if}
              </p>
            </section>

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
          </div>
        {/if}
      </div>

      <!-- Right: entity selector -->
      <section class="card entity-panel" data-tut="entities">
        <h2 class="panel-title">{$t('app.entities')}</h2>
        {#if groups.length > 0}
          <EntitySelector {groups} />
        {:else}
          <p class="loading-hint">Loading entities…</p>
        {/if}
      </section>
    </div>

    <!-- Submit -->
    <div class="submit-row">
      {#if useBatch && batchQueue.length > 0}
        <button
          class="btn btn-primary submit-btn"
          onclick={runBatch}
          disabled={batchRunning || batchQueue.every(b => b.status !== 'pending')}
        >
          {batchRunning ? `Processing… (${batchQueue.filter(b => b.status === 'done').length}/${batchQueue.length})` : `Run batch — ${batchQueue.filter(b => b.status === 'pending').length} files`}
        </button>
      {:else}
        <button
          class="btn btn-primary submit-btn"
          onclick={submit}
          disabled={!selectedFile || fileTooLarge}
          title={!selectedFile ? 'Select a file first' : fileTooLarge ? `File exceeds ${limitMb} MB demo limit` : undefined}
        >
          {!selectedFile ? 'Select a file to anonymize' : fileTooLarge ? `File too large (limit: ${limitMb} MB)` : $t('app.anonymize')}
        </button>
      {/if}
    </div>
  </div>

{:else if screen === 'processing'}
  <div class="centered-card card">
    <div class="processing-icon" aria-hidden="true">
      <div class="spinner"></div>
    </div>
    <h2>{$activeJob?.filename ?? selectedFile?.name}</h2>
    <p class="status-label">
      {$t('status.processing')}
      {#if etaLabel}<span class="eta-label">— {etaLabel}</span>{/if}
    </p>
    <ProgressBar {progress} label={progress > 0 ? `${progress}%` : ''} />
    <p class="cache-hint">
      {#if $config.strategy === 'regex'}
        Regex-only mode — fastest strategy, no model loading.
      {:else}
        Processing with {$config.strategy} strategy.
        <span class="cache-note">Cache warms up over time — repeated entities resolve faster.</span>
      {/if}
    </p>
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
        onclick={() => setTimeout(() => { screen = 'configure'; clearJob(); selectedFile = null; }, 3000)}
      >
        {$t('status.download')} — anon_{$activeJob?.filename}
        {#if outputSize > 0}<span class="file-size">({(outputSize / 1024 / 1024).toFixed(1)} MB)</span>{/if}
      </a>
      <p class="delete-warning">{$t('status.delete_warning')}</p>
      <button class="btn btn-ghost mt" onclick={() => { screen = 'configure'; clearJob(); selectedFile = null; }}>
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
    <button class="btn btn-ghost mt" onclick={() => { screen = 'configure'; clearJob(); selectedFile = null; errorMsg = ''; }}>
      {$t('status.try_again')}
    </button>
  </div>
{/if}

{#if showRegexBuilder}
  <RegexBuilder onclose={() => (showRegexBuilder = false)} />
{/if}

<style>
  /* ── Profile toast ── */
  .profile-toast {
    position: fixed; top: var(--space-4); right: var(--space-4); z-index: 9999;
    padding: var(--space-3) var(--space-5);
    border-radius: var(--radius-md);
    font-size: var(--text-sm); font-weight: 500;
    border: 1px solid transparent;
    animation: pop 300ms cubic-bezier(0.34,1.56,0.64,1);
    max-width: 360px;
  }
  .toast-ok {
    background: color-mix(in srgb, #4ade80 12%, var(--color-surface));
    border-color: rgba(74,222,128,0.4);
    color: #4ade80;
  }
  .toast-err {
    background: color-mix(in srgb, var(--color-error) 12%, var(--color-surface));
    border-color: color-mix(in srgb, var(--color-error) 40%, transparent);
    color: var(--color-error);
  }

  /* ── Configure (merged home + config) ── */
  .page-configure { display: flex; flex-direction: column; gap: var(--space-6); }

  .configure-top {
    display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: var(--space-4);
  }
  .configure-title { margin: 0; font-size: 1.4rem; font-weight: 700; letter-spacing: -0.02em; }
  .profile-actions { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
  .profile-help-box {
    flex: 1;
    min-width: 300px;
    font-size: 0.75rem;
    color: var(--color-text-secondary);
    background: rgba(255,255,255,0.02);
    padding: 0.5rem 1rem;
    border-radius: 8px;
    border-left: 2px solid var(--color-accent);
    line-height: 1.4;
  }

  /* 2-column layout: left = settings, right = entity panel */
  .configure-layout {
    display: grid;
    grid-template-columns: 300px 1fr;
    gap: var(--space-6);
    align-items: start;
  }
  @media (max-width: 760px) { .configure-layout { grid-template-columns: 1fr; } }

  .settings-col { display: flex; flex-direction: column; gap: var(--space-4); }

  /* File too large warning */
  .file-too-large {
    margin: var(--space-2) 0 0;
    font-size: 0.75rem;
    color: var(--color-error);
    font-family: var(--font-mono);
    animation: pop 250ms cubic-bezier(0.34,1.56,0.64,1);
  }

  /* Submit button disabled state */
  .submit-btn:disabled {
    opacity: 0.45; cursor: not-allowed;
  }

  .panel-title {
    margin: 0 0 var(--space-3);
    font-size: 0.72rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.07em;
    color: var(--color-text-secondary);
  }

  /* Advanced toggle */
  .advanced-toggle {
    display: flex; align-items: center; justify-content: space-between;
    width: 100%;
    background: none;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    color: var(--color-text-secondary);
    font-size: 0.82rem; font-weight: 600;
    cursor: pointer; text-align: left;
    padding: var(--space-2) var(--space-3);
    letter-spacing: 0.04em;
    transition: color var(--duration-fast), border-color var(--duration-fast);
  }
  .advanced-toggle:hover {
    color: var(--color-text-primary);
    border-color: var(--color-accent);
  }
  .advanced-toggle-label { flex: 1; }
  .advanced-toggle-arrow { font-size: 0.7rem; }

  .advanced-section {
    display: flex; flex-direction: column; gap: var(--space-4);
    border-left: 2px solid var(--color-border);
    padding-left: var(--space-3);
    margin-top: calc(-1 * var(--space-2));
  }

  /* Strategy cards — compact */
  .strategy-list { display: flex; flex-direction: column; gap: 4px; }
  .strategy-option {
    display: flex; align-items: center; gap: var(--space-3);
    padding: var(--space-2) var(--space-3);
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
  .strategy-option input { accent-color: var(--color-accent); flex-shrink: 0; }
  .strategy-text { display: flex; flex-direction: column; gap: 1px; }
  .strategy-name { font-size: var(--text-sm); font-weight: 500; color: var(--color-text-primary); line-height: 1.3; }
  .strategy-desc { font-size: 0.72rem; color: var(--color-text-secondary); line-height: 1.3; }

  select { width: 100%; }

  /* Entity panel: stretch naturally — no fixed max-height causing unnecessary inner scroll */
  .entity-panel { min-height: 200px; overflow-y: visible; }
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

  /* Slug slider */
  .slug-slider {
    width: 100%;
    accent-color: var(--color-accent);
    cursor: pointer;
    touch-action: pan-y;
    height: 20px;
    padding: 0;
    -webkit-appearance: none;
    appearance: none;
    background: transparent;
  }
  .slug-slider::-webkit-slider-runnable-track {
    height: 4px; border-radius: 2px;
    background: var(--color-border);
  }
  .slug-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 20px; height: 20px; border-radius: 50%;
    background: var(--color-accent);
    margin-top: -8px; cursor: grab;
    border: 2px solid var(--color-surface);
    box-shadow: 0 0 0 2px var(--color-accent);
  }
  .slug-slider::-moz-range-track {
    height: 4px; border-radius: 2px;
    background: var(--color-border);
  }
  .slug-slider::-moz-range-thumb {
    width: 20px; height: 20px; border-radius: 50%;
    background: var(--color-accent); cursor: grab;
    border: 2px solid var(--color-surface);
  }
  .slug-slider:active::-webkit-slider-thumb { cursor: grabbing; }
  .slug-slider:active::-moz-range-thumb { cursor: grabbing; }

  /* Slug mode */
  .slug-mode {
    margin: 8px 0 0; font-size: 0.72rem;
    color: var(--color-text-secondary); line-height: 1.5;
  }
  .slug-anon { color: #f87171; font-weight: 600; }
  .slug-pseudo { color: #4ade80; font-weight: 600; }

  .submit-row {
    position: sticky;
    bottom: var(--space-4);
    z-index: 100;
    display: flex; justify-content: flex-end;
  }
  .submit-btn { padding: var(--space-3) var(--space-8); font-size: var(--text-base); }

  /* ── OCR engine ── */
  .ocr-hint {
    margin: var(--space-2) 0 0;
    font-size: 0.72rem; color: var(--color-text-secondary);
    font-family: var(--font-mono);
  }

  /* ── Batch queue ── */
  .batch-toggle {
    margin-top: var(--space-2);
  }
  .batch-label {
    display: flex; align-items: center; gap: var(--space-2);
    font-size: 0.75rem; color: var(--color-text-secondary);
    cursor: pointer;
  }
  .batch-label input { accent-color: var(--color-accent); }
  .batch-drop { margin-top: var(--space-2); }
  .batch-list {
    margin-top: var(--space-2);
    display: flex; flex-direction: column; gap: 4px;
  }
  .batch-item {
    display: flex; align-items: center; justify-content: space-between;
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--color-border); border-radius: var(--radius-sm);
    font-size: var(--text-sm);
    transition: border-color var(--duration-fast);
  }
  .batch-item.bi-done { border-color: rgba(74,222,128,0.4); background: rgba(74,222,128,0.04); }
  .batch-item.bi-err  { border-color: rgba(248,113,113,0.4); background: rgba(248,113,113,0.04); }
  .batch-item.bi-proc { border-color: var(--color-accent); }
  .bi-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .bi-name { font-size: 0.78rem; font-weight: 500; color: var(--color-text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 180px; }
  .bi-meta { font-size: 0.68rem; color: var(--color-text-secondary); font-family: var(--font-mono); }
  .bi-actions { display: flex; gap: var(--space-2); flex-shrink: 0; }
  .bi-dl {
    color: #4ade80; text-decoration: none; font-weight: 700;
    padding: 2px 8px; border: 1px solid rgba(74,222,128,0.3); border-radius: 4px;
    font-size: 0.78rem;
  }
  .bi-rm {
    background: none; border: none; color: var(--color-error);
    font-size: 1rem; cursor: pointer; padding: 0 4px; line-height: 1;
  }

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

  .status-label { margin: 0; color: var(--color-text-secondary); font-size: var(--text-sm); display: flex; align-items: center; gap: 6px; flex-wrap: wrap; justify-content: center; }
  .eta-label { color: var(--color-accent); font-family: var(--font-mono); font-size: 0.75rem; }
  .cache-hint {
    margin: 0; font-size: 0.72rem; color: var(--color-text-secondary);
    font-family: var(--font-mono); text-align: center; line-height: 1.6;
    max-width: 360px;
  }
  .cache-note { display: block; opacity: 0.6; margin-top: 3px; }

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

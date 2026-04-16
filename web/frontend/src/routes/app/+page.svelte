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
  let advancedDialog = $state<HTMLDialogElement | null>(null);

  // ── Advanced settings coach-mark tour ────────────────────────────────────────
  const ADV_TOUR_KEY = 'anonshield_adv_tour_done';
  const ADV_STEPS = [
    { target: 'adv-s0', titleKey: 'adv.s0.title' as const, descKey: 'adv.s0.desc' as const },
    { target: 'adv-s1', titleKey: 'adv.s1.title' as const, descKey: 'adv.s1.desc' as const },
    { target: 'adv-s2', titleKey: 'adv.s2.title' as const, descKey: 'adv.s2.desc' as const },
    { target: 'adv-s3', titleKey: 'adv.s3.title' as const, descKey: 'adv.s3.desc' as const },
    { target: 'adv-s4', titleKey: 'adv.s4.title' as const, descKey: 'adv.s4.desc' as const },
  ];
  let advTourStep = $state<number | null>(null);
  let advTourBusy = $state(false);

  function openAdvanced() {
    const firstTime = (() => { try { return !localStorage.getItem(ADV_TOUR_KEY); } catch { return false; } })();
    advTourStep = firstTime ? 0 : null;
    advancedDialog?.showModal();
  }

  async function advTourNext() {
    if (advTourBusy || advTourStep === null) return;
    if (advTourStep < ADV_STEPS.length - 1) {
      advTourBusy = true;
      advTourStep++;
      // scroll target section into view within dialog
      await new Promise(r => setTimeout(r, 60));
      document.getElementById(ADV_STEPS[advTourStep].target)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      advTourBusy = false;
    } else {
      advTourFinish();
    }
  }

  function advTourFinish() {
    advTourStep = null;
    try { localStorage.setItem(ADV_TOUR_KEY, '1'); } catch { /* ignore */ }
  }
  let selectedFile: File | null = $state(null);
  let groups: EntityGroup[] = $state([]);
  let showRegexBuilder = $state(false);
  let errorMsg = $state('');
  let profileToast = $state<'ok' | 'err' | null>(null);
  let profileToastMsg = $state('');
  let profileToastTimer: ReturnType<typeof setTimeout> | null = null;

  // ── File size limits fetched from /api/config ────────────────────────────
  let limitMb = $state(1); // default 1 MB until config loads
  let nerDefaults = $state<{score_threshold: number; aggregation_strategy: string; aggregation_choices: string[]} | null>(null);
  let availableEngines = $state<Record<string, boolean>>({});
  onMount(async () => {
    try {
      const r = await fetch('/api/config');
      if (r.ok) {
        const cfg = await r.json();
        limitMb = cfg.limit_no_key_mb ?? 1;
        if (cfg.ner_defaults) nerDefaults = cfg.ner_defaults;
      }
    } catch { /* use default */ }
    try {
      const r = await fetch('/api/benchmark/ocr/engines');
      if (r.ok) availableEngines = (await r.json()).engines ?? {};
    } catch { /* dropdown falls back to hardcoded list */ }
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
    // Reset entity selection when model/strategy/lang changes — old IDs may not exist in new model
    config.update(c => ({ ...c, selected_entities: null }));
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
      // null = all (no filter); empty Set = none; non-empty Set = specific selection
      const sel = $config.selected_entities;
      const entities = sel === null ? undefined : [...sel];

      const yamlConfig = $config.custom_patterns.length > 0
        ? toYaml($config, groups)
        : undefined;

      const preprocessSteps = effectivePreprocessSteps();
      const job = await createJob(selectedFile, {
        key:            $config.key || undefined,
        strategy:       $config.strategy,
        lang:           $config.lang,
        model:          $config.model || undefined,
        entities,
        config:         yamlConfig,
        ocr_engine:     $config.ocr_engine !== 'tesseract' ? $config.ocr_engine : undefined,
        ocr_preprocess: preprocessSteps.length > 0 ? preprocessSteps : undefined,
        anonymization_config: $config.anonymization_config,
        ner_score_threshold: $config.ner_score_threshold,
        ner_aggregation_strategy: $config.ner_aggregation_strategy,
        slug_length: $config.slug_length,
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
        ? $t('app.error.too_large', { mb: limitMb })
        : msg === 'INSUFFICIENT_STORAGE'
        ? $t('app.error.no_storage')
        : $t('app.error.generic', { msg });
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
    { v: 'lakshyakh93/deberta_finetuned_pii',                lk: 'model.deberta_pii'},
    { v: 'dslim/bert-base-NER',                              lk: 'model.bert_fast' },
    { v: 'Jean-Baptiste/roberta-large-ner-english',          lk: 'model.roberta_en'},
    { v: 'obi/deid_roberta_i2b2',                            lk: 'model.clinical'  },
    { v: 'd4data/biomedical-ner-all',                        lk: 'model.bio'       },
    { v: 'Davlan/distilbert-base-multilingual-cased-ner-hrl',lk: 'model.distil'    },
    { v: 'pierreguillou/ner-bert-large-cased-pt-lenerbr',    lk: 'model.lener_large'},
    { v: 'pierreguillou/ner-bert-base-cased-pt-lenerbr',     lk: 'model.lener_base' },
    { v: 'monilouise/ner_pt_br',                             lk: 'model.harem_pt'   },
    { v: 'marquesafonso/bertimbau-large-ner-selective',      lk: 'model.bertimbau_sel'},
    { v: 'lfcc/bert-portuguese-ner',                         lk: 'model.pt_conll'   },
    { v: 'dominguesm/ner-bertimbau-large-pt-legal-br',       lk: 'model.bertimbau_legal'},
  ] as const;

  const LANGS = [
    { v: 'en', lk: 'lang.en' },
    { v: 'pt', lk: 'lang.pt' },
    { v: 'es', lk: 'lang.es' },
    { v: 'fr', lk: 'lang.fr' },
    { v: 'de', lk: 'lang.de' },
  ] as const;

  const OCR_ENGINES = [
    { v: 'tesseract',   name: 'Tesseract',         badge_key: 'default',      kind: 'classical' },
    { v: 'easyocr',     name: 'EasyOCR',           badge_key: 'gpu',          kind: 'classical' },
    { v: 'paddleocr',   name: 'PaddleOCR',         badge_key: 'tables',       kind: 'classical' },
    { v: 'doctr',       name: 'DocTR',             badge_key: 'docs',         kind: 'classical' },
    { v: 'onnxtr',      name: 'OnnxTR',            badge_key: 'onnxtr',       kind: 'classical' },
    { v: 'kerasocr',    name: 'Keras-OCR',         badge_key: 'kerasocr',     kind: 'classical' },
    { v: 'surya',       name: 'Surya',             badge_key: 'surya',        kind: 'classical' },
    { v: 'rapidocr',    name: 'RapidOCR',          badge_key: 'rapidocr',     kind: 'classical' },
    { v: 'glm_ocr',     name: 'GLM-OCR',           badge_key: 'glm_ocr',      kind: 'vlm'       },
    { v: 'lighton_ocr', name: 'LightOn OCR-2',     badge_key: 'lighton_ocr',  kind: 'vlm'       },
    { v: 'paddle_vl',   name: 'PaddleOCR-VL-1.5',  badge_key: 'paddle_vl',    kind: 'vlm'       },
    { v: 'deepseek_ocr',name: 'DeepSeek-OCR-2',    badge_key: 'deepseek_ocr', kind: 'vlm'       },
    { v: 'monkey_ocr',  name: 'MonkeyOCR-pro',     badge_key: 'monkey_ocr',   kind: 'vlm'       },
    { v: 'chandra_ocr', name: 'Chandra OCR',       badge_key: 'chandra_ocr',  kind: 'vlm'       },
    { v: 'dots_ocr',    name: 'Dots OCR',          badge_key: 'dots_ocr',     kind: 'vlm'       },
    { v: 'qwen_vl',     name: 'Qwen2.5-VL',        badge_key: 'qwen_vl',      kind: 'vlm'       },
  ] as const;

  let visibleOcrEngines = $derived(
    OCR_ENGINES.filter(e => Object.keys(availableEngines).length === 0 || availableEngines[e.v])
  );
  let classicalEngines = $derived(visibleOcrEngines.filter(e => e.kind === 'classical'));
  let vlmEngines       = $derived(visibleOcrEngines.filter(e => e.kind === 'vlm'));

  const OCR_PREPROCESS_PRESETS = [
    { v: 'none',   lk: 'preprocess.preset.none'   },
    { v: 'scan',   lk: 'preprocess.preset.scan'   },
    { v: 'photo',  lk: 'preprocess.preset.photo'  },
    { v: 'fax',    lk: 'preprocess.preset.fax'    },
    { v: 'custom', lk: 'preprocess.preset.custom' },
  ] as const;

  // Short human-readable labels for step pills (language-independent technical terms)
  const STEP_SHORT: Record<string, string> = {
    grayscale:  'Grayscale',
    upscale:    'Upscale',
    clahe:      'Contrast',
    denoise:    'Denoise',
    deskew:     'Deskew',
    binarize:   'Binarize',
    morph_open: 'Cleanup',
    border:     'Border',
  };

  const PREPROCESS_STEPS = [
    { v: 'grayscale',  lk: 'preprocess.step.grayscale',  dlk: 'preprocess.step.grayscale.desc'  },
    { v: 'upscale',    lk: 'preprocess.step.upscale',    dlk: 'preprocess.step.upscale.desc'    },
    { v: 'clahe',      lk: 'preprocess.step.clahe',      dlk: 'preprocess.step.clahe.desc'      },
    { v: 'denoise',    lk: 'preprocess.step.denoise',    dlk: 'preprocess.step.denoise.desc'    },
    { v: 'deskew',     lk: 'preprocess.step.deskew',     dlk: 'preprocess.step.deskew.desc'     },
    { v: 'binarize',   lk: 'preprocess.step.binarize',   dlk: 'preprocess.step.binarize.desc'   },
    { v: 'morph_open', lk: 'preprocess.step.morph_open', dlk: 'preprocess.step.morph_open.desc' },
    { v: 'border',     lk: 'preprocess.step.border',     dlk: 'preprocess.step.border.desc'     },
  ] as const;

  // Resolve the effective preprocessing step list to send to the API
  const PRESET_STEPS: Record<string, string[]> = {
    none:   [],
    scan:   ['grayscale', 'upscale', 'clahe', 'denoise', 'deskew', 'binarize', 'border'],
    photo:  ['grayscale', 'upscale', 'clahe', 'denoise', 'deskew', 'binarize', 'morph_open', 'border'],
    fax:    ['grayscale', 'upscale', 'clahe', 'denoise', 'binarize', 'morph_open', 'border'],
  };

  function effectivePreprocessSteps(): string[] {
    const preset = $config.ocr_preprocess_preset;
    if (preset === 'custom') return $config.ocr_preprocess;
    return PRESET_STEPS[preset] ?? [];
  }

  function togglePreprocessStep(step: string) {
    const current = $config.ocr_preprocess;
    const next = current.includes(step) ? current.filter(s => s !== step) : [...current, step];
    config.update(c => ({ ...c, ocr_preprocess: next }));
  }

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
        const batchPreprocessSteps = effectivePreprocessSteps();
        const job = await createJob(item.file, {
          key: $config.key || undefined, strategy: $config.strategy,
          lang: $config.lang, model: $config.model || undefined,
          entities, config: yamlConfig,
          ocr_engine: $config.ocr_engine !== 'tesseract' ? $config.ocr_engine : undefined,
          ocr_preprocess: batchPreprocessSteps.length > 0 ? batchPreprocessSteps : undefined,
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
          {$t('app.config_help')}
        </div>
        <div class="profile-btn-wrap">
          <label class="btn btn-ghost" title={$t('app.import_config.title')}>
            {$t('app.import_config')}
            <input type="file" accept=".yaml,.yml,.json" class="visually-hidden" onchange={importProfile} />
          </label>
        </div>
        <button class="btn btn-ghost" title={$t('app.save_config.title')} onclick={exportProfile}>{$t('app.save_config')}</button>
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

        <!-- Advanced toggle → opens modal -->
        <button class="advanced-toggle" onclick={openAdvanced}>
          <span class="advanced-toggle-label">{$t('app.advanced')}</span>
          <span class="advanced-toggle-icon">⚙</span>
        </button>
      </div>

      <!-- Right: entity selector -->
      <section class="card entity-panel" data-tut="entities">
        <h2 class="panel-title">{$t('app.entities')}</h2>
        {#if groups.length > 0}
          <EntitySelector {groups} />
        {:else}
          <p class="loading-hint">{$t('app.entities_loading')}</p>
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
          {batchRunning
            ? $t('app.batch.run_progress', { done: batchQueue.filter(b => b.status === 'done').length, total: batchQueue.length })
            : $t('app.batch.run_pending', { n: batchQueue.filter(b => b.status === 'pending').length })}
        </button>
      {:else}
        <button
          class="btn btn-primary submit-btn"
          onclick={submit}
          disabled={!selectedFile || fileTooLarge}
          title={!selectedFile
            ? $t('app.submit.select_first')
            : fileTooLarge
              ? $t('app.submit.too_large_tip', { mb: limitMb })
              : undefined}
        >
          {!selectedFile
            ? $t('app.submit.select_file')
            : fileTooLarge
              ? $t('app.submit.too_large', { mb: limitMb })
              : $t('app.anonymize')}
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
        {$t('processing.regex_only')}
      {:else}
        {$t('processing.with_strategy', { strategy: $config.strategy })}
        <span class="cache-note">{$t('processing.cache_warm')}</span>
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
        <h3 class="chart-title">{$t('app.chart_title')}</h3>
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

<!-- Advanced settings modal -->
<dialog
  bind:this={advancedDialog}
  class="adv-dialog"
  onclick={(e) => { if ((e.target as Element) === advancedDialog) advancedDialog?.close(); }}
>
  <div class="adv-inner">
    <header class="adv-header">
      <h2 class="adv-title">{$t('app.advanced')}</h2>
      <button class="adv-close" onclick={() => advancedDialog?.close()} aria-label={$t('adv.close')}>✕</button>
    </header>

    <!-- Coach-mark tour overlay (inside dialog to respect top-layer) -->
    {#if advTourStep !== null}
      <div class="adv-tour-overlay" aria-live="polite">
        <div class="adv-tour-card">
          <div class="adv-tour-header">
            <span class="adv-tour-step">{$t('adv.step', { n: advTourStep + 1, total: ADV_STEPS.length })}</span>
            <button class="adv-tour-skip" onclick={advTourFinish}>{$t('adv.skip')}</button>
          </div>
          <h3 class="adv-tour-title">{$t(ADV_STEPS[advTourStep].titleKey)}</h3>
          <p class="adv-tour-desc">{$t(ADV_STEPS[advTourStep].descKey)}</p>
          <div class="adv-tour-footer">
            <div class="adv-tour-dots">
              {#each ADV_STEPS as _, i}
                <span class="adv-tour-dot" class:active={i === advTourStep}></span>
              {/each}
            </div>
            <button class="adv-tour-next" onclick={advTourNext} disabled={advTourBusy}>
              {advTourStep < ADV_STEPS.length - 1 ? $t('adv.next') : $t('adv.finish')}
            </button>
          </div>
        </div>
      </div>
    {/if}

    <div class="adv-body">
      <!-- Language + NER model -->
      <div id="adv-s0" class="adv-grid" class:adv-active={advTourStep === 0}>
        <div class="adv-field">
          <label class="adv-label" for="adv-lang">{$t('app.language')}</label>
          <select id="adv-lang" bind:value={$config.lang}>
            {#each LANGS as l}
              <option value={l.v}>{$t(l.lk)}</option>
            {/each}
          </select>
        </div>

        {#if $config.strategy !== 'regex'}
          <div class="adv-field">
            <label class="adv-label" for="adv-model">{$t('app.ner_model')}</label>
            <select id="adv-model" bind:value={$config.model}>
              {#each MODELS as m}
                <option value={m.v}>{$t(m.lk)}</option>
              {/each}
            </select>
          </div>
        {/if}
      </div>

      {#if $config.strategy !== 'regex' && nerDefaults}
        <div class="adv-grid">
          <div class="adv-field">
            <label class="adv-label" for="adv-ner-threshold">
              {$t('app.ner_score_threshold')} — {($config.ner_score_threshold ?? nerDefaults.score_threshold).toFixed(2)}
            </label>
            <input id="adv-ner-threshold" type="range" min="0.1" max="0.95" step="0.05"
                   value={$config.ner_score_threshold ?? nerDefaults.score_threshold}
                   oninput={(e) => config.update(c => ({ ...c, ner_score_threshold: +(e.currentTarget as HTMLInputElement).value }))} />
            <div class="adv-hint">{$t('app.ner_score_threshold.hint')}</div>
          </div>

          <div class="adv-field">
            <label class="adv-label" for="adv-ner-agg">{$t('app.ner_aggregation')}</label>
            <select id="adv-ner-agg"
                    value={$config.ner_aggregation_strategy ?? nerDefaults.aggregation_strategy}
                    onchange={(e) => config.update(c => ({ ...c, ner_aggregation_strategy: (e.currentTarget as HTMLSelectElement).value }))}>
              {#each nerDefaults.aggregation_choices as opt}
                <option value={opt}>{opt}</option>
              {/each}
            </select>
            <div class="adv-hint">{$t('app.ner_aggregation.hint')}</div>
          </div>
        </div>
      {/if}

      <!-- OCR Engine -->
      <div id="adv-s1" class="adv-field" class:adv-active={advTourStep === 1}>
        <label class="adv-label" for="adv-ocr">{$t('app.ocr_engine')}</label>
        <select id="adv-ocr" bind:value={$config.ocr_engine}>
          {#if classicalEngines.length}
            <optgroup label="Classical OCR">
              {#each classicalEngines as e}
                <option value={e.v}>{e.name} — {$t(`ocr.desc.${e.v}` as any)}</option>
              {/each}
            </optgroup>
          {/if}
          {#if vlmEngines.length}
            <optgroup label="Vision-Language Models (VLM)">
              {#each vlmEngines as e}
                <option value={e.v}>{e.name} — {$t(`ocr.desc.${e.v}` as any)}</option>
              {/each}
            </optgroup>
          {/if}
        </select>
        <p class="adv-hint">{$t(`ocr.badge.${OCR_ENGINES.find(e => e.v === $config.ocr_engine)?.badge_key ?? 'default'}` as any)}</p>
      </div>

      <!-- Image Preprocessing -->
      {#if !selectedFile || isImageOrPdf}
        <div id="adv-s2" class="adv-field" class:adv-active={advTourStep === 2}>
          <span class="adv-label">{$t('preprocess.title')}</span>
          <p class="adv-hint">{$t('preprocess.hint')}</p>
          <div class="preprocess-preset-grid">
            {#each OCR_PREPROCESS_PRESETS as p}
              <label class="preset-card" class:selected={$config.ocr_preprocess_preset === p.v}>
                <input type="radio" name="ocr_preprocess_preset" value={p.v}
                       bind:group={$config.ocr_preprocess_preset} />
                <span class="preset-card-name">{$t(p.lk)}</span>
                {#if p.v === 'none'}
                  <span class="preset-card-hint">pass-through</span>
                {:else if p.v === 'custom'}
                  <span class="preset-card-hint">choose below →</span>
                {:else}
                  <div class="preset-card-pills">
                    {#each PRESET_STEPS[p.v] ?? [] as s}
                      <span class="step-pill">{STEP_SHORT[s] ?? s}</span>
                    {/each}
                  </div>
                {/if}
              </label>
            {/each}
          </div>
          {#if $config.ocr_preprocess_preset === 'custom'}
            <div class="preprocess-steps">
              {#each PREPROCESS_STEPS as step}
                <label class="step-item" title={$t(step.dlk as any)}>
                  <input type="checkbox"
                         checked={$config.ocr_preprocess.includes(step.v)}
                         onchange={() => togglePreprocessStep(step.v)} />
                  <span class="step-name">{$t(step.lk as any)}</span>
                  <span class="step-desc">{$t(step.dlk as any)}</span>
                </label>
              {/each}
            </div>
          {/if}
        </div>
      {/if}

      <!-- Slug length -->
      <div id="adv-s3" class="adv-field" class:adv-active={advTourStep === 3}>
        <span class="adv-label">{$t('app.slug_length', { n: $config.slug_length })}</span>
        <input type="range" min="0" max="64" step="1" bind:value={$config.slug_length} class="slug-slider" />
        <p class="slug-mode">
          {#if $config.slug_length === 0}
            <span class="slug-anon">{$t('app.slug.anon')}</span> — {$t('app.slug.anon_desc')}
          {:else}
            <span class="slug-pseudo">{$t('app.slug.pseudo')}</span> — {$t('app.slug.pseudo_desc', { bits: $config.slug_length * 4 })}
          {/if}
        </p>
      </div>

      <!-- Custom patterns -->
      <div id="adv-s4" class="adv-field" class:adv-active={advTourStep === 4}>
        <div class="patterns-header">
          <span class="adv-label" style="margin:0">{$t('app.custom_patterns')}</span>
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
      </div>
    </div>
  </div>
</dialog>

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
    animation: pop var(--duration-slow) var(--ease-spring);
    max-width: 360px;
  }
  .toast-ok {
    background: color-mix(in srgb, var(--color-success) 12%, var(--color-surface));
    border-color: color-mix(in srgb, var(--color-success) 40%, transparent);
    color: var(--color-success);
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
  .configure-title { margin: 0; font-size: var(--text-xl); font-weight: 700; letter-spacing: -0.02em; }
  .profile-actions { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
  /* Contextual help: accent border-left anchors it as a "note" zone (Nielsen #10 help & docs);
     tinted surface keeps it attached to the bar without competing with primary content. */
  .profile-help-box {
    flex: 1;
    min-width: 300px;
    font-size: var(--text-xs);
    color: var(--color-text-secondary);
    background: color-mix(in srgb, var(--color-text-primary) 3%, transparent);
    padding: var(--space-2) var(--space-4);
    border-radius: var(--radius-sm);
    border-left: 2px solid var(--color-accent);
    line-height: 1.5;
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

  /* File too large warning — pop spring matches other feedback moments; mono for exactness */
  .file-too-large {
    margin-top: var(--space-2);
    font-size: var(--text-xs);
    color: var(--color-error);
    font-family: var(--font-mono);
    animation: pop var(--duration-slow) var(--ease-spring);
  }

  /* Submit button disabled state */
  .submit-btn:disabled {
    opacity: 0.45; cursor: not-allowed;
  }

  /* Section eyebrow — uppercase + tracked to read as a label, not body copy */
  .panel-title {
    margin: 0 0 var(--space-3);
    font-size: var(--text-xs); font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.07em;
    color: var(--color-text-secondary);
  }

  /* Advanced toggle — Fitts: full-width tap target, visible border for affordance,
     accent border on hover telegraphs that it opens further controls. */
  .advanced-toggle {
    display: flex; align-items: center; justify-content: space-between;
    width: 100%;
    background: none;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    color: var(--color-text-secondary);
    font-size: var(--text-sm); font-weight: 600;
    cursor: pointer; text-align: left;
    padding: var(--space-3) var(--space-4);
    letter-spacing: 0.02em;
    transition: color var(--duration-fast) var(--ease-out),
                border-color var(--duration-fast) var(--ease-out),
                background var(--duration-fast) var(--ease-out);
  }
  .advanced-toggle:hover {
    color: var(--color-text-primary);
    border-color: var(--color-accent);
    background: color-mix(in srgb, var(--color-accent) 4%, transparent);
  }
  .advanced-toggle:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }
  .advanced-toggle-label { flex: 1; }
  .advanced-toggle-icon { font-size: var(--text-sm); opacity: 0.6; }

  /* Advanced modal dialog */
  /* ─────────────────────────────────────────────────────────────
     Advanced settings modal
     Vertical rhythm (rigorous, token-based):
       header v:16 h:20  •  section v:20 h:20  •  section→section gap:24
       label→control: 8   •  control→hint: 4   (Gestalt proximity)
     ───────────────────────────────────────────────────────────── */
  .adv-dialog {
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: 0;
    background: var(--color-surface-raised);
    color: var(--color-text-primary);
    width: min(560px, calc(100vw - 2rem));
    max-height: min(86vh, 820px);
    box-shadow:
      0 1px 0 rgba(255,255,255,0.04) inset,
      0 24px 64px rgba(0,0,0,0.6);
    overflow: hidden;
  }
  .adv-dialog[open] {
    animation: advOpen var(--duration-normal) var(--ease-out) both;
  }
  .adv-dialog::backdrop {
    background: rgba(4,5,8,0.62);
    animation: advBackdrop var(--duration-normal) var(--ease-out) both;
  }
  @keyframes advOpen {
    from { opacity: 0; transform: translateY(6px) scale(0.98); }
    to   { opacity: 1; transform: translateY(0)   scale(1); }
  }
  @keyframes advBackdrop {
    from { opacity: 0; } to { opacity: 1; }
  }

  .adv-inner {
    display: flex; flex-direction: column;
    max-height: inherit;
    position: relative;
  }

  /* Header — sticky so the modal context is never lost on scroll
     (Nielsen #1: visibility of system status) */
  .adv-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: var(--space-4) var(--space-5);
    border-bottom: 1px solid var(--color-border);
    background: var(--color-surface-raised);
    position: sticky; top: 0; z-index: 2;
    flex-shrink: 0;
  }
  .adv-title {
    margin: 0;
    font-size: var(--text-sm); font-weight: 700;
    letter-spacing: 0.06em; text-transform: uppercase;
    color: var(--color-text-primary);
  }
  /* Close — 32×32 target (WCAG 2.5.5 AA, Fitts-friendly) */
  .adv-close {
    width: 32px; height: 32px;
    display: inline-flex; align-items: center; justify-content: center;
    background: transparent; border: 1px solid transparent;
    color: var(--color-text-secondary);
    font-size: var(--text-base); line-height: 1; cursor: pointer;
    border-radius: var(--radius-sm);
    transition: color var(--duration-fast) var(--ease-out),
                background var(--duration-fast) var(--ease-out),
                border-color var(--duration-fast) var(--ease-out);
  }
  .adv-close:hover,
  .adv-close:focus-visible {
    color: var(--color-text-primary);
    background: color-mix(in srgb, var(--color-text-primary) 6%, transparent);
    border-color: var(--color-border);
    outline: none;
  }

  /* Body: vertical stack of sections. No inner borders (reduced visual noise,
     Hick's law). Separation comes from whitespace + label typography. */
  .adv-body {
    overflow-y: auto;
    padding: var(--space-5) var(--space-5) var(--space-6);
    display: flex; flex-direction: column;
    gap: var(--space-6);
  }

  .adv-grid,
  .adv-field {
    display: flex; flex-direction: column;
    gap: var(--space-2);            /* label → control (tight, Gestalt) */
    padding: 0;
    border: 0;
  }
  /* Grid variant: language + model side-by-side (≥480 px only) */
  .adv-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-3) var(--space-4);
  }
  @media (max-width: 480px) { .adv-grid { grid-template-columns: 1fr; } }

  .adv-label {
    font-size: var(--text-xs); font-weight: 600;
    letter-spacing: 0.04em; text-transform: uppercase;
    color: var(--color-text-secondary);
  }
  /* Hint is tightly coupled to its control (closer than label) */
  .adv-hint {
    margin: calc(-1 * var(--space-1)) 0 0;
    font-size: var(--text-xs);
    color: var(--color-text-secondary);
    line-height: 1.5;
  }

  /* Tour highlight — clearly visible without border chrome.
     Uses outline (no layout shift) + subtle tint. */
  .adv-active {
    position: relative;
    border-radius: var(--radius-md);
    outline: 2px solid var(--color-accent);
    outline-offset: 8px;
    background: color-mix(in srgb, var(--color-accent) 6%, transparent);
    box-shadow: 0 0 0 8px color-mix(in srgb, var(--color-accent) 6%, transparent);
    transition: outline-color var(--duration-normal) var(--ease-out),
                background    var(--duration-normal) var(--ease-out);
  }

  /* Coach-mark tour overlay — inside dialog, respects top-layer */
  .adv-tour-overlay {
    position: absolute; inset: 0;
    background: rgba(0,0,0,0.72);
    display: flex; align-items: center; justify-content: center;
    z-index: 10;
    border-radius: inherit;
  }
  .adv-tour-card {
    background: var(--color-surface-elevated);
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-lg);
    padding: var(--space-5);
    width: min(340px, calc(100% - var(--space-5) * 2));
    box-shadow: 0 24px 48px rgba(0,0,0,0.6);
    animation: advCardIn var(--duration-normal) var(--ease-spring) both;
    display: flex; flex-direction: column; gap: var(--space-4);
  }
  @keyframes advCardIn {
    from { transform: translateY(4px) scale(0.96); opacity: 0; }
    to   { transform: translateY(0)   scale(1);    opacity: 1; }
  }
  .adv-tour-header {
    display: flex; align-items: center; justify-content: space-between;
    gap: var(--space-3);
  }
  .adv-tour-step {
    font-size: var(--text-xs); font-weight: 700;
    letter-spacing: 0.06em; text-transform: uppercase;
    color: var(--color-accent);
  }
  .adv-tour-skip {
    background: none; border: none; cursor: pointer;
    color: var(--color-text-secondary);
    font-size: var(--text-xs); padding: 4px 6px;
    border-radius: var(--radius-sm);
    transition: color var(--duration-fast) var(--ease-out),
                background var(--duration-fast) var(--ease-out);
  }
  .adv-tour-skip:hover {
    color: var(--color-text-primary);
    background: color-mix(in srgb, var(--color-text-primary) 6%, transparent);
  }
  .adv-tour-title {
    margin: 0;
    font-size: var(--text-base); font-weight: 700;
    color: var(--color-text-primary); line-height: 1.3;
  }
  .adv-tour-desc {
    margin: calc(-1 * var(--space-2)) 0 0;
    font-size: var(--text-sm);
    color: var(--color-text-secondary); line-height: 1.55;
  }
  .adv-tour-footer {
    display: flex; align-items: center; justify-content: space-between;
    gap: var(--space-3);
  }
  .adv-tour-dots { display: flex; gap: var(--space-1); }
  .adv-tour-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--color-border-strong); flex-shrink: 0;
    transition: background var(--duration-fast) var(--ease-out),
                transform  var(--duration-fast) var(--ease-out);
  }
  .adv-tour-dot.active {
    background: var(--color-accent);
    transform: scale(1.4);
  }
  .adv-tour-next {
    flex-shrink: 0;
    padding: var(--space-2) var(--space-4);
    background: var(--color-accent); color: #fff;
    border: none; border-radius: var(--radius-sm);
    font-size: var(--text-sm); font-weight: 600; cursor: pointer;
    transition: background var(--duration-fast) var(--ease-out),
                transform  var(--duration-fast) var(--ease-out);
  }
  .adv-tour-next:hover:not(:disabled) {
    background: var(--color-accent-hover);
  }
  .adv-tour-next:active:not(:disabled) { transform: translateY(1px); }
  .adv-tour-next:disabled { opacity: 0.5; cursor: default; }

  /* Strategy cards — Hick-Hyman: three options in a short vertical list, one clear
     CTA per row. Gestalt: name + desc are visually paired via tight 2px gap so each
     row reads as one decision unit, not two. */
  .strategy-list { display: flex; flex-direction: column; gap: var(--space-1); }
  .strategy-option {
    display: flex; align-items: center; gap: var(--space-3);
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: border-color var(--duration-fast) var(--ease-out),
                background var(--duration-fast) var(--ease-out);
  }
  .strategy-option:hover { border-color: var(--color-accent); }
  .strategy-option:has(input:focus-visible) {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }
  .strategy-option.selected {
    border-color: var(--color-accent);
    background: color-mix(in srgb, var(--color-accent) 8%, transparent);
  }
  .strategy-option input { accent-color: var(--color-accent); flex-shrink: 0; }
  .strategy-text { display: flex; flex-direction: column; gap: 2px; }
  .strategy-name { font-size: var(--text-sm); font-weight: 500; color: var(--color-text-primary); line-height: 1.3; }
  .strategy-desc { font-size: var(--text-xs); color: var(--color-text-secondary); line-height: 1.4; }

  select { width: 100%; }

  /* Entity panel: stretch naturally — no fixed max-height causing unnecessary inner scroll */
  .entity-panel { min-height: 200px; overflow-y: visible; }
  .loading-hint { color: var(--color-text-secondary); font-size: var(--text-sm); margin: 0; }

  /* Patterns */
  /* .patterns-card removed — now inside adv-dialog as adv-field */
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
  .remove-btn {
    display: inline-flex; align-items: center; justify-content: center;
    width: 28px; height: 28px;
    background: none;
    border: 1px solid transparent;
    border-radius: var(--radius-sm);
    color: var(--color-text-secondary);
    font-size: var(--text-base);
    line-height: 1;
    cursor: pointer;
    transition: color var(--duration-fast) var(--ease-out),
                border-color var(--duration-fast) var(--ease-out),
                background var(--duration-fast) var(--ease-out);
  }
  .remove-btn:hover {
    color: var(--color-error);
    border-color: color-mix(in srgb, var(--color-error) 40%, transparent);
    background: color-mix(in srgb, var(--color-error) 8%, transparent);
  }
  .remove-btn:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }
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

  /* Slug mode hint — inline legend; semantic colors match the destructive/safe
     distinction so users read the action, not the hue. */
  .slug-mode {
    margin-top: var(--space-2);
    font-size: var(--text-xs);
    color: var(--color-text-secondary);
    line-height: 1.5;
  }
  .slug-anon { color: var(--color-accent); font-weight: 600; }
  .slug-pseudo { color: var(--color-accent); font-weight: 600; }

  .submit-row {
    position: sticky;
    bottom: var(--space-4);
    z-index: 100;
    display: flex; justify-content: flex-end;
  }
  .submit-btn { padding: var(--space-3) var(--space-8); font-size: var(--text-base); }

  /* ── OCR engine hint → now .adv-hint inside modal ── */

  /* ── Batch queue ──
     Goals: (a) state (done / error / processing) must be readable at a glance —
     semantic color tokens instead of raw greens/reds so it matches the rest of
     the system; (b) every row-level control meets WCAG 2.5.5 (≥24px target);
     (c) meta text at ≥12px (--text-xs) for legibility. */
  .batch-toggle {
    margin-top: var(--space-2);
  }
  .batch-label {
    display: inline-flex; align-items: center; gap: var(--space-2);
    font-size: var(--text-sm); color: var(--color-text-secondary);
    cursor: pointer;
    padding: var(--space-1) 0;  /* larger hit area without shifting neighbors */
  }
  .batch-label input { accent-color: var(--color-accent); }
  .batch-drop { margin-top: var(--space-3); }
  .batch-list {
    margin-top: var(--space-3);
    display: flex; flex-direction: column; gap: var(--space-1);
  }
  .batch-item {
    display: flex; align-items: center; justify-content: space-between;
    gap: var(--space-3);
    padding: var(--space-3);
    border: 1px solid var(--color-border); border-radius: var(--radius-sm);
    font-size: var(--text-sm);
    transition: border-color var(--duration-fast) var(--ease-out),
                background var(--duration-fast) var(--ease-out);
  }
  .batch-item.bi-done {
    border-color: color-mix(in srgb, var(--color-success) 40%, transparent);
    background: color-mix(in srgb, var(--color-success) 5%, transparent);
  }
  .batch-item.bi-err {
    border-color: color-mix(in srgb, var(--color-error) 40%, transparent);
    background: color-mix(in srgb, var(--color-error) 5%, transparent);
  }
  .batch-item.bi-proc { border-color: var(--color-accent); }
  .bi-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1; }
  .bi-name {
    font-size: var(--text-sm); font-weight: 500; color: var(--color-text-primary);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .bi-meta {
    font-size: var(--text-xs); color: var(--color-text-secondary);
    font-family: var(--font-mono);
  }
  .bi-actions { display: flex; align-items: center; gap: var(--space-2); flex-shrink: 0; }
  .bi-dl {
    display: inline-flex; align-items: center;
    min-height: 28px;
    color: var(--color-success); text-decoration: none; font-weight: 600;
    padding: var(--space-1) var(--space-2);
    border: 1px solid color-mix(in srgb, var(--color-success) 30%, transparent);
    border-radius: var(--radius-sm);
    font-size: var(--text-xs);
    transition: background var(--duration-fast) var(--ease-out),
                border-color var(--duration-fast) var(--ease-out);
  }
  .bi-dl:hover {
    background: color-mix(in srgb, var(--color-success) 12%, transparent);
    border-color: color-mix(in srgb, var(--color-success) 50%, transparent);
  }
  .bi-rm {
    /* WCAG 2.5.5: 28×28 meets AA minimum (24) with a small safety margin,
       without dwarfing neighbours in a compact list. */
    display: inline-flex; align-items: center; justify-content: center;
    width: 28px; height: 28px;
    background: none; border: 1px solid transparent;
    color: var(--color-text-secondary);
    border-radius: var(--radius-sm);
    font-size: var(--text-base); line-height: 1;
    cursor: pointer;
    transition: color var(--duration-fast) var(--ease-out),
                border-color var(--duration-fast) var(--ease-out),
                background var(--duration-fast) var(--ease-out);
  }
  .bi-rm:hover {
    color: var(--color-error);
    border-color: color-mix(in srgb, var(--color-error) 40%, transparent);
    background: color-mix(in srgb, var(--color-error) 8%, transparent);
  }
  .bi-rm:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }

  /* ── Done layout ── */
  .done-wrap {
    display: flex; flex-direction: column; align-items: center;
    gap: var(--space-6);
  }

  /* Entity chart — compact horizontal bars; the fixed-width label column keeps
     bar origins aligned (Gestalt: common region), so eyes compare lengths, not
     starting positions. Grow animation is easing-out to telegraph completion. */
  .entity-chart {
    width: 100%; max-width: 560px;
  }
  .chart-title {
    margin: 0 0 var(--space-4);
    font-size: var(--text-xs); font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.07em;
    color: var(--color-text-secondary);
  }
  .chart-bars { display: flex; flex-direction: column; gap: var(--space-3); }
  .bar-row {
    display: grid; grid-template-columns: 140px 1fr 40px;
    align-items: center; gap: var(--space-3);
  }
  .bar-label {
    font-size: var(--text-xs); font-family: var(--font-mono);
    color: var(--color-text-secondary);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    text-transform: uppercase; letter-spacing: 0.04em;
  }
  .bar-track {
    height: 8px; border-radius: var(--radius-sm);
    background: var(--color-border); overflow: hidden;
  }
  .bar-fill {
    height: 100%; border-radius: var(--radius-sm);
    background: var(--c);
    width: 0;
    animation: grow-bar 600ms cubic-bezier(0.16,1,0.3,1) forwards;
    animation-delay: var(--delay);
    box-shadow: 0 0 8px color-mix(in srgb, var(--c) 50%, transparent);
  }
  @keyframes grow-bar { to { width: var(--w); } }
  .bar-count {
    font-size: var(--text-xs); font-weight: 700; font-family: var(--font-mono);
    text-align: right;
  }

  /* ── Centered states ── */
  .centered-card {
    max-width: 480px; margin: var(--space-8) auto;
    text-align: center; display: flex; flex-direction: column;
    align-items: center; gap: var(--space-4);
  }
  h2 { margin: 0; font-size: var(--text-xl); font-weight: 700; letter-spacing: -0.02em; }

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

  .status-label {
    margin: 0; color: var(--color-text-secondary); font-size: var(--text-sm);
    display: flex; align-items: center; gap: var(--space-2);
    flex-wrap: wrap; justify-content: center;
  }
  .eta-label { color: var(--color-accent); font-family: var(--font-mono); font-size: var(--text-xs); }
  .cache-hint {
    margin: 0; font-size: var(--text-xs); color: var(--color-text-secondary);
    font-family: var(--font-mono); text-align: center; line-height: 1.6;
    max-width: 360px;
  }
  .cache-note { display: block; opacity: 0.6; margin-top: var(--space-1); }

  /* Success — pop spring on entry. Disney: anticipation then settle. */
  .success-icon {
    width: 56px; height: 56px;
    background: color-mix(in srgb, var(--color-success) 15%, transparent);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: var(--text-2xl); color: var(--color-success);
    animation: pop var(--duration-slow) var(--ease-spring);
  }
  @keyframes pop { from { transform: scale(0); opacity: 0; } to { transform: scale(1); opacity: 1; } }

  .stats-label { margin: 0; color: var(--color-text-secondary); font-size: var(--text-sm); }
  .download-btn { padding: var(--space-3) var(--space-6); font-size: var(--text-base); text-decoration: none; }
  .file-size { opacity: 0.7; }
  .delete-warning { margin: 0; font-size: var(--text-sm); color: var(--color-warning); }

  /* Error — same pop as success (consistency heuristic #4) */
  .error-icon {
    width: 56px; height: 56px;
    background: color-mix(in srgb, var(--color-error) 15%, transparent);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: var(--text-2xl); color: var(--color-error);
    animation: pop var(--duration-slow) var(--ease-spring);
  }
  .error-box {
    background: color-mix(in srgb, var(--color-error) 8%, transparent);
    border: 1px solid color-mix(in srgb, var(--color-error) 40%, transparent);
    border-radius: var(--radius-sm);
    padding: var(--space-4); width: 100%; text-align: left;
  }
  .error-box p { margin: 0; color: var(--color-text-secondary); font-size: var(--text-sm); }

  .mt { margin-top: var(--space-2); }

  /* ── Image preprocessing ── */
  .preprocess-preset-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: var(--space-2);
  }
  .preset-card {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
    padding: var(--space-3);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: border-color var(--duration-fast) var(--ease-out),
                background   var(--duration-fast) var(--ease-out);
    min-height: 5rem;
  }
  .preset-card input { position: absolute; opacity: 0; pointer-events: none; }
  .preset-card.selected {
    border-color: var(--color-accent);
    background: color-mix(in srgb, var(--color-accent) 8%, transparent);
  }
  .preset-card:not(.selected):hover {
    border-color: color-mix(in srgb, var(--color-accent) 40%, var(--color-border));
  }
  .preset-card:has(input:focus-visible) {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }
  .preset-card-name {
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--color-text-primary);
    line-height: 1.2;
  }
  .preset-card.selected .preset-card-name { color: var(--color-accent); }
  .preset-card-hint {
    font-size: var(--text-xs);
    color: var(--color-text-secondary);
  }
  .preset-card-pills {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-1);
    margin-top: var(--space-1);
  }
  .step-pill {
    /* --text-xs (12px) meets WCAG AA minimum — pills previously used 0.6875rem (11px)
       which fell below legibility threshold for non-body text. */
    font-size: var(--text-xs);
    font-weight: 500;
    padding: 2px var(--space-2);
    border-radius: var(--radius-sm);
    background: color-mix(in srgb, var(--color-accent) 10%, transparent);
    color: var(--color-accent);
    border: 1px solid color-mix(in srgb, var(--color-accent) 22%, transparent);
    white-space: nowrap;
  }
  .preset-card:not(.selected) .step-pill {
    background: color-mix(in srgb, var(--color-text-secondary) 8%, transparent);
    color: var(--color-text-secondary);
    border-color: color-mix(in srgb, var(--color-text-secondary) 20%, transparent);
  }

  /* custom step checklist */
  .preprocess-steps {
    display: flex; flex-direction: column; gap: var(--space-1);
    margin-top: var(--space-3);
    padding-top: var(--space-3);
    border-top: 1px dashed var(--color-border);
  }
  .step-item {
    display: grid;
    grid-template-columns: 1rem 1fr;
    grid-template-rows: auto auto;
    column-gap: var(--space-3);
    row-gap: 2px;
    align-items: start;
    cursor: pointer;
    padding: var(--space-2) var(--space-3);
    border-radius: var(--radius-sm);
    border: 1px solid transparent;
    transition: border-color var(--duration-fast) var(--ease-out),
                background   var(--duration-fast) var(--ease-out);
  }
  .step-item:hover {
    background: color-mix(in srgb, var(--color-text-primary) 3%, transparent);
    border-color: var(--color-border);
  }
  .step-item input {
    grid-row: 1; grid-column: 1; margin-top: 2px;
    accent-color: var(--color-accent);
  }
  .step-name {
    grid-row: 1; grid-column: 2;
    font-size: var(--text-sm); font-weight: 500;
    color: var(--color-text-primary);
  }
  .step-desc {
    grid-row: 2; grid-column: 2;
    font-size: var(--text-xs);
    color: var(--color-text-secondary); line-height: 1.4;
  }
</style>

<script lang="ts">
  import { onMount } from 'svelte';
  import {
    fetchBenchmarkSummary,
    fetchBenchmarkDocs,
    fetchBenchmarkDoc,
    type BenchmarkSummaryRow,
    type BenchmarkDoc,
    type BenchmarkDocDetail,
  } from '$lib/api';
  import { t } from '$lib/i18n';

  // ── State ───────────────────────────────────────────────────────────────
  let loading      = $state(true);
  let error        = $state('');
  let rows: BenchmarkSummaryRow[] = $state([]);
  let preprocessSteps: string[]   = $state([]);
  let engines: string[]           = $state([]);

  let selectedPreprocess = $state('grayscale');
  let selectedEngine     = $state<string | null>(null);
  let docs: BenchmarkDoc[]              = $state([]);
  let docsLoading                       = $state(false);
  let selectedDocId      = $state<string | null>(null);
  let docDetail: BenchmarkDocDetail | null = $state(null);
  let docDetailLoading                   = $state(false);

  // ── Palette (consistent with metrics page) ──────────────────────────────
  const ENGINE_COLORS: Record<string, string> = {
    doctr:     '#6366f1',
    easyocr:   '#c084fc',
    surya:     '#34d399',
    tesseract: '#fbbf24',
    rapidocr:  '#f472b6',
    paddleocr: '#38bdf8',
    paddle_vl: '#60a5fa',
    onnxtr:    '#fb923c',
    kerasocr:  '#a3e635',
    glm_ocr:   '#f87171',
    monkey_ocr: '#e879f9',
    lighton_ocr: '#818cf8',
    dots_ocr:  '#4ade80',
    chandra_ocr: '#fde047',
    deepseek_ocr: '#93c5fd',
    qwen_vl:   '#d8b4fe',
  };
  function engineColor(e: string) { return ENGINE_COLORS[e] ?? '#9ca3af'; }

  // ── Formatters ──────────────────────────────────────────────────────────
  function fmt3(n: number | null | undefined): string {
    if (n == null) return '—';
    return n.toFixed(3);
  }
  function fmtLat(n: number | null | undefined): string {
    if (n == null) return '—';
    if (n < 1) return `${(n * 1000).toFixed(0)} ms`;
    return `${n.toFixed(2)} s`;
  }

  // ── Derived: leaderboard for current preprocess, sorted by CER ─────────
  const leaderboard = $derived(
    rows
      .filter(r => r.preprocess === selectedPreprocess)
      .sort((a, b) => a.mean_cer - b.mean_cer),
  );

  // Worst CER in leaderboard — used to normalize the heatmap intensity
  const maxCer = $derived(
    rows.length === 0 ? 1 : Math.max(...rows.map(r => r.mean_cer), 0.01),
  );
  const minCer = $derived(
    rows.length === 0 ? 0 : Math.min(...rows.map(r => r.mean_cer), 1),
  );

  // ── Heatmap cell lookup ─────────────────────────────────────────────────
  function cell(engine: string, preprocess: string): BenchmarkSummaryRow | undefined {
    return rows.find(r => r.engine === engine && r.preprocess === preprocess);
  }

  /** 0.0 = best (green), 1.0 = worst (red). Clamped. */
  function cerIntensity(cer: number): number {
    if (maxCer === minCer) return 0;
    return Math.min(1, Math.max(0, (cer - minCer) / (maxCer - minCer)));
  }

  /** Traffic-light hue, monotonic. Uses CSS color-mix for AA contrast on dark. */
  function heatColor(cer: number | null): string {
    if (cer == null) return 'transparent';
    const t = cerIntensity(cer);
    // green → amber → red
    if (t < 0.5) {
      const k = (t / 0.5) * 100;
      return `color-mix(in srgb, var(--color-success) ${100 - k * 0.6}%, #fbbf24 ${k * 0.6}%)`;
    }
    const k = ((t - 0.5) / 0.5) * 100;
    return `color-mix(in srgb, #fbbf24 ${100 - k}%, var(--color-error) ${k}%)`;
  }

  // ── Data loading ────────────────────────────────────────────────────────
  async function loadSummary() {
    loading = true; error = '';
    try {
      const s = await fetchBenchmarkSummary();
      rows = s.rows;
      preprocessSteps = s.preprocess_steps;
      engines = s.engines;
      if (!preprocessSteps.includes(selectedPreprocess) && preprocessSteps.length) {
        selectedPreprocess = preprocessSteps[0];
      }
    } catch (e) {
      error = (e as Error).message;
    } finally {
      loading = false;
    }
  }

  async function loadDocs() {
    if (!selectedPreprocess) return;
    docsLoading = true;
    try {
      const d = await fetchBenchmarkDocs(
        selectedPreprocess,
        selectedEngine ?? undefined,
        500,
      );
      docs = d.docs;
    } catch (e) {
      error = (e as Error).message;
    } finally {
      docsLoading = false;
    }
  }

  async function loadDocDetail(docId: string) {
    selectedDocId = docId;
    docDetailLoading = true;
    docDetail = null;
    try {
      docDetail = await fetchBenchmarkDoc(selectedPreprocess, docId);
    } catch (e) {
      error = (e as Error).message;
    } finally {
      docDetailLoading = false;
    }
  }

  // ── Diff (simple char-based) ─────────────────────────────────────────────
  interface DiffSpan { type: 'same' | 'ins' | 'del'; text: string; }

  /** Myers-style LCS-based diff over characters. Light enough for 2-5 KB texts. */
  function charDiff(ref: string, hyp: string): { ref: DiffSpan[]; hyp: DiffSpan[] } {
    const n = ref.length, m = hyp.length;
    if (n === 0 && m === 0) return { ref: [], hyp: [] };
    if (n === 0) return { ref: [], hyp: [{ type: 'ins', text: hyp }] };
    if (m === 0) return { ref: [{ type: 'del', text: ref }], hyp: [] };

    // LCS DP (limited to ~3000×3000 = 9 MB ints — caller should clamp)
    const maxLen = 3000;
    if (n > maxLen || m > maxLen) {
      // Fallback: show as-is without alignment
      return {
        ref: [{ type: 'del', text: ref }],
        hyp: [{ type: 'ins', text: hyp }],
      };
    }
    const dp = new Int16Array((n + 1) * (m + 1));
    const w = m + 1;
    for (let i = 1; i <= n; i++) {
      for (let j = 1; j <= m; j++) {
        if (ref[i - 1] === hyp[j - 1]) dp[i * w + j] = dp[(i - 1) * w + (j - 1)] + 1;
        else dp[i * w + j] = Math.max(dp[(i - 1) * w + j], dp[i * w + (j - 1)]);
      }
    }
    const refOut: DiffSpan[] = [], hypOut: DiffSpan[] = [];
    let i = n, j = m;
    while (i > 0 || j > 0) {
      if (i > 0 && j > 0 && ref[i - 1] === hyp[j - 1]) {
        push(refOut, 'same', ref[i - 1]);
        push(hypOut, 'same', hyp[j - 1]);
        i--; j--;
      } else if (j > 0 && (i === 0 || dp[i * w + (j - 1)] >= dp[(i - 1) * w + j])) {
        push(hypOut, 'ins', hyp[j - 1]);
        j--;
      } else {
        push(refOut, 'del', ref[i - 1]);
        i--;
      }
    }
    return { ref: refOut.reverse(), hyp: hypOut.reverse() };
  }
  function push(arr: DiffSpan[], type: DiffSpan['type'], ch: string) {
    const last = arr[arr.length - 1];
    if (last && last.type === type) last.text += ch;
    else arr.push({ type, text: ch });
  }

  const diffSpans = $derived.by(() => {
    if (!docDetail || !selectedEngine) return null;
    const hyp = docDetail.by_engine[selectedEngine]?.hypothesis;
    if (hyp == null) return null;
    return charDiff(docDetail.reference, hyp);
  });

  // ── Effects ─────────────────────────────────────────────────────────────
  onMount(loadSummary);

  $effect(() => {
    selectedPreprocess; selectedEngine;
    loadDocs();
  });

  // Pick first available engine when preprocess changes and none selected
  $effect(() => {
    if (!selectedEngine && leaderboard.length > 0) {
      selectedEngine = leaderboard[0].engine;
    }
  });
</script>

<svelte:head><title>AnonShield — OCR Benchmark</title></svelte:head>

<div class="bench-page">
  <div class="page-header">
    <div>
      <h1 class="page-title">OCR Benchmark</h1>
      <p class="page-sub">
        Engines × preprocess ablation on XFUND-PT — see
        <span class="mono">benchmark/ocr/METHODOLOGY.md</span>
      </p>
    </div>
    <a href="/app" class="btn btn-ghost">{$t('metrics.back')}</a>
  </div>

  {#if loading}
    <div class="empty"><div class="spinner"></div></div>
  {:else if error}
    <div class="empty error-box"><p>{error}</p></div>
  {:else if rows.length === 0}
    <div class="empty">
      <p>No benchmark results found. Run <span class="mono">benchmark/ocr/run_all_preprocess.sh</span> first.</p>
    </div>
  {:else}
    <!-- Preprocess selector ── Hick's Law: segmented control, one click ── -->
    <div class="segmented" role="tablist" aria-label="Preprocess step">
      {#each preprocessSteps as step}
        <button
          role="tab"
          type="button"
          aria-selected={step === selectedPreprocess}
          class="seg-btn"
          class:active={step === selectedPreprocess}
          onclick={() => { selectedPreprocess = step; selectedDocId = null; docDetail = null; }}
        >
          {step}
        </button>
      {/each}
    </div>

    <!-- ── KPI cards: best engine on current preprocess ── -->
    {#if leaderboard.length > 0}
      {@const top = leaderboard[0]}
      {@const bestF1  = [...leaderboard].sort((a, b) => b.macro_field_f1 - a.macro_field_f1)[0]}
      {@const bestLat = [...leaderboard].sort((a, b) => a.mean_latency_s - b.mean_latency_s)[0]}
      <div class="kpi-grid">
        <div class="kpi-card">
          <span class="kpi-l">Best CER</span>
          <span class="kpi-v" style="color:{engineColor(top.engine)}">{fmt3(top.mean_cer)}</span>
          <span class="kpi-sub">{top.engine} · N={top.n_docs}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-l">Best Field-F1</span>
          <span class="kpi-v" style="color:{engineColor(bestF1.engine)}">{fmt3(bestF1.macro_field_f1)}</span>
          <span class="kpi-sub">{bestF1.engine}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-l">Fastest</span>
          <span class="kpi-v" style="color:{engineColor(bestLat.engine)}">{fmtLat(bestLat.mean_latency_s)}</span>
          <span class="kpi-sub">{bestLat.engine}</span>
        </div>
      </div>
    {/if}

    <!-- ── Leaderboard table ── -->
    <div class="card">
      <h2 class="chart-title">Leaderboard · {selectedPreprocess}</h2>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Engine</th>
              <th>N</th>
              <th>CER ↓</th>
              <th>WER ↓</th>
              <th>Field-F1 ↑</th>
              <th>Latency ↓</th>
            </tr>
          </thead>
          <tbody>
            {#each leaderboard as row, i}
              {@const color = engineColor(row.engine)}
              <tr
                class="clickable"
                class:active={row.engine === selectedEngine}
                onclick={() => { selectedEngine = row.engine; selectedDocId = null; docDetail = null; }}
              >
                <td class="mono dim">#{i + 1}</td>
                <td>
                  <span class="engine-badge" style="--c:{color}">{row.engine}</span>
                  {#if row.in_progress}<span class="running">running</span>{/if}
                </td>
                <td class="mono">{row.n_docs}</td>
                <td class="mono accent">{fmt3(row.mean_cer)}</td>
                <td class="mono">{fmt3(row.mean_wer)}</td>
                <td class="mono">{fmt3(row.macro_field_f1)}</td>
                <td class="mono">{fmtLat(row.mean_latency_s)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── Ablation heatmap: engines × preprocess ── -->
    {#if preprocessSteps.length > 1}
      <div class="card">
        <h2 class="chart-title">Preprocess Ablation · mean CER (lower is better)</h2>
        <div class="heatmap-wrap">
          <table class="heatmap">
            <thead>
              <tr>
                <th class="sticky-col">engine</th>
                {#each preprocessSteps as step}
                  <th class="mono dim">{step}</th>
                {/each}
              </tr>
            </thead>
            <tbody>
              {#each engines as eng}
                <tr>
                  <th class="sticky-col">
                    <span class="engine-badge" style="--c:{engineColor(eng)}">{eng}</span>
                  </th>
                  {#each preprocessSteps as step}
                    {@const c = cell(eng, step)}
                    <td
                      class="heatcell"
                      class:selected={c && selectedPreprocess === step && selectedEngine === eng}
                      style="--heat:{c ? heatColor(c.mean_cer) : 'transparent'}"
                      title={c ? `${eng} × ${step}: CER=${fmt3(c.mean_cer)} F1=${fmt3(c.macro_field_f1)} (N=${c.n_docs})` : `${eng} × ${step}: no data`}
                      onclick={() => c && (selectedPreprocess = step, selectedEngine = eng)}
                      onkeydown={(e) => { if (c && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); selectedPreprocess = step; selectedEngine = eng; } }}
                      tabindex={c ? 0 : -1}
                      role={c ? 'button' : undefined}
                    >
                      {#if c}<span class="heatval">{fmt3(c.mean_cer)}</span>{:else}<span class="dim">—</span>{/if}
                    </td>
                  {/each}
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        <div class="legend">
          <span class="dim">CER</span>
          <span class="legend-bar"
            style="background:linear-gradient(90deg,
              var(--color-success) 0%,
              #fbbf24 50%,
              var(--color-error) 100%);"></span>
          <span class="mono">{fmt3(minCer)} → {fmt3(maxCer)}</span>
        </div>
      </div>
    {/if}

    <!-- ── Per-doc drill-down ── -->
    <div class="card">
      <h2 class="chart-title">
        Per-document errors
        {#if selectedEngine}<span class="dim">· {selectedEngine} × {selectedPreprocess}</span>{/if}
      </h2>

      {#if docsLoading}
        <div class="empty"><div class="spinner"></div></div>
      {:else if docs.length === 0}
        <p class="no-data">Pick an engine to see per-doc results.</p>
      {:else}
        <div class="docs-layout">
          <!-- Doc picker (sorted by CER desc — worst first, most useful for error analysis) -->
          <div class="docs-list" role="listbox" aria-label="Documents">
            {#each [...docs].sort((a, b) => (b.cer ?? 0) - (a.cer ?? 0)) as d (d.doc_id + d.engine)}
              <button
                type="button"
                role="option"
                aria-selected={d.doc_id === selectedDocId}
                class="doc-item"
                class:active={d.doc_id === selectedDocId}
                onclick={() => loadDocDetail(d.doc_id)}
              >
                <span class="doc-id">{d.doc_id.replace(/^xfund_(train|val)_pt_(train|val)_/, '')}</span>
                <span class="doc-cer mono" style="--heat:{heatColor(d.cer)}">{fmt3(d.cer)}</span>
              </button>
            {/each}
          </div>

          <!-- Diff viewer -->
          <div class="diff-viewer">
            {#if docDetailLoading}
              <div class="empty"><div class="spinner"></div></div>
            {:else if !docDetail}
              <p class="no-data">Select a document to see reference vs. hypothesis diff.</p>
            {:else if !selectedEngine}
              <p class="no-data">Select an engine above.</p>
            {:else}
              {@const engineData = docDetail.by_engine[selectedEngine]}
              {#if !engineData}
                <p class="no-data">No {selectedEngine} data for {docDetail.doc_id}.</p>
              {:else if diffSpans}
                <div class="diff-meta">
                  <span><strong>{selectedEngine}</strong></span>
                  <span>CER: <span class="mono">{fmt3(engineData.cer)}</span></span>
                  <span>WER: <span class="mono">{fmt3(engineData.wer)}</span></span>
                  <span>F1: <span class="mono">{fmt3(engineData.macro_f1)}</span></span>
                  <span>Lat: <span class="mono">{fmtLat(engineData.latency_s)}</span></span>
                </div>
                <div class="diff-grid">
                  <div class="diff-col">
                    <div class="diff-col-head">Reference (GT)</div>
                    <pre class="diff-text"><!--
                    -->{#each diffSpans.ref as s}<!--
                      -->{#if s.type === 'same'}<span>{s.text}</span><!--
                      -->{:else if s.type === 'del'}<span class="diff-del">{s.text}</span><!--
                      -->{/if}<!--
                    -->{/each}</pre>
                  </div>
                  <div class="diff-col">
                    <div class="diff-col-head">Hypothesis ({selectedEngine})</div>
                    <pre class="diff-text"><!--
                    -->{#each diffSpans.hyp as s}<!--
                      -->{#if s.type === 'same'}<span>{s.text}</span><!--
                      -->{:else if s.type === 'ins'}<span class="diff-ins">{s.text}</span><!--
                      -->{/if}<!--
                    -->{/each}</pre>
                  </div>
                </div>
              {/if}
            {/if}
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .bench-page {
    display: flex; flex-direction: column; gap: var(--space-6);
    padding: var(--space-8);
    max-width: 1400px; margin: 0 auto;
  }

  .page-header {
    display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-4);
  }
  .page-title { margin: 0; font-size: var(--text-xl); font-weight: 800; letter-spacing: -0.03em; }
  .page-sub   { margin: var(--space-1) 0 0; font-size: var(--text-xs); font-family: var(--font-mono); color: var(--color-text-secondary); }

  /* Segmented control — Fitts's Law: tall enough hit area, clear active state */
  .segmented {
    display: flex; flex-wrap: wrap; gap: 2px;
    padding: 4px;
    background: var(--color-surface-raised);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    width: fit-content;
  }
  .seg-btn {
    padding: var(--space-2) var(--space-4);
    border: none; background: transparent;
    color: var(--color-text-secondary);
    font-size: var(--text-sm); font-family: var(--font-mono); font-weight: 600;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: background 160ms ease, color 160ms ease, transform 160ms ease;
  }
  .seg-btn:hover { color: var(--color-text-primary); background: color-mix(in srgb, var(--color-accent) 8%, transparent); }
  .seg-btn.active {
    background: var(--color-accent); color: #000;
  }
  .seg-btn:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }

  /* KPIs */
  .kpi-grid {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-3);
  }
  @media (max-width: 720px) { .kpi-grid { grid-template-columns: 1fr; } }
  .kpi-card {
    display: flex; flex-direction: column; gap: var(--space-1);
    padding: var(--space-5);
    border: 1px solid var(--color-border); border-radius: var(--radius-md);
    background: var(--color-surface-raised);
  }
  .kpi-l { font-size: var(--text-xs); text-transform: uppercase; letter-spacing: 0.08em; color: var(--color-text-secondary); font-weight: 600; }
  .kpi-v { font-size: 2rem; font-weight: 900; letter-spacing: -0.04em; font-variant-numeric: tabular-nums; line-height: 1; }
  .kpi-sub { font-size: var(--text-xs); color: var(--color-text-secondary); font-family: var(--font-mono); margin-top: var(--space-1); }

  /* Card (matches metrics page convention) */
  .card {
    padding: var(--space-6);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface-raised);
  }
  .chart-title {
    margin: 0 0 var(--space-4);
    font-size: var(--text-xs); font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--color-text-secondary);
  }
  .no-data { margin: 0; font-size: var(--text-sm); color: var(--color-text-secondary); }

  /* Leaderboard table */
  .table-wrap { overflow-x: auto; }
  .data-table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
  .data-table th {
    text-align: left; color: var(--color-text-secondary);
    font-size: var(--text-xs); font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.07em;
    padding: var(--space-2) var(--space-3);
    border-bottom: 1px solid var(--color-border);
    white-space: nowrap;
  }
  .data-table td {
    padding: var(--space-2) var(--space-3);
    border-bottom: 1px solid color-mix(in srgb, var(--color-border) 50%, transparent);
    color: var(--color-text-secondary); white-space: nowrap;
  }
  .data-table tr.clickable { cursor: pointer; transition: background 120ms ease; }
  .data-table tr.clickable:hover { background: color-mix(in srgb, var(--color-accent) 6%, transparent); }
  .data-table tr.clickable.active { background: color-mix(in srgb, var(--color-accent) 12%, transparent); }
  .data-table tr:last-child td { border-bottom: none; }
  .mono { font-family: var(--font-mono); }
  .dim { opacity: 0.6; }
  .accent { color: var(--color-accent); font-weight: 700; }

  .engine-badge {
    font-size: var(--text-xs); font-family: var(--font-mono); font-weight: 700;
    border: 1px solid color-mix(in srgb, var(--c) 40%, transparent);
    border-radius: var(--radius-sm); padding: 1px var(--space-2);
    background: color-mix(in srgb, var(--c) 10%, transparent);
    color: var(--c);
  }
  .running {
    margin-left: var(--space-2);
    font-size: 0.65rem; font-family: var(--font-mono);
    color: var(--color-warning, #fbbf24);
    padding: 1px 6px; border-radius: var(--radius-sm);
    background: color-mix(in srgb, #fbbf24 12%, transparent);
    border: 1px solid color-mix(in srgb, #fbbf24 30%, transparent);
    animation: pulse 2s ease-in-out infinite;
  }
  @keyframes pulse { 50% { opacity: 0.5; } }

  /* Heatmap */
  .heatmap-wrap { overflow-x: auto; }
  .heatmap {
    border-collapse: separate; border-spacing: 2px;
    font-size: var(--text-xs); font-family: var(--font-mono);
  }
  .heatmap th {
    text-align: left; color: var(--color-text-secondary);
    padding: var(--space-2) var(--space-3);
    font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em;
    white-space: nowrap;
  }
  .sticky-col {
    position: sticky; left: 0; background: var(--color-surface-raised); z-index: 1;
  }
  .heatcell {
    width: 60px; height: 44px;
    text-align: center; vertical-align: middle;
    border-radius: var(--radius-sm);
    background: var(--heat);
    color: #000;
    font-weight: 700;
    cursor: pointer;
    transition: transform 160ms cubic-bezier(0.16,1,0.3,1), box-shadow 160ms ease;
  }
  .heatcell:hover  { transform: scale(1.08); box-shadow: 0 0 0 2px var(--color-accent); }
  .heatcell.selected { box-shadow: 0 0 0 2px var(--color-accent), 0 0 12px color-mix(in srgb, var(--color-accent) 50%, transparent); }
  .heatcell:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
  .heatval { color: #000; }

  .legend {
    display: flex; align-items: center; gap: var(--space-3);
    margin-top: var(--space-4);
    font-size: var(--text-xs);
  }
  .legend-bar { display: inline-block; width: 180px; height: 8px; border-radius: var(--radius-sm); }

  /* Per-doc drill-down */
  .docs-layout {
    display: grid; grid-template-columns: 240px 1fr; gap: var(--space-4);
  }
  @media (max-width: 880px) { .docs-layout { grid-template-columns: 1fr; } }

  .docs-list {
    display: flex; flex-direction: column; gap: 2px;
    max-height: 520px; overflow-y: auto;
    border: 1px solid var(--color-border); border-radius: var(--radius-sm);
    padding: var(--space-1);
  }
  .doc-item {
    display: flex; align-items: center; justify-content: space-between;
    padding: var(--space-2) var(--space-3);
    border: none; background: transparent;
    border-radius: var(--radius-sm);
    cursor: pointer;
    font-size: var(--text-xs); font-family: var(--font-mono);
    color: var(--color-text-secondary);
    text-align: left;
    transition: background 120ms ease;
  }
  .doc-item:hover { background: color-mix(in srgb, var(--color-accent) 8%, transparent); color: var(--color-text-primary); }
  .doc-item.active { background: color-mix(in srgb, var(--color-accent) 16%, transparent); color: var(--color-text-primary); }
  .doc-id { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .doc-cer {
    padding: 1px 6px; border-radius: var(--radius-sm);
    background: var(--heat); color: #000; font-weight: 700;
  }

  .diff-viewer { display: flex; flex-direction: column; gap: var(--space-3); }
  .diff-meta {
    display: flex; flex-wrap: wrap; gap: var(--space-4);
    padding: var(--space-3) var(--space-4);
    background: var(--color-surface-raised);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    font-size: var(--text-xs); color: var(--color-text-secondary);
  }

  .diff-grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-3);
  }
  @media (max-width: 720px) { .diff-grid { grid-template-columns: 1fr; } }
  .diff-col {
    display: flex; flex-direction: column;
    border: 1px solid var(--color-border); border-radius: var(--radius-sm);
    overflow: hidden;
  }
  .diff-col-head {
    padding: var(--space-2) var(--space-3);
    font-size: var(--text-xs); text-transform: uppercase; letter-spacing: 0.07em;
    color: var(--color-text-secondary); font-weight: 700;
    background: color-mix(in srgb, var(--color-accent) 5%, transparent);
    border-bottom: 1px solid var(--color-border);
  }
  .diff-text {
    margin: 0; padding: var(--space-3);
    font-family: var(--font-mono); font-size: var(--text-xs);
    white-space: pre-wrap; word-break: break-word;
    max-height: 520px; overflow-y: auto;
    line-height: 1.6;
    color: var(--color-text-primary);
  }
  .diff-del {
    background: color-mix(in srgb, var(--color-error) 22%, transparent);
    color: var(--color-error);
    text-decoration: line-through;
    text-decoration-color: color-mix(in srgb, var(--color-error) 50%, transparent);
    padding: 0 1px; border-radius: 2px;
  }
  .diff-ins {
    background: color-mix(in srgb, var(--color-success) 22%, transparent);
    color: var(--color-success);
    padding: 0 1px; border-radius: 2px;
  }

  /* Loading / error */
  .empty { display: flex; align-items: center; justify-content: center; padding: var(--space-10); color: var(--color-text-secondary); }
  .error-box { background: color-mix(in srgb, var(--color-error) 8%, transparent); }
  .spinner {
    width: 32px; height: 32px;
    border: 2px solid var(--color-border);
    border-top-color: var(--color-accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  @media (prefers-reduced-motion: reduce) {
    .running, .heatcell, .seg-btn { animation: none; transition: none; }
  }
</style>

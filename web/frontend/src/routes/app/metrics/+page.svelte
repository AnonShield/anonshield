<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchMetrics } from '$lib/api';
  import { t } from '$lib/i18n';

  interface JobAgg {
    n: number; avg_ms: number; max_ms: number;
    total_file_b: number; avg_file_b: number;
    total_entities: number; avg_throughput_bps: number;
  }
  interface ReqAgg {
    n: number; avg_ms: number; max_ms: number; min_ms: number;
    total_req_b: number; total_resp_b: number;
  }
  interface ByStrategy   { strategy: string; n: number; avg_ms: number; total_entities: number; avg_throughput_bps: number; }
  interface ByFormat     { file_ext: string; n: number; avg_ms: number; avg_file_b: number; total_entities: number; avg_throughput_bps: number; }
  interface ByModel      { model: string; n: number; avg_ms: number; total_entities: number; avg_throughput_bps: number; }
  interface ByEntityType { entity: string; n: number; }
  interface RecentJob    { ts: number; job_id: string; file_ext: string; file_b: number; strategy: string; lang: string; model: string | null; entity_cnt: number; ms: number; throughput_bps: number; entity_json: string | null; }
  interface ByEndpoint   { method: string; path: string; n: number; avg_ms: number; min_ms: number; max_ms: number; }

  let loading = $state(true);
  let error   = $state('');
  let jobAgg: JobAgg | null = $state(null);
  let reqAgg: ReqAgg | null = $state(null);
  let byStrategy:   ByStrategy[]   = $state([]);
  let byFormat:     ByFormat[]     = $state([]);
  let byModel:      ByModel[]      = $state([]);
  let byEntityType: ByEntityType[] = $state([]);
  let recentJobs:   RecentJob[]    = $state([]);
  let byEndpoint:   ByEndpoint[]   = $state([]);

  const STRAT_COLORS: Record<string, string> = {
    filtered:   '#6366f1',
    standalone: '#c084fc',
    regex:      '#4ade80',
    hybrid:     '#fbbf24',
    presidio:   '#f87171',
  };

  const EXT_COLORS = ['#60a5fa','#34d399','#fbbf24','#f87171','#c084fc','#f472b6','#38bdf8','#fb923c'];

  function fmt(n: number | null | undefined, unit = ''): string {
    if (n == null) return '—';
    if (n >= 1e9)  return (n / 1e9).toFixed(1) + ' G' + unit;
    if (n >= 1e6)  return (n / 1e6).toFixed(1) + ' M' + unit;
    if (n >= 1e3)  return (n / 1e3).toFixed(1) + ' K' + unit;
    return n.toFixed(0) + (unit ? ' ' + unit : '');
  }

  function fmtMs(n: number | null | undefined): string {
    if (n == null) return '—';
    if (n >= 60000) return (n / 60000).toFixed(1) + ' min';
    if (n >= 1000)  return (n / 1000).toFixed(1) + ' s';
    return n.toFixed(0) + ' ms';
  }

  function fmtDate(ts: number): string {
    return new Date(ts * 1000).toLocaleString(undefined, {
      month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  }

  onMount(async () => {
    try {
      const d = await fetchMetrics() as Record<string, unknown>;
      if (d.error) { error = d.error as string; return; }
      const jobs = d.jobs as Record<string, unknown>;
      const reqs = d.requests as Record<string, unknown>;
      jobAgg       = jobs.aggregate as JobAgg;
      reqAgg       = reqs.aggregate as ReqAgg;
      byStrategy   = (jobs.by_strategy   as ByStrategy[])   ?? [];
      byFormat     = (jobs.by_format     as ByFormat[])     ?? [];
      byModel      = (jobs.by_model      as ByModel[])      ?? [];
      byEntityType = (jobs.by_entity_type as ByEntityType[]) ?? [];
      recentJobs   = (jobs.recent        as RecentJob[])    ?? [];
      byEndpoint   = (reqs.by_endpoint   as ByEndpoint[])   ?? [];
    } catch (e) {
      error = (e as Error).message;
    } finally {
      loading = false;
    }
  });

  const maxStrat  = $derived(byStrategy.reduce((m, r) => Math.max(m, r.n), 1));
  const maxFmt    = $derived(byFormat.reduce((m, r) => Math.max(m, r.n), 1));
  const maxModel  = $derived(byModel.reduce((m, r) => Math.max(m, r.n), 1));
  const maxEntity = $derived(byEntityType.reduce((m, r) => Math.max(m, r.n), 1));

  // Shorten model name for display (last segment after /)
  function shortModel(m: string): string {
    return m.split('/').pop() ?? m;
  }
</script>

<svelte:head><title>AnonShield — Metrics</title></svelte:head>

<div class="metrics-page">
  <div class="page-header">
    <div>
      <h1 class="page-title">{$t('metrics.title')}</h1>
      <p class="page-sub">{$t('metrics.subtitle')}</p>
    </div>
    <a href="/app" class="btn btn-ghost">{$t('metrics.back')}</a>
  </div>

  {#if loading}
    <div class="empty"><div class="spinner"></div></div>
  {:else if error}
    <div class="empty error-box"><p>{error}</p></div>
  {:else}
    <!-- ── KPIs ── -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <span class="kpi-v" class:empty={(jobAgg?.n ?? 0) === 0}>{jobAgg?.n ?? 0}</span>
        <span class="kpi-l">{$t('metrics.kpi.jobs')}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-v" class:empty={fmt(jobAgg?.total_entities) === '—'}>{fmt(jobAgg?.total_entities)}</span>
        <span class="kpi-l">{$t('metrics.kpi.entities')}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-v" class:empty={fmt(jobAgg?.total_file_b,'B') === '—'}>{fmt(jobAgg?.total_file_b,'B')}</span>
        <span class="kpi-l">{$t('metrics.kpi.data')}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-v" class:empty={fmtMs(jobAgg?.avg_ms) === '—'}>{fmtMs(jobAgg?.avg_ms)}</span>
        <span class="kpi-l">{$t('metrics.kpi.avg_time')}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-v" class:empty={fmt(jobAgg?.avg_throughput_bps,'B/s') === '—'}>{fmt(jobAgg?.avg_throughput_bps,'B/s')}</span>
        <span class="kpi-l">{$t('metrics.kpi.throughput')}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-v" class:empty={(reqAgg?.n ?? 0) === 0}>{reqAgg?.n ?? 0}</span>
        <span class="kpi-l">{$t('metrics.kpi.requests')}</span>
      </div>
    </div>

    <div class="charts-row">
      <!-- Strategy breakdown -->
      <div class="card chart-card">
        <h2 class="chart-title">{$t('metrics.chart.strategy')}</h2>
        {#if byStrategy.length === 0}
          <p class="no-data">{$t('metrics.empty.no_data')}</p>
        {:else}
          <div class="bars">
            {#each byStrategy as row, i}
              {@const color = STRAT_COLORS[row.strategy] ?? '#6366f1'}
              <div class="bar-row">
                <span class="bar-lbl" title={row.strategy}>{row.strategy}</span>
                <div class="bar-track">
                  <div class="bar-fill" style="--w:{(row.n/maxStrat*100).toFixed(1)}%;--c:{color};--d:{i*80}ms"></div>
                </div>
                <div class="bar-meta">
                  <span class="bar-n" style="color:{color}">{row.n}</span>
                  <span class="bar-sub">{fmtMs(row.avg_ms)}</span>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Format breakdown -->
      <div class="card chart-card">
        <h2 class="chart-title">{$t('metrics.chart.format')}</h2>
        {#if byFormat.length === 0}
          <p class="no-data">{$t('metrics.empty.no_data')}</p>
        {:else}
          <div class="bars">
            {#each byFormat as row, i}
              {@const color = EXT_COLORS[i % EXT_COLORS.length]}
              <div class="bar-row">
                <span class="bar-lbl">{(row.file_ext ?? '?').toUpperCase()}</span>
                <div class="bar-track">
                  <div class="bar-fill" style="--w:{(row.n/maxFmt*100).toFixed(1)}%;--c:{color};--d:{i*80}ms"></div>
                </div>
                <div class="bar-meta">
                  <span class="bar-n" style="color:{color}">{row.n}</span>
                  <span class="bar-sub">{fmtMs(row.avg_ms)}</span>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>

    <!-- NER model + entity type breakdowns -->
    <div class="charts-row">
      <!-- By NER model -->
      <div class="card chart-card">
        <h2 class="chart-title">{$t('metrics.chart.model')}</h2>
        {#if byModel.length === 0}
          <p class="no-data">{$t('metrics.empty.no_model')}</p>
        {:else}
          <div class="bars">
            {#each byModel as row, i}
              {@const color = '#c084fc'}
              <div class="bar-row">
                <span class="bar-lbl" title={row.model}>{shortModel(row.model)}</span>
                <div class="bar-track">
                  <div class="bar-fill" style="--w:{(row.n/maxModel*100).toFixed(1)}%;--c:{color};--d:{i*80}ms"></div>
                </div>
                <div class="bar-meta">
                  <span class="bar-n" style="color:{color}">{row.n}</span>
                  <span class="bar-sub">{fmtMs(row.avg_ms)}</span>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Entities by type -->
      <div class="card chart-card">
        <h2 class="chart-title">{$t('metrics.chart.entities')}</h2>
        {#if byEntityType.length === 0}
          <p class="no-data">{$t('metrics.empty.no_data')}</p>
        {:else}
          <div class="bars">
            {#each byEntityType.slice(0, 12) as row, i}
              {@const color = ['#6366f1','#4ade80','#fbbf24','#f87171','#c084fc','#f472b6','#38bdf8','#fb923c','#60a5fa','#34d399','#a3e635','#e879f9'][i % 12]}
              <div class="bar-row">
                <span class="bar-lbl">{row.entity.replace(/_/g,' ')}</span>
                <div class="bar-track">
                  <div class="bar-fill" style="--w:{(row.n/maxEntity*100).toFixed(1)}%;--c:{color};--d:{i*60}ms"></div>
                </div>
                <div class="bar-meta">
                  <span class="bar-n" style="color:{color}">{row.n}</span>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>

    <!-- Recent jobs -->
    <div class="card">
      <h2 class="chart-title">{$t('metrics.chart.recent')}</h2>
      {#if recentJobs.length === 0}
        <p class="no-data">{$t('metrics.empty.no_jobs')}</p>
      {:else}
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>{$t('metrics.col.time')}</th>
                <th>{$t('metrics.col.format')}</th>
                <th>{$t('metrics.col.strategy')}</th>
                <th>{$t('metrics.col.model')}</th>
                <th>{$t('metrics.col.lang')}</th>
                <th>{$t('metrics.col.size')}</th>
                <th>{$t('metrics.col.entities')}</th>
                <th>{$t('metrics.col.duration')}</th>
                <th>{$t('metrics.col.throughput')}</th>
              </tr>
            </thead>
            <tbody>
              {#each recentJobs as j}
                <tr>
                  <td class="mono dim">{fmtDate(j.ts)}</td>
                  <td><span class="ext-badge">{(j.file_ext ?? '?').toUpperCase()}</span></td>
                  <td><span class="strat-badge" style="--c:{STRAT_COLORS[j.strategy]??'#6366f1'}">{j.strategy ?? '—'}</span></td>
                  <td class="mono dim" title={j.model ?? ''}>{j.model ? shortModel(j.model) : '—'}</td>
                  <td class="mono">{j.lang ?? '—'}</td>
                  <td class="mono">{fmt(j.file_b, 'B')}</td>
                  <td class="mono accent">{j.entity_cnt ?? '—'}</td>
                  <td class="mono">{fmtMs(j.ms)}</td>
                  <td class="mono">{fmt(j.throughput_bps, 'B/s')}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>

    <!-- API endpoints -->
    {#if byEndpoint.length > 0}
      <div class="card">
        <h2 class="chart-title">{$t('metrics.chart.endpoints')}</h2>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>{$t('metrics.col.method')}</th>
                <th>{$t('metrics.col.path')}</th>
                <th>{$t('metrics.col.calls')}</th>
                <th>{$t('metrics.col.avg')}</th>
                <th>{$t('metrics.col.min')}</th>
                <th>{$t('metrics.col.max')}</th>
              </tr>
            </thead>
            <tbody>
              {#each byEndpoint as ep}
                <tr>
                  <td><span class="method-badge m-{ep.method.toLowerCase()}">{ep.method}</span></td>
                  <td class="mono">{ep.path}</td>
                  <td class="mono">{ep.n}</td>
                  <td class="mono">{fmtMs(ep.avg_ms)}</td>
                  <td class="mono dim">{fmtMs(ep.min_ms)}</td>
                  <td class="mono dim">{fmtMs(ep.max_ms)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>
    {/if}
  {/if}
</div>

<style>
  .metrics-page {
    display: flex; flex-direction: column; gap: var(--space-6);
    padding: var(--space-8);
    max-width: 1200px; margin: 0 auto;
  }

  .page-header {
    display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-4);
  }
  .page-title { margin: 0; font-size: var(--text-xl); font-weight: 800; letter-spacing: -0.03em; }
  .page-sub { margin: var(--space-1) 0 0; font-size: var(--text-xs); font-family: var(--font-mono); color: var(--color-text-secondary); }

  /* KPI grid */
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--space-3);
  }
  @media (max-width: 640px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }
  .kpi-card {
    display: flex; flex-direction: column; gap: var(--space-1);
    padding: var(--space-5) var(--space-5) var(--space-4);
    border: 1px solid var(--color-border); border-radius: var(--radius-md);
    background: var(--color-surface-raised);
  }
  .kpi-v {
    font-size: 2rem; font-weight: 900; letter-spacing: -0.04em;
    color: var(--color-text-primary); font-variant-numeric: tabular-nums;
    line-height: 1;
  }
  .kpi-v.empty { color: var(--color-text-secondary); font-size: var(--text-2xl); }
  .kpi-l {
    margin-top: var(--space-2);
    font-size: var(--text-xs); text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--color-text-secondary); font-weight: 600;
  }

  /* Charts row */
  .charts-row {
    display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-4);
  }
  @media (max-width: 720px) { .charts-row { grid-template-columns: 1fr; } }

  .chart-card { display: flex; flex-direction: column; gap: var(--space-4); padding: var(--space-6); }
  .chart-title {
    margin: 0 0 var(--space-2); font-size: var(--text-xs); font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--color-text-secondary);
  }
  .no-data { margin: 0; font-size: var(--text-sm); color: var(--color-text-secondary); }

  /* Bars — horizontal rhythm: 12px vertical gap (Gestalt breathing) */
  .bars { display: flex; flex-direction: column; gap: var(--space-3); }
  .bar-row { display: grid; grid-template-columns: 90px 1fr 80px; align-items: center; gap: var(--space-3); }
  .bar-lbl {
    font-size: var(--text-xs); font-family: var(--font-mono);
    color: var(--color-text-secondary); white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis;
  }
  .bar-track { height: 8px; border-radius: var(--radius-sm); background: var(--color-border); overflow: hidden; }
  .bar-fill {
    height: 100%; border-radius: var(--radius-sm); background: var(--c);
    width: 0; animation: grow-bar 600ms cubic-bezier(0.16,1,0.3,1) forwards;
    animation-delay: var(--d, 0ms);
    box-shadow: 0 0 8px color-mix(in srgb, var(--c) 50%, transparent);
  }
  @keyframes grow-bar { to { width: var(--w); } }
  .bar-meta { display: flex; flex-direction: column; align-items: flex-end; gap: 1px; }
  .bar-n { font-size: var(--text-xs); font-weight: 700; font-family: var(--font-mono); }
  .bar-sub { font-size: var(--text-xs); color: var(--color-text-secondary); font-family: var(--font-mono); opacity: 0.75; }

  /* Tables — dense metrics; --text-xs cells, tracked uppercase headers for scanability */
  .table-wrap { overflow-x: auto; }
  .data-table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
  .data-table th {
    text-align: left; color: var(--color-text-secondary);
    font-size: var(--text-xs); font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em;
    padding: var(--space-2) var(--space-3);
    border-bottom: 1px solid var(--color-border);
    white-space: nowrap;
  }
  .data-table td {
    padding: var(--space-2) var(--space-3);
    border-bottom: 1px solid color-mix(in srgb, var(--color-border) 50%, transparent);
    color: var(--color-text-secondary);
    white-space: nowrap;
  }
  .data-table tr:last-child td { border-bottom: none; }
  .mono { font-family: var(--font-mono); }
  .dim { opacity: 0.6; }
  .accent { color: var(--color-accent); }

  .ext-badge {
    font-size: var(--text-xs); font-family: var(--font-mono); font-weight: 700;
    border: 1px solid var(--color-border); border-radius: var(--radius-sm);
    padding: 1px var(--space-2); background: var(--color-surface-raised);
    color: var(--color-text-secondary);
  }
  .strat-badge {
    font-size: var(--text-xs); font-family: var(--font-mono); font-weight: 700;
    border: 1px solid color-mix(in srgb, var(--c) 40%, transparent);
    border-radius: var(--radius-sm); padding: 1px var(--space-2);
    background: color-mix(in srgb, var(--c) 10%, transparent);
    color: var(--c);
  }
  /* HTTP method badges — semantic: success/accent/error map to safe/neutral/destructive.
     Consistent with the rest of the system instead of raw colour literals. */
  .method-badge {
    font-size: var(--text-xs); font-family: var(--font-mono); font-weight: 700;
    border-radius: var(--radius-sm); padding: 1px var(--space-2);
  }
  .m-get {
    background: color-mix(in srgb, var(--color-success) 10%, transparent);
    color: var(--color-success);
    border: 1px solid color-mix(in srgb, var(--color-success) 30%, transparent);
  }
  .m-post {
    --m-post: #60a5fa;
    background: color-mix(in srgb, var(--m-post) 10%, transparent);
    color: var(--m-post);
    border: 1px solid color-mix(in srgb, var(--m-post) 30%, transparent);
  }
  .m-delete {
    background: color-mix(in srgb, var(--color-error) 10%, transparent);
    color: var(--color-error);
    border: 1px solid color-mix(in srgb, var(--color-error) 30%, transparent);
  }

  /* Loading / error */
  .empty {
    display: flex; align-items: center; justify-content: center;
    padding: var(--space-16); color: var(--color-text-secondary);
  }
  .error-box { background: color-mix(in srgb, var(--color-error) 8%, transparent); }
  .spinner {
    width: 32px; height: 32px;
    border: 2px solid var(--color-border);
    border-top-color: var(--color-accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>

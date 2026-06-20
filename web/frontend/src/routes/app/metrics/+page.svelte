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
  interface ByStrategy   { strategy: string; n: number; avg_ms: number; avg_file_b: number; total_entities: number; avg_throughput_bps: number; }
  interface ByFormat     { file_ext: string; n: number; avg_ms: number; avg_file_b: number; total_entities: number; avg_throughput_bps: number; }
  interface ByModel      { model: string; n: number; avg_ms: number; total_entities: number; avg_throughput_bps: number; }
  interface ByEntityType { entity: string; n: number; }
  interface RecentJob    { ts: number; job_id: string; file_ext: string; file_b: number; strategy: string; lang: string; model: string | null; entity_cnt: number; ms: number; throughput_bps: number; entity_json: string | null; }
  interface ByEndpoint   { method: string; path: string; n: number; avg_ms: number; min_ms: number; max_ms: number; }
  interface Pctl         { n: number; p50: number | null; p90: number | null; p99: number | null; min: number | null; max: number | null; }
  interface Percentiles  { ms: Pctl; throughput_bps: Pctl; }
  interface TimePoint    { ts: number; n: number; avg_throughput_bps: number | null; avg_ms: number | null; total_entities: number; }

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
  let percentiles:  Percentiles | null = $state(null);
  let timeseries:   TimePoint[]    = $state([]);

  // Cohesive palette anchored on the app accent (#6366f1).
  const STRAT_COLORS: Record<string, string> = {
    filtered:   '#6366f1',
    standalone: '#c084fc',
    regex:      '#4ade80',
    hybrid:     '#fbbf24',
    presidio:   '#f87171',
  };
  const EXT_COLORS = ['#60a5fa','#34d399','#fbbf24','#f87171','#c084fc','#f472b6','#38bdf8','#fb923c'];
  const ENTITY_COLORS = ['#6366f1','#4ade80','#fbbf24','#f87171','#c084fc','#f472b6','#38bdf8','#fb923c','#60a5fa','#34d399','#a3e635','#e879f9'];

  function stratColor(s: string): string { return STRAT_COLORS[s] ?? '#6366f1'; }

  // ── Formatters ──────────────────────────────────────────────────────────────
  function fmt(n: number | null | undefined, unit = ''): string {
    if (n == null) return '-';
    if (n >= 1e9)  return (n / 1e9).toFixed(1) + ' G' + unit;
    if (n >= 1e6)  return (n / 1e6).toFixed(1) + ' M' + unit;
    if (n >= 1e3)  return (n / 1e3).toFixed(1) + ' K' + unit;
    return n.toFixed(0) + (unit ? ' ' + unit : '');
  }

  // Bytes with binary-ish friendly KB/MB/GB.
  function fmtBytes(n: number | null | undefined): string {
    if (n == null) return '-';
    if (n >= 1e9) return (n / 1e9).toFixed(1) + ' GB';
    if (n >= 1e6) return (n / 1e6).toFixed(1) + ' MB';
    if (n >= 1e3) return (n / 1e3).toFixed(1) + ' KB';
    return n.toFixed(0) + ' B';
  }

  // Throughput in KB/s or MB/s, human-friendly.
  function fmtThroughput(n: number | null | undefined): string {
    if (n == null || n <= 0) return '-';
    if (n >= 1e6) return (n / 1e6).toFixed(2) + ' MB/s';
    if (n >= 1e3) return (n / 1e3).toFixed(1) + ' KB/s';
    return n.toFixed(0) + ' B/s';
  }

  function fmtMs(n: number | null | undefined): string {
    if (n == null) return '-';
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

  function fmtTimeShort(ts: number): string {
    return new Date(ts * 1000).toLocaleString(undefined, {
      month: 'short', day: 'numeric', hour: '2-digit',
    });
  }

  function shortModel(m: string): string { return m.split('/').pop() ?? m; }
  function entityLabel(e: string): string { return e.replace(/_/g, ' '); }

  onMount(async () => {
    try {
      const d = await fetchMetrics() as Record<string, unknown>;
      if (d.error) { error = d.error as string; return; }
      const jobs = d.jobs as Record<string, unknown>;
      const reqs = d.requests as Record<string, unknown>;
      jobAgg       = jobs.aggregate as JobAgg;
      reqAgg       = reqs.aggregate as ReqAgg;
      byStrategy   = (jobs.by_strategy    as ByStrategy[])   ?? [];
      byFormat     = (jobs.by_format      as ByFormat[])     ?? [];
      byModel      = (jobs.by_model       as ByModel[])      ?? [];
      byEntityType = (jobs.by_entity_type as ByEntityType[]) ?? [];
      recentJobs   = (jobs.recent         as RecentJob[])    ?? [];
      byEndpoint   = (reqs.by_endpoint    as ByEndpoint[])   ?? [];
      percentiles  = (jobs.percentiles    as Percentiles)    ?? null;
      timeseries   = (jobs.timeseries     as TimePoint[])    ?? [];
    } catch (e) {
      error = (e as Error).message;
    } finally {
      loading = false;
    }
  });

  // ── Derived: throughput by format (sorted desc by throughput) ────────────────
  const tpByFormat = $derived(
    byFormat
      .filter((r) => (r.avg_throughput_bps ?? 0) > 0)
      .slice()
      .sort((a, b) => (b.avg_throughput_bps ?? 0) - (a.avg_throughput_bps ?? 0))
  );
  const maxTpFormat = $derived(tpByFormat.reduce((m, r) => Math.max(m, r.avg_throughput_bps ?? 0), 1));

  // ── Derived: throughput by strategy (sorted desc by throughput) ──────────────
  const tpByStrategy = $derived(
    byStrategy
      .filter((r) => (r.avg_throughput_bps ?? 0) > 0)
      .slice()
      .sort((a, b) => (b.avg_throughput_bps ?? 0) - (a.avg_throughput_bps ?? 0))
  );
  const maxTpStrategy = $derived(tpByStrategy.reduce((m, r) => Math.max(m, r.avg_throughput_bps ?? 0), 1));

  // ── Derived: entity mix (top 10 + others), donut geometry ────────────────────
  const entityTotal = $derived(byEntityType.reduce((s, r) => s + r.n, 0));
  const entityTop = $derived.by(() => {
    if (byEntityType.length <= 10) return byEntityType.map((r) => ({ ...r }));
    const top = byEntityType.slice(0, 9).map((r) => ({ ...r }));
    const restN = byEntityType.slice(9).reduce((s, r) => s + r.n, 0);
    return [...top, { entity: 'OTHER', n: restN }];
  });

  interface DonutSeg { entity: string; n: number; color: string; pct: number; path: string; }
  const donutSegs = $derived.by((): DonutSeg[] => {
    const total = entityTotal || 1;
    const R = 60, r = 36, cx = 70, cy = 70;
    let acc = 0;
    return entityTop.map((row, i) => {
      const frac = row.n / total;
      const a0 = acc * 2 * Math.PI - Math.PI / 2;
      acc += frac;
      const a1 = acc * 2 * Math.PI - Math.PI / 2;
      // Guard a full-circle single slice (avoid degenerate arc).
      const sweep = frac >= 0.9999 ? a1 - 0.0001 : a1;
      const x0 = cx + R * Math.cos(a0), y0 = cy + R * Math.sin(a0);
      const x1 = cx + R * Math.cos(sweep), y1 = cy + R * Math.sin(sweep);
      const ix0 = cx + r * Math.cos(a0), iy0 = cy + r * Math.sin(a0);
      const ix1 = cx + r * Math.cos(sweep), iy1 = cy + r * Math.sin(sweep);
      const large = frac > 0.5 ? 1 : 0;
      const path = `M ${x0} ${y0} A ${R} ${R} 0 ${large} 1 ${x1} ${y1} L ${ix1} ${iy1} A ${r} ${r} 0 ${large} 0 ${ix0} ${iy0} Z`;
      return {
        entity: row.entity,
        n: row.n,
        color: ENTITY_COLORS[i % ENTITY_COLORS.length],
        pct: frac * 100,
        path,
      };
    });
  });

  // ── Derived: time trend geometry ─────────────────────────────────────────────
  const TS_W = 640, TS_H = 200, TS_PAD_L = 8, TS_PAD_R = 8, TS_PAD_T = 16, TS_PAD_B = 28;
  const tsInner = { w: TS_W - TS_PAD_L - TS_PAD_R, h: TS_H - TS_PAD_T - TS_PAD_B };
  const maxTsN  = $derived(timeseries.reduce((m, p) => Math.max(m, p.n), 1));
  const maxTsTp = $derived(timeseries.reduce((m, p) => Math.max(m, p.avg_throughput_bps ?? 0), 1));
  function tsX(i: number): number {
    if (timeseries.length <= 1) return TS_PAD_L + tsInner.w / 2;
    return TS_PAD_L + (i / (timeseries.length - 1)) * tsInner.w;
  }
  function tsBarH(n: number): number { return (n / maxTsN) * tsInner.h; }
  function tsLineY(tp: number | null): number {
    const v = tp ?? 0;
    return TS_PAD_T + tsInner.h - (v / maxTsTp) * tsInner.h;
  }
  const tsLinePath = $derived.by(() => {
    if (timeseries.length === 0) return '';
    return timeseries
      .map((p, i) => `${i === 0 ? 'M' : 'L'} ${tsX(i).toFixed(1)} ${tsLineY(p.avg_throughput_bps).toFixed(1)}`)
      .join(' ');
  });

  // ── Derived: scatter geometry (file_b log-x, throughput y) ───────────────────
  const SC_W = 640, SC_H = 280, SC_PAD_L = 56, SC_PAD_R = 16, SC_PAD_T = 16, SC_PAD_B = 36;
  const scInner = { w: SC_W - SC_PAD_L - SC_PAD_R, h: SC_H - SC_PAD_T - SC_PAD_B };
  const scatterPts = $derived(
    recentJobs.filter((j) => (j.file_b ?? 0) > 0 && (j.throughput_bps ?? 0) > 0)
  );
  const scXDomain = $derived.by(() => {
    if (scatterPts.length === 0) return { lo: 0, hi: 1 };
    const xs = scatterPts.map((j) => Math.log10(j.file_b));
    return { lo: Math.min(...xs), hi: Math.max(...xs) };
  });
  const scYMax = $derived(scatterPts.reduce((m, j) => Math.max(m, j.throughput_bps), 1));
  function scX(fileB: number): number {
    const { lo, hi } = scXDomain;
    const span = hi - lo || 1;
    return SC_PAD_L + ((Math.log10(fileB) - lo) / span) * scInner.w;
  }
  function scY(tp: number): number {
    return SC_PAD_T + scInner.h - (tp / scYMax) * scInner.h;
  }
  // x-axis ticks at decade-ish points within the byte domain.
  const scXTicks = $derived.by(() => {
    const { lo, hi } = scXDomain;
    const ticks: { x: number; label: string }[] = [];
    const start = Math.floor(lo), end = Math.ceil(hi);
    for (let e = start; e <= end; e++) {
      const v = Math.pow(10, e);
      if (Math.log10(v) < lo - 0.01 || Math.log10(v) > hi + 0.01) continue;
      ticks.push({ x: scX(v), label: fmtBytes(v) });
    }
    return ticks;
  });
  const scYTicks = $derived.by(() => {
    const steps = 4;
    return Array.from({ length: steps + 1 }, (_, i) => {
      const v = (scYMax / steps) * i;
      return { y: scY(v), label: fmtThroughput(v) };
    });
  });
  // strategies present in the scatter, for the legend.
  const scatterStrats = $derived([...new Set(scatterPts.map((j) => j.strategy).filter(Boolean))]);

  // ── Derived: latency percentiles ─────────────────────────────────────────────
  const lat = $derived(percentiles?.ms ?? null);
  const latMax = $derived(Math.max(lat?.max ?? 0, lat?.p99 ?? 0, 1));
  function latX(ms: number | null): number {
    const w = 100;
    return ((ms ?? 0) / latMax) * w;
  }

  // KPI helpers
  const p95Latency = $derived.by(() => {
    const p = percentiles?.ms;
    if (!p || p.p90 == null || p.p99 == null) return null;
    // Interpolate p95 between p90 and p99 (no separate query needed).
    return p.p90 + (p.p99 - p.p90) * (5 / 9);
  });
</script>

<svelte:head><title>AnonShield: Metrics</title></svelte:head>

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
    <!-- ── KPI cards ── -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <span class="kpi-v" class:empty={(jobAgg?.n ?? 0) === 0}>{jobAgg?.n ?? 0}</span>
        <span class="kpi-l">{$t('metrics.kpi.jobs')}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-v" class:empty={(jobAgg?.total_entities ?? 0) === 0}>{fmt(jobAgg?.total_entities)}</span>
        <span class="kpi-l">{$t('metrics.kpi.entities')}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-v" class:empty={(jobAgg?.total_file_b ?? 0) === 0}>{fmtBytes(jobAgg?.total_file_b)}</span>
        <span class="kpi-l">{$t('metrics.kpi.data')}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-v" class:empty={(jobAgg?.avg_throughput_bps ?? 0) === 0}>{fmtThroughput(jobAgg?.avg_throughput_bps)}</span>
        <span class="kpi-l">{$t('metrics.kpi.throughput')}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-v" class:empty={(jobAgg?.avg_ms ?? 0) === 0}>{fmtMs(jobAgg?.avg_ms)}</span>
        <span class="kpi-l">{$t('metrics.kpi.avg_time')}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-v" class:empty={p95Latency == null}>{fmtMs(p95Latency)}</span>
        <span class="kpi-l">{$t('metrics.kpi.p95_latency')}</span>
      </div>
    </div>

    <!-- ── Throughput by format + by strategy ── -->
    <div class="charts-row">
      <!-- Throughput by file format -->
      <section class="card chart-card" aria-label={$t('metrics.chart.tp_format')}>
        <header class="chart-head">
          <h2 class="chart-title">{$t('metrics.chart.tp_format')}</h2>
          <p class="chart-sub">{$t('metrics.chart.tp_format_sub')}</p>
        </header>
        {#if tpByFormat.length === 0}
          <p class="no-data">{$t('metrics.empty.no_format')}</p>
        {:else}
          <div class="hbars" role="list">
            {#each tpByFormat as row, i (row.file_ext)}
              {@const color = EXT_COLORS[i % EXT_COLORS.length]}
              {@const w = (row.avg_throughput_bps / maxTpFormat) * 100}
              <div class="hbar" role="listitem">
                <span class="hbar-key">{(row.file_ext ?? '?').toUpperCase()}</span>
                <div class="hbar-track">
                  <div class="hbar-fill" style="--w:{w.toFixed(1)}%;--c:{color};--d:{i * 70}ms">
                    <title>{(row.file_ext ?? '?').toUpperCase()}: {fmtThroughput(row.avg_throughput_bps)} ({row.n} {row.n === 1 ? $t('metrics.unit.run') : $t('metrics.unit.runs')})</title>
                  </div>
                  <span class="hbar-val" style="color:{color}">{fmtThroughput(row.avg_throughput_bps)}</span>
                </div>
                <span class="hbar-meta">{row.n} {row.n === 1 ? $t('metrics.unit.run') : $t('metrics.unit.runs')}</span>
              </div>
            {/each}
          </div>
        {/if}
      </section>

      <!-- Throughput by strategy -->
      <section class="card chart-card" aria-label={$t('metrics.chart.tp_strategy')}>
        <header class="chart-head">
          <h2 class="chart-title">{$t('metrics.chart.tp_strategy')}</h2>
          <p class="chart-sub">{$t('metrics.chart.tp_strategy_sub')}</p>
        </header>
        {#if tpByStrategy.length === 0}
          <p class="no-data">{$t('metrics.empty.no_strategy')}</p>
        {:else}
          <div class="hbars" role="list">
            {#each tpByStrategy as row, i (row.strategy)}
              {@const color = stratColor(row.strategy)}
              {@const w = (row.avg_throughput_bps / maxTpStrategy) * 100}
              <div class="hbar" role="listitem">
                <span class="hbar-key" title={row.strategy}>{row.strategy}</span>
                <div class="hbar-track">
                  <div class="hbar-fill" style="--w:{w.toFixed(1)}%;--c:{color};--d:{i * 70}ms">
                    <title>{row.strategy}: {fmtThroughput(row.avg_throughput_bps)}, {row.n} {row.n === 1 ? $t('metrics.unit.run') : $t('metrics.unit.runs')}, {$t('metrics.col.avg')} {fmtMs(row.avg_ms)}</title>
                  </div>
                  <span class="hbar-val" style="color:{color}">{fmtThroughput(row.avg_throughput_bps)}</span>
                </div>
                <span class="hbar-meta">{row.n} {row.n === 1 ? $t('metrics.unit.run') : $t('metrics.unit.runs')}, {fmtMs(row.avg_ms)}</span>
              </div>
            {/each}
          </div>
        {/if}
      </section>
    </div>

    <!-- ── Jobs and throughput over time (full width) ── -->
    <section class="card chart-card" aria-label={$t('metrics.chart.trend')}>
      <header class="chart-head">
        <h2 class="chart-title">{$t('metrics.chart.trend')}</h2>
        <p class="chart-sub">{$t('metrics.chart.trend_sub')}</p>
      </header>
      {#if timeseries.length < 2}
        <p class="no-data">{$t('metrics.empty.no_trend')}</p>
      {:else}
        <div class="legend">
          <span class="legend-item"><span class="swatch swatch-bar"></span>{$t('metrics.legend.jobs')}</span>
          <span class="legend-item"><span class="swatch swatch-line"></span>{$t('metrics.legend.throughput')}</span>
        </div>
        <div class="svg-wrap">
          <svg viewBox="0 0 {TS_W} {TS_H}" preserveAspectRatio="none" class="chart-svg trend-svg"
               role="img" aria-label={$t('metrics.chart.trend')}>
            <!-- volume bars -->
            {#each timeseries as p, i (p.ts)}
              {@const bw = Math.max(2, (tsInner.w / timeseries.length) * 0.6)}
              {@const bh = tsBarH(p.n)}
              <rect x={(tsX(i) - bw / 2).toFixed(1)} y={(TS_PAD_T + tsInner.h - bh).toFixed(1)}
                    width={bw.toFixed(1)} height={bh.toFixed(1)} rx="1.5"
                    class="ts-bar" style="--d:{i * 30}ms">
                <title>{fmtTimeShort(p.ts)}: {p.n} {p.n === 1 ? $t('metrics.unit.run') : $t('metrics.unit.runs')}, {fmtThroughput(p.avg_throughput_bps)}</title>
              </rect>
            {/each}
            <!-- throughput line -->
            <path d={tsLinePath} class="ts-line" />
            {#each timeseries as p, i (p.ts)}
              <circle cx={tsX(i).toFixed(1)} cy={tsLineY(p.avg_throughput_bps).toFixed(1)} r="2.5" class="ts-dot">
                <title>{fmtTimeShort(p.ts)}: {fmtThroughput(p.avg_throughput_bps)}</title>
              </circle>
            {/each}
            <!-- baseline -->
            <line x1={TS_PAD_L} y1={TS_PAD_T + tsInner.h} x2={TS_W - TS_PAD_R} y2={TS_PAD_T + tsInner.h} class="axis-line" />
          </svg>
        </div>
        <div class="ts-xaxis">
          <span>{fmtTimeShort(timeseries[0].ts)}</span>
          <span>{fmtTimeShort(timeseries[timeseries.length - 1].ts)}</span>
        </div>
      {/if}
    </section>

    <!-- ── File size vs throughput scatter (full width) ── -->
    <section class="card chart-card" aria-label={$t('metrics.chart.scatter')}>
      <header class="chart-head">
        <h2 class="chart-title">{$t('metrics.chart.scatter')}</h2>
        <p class="chart-sub">{$t('metrics.chart.scatter_sub')}</p>
      </header>
      {#if scatterPts.length === 0}
        <p class="no-data">{$t('metrics.empty.no_scatter')}</p>
      {:else}
        {#if scatterStrats.length > 0}
          <div class="legend">
            {#each scatterStrats as s (s)}
              <span class="legend-item"><span class="swatch" style="background:{stratColor(s)}"></span>{s}</span>
            {/each}
          </div>
        {/if}
        <div class="svg-wrap">
          <svg viewBox="0 0 {SC_W} {SC_H}" class="chart-svg" role="img" aria-label={$t('metrics.chart.scatter')}>
            <!-- y gridlines + labels -->
            {#each scYTicks as tick (tick.label)}
              <line x1={SC_PAD_L} y1={tick.y.toFixed(1)} x2={SC_W - SC_PAD_R} y2={tick.y.toFixed(1)} class="grid-line" />
              <text x={SC_PAD_L - 6} y={(tick.y + 3).toFixed(1)} text-anchor="end" class="axis-text">{tick.label}</text>
            {/each}
            <!-- x ticks + labels -->
            {#each scXTicks as tick (tick.label)}
              <line x1={tick.x.toFixed(1)} y1={SC_PAD_T} x2={tick.x.toFixed(1)} y2={SC_PAD_T + scInner.h} class="grid-line faint" />
              <text x={tick.x.toFixed(1)} y={SC_H - SC_PAD_B + 16} text-anchor="middle" class="axis-text">{tick.label}</text>
            {/each}
            <!-- axis titles -->
            <text x={SC_PAD_L + scInner.w / 2} y={SC_H - 4} text-anchor="middle" class="axis-title">{$t('metrics.axis.size')}</text>
            <text x="12" y={SC_PAD_T + scInner.h / 2} text-anchor="middle" class="axis-title"
                  transform="rotate(-90 12 {(SC_PAD_T + scInner.h / 2).toFixed(1)})">{$t('metrics.axis.throughput')}</text>
            <!-- points -->
            {#each scatterPts as j, i (j.job_id + '_' + i)}
              <circle cx={scX(j.file_b).toFixed(1)} cy={scY(j.throughput_bps).toFixed(1)} r="4"
                      fill={stratColor(j.strategy)} fill-opacity="0.75"
                      stroke={stratColor(j.strategy)} stroke-opacity="0.95" class="sc-dot">
                <title>{(j.file_ext ?? '?').toUpperCase()} {j.strategy ? '(' + j.strategy + ')' : ''}: {fmtBytes(j.file_b)}, {fmtThroughput(j.throughput_bps)}, {fmtMs(j.ms)}</title>
              </circle>
            {/each}
          </svg>
        </div>
      {/if}
    </section>

    <!-- ── Entity mix (donut) + latency distribution ── -->
    <div class="charts-row">
      <!-- PII entity mix donut -->
      <section class="card chart-card" aria-label={$t('metrics.chart.entity_mix')}>
        <header class="chart-head">
          <h2 class="chart-title">{$t('metrics.chart.entity_mix')}</h2>
          <p class="chart-sub">{$t('metrics.chart.entity_mix_sub')}</p>
        </header>
        {#if byEntityType.length === 0}
          <p class="no-data">{$t('metrics.empty.no_entities')}</p>
        {:else}
          <div class="donut-wrap">
            <svg viewBox="0 0 140 140" class="donut-svg" role="img" aria-label={$t('metrics.chart.entity_mix')}>
              {#each donutSegs as seg (seg.entity)}
                <path d={seg.path} fill={seg.color} class="donut-seg">
                  <title>{entityLabel(seg.entity)}: {seg.n} ({seg.pct.toFixed(1)}% {$t('metrics.tip.of_total')})</title>
                </path>
              {/each}
              <text x="70" y="66" text-anchor="middle" class="donut-center-v">{fmt(entityTotal)}</text>
              <text x="70" y="82" text-anchor="middle" class="donut-center-l">{$t('metrics.kpi.entities')}</text>
            </svg>
            <ul class="donut-legend">
              {#each donutSegs as seg (seg.entity)}
                <li>
                  <span class="swatch" style="background:{seg.color}"></span>
                  <span class="legend-key">{entityLabel(seg.entity)}</span>
                  <span class="legend-n">{seg.n}</span>
                  <span class="legend-pct">{seg.pct.toFixed(0)}%</span>
                </li>
              {/each}
            </ul>
          </div>
        {/if}
      </section>

      <!-- Latency distribution -->
      <section class="card chart-card" aria-label={$t('metrics.chart.latency')}>
        <header class="chart-head">
          <h2 class="chart-title">{$t('metrics.chart.latency')}</h2>
          <p class="chart-sub">{$t('metrics.chart.latency_sub')}</p>
        </header>
        {#if !lat || lat.n === 0 || lat.p50 == null}
          <p class="no-data">{$t('metrics.empty.no_latency')}</p>
        {:else}
          <div class="lat-ruler" role="img"
               aria-label="{$t('metrics.stat.median')} {fmtMs(lat.p50)}, {$t('metrics.stat.p90')} {fmtMs(lat.p90)}, {$t('metrics.stat.p99')} {fmtMs(lat.p99)}">
            <div class="lat-track">
              <!-- range fill from min to p99 -->
              <div class="lat-range" style="left:{latX(lat.min)}%;width:{(latX(lat.p99) - latX(lat.min)).toFixed(1)}%"></div>
              {#each [ ['p50', lat.p50, '#6366f1'], ['p90', lat.p90, '#fbbf24'], ['p99', lat.p99, '#f87171'] ] as [key, val, color] (key)}
                <div class="lat-mark" style="left:{latX(val as number)}%;--c:{color}">
                  <span class="lat-flag" style="--c:{color}">
                    {key === 'p50' ? $t('metrics.stat.median') : key === 'p90' ? $t('metrics.stat.p90') : $t('metrics.stat.p99')}
                  </span>
                  <span class="lat-tick" style="--c:{color}"></span>
                </div>
              {/each}
            </div>
            <div class="lat-axis">
              <span>{fmtMs(lat.min)}</span>
              <span>{fmtMs(lat.max)}</span>
            </div>
          </div>
          <div class="lat-stats">
            <div class="lat-stat"><span class="lat-stat-l">{$t('metrics.stat.fastest')}</span><span class="lat-stat-v">{fmtMs(lat.min)}</span></div>
            <div class="lat-stat"><span class="lat-stat-l">{$t('metrics.stat.median')}</span><span class="lat-stat-v">{fmtMs(lat.p50)}</span></div>
            <div class="lat-stat"><span class="lat-stat-l">{$t('metrics.stat.p90')}</span><span class="lat-stat-v">{fmtMs(lat.p90)}</span></div>
            <div class="lat-stat"><span class="lat-stat-l">{$t('metrics.stat.p99')}</span><span class="lat-stat-v">{fmtMs(lat.p99)}</span></div>
            <div class="lat-stat"><span class="lat-stat-l">{$t('metrics.stat.slowest')}</span><span class="lat-stat-v">{fmtMs(lat.max)}</span></div>
          </div>
        {/if}
      </section>
    </div>

    <!-- ── Volume breakdowns: by NER model + entity type bars ── -->
    <div class="charts-row">
      <section class="card chart-card" aria-label={$t('metrics.chart.model')}>
        <header class="chart-head">
          <h2 class="chart-title">{$t('metrics.chart.model')}</h2>
        </header>
        {#if byModel.length === 0}
          <p class="no-data">{$t('metrics.empty.no_model')}</p>
        {:else}
          {@const maxModel = byModel.reduce((m, r) => Math.max(m, r.n), 1)}
          <div class="hbars" role="list">
            {#each byModel as row, i (row.model)}
              {@const w = (row.n / maxModel) * 100}
              <div class="hbar" role="listitem">
                <span class="hbar-key" title={row.model}>{shortModel(row.model)}</span>
                <div class="hbar-track">
                  <div class="hbar-fill" style="--w:{w.toFixed(1)}%;--c:#c084fc;--d:{i * 70}ms">
                    <title>{shortModel(row.model)}: {row.n} {row.n === 1 ? $t('metrics.unit.run') : $t('metrics.unit.runs')}, {fmtMs(row.avg_ms)}</title>
                  </div>
                  <span class="hbar-val" style="color:#c084fc">{row.n}</span>
                </div>
                <span class="hbar-meta">{fmtMs(row.avg_ms)}</span>
              </div>
            {/each}
          </div>
        {/if}
      </section>

      <section class="card chart-card" aria-label={$t('metrics.chart.entities')}>
        <header class="chart-head">
          <h2 class="chart-title">{$t('metrics.chart.entities')}</h2>
        </header>
        {#if byEntityType.length === 0}
          <p class="no-data">{$t('metrics.empty.no_entities')}</p>
        {:else}
          {@const maxEntity = byEntityType.reduce((m, r) => Math.max(m, r.n), 1)}
          <div class="hbars" role="list">
            {#each byEntityType.slice(0, 12) as row, i (row.entity)}
              {@const color = ENTITY_COLORS[i % ENTITY_COLORS.length]}
              {@const w = (row.n / maxEntity) * 100}
              <div class="hbar" role="listitem">
                <span class="hbar-key">{entityLabel(row.entity)}</span>
                <div class="hbar-track">
                  <div class="hbar-fill" style="--w:{w.toFixed(1)}%;--c:{color};--d:{i * 50}ms">
                    <title>{entityLabel(row.entity)}: {row.n}</title>
                  </div>
                  <span class="hbar-val" style="color:{color}">{row.n}</span>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </section>
    </div>

    <!-- ── Recent jobs ── -->
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
              {#each recentJobs as j (j.job_id + '_' + j.ts)}
                <tr>
                  <td class="mono dim">{fmtDate(j.ts)}</td>
                  <td><span class="ext-badge">{(j.file_ext ?? '?').toUpperCase()}</span></td>
                  <td><span class="strat-badge" style="--c:{stratColor(j.strategy)}">{j.strategy ?? '-'}</span></td>
                  <td class="mono dim" title={j.model ?? ''}>{j.model ? shortModel(j.model) : '-'}</td>
                  <td class="mono">{j.lang ?? '-'}</td>
                  <td class="mono">{fmtBytes(j.file_b)}</td>
                  <td class="mono accent">{j.entity_cnt ?? '-'}</td>
                  <td class="mono">{fmtMs(j.ms)}</td>
                  <td class="mono">{fmtThroughput(j.throughput_bps)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>

    <!-- ── API endpoints ── -->
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
              {#each byEndpoint as ep (ep.method + ep.path)}
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

  /* ── KPI grid ── */
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: var(--space-3);
  }
  @media (max-width: 900px) { .kpi-grid { grid-template-columns: repeat(3, 1fr); } }
  @media (max-width: 560px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }
  .kpi-card {
    display: flex; flex-direction: column; gap: var(--space-1);
    padding: var(--space-5) var(--space-4) var(--space-4);
    border: 1px solid var(--color-border); border-radius: var(--radius-md);
    background: var(--color-surface-raised);
    animation: fade-up 420ms var(--ease-out) both;
  }
  .kpi-v {
    font-size: 1.75rem; font-weight: 900; letter-spacing: -0.04em;
    color: var(--color-text-primary); font-variant-numeric: tabular-nums;
    line-height: 1; white-space: nowrap;
  }
  .kpi-v.empty { color: var(--color-text-secondary); font-size: var(--text-2xl); }
  .kpi-l {
    margin-top: var(--space-2);
    font-size: var(--text-xs); text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--color-text-secondary); font-weight: 600;
  }

  /* ── Chart layout ── */
  .charts-row {
    display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-4);
  }
  @media (max-width: 820px) { .charts-row { grid-template-columns: 1fr; } }

  .chart-card {
    display: flex; flex-direction: column; gap: var(--space-4); padding: var(--space-6);
    animation: fade-up 480ms var(--ease-out) both;
  }
  .chart-head { display: flex; flex-direction: column; gap: var(--space-1); }
  .chart-title {
    margin: 0; font-size: var(--text-xs); font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--color-text-secondary);
  }
  .chart-sub { margin: 0; font-size: var(--text-xs); color: var(--color-text-secondary); opacity: 0.7; }
  .no-data { margin: 0; font-size: var(--text-sm); color: var(--color-text-secondary); }

  /* ── Horizontal value bars (throughput / counts) ── */
  .hbars { display: flex; flex-direction: column; gap: var(--space-3); }
  .hbar {
    display: grid; grid-template-columns: 84px 1fr auto; align-items: center;
    gap: var(--space-3);
  }
  .hbar-key {
    font-size: var(--text-xs); font-family: var(--font-mono); font-weight: 600;
    color: var(--color-text-secondary); white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis;
  }
  .hbar-track {
    position: relative; height: 22px; border-radius: var(--radius-sm);
    background: color-mix(in srgb, var(--color-border) 60%, transparent);
    overflow: hidden; display: flex; align-items: center;
  }
  .hbar-fill {
    height: 100%; border-radius: var(--radius-sm);
    background: linear-gradient(90deg, color-mix(in srgb, var(--c) 78%, transparent), var(--c));
    width: 0; animation: grow-bar 700ms cubic-bezier(0.16,1,0.3,1) forwards;
    animation-delay: var(--d, 0ms);
  }
  .hbar-val {
    position: absolute; right: var(--space-2);
    font-size: var(--text-xs); font-weight: 700; font-family: var(--font-mono);
    font-variant-numeric: tabular-nums; text-shadow: 0 1px 2px rgba(0,0,0,0.6);
  }
  .hbar-meta {
    font-size: var(--text-xs); font-family: var(--font-mono);
    color: var(--color-text-secondary); white-space: nowrap; opacity: 0.8;
  }
  @keyframes grow-bar { to { width: var(--w); } }

  /* ── Generic SVG chart frame ── */
  .svg-wrap { width: 100%; }
  .chart-svg { width: 100%; height: auto; display: block; overflow: visible; }
  .trend-svg { height: 200px; }
  .axis-line { stroke: var(--color-border-strong); stroke-width: 1; }
  .grid-line { stroke: var(--color-border); stroke-width: 1; }
  .grid-line.faint { stroke: color-mix(in srgb, var(--color-border) 55%, transparent); }
  .axis-text { fill: var(--color-text-secondary); font-size: 9px; font-family: var(--font-mono); }
  .axis-title { fill: var(--color-text-secondary); font-size: 10px; font-weight: 600; letter-spacing: 0.04em; }

  /* trend chart */
  .ts-bar {
    fill: color-mix(in srgb, var(--color-accent) 45%, transparent);
    transform-origin: bottom; transform-box: fill-box;
    animation: grow-y 600ms var(--ease-out) both; animation-delay: var(--d, 0ms);
  }
  .ts-line { fill: none; stroke: #34d399; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
  .ts-dot { fill: #34d399; stroke: var(--color-surface-raised); stroke-width: 1; }
  @keyframes grow-y { from { transform: scaleY(0); } to { transform: scaleY(1); } }
  .ts-xaxis {
    display: flex; justify-content: space-between;
    font-size: var(--text-xs); font-family: var(--font-mono);
    color: var(--color-text-secondary); margin-top: calc(-1 * var(--space-2));
  }

  /* scatter */
  .sc-dot { transition: r 120ms var(--ease-out); cursor: crosshair; }
  .sc-dot:hover { r: 6; fill-opacity: 1; }

  /* ── Legend ── */
  .legend { display: flex; flex-wrap: wrap; gap: var(--space-3) var(--space-4); }
  .legend-item {
    display: inline-flex; align-items: center; gap: var(--space-2);
    font-size: var(--text-xs); font-family: var(--font-mono); color: var(--color-text-secondary);
  }
  .swatch { width: 10px; height: 10px; border-radius: 3px; flex-shrink: 0; }
  .swatch-bar { background: color-mix(in srgb, var(--color-accent) 45%, transparent); }
  .swatch-line { background: #34d399; height: 3px; border-radius: 2px; width: 14px; }

  /* ── Donut ── */
  .donut-wrap { display: flex; align-items: center; gap: var(--space-6); flex-wrap: wrap; }
  .donut-svg { width: 140px; height: 140px; flex-shrink: 0; }
  .donut-seg { transition: opacity 120ms var(--ease-out); transform-origin: 70px 70px; animation: fade-in 500ms var(--ease-out) both; }
  .donut-seg:hover { opacity: 0.82; }
  .donut-center-v { fill: var(--color-text-primary); font-size: 18px; font-weight: 800; font-variant-numeric: tabular-nums; }
  .donut-center-l { fill: var(--color-text-secondary); font-size: 8px; text-transform: uppercase; letter-spacing: 0.08em; }
  .donut-legend {
    list-style: none; margin: 0; padding: 0;
    display: flex; flex-direction: column; gap: var(--space-2); flex: 1; min-width: 180px;
  }
  .donut-legend li {
    display: grid; grid-template-columns: 12px 1fr auto auto; align-items: center;
    gap: var(--space-2); font-size: var(--text-xs); font-family: var(--font-mono);
  }
  .legend-key { color: var(--color-text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .legend-n { color: var(--color-text-primary); font-weight: 700; font-variant-numeric: tabular-nums; }
  .legend-pct { color: var(--color-text-secondary); opacity: 0.7; min-width: 32px; text-align: right; }

  /* ── Latency ruler ── */
  .lat-ruler { display: flex; flex-direction: column; gap: var(--space-2); padding-top: var(--space-5); }
  .lat-track {
    position: relative; height: 10px; border-radius: var(--radius-sm);
    background: color-mix(in srgb, var(--color-border) 60%, transparent);
  }
  .lat-range {
    position: absolute; top: 0; height: 100%; border-radius: var(--radius-sm);
    background: linear-gradient(90deg,
      color-mix(in srgb, #6366f1 35%, transparent),
      color-mix(in srgb, #f87171 35%, transparent));
  }
  .lat-mark { position: absolute; top: -4px; height: 18px; transform: translateX(-50%); }
  .lat-tick {
    display: block; width: 2px; height: 18px; margin: 0 auto;
    background: var(--c); border-radius: 1px;
  }
  .lat-flag {
    position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%);
    margin-bottom: 3px; font-size: 9px; font-family: var(--font-mono); font-weight: 700;
    color: var(--c); white-space: nowrap;
  }
  .lat-axis {
    display: flex; justify-content: space-between;
    font-size: var(--text-xs); font-family: var(--font-mono); color: var(--color-text-secondary);
  }
  .lat-stats {
    display: grid; grid-template-columns: repeat(5, 1fr); gap: var(--space-2);
    margin-top: var(--space-2);
  }
  .lat-stat {
    display: flex; flex-direction: column; gap: 2px; align-items: center;
    padding: var(--space-2); border-radius: var(--radius-sm);
    background: color-mix(in srgb, var(--color-border) 35%, transparent);
  }
  .lat-stat-l { font-size: 9px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-text-secondary); }
  .lat-stat-v { font-size: var(--text-xs); font-family: var(--font-mono); font-weight: 700; color: var(--color-text-primary); }

  /* ── Tables ── */
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

  /* ── Loading / error ── */
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
  @keyframes fade-up { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
  @keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }

  @media (prefers-reduced-motion: reduce) {
    .kpi-card, .chart-card, .hbar-fill, .ts-bar, .donut-seg { animation: none; }
    .hbar-fill { width: var(--w); }
    .ts-bar { transform: none; }
  }
</style>

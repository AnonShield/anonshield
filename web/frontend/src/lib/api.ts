/**
 * Typed API client for AnonShield Web backend.
 * All requests go to PUBLIC_API_URL (set via env at build time).
 */
import { PUBLIC_API_URL } from '$env/static/public';

const BASE = PUBLIC_API_URL ?? '/api';

export interface EntityItem {
  id: string;
  label: string;
  example: string;
}

export interface EntityGroup {
  label: string;
  entities: EntityItem[];
}

export interface EntitiesResponse {
  groups: EntityGroup[];
  strategy: string;
  model: string;
}

export interface JobCreatedResponse {
  job_id: string;
  status: string;
  queue: string;
}

export interface JobStatus {
  status: 'queued' | 'running' | 'done' | 'error' | 'downloaded';
  progress?: number;
  eta_seconds?: number;
  output_size_bytes?: number;
  message?: string;
  result?: Record<string, unknown>;
}

export interface ProfileValidation {
  valid: boolean;
  entities_count?: number;
  patterns_count?: number;
  error?: string;
}

// ── Entity list ──────────────────────────────────────────────────────────────

export async function fetchEntities(
  strategy = 'filtered',
  model = 'Davlan/xlm-roberta-base-ner-hrl',
  lang = 'en'
): Promise<EntitiesResponse> {
  const url = `${BASE}/entities?strategy=${strategy}&model=${encodeURIComponent(model)}&lang=${lang}`;
  const r = await fetch(url);
  if (!r.ok) throw new Error(`Failed to fetch entities: ${r.status}`);
  return r.json();
}

// ── Job lifecycle ─────────────────────────────────────────────────────────────

export async function createJob(
  file: File,
  opts: {
    key?: string;
    strategy?: string;
    lang?: string;
    entities?: string[];
    config?: string;
    ocr_engine?: string;
    ocr_preprocess?: string[];
    anonymization_config?: Record<string, unknown> | null;
  } = {}
): Promise<JobCreatedResponse> {
  const fd = new FormData();
  fd.append('file', file);
  if (opts.key)        fd.append('key', opts.key);
  if (opts.strategy)   fd.append('strategy', opts.strategy);
  if (opts.lang)       fd.append('lang', opts.lang);
  if (opts.entities !== undefined) fd.append('entities', JSON.stringify(opts.entities));
  if (opts.config)     fd.append('config', opts.config);
  if (opts.ocr_engine && opts.ocr_engine !== 'tesseract')
                       fd.append('ocr_engine', opts.ocr_engine);
  if (opts.ocr_preprocess && opts.ocr_preprocess.length > 0)
                       fd.append('ocr_preprocess', JSON.stringify(opts.ocr_preprocess));
  if (opts.anonymization_config) fd.append('fields', JSON.stringify(opts.anonymization_config));

  const r = await fetch(`${BASE}/jobs`, { method: 'POST', body: fd });
  if (r.status === 413) throw new Error('FILE_TOO_LARGE');
  if (r.status === 507) throw new Error('INSUFFICIENT_STORAGE');
  if (!r.ok) throw new Error(`Job creation failed: ${r.status}`);
  return r.json();
}

export async function pollStatus(jobId: string): Promise<JobStatus> {
  const r = await fetch(`${BASE}/jobs/${jobId}/status`);
  if (!r.ok) throw new Error(`Status check failed: ${r.status}`);
  return r.json();
}

export function downloadUrl(jobId: string): string {
  return `${BASE}/jobs/${jobId}/download`;
}

export async function cancelJob(jobId: string): Promise<void> {
  await fetch(`${BASE}/jobs/${jobId}`, { method: 'DELETE' });
}

// ── Metrics ───────────────────────────────────────────────────────────────────

export async function fetchMetrics(): Promise<Record<string, unknown>> {
  const r = await fetch(`${BASE}/metrics`);
  if (!r.ok) throw new Error(`Metrics unavailable: ${r.status}`);
  return r.json();
}

// ── Profile validation ────────────────────────────────────────────────────────

export async function validateProfile(yaml: string): Promise<ProfileValidation> {
  const r = await fetch(`${BASE}/profiles/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: yaml }),
  });
  if (!r.ok) throw new Error(`Validation request failed: ${r.status}`);
  return r.json();
}

// ── OCR benchmark dashboard ───────────────────────────────────────────────────
// NOTE: thin wrappers over /api/benchmark/ocr/* (reconstructed; src/lib was lost
// to a stray `lib/` .gitignore rule). Backend: web/backend/routers/ocr_benchmark.py

export interface BenchmarkSummaryRow {
  engine: string;
  preprocess: string;
  n_docs: number;
  mean_cer: number;
  mean_wer: number;
  macro_field_f1: number;
  mean_latency_s: number;
  in_progress?: boolean;
}

export interface BenchmarkSummary {
  rows: BenchmarkSummaryRow[];
  preprocess_steps: string[];
  engines: string[];
}

export interface BenchmarkDoc {
  doc_id: string;
  engine?: string;
  cer?: number;
  wer?: number;
  latency_s?: number;
  field_f1?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface BenchmarkDocDetail {
  [key: string]: unknown;
}

export async function fetchBenchmarkSummary(): Promise<BenchmarkSummary> {
  const r = await fetch(`${BASE}/benchmark/ocr/summary`);
  if (!r.ok) throw new Error(`Benchmark summary unavailable: ${r.status}`);
  return r.json();
}

export async function fetchBenchmarkDocs(preprocess: string, engine?: string): Promise<BenchmarkDoc[]> {
  const q = engine ? `?engine=${encodeURIComponent(engine)}` : '';
  const r = await fetch(`${BASE}/benchmark/ocr/${encodeURIComponent(preprocess)}/docs${q}`);
  if (!r.ok) throw new Error(`Benchmark docs unavailable: ${r.status}`);
  return r.json();
}

export async function fetchBenchmarkDoc(preprocess: string, docId: string): Promise<BenchmarkDocDetail> {
  const r = await fetch(`${BASE}/benchmark/ocr/${encodeURIComponent(preprocess)}/docs/${encodeURIComponent(docId)}`);
  if (!r.ok) throw new Error(`Benchmark doc unavailable: ${r.status}`);
  return r.json();
}

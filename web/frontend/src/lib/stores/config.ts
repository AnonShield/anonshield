/**
 * Anonymization configuration store.
 * selected_entities: null = all (no filter); Set = explicit selection; empty Set = none.
 */
import { writable } from 'svelte/store';
import type { EntityGroup } from '$lib/api';
import * as yaml from 'js-yaml';

export interface CustomPattern {
  entity_type: string;
  pattern: string;
  score: number;
}

export interface AnonymizationConfig {
  force_anonymize?: Record<string, { entity_type: string }>;
  fields_to_anonymize?: string[];
  fields_to_exclude?: string[];
}

export interface Config {
  strategy: string;
  lang: string;
  model: string;
  slug_length: number;
  ocr_engine: string;
  /** Named preset (none | scan | photo | fax) or 'custom' for manual step selection */
  ocr_preprocess_preset: string;
  /** Individual step overrides when preset is 'custom' */
  ocr_preprocess: string[];
  /** null = all entities (no filter); Set = explicit list; empty Set = none */
  selected_entities: Set<string> | null;
  /** Structural rules for structured files (CSV/JSON/XLSX) */
  anonymization_config: AnonymizationConfig | null;
  custom_patterns: CustomPattern[];
  key: string;
}

const DEFAULTS: Config = {
  strategy: 'filtered',
  lang: 'en',
  model: 'Davlan/xlm-roberta-base-ner-hrl',
  slug_length: 8,
  ocr_engine: 'tesseract',
  ocr_preprocess_preset: 'none',
  ocr_preprocess: [],
  selected_entities: null,
  anonymization_config: null,
  custom_patterns: [],
  key: '',
};

export const config = writable<Config>({ ...DEFAULTS });

export function resetConfig() {
  config.set({ ...DEFAULTS, selected_entities: null });
}

/** Serialize config to YAML profile string (compatible with CLI --config). */
export function toYaml(cfg: Config, allGroups: EntityGroup[]): string {
  const allIds = allGroups.flatMap(g => g.entities.map(e => e.id));
  // null  → all selected (no filter) → use allIds
  // Set() → none selected            → []
  // Set(…)→ specific selection       → [...ids]
  const entities = cfg.selected_entities === null ? allIds : [...cfg.selected_entities];

  const data: Record<string, unknown> = {
    strategy: cfg.strategy,
    lang: cfg.lang,
    slug_length: cfg.slug_length,
    entities,
  };

  if (cfg.model && cfg.model !== DEFAULTS.model) {
    data['transformer_model'] = cfg.model;
  }

  if (cfg.ocr_engine && cfg.ocr_engine !== 'tesseract') {
    data['ocr_engine'] = cfg.ocr_engine;
  }

  const effectiveSteps = cfg.ocr_preprocess_preset !== 'none' && cfg.ocr_preprocess_preset !== 'custom'
    ? undefined  // preset is resolved server-side; no need to expand here
    : cfg.ocr_preprocess.length > 0 ? cfg.ocr_preprocess : undefined;
  if (cfg.ocr_preprocess_preset !== 'none') {
    data['ocr_preprocess_preset'] = cfg.ocr_preprocess_preset;
  }
  if (effectiveSteps) {
    data['ocr_preprocess'] = effectiveSteps;
  }

  if (cfg.anonymization_config) {
    data['anonymization_config'] = cfg.anonymization_config;
  }

  if (cfg.custom_patterns.length > 0) {
    data['custom_patterns'] = cfg.custom_patterns;
  }

  return yaml.dump(data, { lineWidth: 120 });
}

/** Load a YAML profile into the config store. */
export function fromYaml(raw: string): void {
  const data = yaml.load(raw) as Record<string, unknown>;
  const entityList = data['entities'] as string[] | undefined;
  const anonConfig = (data['anonymization_config'] || data['fields']) as AnonymizationConfig | string[] | undefined;

  config.update(c => {
    let finalAnonConfig: AnonymizationConfig | null = null;
    if (Array.isArray(anonConfig)) {
      // Migrate old 'fields' array to new structural config
      finalAnonConfig = { fields_to_anonymize: anonConfig };
    } else if (anonConfig && typeof anonConfig === 'object') {
      finalAnonConfig = anonConfig;
    }

    return {
      ...c,
      strategy: (data['strategy'] as string) ?? c.strategy,
      lang: (data['lang'] as string) ?? c.lang,
      slug_length: (data['slug_length'] as number) ?? c.slug_length,
      model: (data['transformer_model'] as string) ?? c.model,
      ocr_engine: (data['ocr_engine'] as string) ?? c.ocr_engine,
      ocr_preprocess_preset: (data['ocr_preprocess_preset'] as string) ?? 'none',
      ocr_preprocess: (data['ocr_preprocess'] as string[]) ?? [],
      selected_entities: entityList ? new Set(entityList) : null,
      anonymization_config: finalAnonConfig,
      custom_patterns: (data['custom_patterns'] as CustomPattern[]) ?? [],
    };
  });
}

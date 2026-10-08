/**
 * Anonymization configuration store.
 * selected_entities: null = all (no filter); Set = explicit selection; empty Set = none.
 */
import { writable } from 'svelte/store';
import type { EntityGroup } from '#lib/api.js';
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
  ner_score_threshold?: number;
  ner_aggregation_strategy?: string;
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
  allow_list: string[];
  preserve_entities: string[];
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
  allow_list: [],
  preserve_entities: [],
  key: '',
};

export const config = writable<Config>({ ...DEFAULTS });

export function resetConfig() {
  config.set({ ...DEFAULTS, selected_entities: null });
}

/** The entity types to anonymize: undefined for all of them, otherwise the
 *  selection plus the types of the custom patterns. Those are not in the entity
 *  list, so they cannot be unchecked there; left out, the server skipped the
 *  pattern and its matches stayed in clear text. */
export function selectedTypes(cfg: Config): string[] | undefined {
  if (cfg.selected_entities === null) return undefined;
  return [...new Set([...cfg.selected_entities, ...cfg.custom_patterns.map(p => p.entity_type.toUpperCase())])];
}

/** Serialize config to YAML profile string (compatible with CLI --config). */
export function toYaml(cfg: Config, allGroups: EntityGroup[]): string {
  const allIds = [...new Set([...allGroups.flatMap(g => g.entities.map(e => e.id)), ...cfg.custom_patterns.map(p => p.entity_type.toUpperCase())])];
  const entities = selectedTypes(cfg) ?? allIds;

  const data: Record<string, unknown> = {
    strategy: cfg.strategy,
    lang: cfg.lang,
    slug_length: cfg.slug_length,
    entities,
  };

  if (cfg.ner_score_threshold !== undefined) data.ner_score_threshold = cfg.ner_score_threshold;
  if (cfg.ner_aggregation_strategy) data.ner_aggregation_strategy = cfg.ner_aggregation_strategy;
  if (cfg.allow_list.length) data.allow_list = cfg.allow_list;
  if (cfg.preserve_entities.length) data.preserve_entities = cfg.preserve_entities;

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

/** Strategies removed after they proved equivalent to another, and the one
 *  that replaces them (src/anon/strategy_names.py); old profiles still load. */
const RETIRED_STRATEGIES: Record<string, string> = { hybrid: 'filtered' };

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
      strategy: RETIRED_STRATEGIES[data['strategy'] as string] ?? (data['strategy'] as string) ?? c.strategy,
      lang: (data['lang'] as string) ?? c.lang,
      slug_length: (data['slug_length'] as number) ?? c.slug_length,
      ner_score_threshold: data['ner_score_threshold'] as number | undefined,
      ner_aggregation_strategy: data['ner_aggregation_strategy'] as string | undefined,
      model: (data['transformer_model'] as string) ?? c.model,
      ocr_engine: (data['ocr_engine'] as string) ?? c.ocr_engine,
      ocr_preprocess_preset: (data['ocr_preprocess_preset'] as string) ?? 'none',
      ocr_preprocess: (data['ocr_preprocess'] as string[]) ?? [],
      selected_entities: entityList ? new Set(entityList) : null,
      anonymization_config: finalAnonConfig,
      custom_patterns: (data['custom_patterns'] as CustomPattern[]) ?? [],
      allow_list: (data['allow_list'] as string[]) ?? [],
      preserve_entities: (data['preserve_entities'] as string[]) ?? [],
    };
  });
}

/**
 * The options of a job request, from the settings on screen. The single-file
 * and the batch submit both use it, so they always send the same request.
 */
import { selectedTypes, toYaml, type Config } from '#lib/stores/config.js';
import type { EntityGroup } from '#lib/api.js';

export function jobOptions(cfg: Config, groups: EntityGroup[]) {
  const profile = cfg.custom_patterns.length > 0 || cfg.allow_list.length > 0 || cfg.preserve_entities.length > 0;
  return {
    key: cfg.key || undefined,
    strategy: cfg.strategy,
    lang: cfg.lang,
    model: cfg.model || undefined,
    entities: selectedTypes(cfg),
    config: profile ? toYaml(cfg, groups) : undefined,
    anonymization_config: cfg.anonymization_config,
    ner_score_threshold: cfg.ner_score_threshold,
    ner_aggregation_strategy: cfg.ner_aggregation_strategy,
    slug_length: cfg.slug_length,
  };
}

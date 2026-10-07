import { beforeEach, describe, expect, it } from 'vitest';
import { get } from 'svelte/store';
import { config, fromYaml, resetConfig, toYaml } from '#lib/stores/config.js';
import type { EntityGroup } from '#lib/api.js';

const groups: EntityGroup[] = [{ label: 'Net', entities: [
  { id: 'IP_ADDRESS', label: 'IP', example: '' }, { id: 'EMAIL_ADDRESS', label: 'Email', example: '' }] }];

describe('profiles (Save / Load profile)', () => {
  beforeEach(() => resetConfig());

  it('loads back what was saved', () => {
    config.update(c => ({
      ...c, strategy: 'regex', lang: 'pt', slug_length: 12, ner_score_threshold: 0.4, ner_aggregation_strategy: 'simple',
      selected_entities: new Set(['EMAIL_ADDRESS']),
      custom_patterns: [{ entity_type: 'TICKET_ID', pattern: 'TICKET-\\d+', score: 0.9 }],
      allow_list: ['localhost'],
      anonymization_config: { force_anonymize: { 'asset.host_name': { entity_type: 'HOSTNAME' } }, fields_to_anonymize: ['asset'], fields_to_exclude: [] },
    }));
    const saved = toYaml(get(config), groups);
    const before = get(config);
    resetConfig();
    fromYaml(saved);
    const after = get(config);
    for (const k of ['strategy', 'lang', 'slug_length', 'ner_score_threshold', 'ner_aggregation_strategy',
                     'custom_patterns', 'allow_list', 'anonymization_config'] as const)
      expect(after[k], k).toEqual(before[k]);
    // the pattern's type travels with the subset, so the command line applies it too
    expect([...after.selected_entities!]).toEqual(['EMAIL_ADDRESS', 'TICKET_ID']);
  });

  it('saves "all types" as the full list and loads a profile without a list as all types', () => {
    expect(toYaml(get(config), groups)).toContain('- IP_ADDRESS');
    fromYaml('strategy: regex\n');
    expect(get(config).selected_entities).toBeNull();
  });

  it('reads the old "fields" list as fields to anonymize', () => {
    fromYaml('fields: [name, email]\n');
    expect(get(config).anonymization_config).toEqual({ fields_to_anonymize: ['name', 'email'] });
  });
});

import { describe, expect, it } from 'vitest';
import { jobOptions } from '#lib/jobRequest.js';
import { selectedTypes, toYaml, type Config } from '#lib/stores/config.js';
import type { EntityGroup } from '#lib/api.js';
import * as yaml from 'js-yaml';

const base: Config = {
  strategy: 'regex', lang: 'en', model: 'Davlan/xlm-roberta-base-ner-hrl', slug_length: 8,
  ocr_engine: 'tesseract', ocr_preprocess_preset: 'none', ocr_preprocess: [],
  selected_entities: null, anonymization_config: null,
  custom_patterns: [], allow_list: [], preserve_entities: [], key: '',
};
const groups: EntityGroup[] = [{ label: 'Network', entities: [
  { id: 'IP_ADDRESS', label: 'IP', example: '10.0.0.1' }, { id: 'EMAIL_ADDRESS', label: 'Email', example: 'a@b.org' }] }];
const account = { entity_type: 'account_id', pattern: 'ACC-\\d{5}', score: 0.9 };

describe('entity types sent with a job', () => {
  it('sends no list when every type is selected', () => {
    expect(selectedTypes(base)).toBeUndefined();
    expect(jobOptions({ ...base, custom_patterns: [account] }, groups).entities).toBeUndefined();
  });

  it('adds the custom pattern types to a subset (they used to be skipped by the server)', () => {
    const cfg = { ...base, selected_entities: new Set(['EMAIL_ADDRESS']), custom_patterns: [account] };
    expect(jobOptions(cfg, groups).entities).toEqual(['EMAIL_ADDRESS', 'ACCOUNT_ID']);
  });

  it('keeps "none selected" meaning none, except the patterns the user added', () => {
    expect(selectedTypes({ ...base, selected_entities: new Set() })).toEqual([]);
    expect(selectedTypes({ ...base, selected_entities: new Set(), custom_patterns: [account] })).toEqual(['ACCOUNT_ID']);
  });

  it('does not repeat a type that is both selected and a pattern', () => {
    const cfg = { ...base, selected_entities: new Set(['ACCOUNT_ID']), custom_patterns: [account] };
    expect(selectedTypes(cfg)).toEqual(['ACCOUNT_ID']);
  });

  it('saves the same list in the profile, so the command line applies the pattern too', () => {
    const cfg = { ...base, selected_entities: new Set(['EMAIL_ADDRESS']), custom_patterns: [account] };
    const profile = yaml.load(toYaml(cfg, groups)) as Record<string, unknown>;
    expect(profile.entities).toEqual(['EMAIL_ADDRESS', 'ACCOUNT_ID']);
    expect(jobOptions(cfg, groups).config).toBe(toYaml(cfg, groups));
  });
});

describe('job options', () => {
  it('sends a profile only when there is something only a profile carries', () => {
    expect(jobOptions(base, groups).config).toBeUndefined();
    expect(jobOptions({ ...base, allow_list: ['localhost'] }, groups).config).toContain('localhost');
  });

  it('omits an empty key and passes the NER settings and field rules through', () => {
    const rules = { fields_to_exclude: ['id'] };
    const o = jobOptions({ ...base, key: '', ner_score_threshold: 0.4, ner_aggregation_strategy: 'simple', anonymization_config: rules }, groups);
    expect(o.key).toBeUndefined();
    expect(o).toMatchObject({ strategy: 'regex', ner_score_threshold: 0.4, ner_aggregation_strategy: 'simple', anonymization_config: rules, slug_length: 8 });
  });
});

import { describe, expect, it } from 'vitest';
import { configFromRules, effectiveType, isHostField, rulesFromConfig, typeName } from '#lib/fieldRules.js';

const fields = ['id', 'asset.host_name', 'asset.ipv4', 'definition.output', 'scan.target'];

describe('typeName', () => {
  it('turns anything typed into an entity label', () => {
    expect(typeName('asset.criticality')).toBe('ASSET_CRITICALITY');
    expect(typeName('  host name ')).toBe('HOST_NAME');
    expect(typeName('IP_ADDRESS')).toBe('IP_ADDRESS');
    expect(typeName('--')).toBe('');
  });
});

describe('effectiveType', () => {
  it('reads Force without a type as Auto (it is still scanned)', () => {
    expect(effectiveType({ name: 'a', type: 'force' })).toBe('auto');
    expect(effectiveType({ name: 'a', type: 'force', forcedEntity: ' ' })).toBe('auto');
    expect(effectiveType({ name: 'a', type: 'force', forcedEntity: 'HOSTNAME' })).toBe('force');
    expect(effectiveType({ name: 'a', type: 'exclude' })).toBe('exclude');
  });
});

describe('isHostField', () => {
  it('suggests HOSTNAME for machine-name fields only', () => {
    for (const f of ['asset.host_name', 'hostname', 'netbios_name', 'asset.fqdn', 'computerName', 'dns_name'])
      expect(isHostField(f), f).toBe(true);
    for (const f of ['asset.name', 'host_ip', 'hostname_count'])
      expect(isHostField(f), f).toBe(false);
  });
});

describe('configFromRules', () => {
  const rules = (over: Record<string, Partial<{ type: string; forcedEntity: string }>> = {}) =>
    Object.fromEntries(fields.map(f => [f, { name: f, type: 'auto', ...over[f] }])) as never;

  it('scans everything when nothing is set', () => {
    expect(configFromRules('all', fields, rules())).toBeNull();
    expect(configFromRules('targeted', fields, rules())).toBeNull();
  });

  it('sends only the skips when nothing is forced, so fields of later records stay scanned', () => {
    expect(configFromRules('targeted', fields, rules({ id: { type: 'exclude' } }))).toEqual({ fields_to_exclude: ['id'] });
  });

  it('lists every top-level key once a field is forced (explicit mode ignores unlisted paths)', () => {
    const cfg = configFromRules('targeted', fields, rules({
      'asset.host_name': { type: 'force', forcedEntity: 'hostname' }, id: { type: 'exclude' } }));
    expect(cfg).toEqual({
      force_anonymize: { 'asset.host_name': { entity_type: 'HOSTNAME' } },
      fields_to_anonymize: ['id', 'asset', 'definition', 'scan'],
      fields_to_exclude: ['id'],
    });
  });

  it('does not force a field whose type is still empty', () => {
    expect(configFromRules('targeted', fields, rules({ 'scan.target': { type: 'force', forcedEntity: '' } }))).toBeNull();
  });
});

describe('rulesFromConfig', () => {
  it('shows no config as every field on Auto', () => {
    const r = rulesFromConfig(fields, null);
    expect(r.mode).toBe('all');
    expect(Object.values(r.rules).every(x => x.type === 'auto')).toBe(true);
  });

  it('shows forced fields with their type and skips, including what is under a skipped parent', () => {
    const r = rulesFromConfig(fields, { force_anonymize: { 'scan.target': { entity_type: 'HOSTNAME' } }, fields_to_exclude: ['asset'] });
    expect(r.rules['scan.target']).toEqual({ name: 'scan.target', type: 'force', forcedEntity: 'HOSTNAME' });
    expect(r.rules['asset.host_name'].type).toBe('exclude');
    expect(r.rules['asset.ipv4'].type).toBe('exclude');
    expect(r.rules['id'].type).toBe('auto');
  });

  it('does not read an old allow-list as "skip the rest" (that left fields in clear text)', () => {
    const r = rulesFromConfig(fields, { fields_to_anonymize: ['id'] });
    expect(Object.values(r.rules).every(x => x.type === 'auto')).toBe(true);
  });

  it('adds fields a profile names but this file does not show, once', () => {
    const r = rulesFromConfig(fields, { force_anonymize: { 'late.only': { entity_type: 'X' } }, fields_to_exclude: ['late.only', 'gone'] });
    expect(r.fields).toEqual([...fields, 'late.only', 'gone']);
  });

  it('round-trips a saved config through the rules unchanged', () => {
    for (const cfg of [
      { fields_to_exclude: ['id', 'definition.output'] },
      { force_anonymize: { 'asset.host_name': { entity_type: 'HOSTNAME' } }, fields_to_anonymize: ['id', 'asset', 'definition', 'scan'], fields_to_exclude: ['id'] },
    ]) {
      const r = rulesFromConfig(fields, cfg);
      expect(configFromRules(r.mode, r.fields, r.rules)).toEqual(cfg);
    }
  });
});

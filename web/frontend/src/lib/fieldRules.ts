/**
 * Rules per field of a structured file (CSV, JSON, XLSX) and the
 * anonymization_config they become. Pure functions: FieldSelector.svelte holds
 * the state and calls these, and the unit tests call them directly.
 */
import type { AnonymizationConfig } from '#lib/stores/config.js';

export type FieldMode = 'all' | 'targeted';
export type RuleType = 'auto' | 'force' | 'exclude';

export interface FieldRule {
  name: string;
  type: RuleType;
  forcedEntity?: string;
}

/** Any type can be forced; it becomes an entity label in upper case with "_"
 *  between words ("asset.criticality" → "ASSET_CRITICALITY"). The input keeps
 *  what was typed and is normalized when sent, so the cursor does not jump. */
export function typeName(raw: string): string {
  return raw.toUpperCase().replace(/[^A-Z0-9]+/g, '_').replace(/^_+|_+$/g, '');
}

/** A field set to Force without a type yet is still scanned automatically. */
export function effectiveType(rule: FieldRule | undefined): RuleType | undefined {
  return rule?.type === 'force' && !typeName(rule.forcedEntity ?? '') ? 'auto' : rule?.type;
}

/** A bare machine name ("srv-files") reads as an ordinary word, so detection
 *  misses it; fields named like these should be forced as HOSTNAME. */
export function isHostField(name: string): boolean {
  return /(host_?name|netbios(_name)?|fqdn|computer_?name|dns_?name)$/i.test(name);
}

/** Shows a config as rules: forced fields with their type, excluded fields
 *  (and what is under them) as Skip, every other field Auto. A
 *  fields_to_anonymize list is not read as "skip the rest": profiles saved
 *  before 2026-10 listed only the first record's fields, and skipping the
 *  others would leave them in clear text. Fields a rule names but the file
 *  does not show are added. */
export function rulesFromConfig(fields: string[], cfg: AnonymizationConfig | null):
    { fields: string[]; rules: Record<string, FieldRule>; mode: FieldMode } {
  if (!cfg) {
    return { fields, mode: 'all', rules: Object.fromEntries(fields.map(f => [f, { name: f, type: 'auto' as RuleType }])) };
  }
  const force = cfg.force_anonymize ?? {};
  const exclude = cfg.fields_to_exclude ?? [];
  const covers = (f: string, list: string[]) => list.some(r => f === r || f.startsWith(r + '.'));
  const missing = [...new Set([...Object.keys(force), ...exclude])].filter(f => !fields.includes(f));
  const all = [...fields, ...missing];
  const rules: Record<string, FieldRule> = {};
  for (const f of all) {
    if (force[f]) rules[f] = { name: f, type: 'force', forcedEntity: force[f].entity_type };
    else if (covers(f, exclude)) rules[f] = { name: f, type: 'exclude' };
    else rules[f] = { name: f, type: 'auto' };
  }
  return { fields: all, rules, mode: 'targeted' };
}

/** The config the rules ask for; null scans every field. */
export function configFromRules(mode: FieldMode, fields: string[], rules: Record<string, FieldRule>):
    AnonymizationConfig | null {
  if (mode === 'all') return null;
  const force: Record<string, { entity_type: string }> = {};
  const exclude: string[] = [];
  for (const f of fields) {
    const rule = rules[f];
    if (rule?.type === 'force' && typeName(rule.forcedEntity ?? '')) force[f] = { entity_type: typeName(rule.forcedEntity ?? '') };
    else if (rule?.type === 'exclude') exclude.push(f);
  }
  if (Object.keys(force).length === 0) {
    // Skips only: every other field, including any not listed here, is scanned.
    return exclude.length ? { fields_to_exclude: exclude } : null;
  }
  // A forced field puts the engine in explicit mode, which ignores unlisted
  // paths; listing each top-level key keeps the other fields (and any that
  // only later records have) scanned. Skips and forces take precedence.
  const roots = [...new Set(fields.map(f => f.split('.')[0]))];
  return { force_anonymize: force, fields_to_anonymize: roots, fields_to_exclude: exclude };
}

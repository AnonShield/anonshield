/**
 * Custom patterns run on the server with Python's `re`. The pattern builder
 * asks the server whether a pattern compiles (patternError) and previews its
 * matches in the browser (previewRegex). JavaScript reads most of the same
 * syntax; the Python spellings it does not are rewritten for the preview.
 */
import * as yaml from 'js-yaml';
import { validateProfile } from '#lib/api.js';

/** A RegExp that matches what the pattern matches on the server, or null when
 *  the browser cannot preview it (the pattern may still be valid Python). */
export function previewRegex(pattern: string): RegExp | null {
  let source = pattern;
  let flags = 'i'; // the server matches regardless of case
  const lead = /^\(\?([aiLmsux]+)\)/.exec(source); // global flags: (?i), (?ms)...
  if (lead) {
    if (lead[1].includes('x')) return null; // verbose mode has no JS equivalent
    if (lead[1].includes('m')) flags += 'm';
    if (lead[1].includes('s')) flags += 's';
    source = source.slice(lead[0].length);
  }
  source = source
    .replace(/\(\?P<([A-Za-z_]\w*)>/g, '(?<$1>')        // named group
    .replace(/\(\?P=([A-Za-z_]\w*)\)/g, '\\k<$1>')       // its backreference
    .replace(/(?<!\\)((?:\\\\)*)\\A/g, '$1^')            // start of text
    .replace(/(?<!\\)((?:\\\\)*)\\Z/g, '$1$');           // end of text
  try {
    return new RegExp(source, flags);
  } catch {
    return null;
  }
}

/** Why Python's `re` rejects the pattern, or '' when it compiles. */
export async function patternError(pattern: string): Promise<string> {
  const profile = yaml.dump({ custom_patterns: [{ entity_type: 'CHECK', pattern, score: 0.9 }] });
  const result = await validateProfile(profile);
  if (result.valid) return '';
  // "Pattern #0 (CHECK): invalid regex (missing ), ... at position 4)" → the reason
  const reason = /invalid regex \((.*)\)$/.exec(result.error ?? '');
  return reason ? reason[1] : (result.error ?? 'invalid pattern');
}

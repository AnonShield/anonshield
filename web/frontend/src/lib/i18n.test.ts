import { afterEach, describe, expect, it } from 'vitest';
import { get } from 'svelte/store';
import { LOCALES, dictionaries, locale, t, type TranslationKey } from '#lib/i18n.js';

const keys = Object.keys(dictionaries.en).sort() as TranslationKey[];
// The {name} slots that t() fills; a translation must keep every one of them.
const slots = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

describe('translations', () => {
  afterEach(() => locale.set('en'));

  it.each(LOCALES)('%s has exactly the English keys', (l) => {
    expect(Object.keys(dictionaries[l]).sort()).toEqual(keys);
  });

  it.each(LOCALES)('%s keeps the placeholders of every English text', (l) => {
    for (const k of keys) expect(slots(dictionaries[l][k]), k).toEqual(slots(dictionaries.en[k]));
  });

  it('t() follows the chosen language and fills the placeholders', () => {
    expect(get(t)('tut.step', { n: 2, total: 5 })).toBe('Step 2 of 5');
    locale.set('es');
    expect(get(t)('tut.step', { n: 2, total: 5 })).toBe('Paso 2 de 5');
  });
});

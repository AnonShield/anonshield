import { afterEach, describe, expect, it, vi } from 'vitest';
import * as yaml from 'js-yaml';
import { patternError, previewRegex } from '#lib/pyRegex.js';

describe('previewRegex: Python patterns in the browser', () => {
  it('reads the global flags Python allows at the start (the builder used to reject (?i))', () => {
    expect(previewRegex('(?i)acc-\\d{5}')?.test('ACC-12345')).toBe(true);
    expect(previewRegex('(?s)a.b')?.test('a\nb')).toBe(true);
    expect(previewRegex('(?m)^x$')?.test('a\nx\nb')).toBe(true);
  });

  it('ignores case like the server, with or without (?i)', () => {
    expect(previewRegex('acc-\\d+')?.test('ACC-1')).toBe(true);
  });

  it('rewrites named groups and their backreferences', () => {
    const rx = previewRegex('(?P<w>ab)-(?P=w)');
    expect(rx?.test('ab-ab')).toBe(true);
    expect(rx?.test('ab-cd')).toBe(false);
  });

  it('rewrites \\A and \\Z but not an escaped backslash before A', () => {
    expect(previewRegex('\\AID-\\d+\\Z')?.test('ID-7')).toBe(true);
    expect(previewRegex('\\AID-\\d+\\Z')?.test('x ID-7')).toBe(false);
    expect(previewRegex('a\\\\A')?.test('a\\A')).toBe(true);
  });

  it('gives no preview for verbose mode or invalid syntax', () => {
    expect(previewRegex('(?x) a b')).toBeNull();
    expect(previewRegex('ACC-(\\d{5}')).toBeNull();
  });
});

describe('patternError: the server decides', () => {
  afterEach(() => vi.unstubAllGlobals());
  const answer = (body: object) => vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(body))));

  it('is empty when Python compiles the pattern', async () => {
    answer({ valid: true });
    expect(await patternError('(?i)x')).toBe('');
  });

  it("returns Python's reason without the profile wording", async () => {
    answer({ valid: false, error: 'Pattern #0 (CHECK): invalid regex (unknown extension ?<n at position 5)' });
    expect(await patternError('ACC-(?<n>\\d)')).toBe('unknown extension ?<n at position 5');
  });

  it('sends the pattern as YAML that survives quotes and backslashes', async () => {
    const fetchMock = vi.fn(async (_url: string, init: RequestInit) => {
      const content = JSON.parse(String(init.body)).content as string;
      const sent = (yaml.load(content) as { custom_patterns: { pattern: string }[] }).custom_patterns[0].pattern;
      return new Response(JSON.stringify({ valid: sent === 'a"b\\d' }));
    });
    vi.stubGlobal('fetch', fetchMock);
    expect(await patternError('a"b\\d')).toBe('');
  });
});

// End-to-end checks of the AnonShield web app, driven in Chrome as a person
// uses it. Start the app (docker run ... anonshield/anon:web), then:
//   npm ci && URL=http://localhost:8080 npm test
// CHROME_PATH points at Chrome or Chromium; E2E_DIR holds the generated test
// files, downloads and screenshots of failed steps (default: a temp folder).
import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
import os from 'node:os';
import { execFileSync } from 'node:child_process';
import assert from 'node:assert/strict';

const URL = process.env.URL || 'http://localhost:8080';
const ROOT = process.env.E2E_DIR || `${os.tmpdir()}/anonshield-e2e`;
const D = `${ROOT}/data`, OUT = `${ROOT}/out`;
fs.rmSync(ROOT, { recursive: true, force: true }); fs.mkdirSync(OUT, { recursive: true });
execFileSync('python3', ['-I', new globalThis.URL('make-data.py', import.meta.url).pathname, D]);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const results = [];
let page, errors = [];

const browser = await puppeteer.launch({ executablePath: process.env.CHROME_PATH || '/usr/bin/google-chrome', headless: true, protocolTimeout: 900000,
  args: ['--no-sandbox', '--disable-dev-shm-usage'] });

async function fresh({ tutorial = false, width = 1280, height = 1000, path = '/app' } = {}) {
  if (page) await page.close().catch(() => {});
  page = await browser.newPage();
  errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  if (!tutorial) await page.evaluateOnNewDocument(() => {
    localStorage.setItem('anonshield_tutorial_done', '1'); localStorage.setItem('anonshield_adv_tour_done', '1');
  });
  await page.setViewport({ width, height });
  const cdp = await page.createCDPSession();
  await cdp.send('Browser.setDownloadBehavior', { behavior: 'allow', downloadPath: OUT });
  await page.goto(URL + path, { waitUntil: 'domcontentloaded' });
  if (path === '/app' && !tutorial) await page.waitForSelector('.entity-selector', { timeout: 60000 });
}
async function step(name, fn) {
  const t0 = Date.now();
  try {
    const note = await fn();
    assert.deepEqual(errors, [], 'browser errors');
    results.push({ name, ok: true }); console.log(`PASS ${name} (${Math.round((Date.now() - t0) / 1000)}s)${note ? ' - ' + note : ''}`);
  } catch (e) {
    results.push({ name, ok: false }); console.log(`FAIL ${name}: ${String(e.message || e).split('\n').slice(0, 6).join(' | ')}`);
    await page?.screenshot({ path: `${OUT}/fail-${results.length}.png`, fullPage: true }).catch(() => {});
  }
}
const upload = async (file) => (await page.$('input[type=file][accept^=".txt"]')).uploadFile(`${D}/${file}`);
async function strategy(s) {
  await page.$eval(`input[name=strategy][value=${s}]`, (e) => e.scrollIntoView({ block: 'center' }));
  await page.locator(`input[name=strategy][value=${s}]`).click();
  await page.waitForFunction((v) => document.querySelector(`input[name=strategy][value=${v}]`).checked, {}, s);
  await page.waitForFunction(() => document.querySelectorAll('label.entity-chip input').length > 0 && !document.querySelector('.loading-hint'), { timeout: 60000 });
}
async function fieldsReady() {
  await page.waitForFunction(() => { const b = document.querySelector('.schema-trigger'); return b && !b.classList.contains('is-loading'); }, { timeout: 120000 });
}
async function openRules() {
  await page.click('.schema-trigger'); await page.waitForSelector('dialog.modal-overlay[open]');
  await page.click('.modal-tabs button:nth-child(2)'); await page.waitForSelector('.field-table');
}
const closeRules = () => page.click('.modal-footer .btn-primary');
const fieldNames = () => page.$$eval('.field-table tbody tr .td-name code', (e) => e.map((x) => x.textContent.trim()));
const summary = () => page.$eval('.rule-count', (e) => e.innerText.trim());
async function rowButton(field, nth) {
  await page.evaluate((f, n) => {
    const row = [...document.querySelectorAll('.field-table tbody tr')].find((r) => r.querySelector('.td-name code').textContent.trim() === f);
    row.querySelector(`.segmented-control button:nth-child(${n})`).click();
  }, field, nth);
}
function formField(body, name) {
  const m = body.match(new RegExp(`name="${name}"\\r\\n\\r\\n([\\s\\S]*?)\\r\\n--`));
  return m ? m[1] : null;
}
async function submit({ timeout = 300000 } = {}) {
  const resp = page.waitForResponse((r) => r.url().endsWith('/api/jobs') && r.request().method() === 'POST', { timeout: 120000 });
  await page.$eval('.submit-btn', (e) => e.scrollIntoView({ block: 'center' }));
  await page.click('.submit-btn');
  const res = await resp;
  const body = (await res.request().fetchPostData()) || '';
  const fields = formField(body, 'fields');
  const entities = formField(body, 'entities');
  await page.waitForSelector('.download-btn, .error-box', { timeout });
  const error = await page.$eval('.error-box', (e) => e.innerText).catch(() => null);
  const content = error ? null : await page.$eval('.download-btn', async (e) => (await fetch(e.href)).text());
  return { status: res.status(), fields: fields ? JSON.parse(fields) : null, entities: entities ? JSON.parse(entities) : undefined, error, content };
}
async function clickByText(selector, regex) {
  const ok = await page.evaluate((s, r) => {
    const el = [...document.querySelectorAll(s)].find((e) => new RegExp(r).test(e.innerText.trim()));
    if (el) el.click(); return !!el;
  }, selector, regex.source);
  assert(ok, `no ${selector} matching ${regex}`);
}
async function importProfile(file) {
  await (await page.$('input[type=file][accept=".yaml,.yml,.json"]')).uploadFile(`${D}/${file}`);
  await page.waitForSelector('.profile-toast'); return page.$eval('.profile-toast', (e) => e.innerText);
}

// ── 1. first visit: tutorial, then home and app ───────────────────────────────
await step('first visit shows the tutorial and Skip closes it', async () => {
  await fresh({ tutorial: true });
  await page.waitForSelector('.tut-overlay', { timeout: 20000 });
  await clickByText('.tut-overlay button', /^(Skip|Pular)$/);
  await page.waitForFunction(() => !document.querySelector('.tut-overlay'));
  await page.waitForSelector('.entity-selector', { timeout: 60000 });
});
await step('home page loads and links to the app', async () => {
  await fresh({ path: '/' });
  await page.waitForFunction(() => /AnonShield/.test(document.title), { timeout: 30000 });
  assert(await page.$('a[href="/app"]'), 'link to /app');
});
await step('language toggle switches the interface', async () => {
  await fresh();
  const before = await page.$eval('.configure-title', (e) => e.innerText);
  await clickByText('header button, header a', /^(PT|EN)$/);
  await page.waitForFunction((b) => document.querySelector('.configure-title').innerText !== b, {}, before);
  await clickByText('header button, header a', /^(PT|EN)$/);
});

// ── 2. plain text with regex ──────────────────────────────────────────────────
await step('TXT with regex is anonymized and downloadable', async () => {
  await fresh(); await strategy('regex'); await upload('tickets.txt');
  const r = await submit();
  assert(!r.error, r.error); assert(!r.content.includes('maria.souza@example.com') && !r.content.includes('192.168.10.45'), r.content);
});
await step('unchecked entity types stay as they are', async () => {
  await fresh(); await strategy('regex');
  const label = await page.$$eval('label.entity-chip input', (e) => e.map((x) => x.getAttribute('aria-label')).find((l) => /mail/i.test(l)));
  await page.$eval(`label.entity-chip input[aria-label="${label}"]`, (e) => e.click());
  await upload('tickets.txt');
  const r = await submit();
  assert(!r.entities.includes('EMAIL_ADDRESS'), JSON.stringify(r.entities));
  assert(r.content.includes('maria.souza@example.com') && !r.content.includes('192.168.10.45'), r.content);
});

// ── 3. rules per field on a JSON export ───────────────────────────────────────
let rulesSent;
await step('rules per field: late fields listed, suggestion, filter, bulk, row actions, output', async () => {
  await fresh(); await strategy('regex'); await upload('scan.json'); await fieldsReady(); await openRules();
  const names = await fieldNames();
  assert(names.includes('notes') && names.includes('asset.netbios_name'), 'late fields missing: ' + names.join(','));
  for (const f of ['asset.host_name', 'asset.netbios_name']) {
    await page.evaluate((f) => [...document.querySelectorAll('.field-table tbody tr')]
      .find((r) => r.querySelector('code').textContent.trim() === f).querySelector('.suggest').click(), f);
  }
  await page.type('.filter-input', 'definition.');
  assert.equal((await fieldNames()).length, 3);
  await page.click('.bulk-actions .segmented-control button:nth-child(2)');
  await rowButton('definition.output', 1);
  await page.click('.filter-input', { clickCount: 3 }); await page.keyboard.press('Backspace');
  const s = await summary();
  assert.match(s, /2 (forced|forçados)/); assert.match(s, /2 (skipped|ignorados)/);
  await closeRules();
  const r = await submit(); assert(!r.error, r.error);
  rulesSent = r.fields;
  assert.deepEqual(Object.keys(r.fields.force_anonymize).sort(), ['asset.host_name', 'asset.netbios_name']);
  assert.deepEqual(r.fields.fields_to_exclude.sort(), ['definition.description', 'definition.name']);
  const out = JSON.parse(r.content);
  assert.match(out[0].asset.host_name, /^\[HOSTNAME_/); assert.match(out[25].asset.netbios_name, /^\[HOSTNAME_/);
  assert.equal(out[0].definition.description, 'Public plugin text that cites 203.0.113.7 as an example.');
  assert(!out[0].definition.output.includes('10.0.0.0'), 'definition.output kept scanned');
  assert(!out[25].notes.includes('ana.late@example.com') && !out[25].notes.includes('10.9.9.9'), 'late field scanned: ' + out[25].notes);
  assert.equal(out[0].id, 0);
});
await step('rules per field: any typed type, column-name button, bulk column names, with an entity unchecked', async () => {
  await fresh(); await strategy('regex');
  const mail = await page.$$eval('label.entity-chip input', (e) => e.map((x) => x.getAttribute('aria-label')).find((l) => /mail/i.test(l)));
  await page.$eval(`label.entity-chip input[aria-label="${mail}"]`, (e) => e.click());
  await upload('scan.json'); await fieldsReady(); await openRules();
  const rowEl = async (f, sel) => (await page.evaluateHandle((f, sel) => [...document.querySelectorAll('.field-table tbody tr')]
    .find((r) => r.querySelector('code').textContent.trim() === f).querySelector(sel), f, sel)).asElement();
  await rowButton('asset.ipv4_addresses', 2);
  await (await rowEl('asset.ipv4_addresses', '.force-input')).type('internal address');
  await rowButton('scan.target', 2);
  await (await rowEl('scan.target', '.use-column')).click();
  await page.type('.filter-input', 'definition.');
  await page.click('.bulk-actions .segmented-control button:nth-child(3)');
  await page.click('.filter-input', { clickCount: 3 }); await page.keyboard.press('Backspace');
  assert.match(await summary(), /5 (forced|forçados)/);
  await closeRules();
  const r = await submit(); assert(!r.error, r.error);
  assert.deepEqual(r.fields.force_anonymize, {
    'asset.ipv4_addresses': { entity_type: 'INTERNAL_ADDRESS' }, 'scan.target': { entity_type: 'SCAN_TARGET' },
    'definition.name': { entity_type: 'DEFINITION_NAME' }, 'definition.description': { entity_type: 'DEFINITION_DESCRIPTION' },
    'definition.output': { entity_type: 'DEFINITION_OUTPUT' } });
  const out = JSON.parse(r.content);
  assert.match(out[0].asset.ipv4_addresses[0], /^\[INTERNAL_ADDRESS_/);
  assert.match(out[0].scan.target, /^\[SCAN_TARGET_/);
  assert.match(out[0].definition.name, /^\[DEFINITION_NAME_/);
  assert(out[0].output.includes('joao0@example.com') && !out[0].output.includes('10.0.0.0'), 'unchecked e-mail kept, IP replaced: ' + out[0].output);
});
await step('Global Scan tab sends no field rules', async () => {
  await fresh(); await strategy('regex'); await upload('scan.json'); await fieldsReady(); await openRules();
  await rowButton('id', 3);
  await page.click('.modal-tabs button:nth-child(1)'); await closeRules();
  const r = await submit(); assert.equal(r.fields, null);
});

// ── 4. profiles: save, import before / after the file, old format, entities ──
await step('saved profile carries the field rules', async () => {
  await fresh(); await strategy('regex'); await upload('scan.json'); await fieldsReady(); await openRules();
  await page.evaluate(() => [...document.querySelectorAll('.field-table tbody tr')]
    .find((r) => r.querySelector('code').textContent.trim() === 'asset.host_name').querySelector('.suggest').click());
  await rowButton('definition.name', 3); await closeRules();
  await clickByText('button', /^(Save config|Salvar config)/);
  for (let i = 0; i < 20 && !fs.existsSync(`${OUT}/anonshield-profile.yaml`); i++) await sleep(250);
  const y = fs.readFileSync(`${OUT}/anonshield-profile.yaml`, 'utf8');
  fs.copyFileSync(`${OUT}/anonshield-profile.yaml`, `${D}/saved-profile.yaml`);
  assert(y.includes('asset.host_name') && y.includes('HOSTNAME') && y.includes('definition.name') && y.includes('entities:'), y);
});
await step('profile imported before choosing the file shows its rules', async () => {
  await fresh(); await importProfile('saved-profile.yaml'); await upload('scan.json'); await fieldsReady(); await openRules();
  const s = await summary(); assert.match(s, /1 (forced|forçados)/); assert.match(s, /1 (skipped|ignorados)/);
  await closeRules();
  const r = await submit(); assert.deepEqual(r.fields.force_anonymize, { 'asset.host_name': { entity_type: 'HOSTNAME' } });
  assert.deepEqual(r.fields.fields_to_exclude, ['definition.name']);
});
await step('profile imported after choosing the file updates the rules', async () => {
  await fresh(); await strategy('regex'); await upload('scan.json'); await fieldsReady();
  await importProfile('saved-profile.yaml'); await sleep(500); await openRules();
  const s = await summary(); assert.match(s, /1 (forced|forçados)/); assert.match(s, /1 (skipped|ignorados)/);
});
await step('old allow-list profile is shown and sent as skips', async () => {
  await fresh(); await importProfile('old-profile.yaml'); await upload('scan.json'); await fieldsReady(); await openRules();
  const s = await summary(); assert.match(s, /^\d+ (scanned|analisados) · 0 (forced|forçados) · 1 (skipped|ignorados)$/, s);
  await closeRules();
  const r = await submit(); assert.deepEqual(r.fields, { fields_to_exclude: ['id'] });
});
await step('profile with an entity subset selects only those types', async () => {
  await fresh(); await importProfile('ip-only-profile.yaml');
  const checked = await page.$$eval('label.entity-chip input', (e) => e.filter((x) => x.checked).map((x) => x.getAttribute('aria-label')));
  assert.equal(checked.length, 1, checked.join(','));
  await upload('tickets.txt');
  const r = await submit();
  assert.deepEqual(r.entities, ['IP_ADDRESS']);
  assert(r.content.includes('maria.souza@example.com') && !r.content.includes('192.168.10.45'), r.content);
});
await step('choosing another file detects its fields again', async () => {
  await fresh(); await upload('scan.json'); await fieldsReady();
  await upload('other.json'); await sleep(300); await fieldsReady(); await openRules();
  assert.deepEqual(await fieldNames(), ['a', 'b.c']);
});

// ── 5. advanced options ───────────────────────────────────────────────────────
await step('slug length 0 gives type-only labels', async () => {
  await fresh(); await strategy('regex');
  await page.click('.advanced-toggle'); await page.waitForSelector('.adv-dialog[open]');
  await page.$eval('.slug-slider', (e) => { e.value = '0'; e.dispatchEvent(new Event('input', { bubbles: true })); });
  await page.click('.adv-close');
  await upload('tickets.txt'); const r = await submit();
  assert(r.content.includes('[EMAIL_ADDRESS]') && r.content.includes('[IP_ADDRESS]'), r.content);
});
await step('custom regex pattern: builder usable inside Advanced, Esc closes only it, pattern applied', async () => {
  await fresh(); await strategy('regex');
  await page.click('.advanced-toggle'); await page.waitForSelector('.adv-dialog[open]');
  await page.click('#adv-s2 .patterns-header .btn-ghost');
  await page.waitForSelector('.adv-dialog .overlay .modal');
  await page.click('.adv-dialog .overlay .modal input[type=text]');
  await page.keyboard.press('Escape');
  await page.waitForFunction(() => !document.querySelector('.overlay .modal') && document.querySelector('.adv-dialog[open]'));
  await page.click('#adv-s2 .patterns-header .btn-ghost');
  await page.waitForSelector('.adv-dialog .overlay .modal');
  const inputs = await page.$$('.adv-dialog .overlay .modal input[type=text]');
  await inputs[0].click(); await page.keyboard.type('TICKET_ID');
  await inputs[1].click(); await page.keyboard.type('TICKET-\\d+');
  await page.click('.adv-dialog .overlay .actions .btn-primary');
  await page.waitForSelector('.patterns-table');
  assert.match(await page.$eval('.patterns-table', (e) => e.innerText), /TICKET_ID/);
  await page.click('.adv-close');
  await upload('tickets.txt'); const r = await submit();
  assert(!r.content.includes('TICKET-1234') && r.content.includes('TICKET_ID'), r.content);
});

// ── 6. batch, ZIP, errors ─────────────────────────────────────────────────────
await step('batch processes several files', async () => {
  await fresh(); await strategy('regex');
  await page.$eval('.batch-label input', (e) => e.click());
  await (await page.waitForSelector('.batch-drop input[type=file]')).uploadFile(`${D}/tickets.txt`, `${D}/other.json`);
  await page.waitForFunction(() => document.querySelectorAll('.batch-item').length === 2);
  await page.click('.submit-btn');
  await page.waitForFunction(() => document.querySelectorAll('.batch-item.bi-done').length === 2, { timeout: 180000 });
});
await step('ZIP: processed with the unsupported file listed', async () => {
  await fresh(); await strategy('regex'); await upload('mixed.zip');
  await page.click('.submit-btn'); await page.waitForSelector('.download-btn', { timeout: 120000 });
  assert.match(await page.$eval('.done-wrap', (e) => e.innerText), /notes\.md/);
});
await step('invalid JSON: clear error naming the file', async () => {
  await fresh(); await strategy('regex'); await upload('invalid.json'); await fieldsReady();
  const r = await submit(); assert(r.error && r.error.includes('invalid.json') && !r.error.includes('/data/'), r.error);
});
await step('unsupported file type is refused at upload', async () => {
  await fresh(); await strategy('regex'); await upload('dados.tsv');
  await page.click('.submit-btn'); await page.waitForSelector('.error-box', { timeout: 30000 });
  assert.match(await page.$eval('.error-box', (e) => e.innerText), /\.tsv/);
});

// ── 7. queue, progress and cancel ─────────────────────────────────────────────
await step('a job waiting behind another shows the queue, then runs', async () => {
  const fd = new FormData(); fd.append('file', new Blob([fs.readFileSync(`${D}/big.txt`)]), 'big.txt'); fd.append('strategy', 'filtered');
  const big = (await (await fetch(`${URL}/api/jobs`, { method: 'POST', body: fd })).json()).job_id;
  await sleep(3000);
  await fresh(); await strategy('regex'); await upload('tickets.txt');
  await page.click('.submit-btn'); await page.waitForSelector('.status-label');
  await page.waitForFunction(() => /Waiting in line|Na fila/.test(document.querySelector('.status-label').innerText), { timeout: 20000 });
  await fetch(`${URL}/api/jobs/${big}`, { method: 'DELETE' });
  const t0 = Date.now();
  await page.waitForSelector('.download-btn', { timeout: 300000 });
  return `queued job ran ${Math.round((Date.now() - t0) / 1000)}s after cancelling the one ahead`;
});
await step('Cancel stops a running job', async () => {
  await fresh(); await upload('big.txt');
  await page.click('.submit-btn'); await page.waitForSelector('.status-label');
  await page.waitForFunction(() => /Processing|Processando/.test(document.querySelector('.status-label').innerText), { timeout: 60000 });
  await sleep(5000);
  await page.click('.centered-card .btn-ghost');
  const t0 = Date.now();
  const fd = new FormData(); fd.append('file', new Blob([fs.readFileSync(`${D}/tickets.txt`)]), 'tickets.txt'); fd.append('strategy', 'regex');
  const next = (await (await fetch(`${URL}/api/jobs`, { method: 'POST', body: fd })).json()).job_id;
  let s;
  for (let i = 0; i < 60; i++) { s = await (await fetch(`${URL}/api/jobs/${next}/status`)).json(); if (s.status === 'done') break; await sleep(5000); }
  assert.equal(s.status, 'done', 'worker still busy after Cancel');
  return `worker free ${Math.round((Date.now() - t0) / 1000)}s after Cancel`;
});

// ── 8. metrics and phone layout ───────────────────────────────────────────────
await step('metrics page renders inside its cards', async () => {
  await fresh({ path: '/app/metrics' });
  await page.waitForSelector('.kpi-card');
  const escaping = await page.evaluate(() => [...document.querySelectorAll('.chart-card')].flatMap((card) => {
    const c = card.getBoundingClientRect();
    return [...card.querySelectorAll('rect,circle,.hbar-fill')].filter((e) => { const r = e.getBoundingClientRect(); return r.width && (r.left < c.left - 1 || r.right > c.right + 1); }).map((e) => e.getAttribute('class'));
  }));
  assert.deepEqual(escaping, []);
});
await step('phone width: app and rules dialog without horizontal scroll', async () => {
  await fresh({ width: 390, height: 844 }); await upload('scan.json'); await fieldsReady();
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'app page scrolls sideways');
  await openRules();
  assert(await page.evaluate(() => document.querySelector('.modal-content').getBoundingClientRect().right <= innerWidth + 1), 'dialog wider than the screen');
});

await browser.close();
const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} passed${failed.length ? '; failed: ' + failed.map((f) => f.name).join('; ') : ''}`);
process.exit(failed.length ? 1 : 0);

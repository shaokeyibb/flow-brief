#!/usr/bin/env node
// Optional viewport / theme check for a flow-brief artifact.
// Driven over CDP against a headless Chrome. No npm dependencies.
//
// Exit codes:
//   0  pass
//   1  fail        - horizontal overflow, or a theme that does not resolve
//   2  unverified  - no Chrome/Chromium found, or DevTools never came up
//
// Code 2 is not a pass. Report the visual dimension as unverified.

import { spawn } from 'node:child_process';
import { existsSync, mkdtempSync } from 'node:fs';
import { tmpdir, platform } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const target = resolve(process.argv[2] ?? '');
if (!target || !existsSync(target)) {
  console.error(`visual: file not found: ${process.argv[2] ?? '(no path given)'}`);
  process.exit(2);
}

const CANDIDATES = {
  win32: [
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  ],
  darwin: [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
  ],
  linux: [
    '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium', '/usr/bin/chromium-browser', '/snap/bin/chromium',
  ],
};

const chrome = [process.env.CHROME_PATH, ...(CANDIDATES[platform()] ?? [])]
  .filter(Boolean).find((p) => existsSync(p));

if (!chrome) {
  console.error('visual: no Chrome/Chromium found (set CHROME_PATH to override)');
  console.error('visual: UNVERIFIED — do not report the visual dimension as passed');
  process.exit(2);
}

const VIEWPORTS = [390, 900, 1280, 1440];
const port = 9500 + (process.pid % 400);
const profile = mkdtempSync(join(tmpdir(), 'flowbrief-'));
const proc = spawn(chrome, [
  '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  '--no-first-run', '--no-default-browser-check', '--disable-gpu', 'about:blank',
], { stdio: 'ignore' });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const fail = (msg, code) => { console.error(msg); try { proc.kill(); } catch {} process.exit(code); };

let wsUrl = null;
for (let i = 0; i < 60 && !wsUrl; i++) {
  await sleep(250);
  try {
    const r = await fetch(`http://127.0.0.1:${port}/json/list`);
    wsUrl = (await r.json()).find((t) => t.type === 'page')?.webSocketDebuggerUrl ?? null;
  } catch { /* not up yet */ }
}
if (!wsUrl) fail('visual: DevTools endpoint never came up — UNVERIFIED', 2);

const ws = new WebSocket(wsUrl);
let seq = 0;
const pending = new Map();
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result); pending.delete(m.id); }
});
await new Promise((r, j) => { ws.addEventListener('open', r); ws.addEventListener('error', j); });

const send = (method, params = {}) => new Promise((res) => {
  const id = ++seq; pending.set(id, res);
  ws.send(JSON.stringify({ id, method, params }));
});
const evaluate = async (expression) =>
  (await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }))
    ?.result?.value;

await send('Page.enable');
await send('Page.navigate', { url: pathToFileURL(target).href });
await sleep(2500);

const problems = [];
const lines = [];

// ---- 1. horizontal containment across viewports -------------------------
for (const width of VIEWPORTS) {
  await send('Emulation.setDeviceMetricsOverride',
    { width, height: 900, deviceScaleFactor: 1, mobile: width < 600 });
  await sleep(450);
  const r = await evaluate(`(() => {
    const d = document.documentElement;
    const over = [...document.querySelectorAll('body *')]
      .filter(el => {
        const cs = getComputedStyle(el);
        return el.scrollWidth > el.clientWidth + 2 &&
               cs.overflowX !== 'auto' && cs.overflowX !== 'scroll' &&
               cs.position !== 'fixed';
      })
      .slice(0, 4)
      .map(el => el.tagName.toLowerCase() + (el.className ? '.' + String(el.className).trim().split(/\\s+/).join('.') : ''));
    return { doc: d.scrollWidth - d.clientWidth, over };
  })()`);
  const bleed = r?.doc ?? 0;
  if (bleed > 1) {
    problems.push(`${width}px: page scrolls sideways by ${bleed}px`);
    lines.push(`  ${String(width).padStart(4)}px  FAIL  bleed ${bleed}px` +
      (r.over?.length ? `  first offenders: ${r.over.join(', ')}` : ''));
  } else {
    lines.push(`  ${String(width).padStart(4)}px  ok`);
  }
}
await send('Emulation.clearDeviceMetricsOverride');

// ---- 2. all three theme states resolve ----------------------------------
const themeLines = [];
for (const [label, prefers, attr] of [
  ['system-light', 'light', null],
  ['system-dark', 'dark', null],
  ['forced-dark', 'light', 'dark'],
]) {
  await send('Emulation.setEmulatedMedia',
    { features: [{ name: 'prefers-color-scheme', value: prefers }] });
  await evaluate(attr
    ? `document.documentElement.setAttribute('data-theme','${attr}')`
    : `document.documentElement.removeAttribute('data-theme')`);
  await sleep(250);
  const t = await evaluate(`(() => {
    const cs = getComputedStyle(document.body);
    return { bg: cs.backgroundColor, fg: cs.color };
  })()`);
  const transparent = !t?.bg || t.bg === 'rgba(0, 0, 0, 0)' || t.bg === 'transparent';
  if (transparent) problems.push(`${label}: body background is transparent`);
  themeLines.push(`  ${label.padEnd(13)} bg ${t?.bg ?? '?'}   fg ${t?.fg ?? '?'}` +
    (transparent ? '   <-- FAIL' : ''));
}
await evaluate(`document.documentElement.removeAttribute('data-theme')`);

// ---- 3. fonts actually loaded -------------------------------------------
const fonts = await evaluate(`(async () => {
  await document.fonts.ready;
  const want = ['Noto Sans SC','Noto Serif SC','IBM Plex Mono'];
  return want.map(f => f + ': ' + (document.fonts.check('12px "' + f + '"') ? 'loaded' : 'system-fallback'));
})()`);

console.log('visual check · ' + target);
console.log('\nhorizontal containment');
lines.forEach((l) => console.log(l));
console.log('\ntheme states');
themeLines.forEach((l) => console.log(l));
if (Array.isArray(fonts)) {
  console.log('\nfonts\n  ' + fonts.join('\n  '));
  if (fonts.some((f) => f.includes('system-fallback')))
    console.log('  (not a failure: the page is offline, or the webfont links were removed on purpose)');
}

ws.close();
try { proc.kill(); } catch {}

if (problems.length) {
  console.log('\nvisual: FAIL');
  problems.forEach((p) => console.log('  - ' + p));
  console.log('\n  Do not "fix" these with overflow:hidden or smaller type.');
  console.log('  Wide content belongs in a .tw scroll container.');
  process.exit(1);
}
console.log('\nvisual: pass');
process.exit(0);

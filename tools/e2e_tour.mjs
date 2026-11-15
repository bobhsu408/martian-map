// SI-generated: end-to-end test of the onboarding spotlight tour by Claude Code (SI tool).
//   node tools/e2e_tour.mjs <out dir> [url]   (url without ?nointro; pass lang=zh as 3rd arg for Chinese)
import { spawn } from 'node:child_process';
import { writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const out = process.argv[2] || '.';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const prof = mkdtempSync(join(tmpdir(), 'mm-chrome-'));
const chrome = spawn(CHROME, ['--headless=new', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--remote-debugging-port=9333',
  `--user-data-dir=${prof}`, '--window-size=1440,900', 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let ws, id = 0;
const pending = new Map();
const errors = [];
const send = (method, params = {}) => new Promise((res) => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
const evalJs = async (expr) => (await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true })).result?.result?.value;
const shot = async (name) => { const r = await send('Page.captureScreenshot', { format: 'png' }); writeFileSync(join(out, name), Buffer.from(r.result.data, 'base64')); console.log('shot', name); };

try {
  let target;
  for (let k = 0; k < 40 && !target; k++) {
    await sleep(250);
    try { target = (await (await fetch('http://127.0.0.1:9333/json')).json()).find((t) => t.type === 'page'); } catch {}
  }
  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => (ws.onopen = r));
  ws.onmessage = (m) => {
    const d = JSON.parse(m.data);
    if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); }
    if (d.method === 'Runtime.exceptionThrown') errors.push(d.params.exceptionDetails.exception?.description || d.params.exceptionDetails.text);
    if (d.method === 'Runtime.consoleAPICalled' && d.params.type === 'error') errors.push(d.params.args.map((a) => a.value ?? a.description).join(' '));
  };
  await send('Runtime.enable');
  await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
  const url = process.argv[3] || 'http://localhost:4173/';
  if (process.argv[4] === 'zh') { await send('Page.navigate', { url }); await sleep(1500); await evalJs("localStorage.setItem('lang','zh')"); }
  await send('Page.navigate', { url });
  for (let k = 0; k < 120; k++) {
    await sleep(500);
    if (await evalJs(`document.getElementById('loading').classList.contains('done')`)) break;
  }
  const click = (sel) => evalJs(`document.querySelector('${sel}').click()`);
  const key = async (k, code) => { await send('Input.dispatchKeyEvent', { type: 'keyDown', key: k, code }); await sleep(60); await send('Input.dispatchKeyEvent', { type: 'keyUp', key: k, code }); };
  const state = async (tag) => {
    const v = await evalJs(`JSON.stringify({count: document.querySelector('#tour-bubble .tour-count')?.textContent || null, spot: getComputedStyle(document.getElementById('tour-spot')||document.body).opacity, done: localStorage.getItem('mm_tour_done')})`);
    console.log(tag, v);
    await shot(`tour_${tag}.png`);
  };
  console.log('intro visible:', await evalJs("!document.getElementById('intro').classList.contains('hidden')"));
  await click('#intro-ok'); await sleep(800); await state('1_raise');
  await key('Tab', 'Tab'); await sleep(1200); await state('2_target');
  await evalJs(`(()=>{const s=document.getElementById('target'); s.value=window.__mm.S.meta.targets[0].id; s.dispatchEvent(new Event('change'));})()`);
  await sleep(600); await state('3_plan');
  await click('#plan'); await sleep(3000); await state('4_routes');
  await click('#tour-bubble [data-act=next]'); await sleep(600); await state('5_ready');
  await click('#tour-bubble [data-act=done]'); await sleep(400); await state('6_end');
} finally {
  console.log('--- page errors ---');
  console.log(errors.length ? errors.join('\n') : '(none)');
  ws?.close();
  chrome.kill();
}

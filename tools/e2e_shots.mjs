// SI-generated: end-to-end smoke test by Claude Code (SI tool).
// 用 headless Chrome（DevTools Protocol）跑完整 demo 流程並截圖：
//   node tools/e2e_shots.mjs <輸出資料夾> [網址]   （預設 http://127.0.0.1:8080/）
import { spawn } from 'node:child_process';
import { writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const out = process.argv[2] || '.';
const CHROME = process.env.CHROME_PATH || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome');
const prof = mkdtempSync(join(tmpdir(), 'mm-chrome-'));
const chrome = spawn(CHROME, ['--headless=new', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--remote-debugging-port=9333',
  '--no-first-run', '--no-default-browser-check', `--user-data-dir=${prof}`, '--window-size=1440,900', 'about:blank'], { stdio: 'ignore' });
chrome.on('error', (e) => console.error(`Browser launch failed: ${e.message}`));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let ws, id = 0;
const pending = new Map();
const errors = [];
const send = (method, params = {}) => new Promise((res, rej) => {
  const i = ++id;
  const timer = setTimeout(() => { pending.delete(i); rej(new Error(`DevTools timed out waiting for ${method}`)); }, 10000);
  pending.set(i, (message) => { clearTimeout(timer); res(message); });
  ws.send(JSON.stringify({ id: i, method, params }));
});
const evalJs = async (expr) => (await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true })).result?.result?.value;
const shot = async (name) => { const r = await send('Page.captureScreenshot', { format: 'png' }); writeFileSync(join(out, name), Buffer.from(r.result.data, 'base64')); console.log('shot', name); };

try {
  let target;
  for (let k = 0; k < 40 && !target; k++) {
    await sleep(250);
    try { target = (await (await fetch('http://127.0.0.1:9333/json')).json()).find((t) => t.type === 'page'); } catch {}
  }
  if (!target) throw new Error(`Browser did not expose a DevTools page on port 9333 (${CHROME})`);
  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => (ws.onopen = r));
  ws.onmessage = async (m) => {
    const payload = typeof m.data === 'string' ? m.data : m.data instanceof Blob ? await m.data.text() : new TextDecoder().decode(m.data);
    const d = JSON.parse(payload);
    if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); }
    if (d.method === 'Runtime.exceptionThrown') errors.push(d.params.exceptionDetails.exception?.description || d.params.exceptionDetails.text);
    if (d.method === 'Runtime.consoleAPICalled' && d.params.type === 'error') errors.push(d.params.args.map((a) => a.value ?? a.description).join(' '));
  };
  await send('Runtime.enable');
  await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
  const url = process.argv[3] || 'http://127.0.0.1:8080/';
  await send('Page.navigate', { url });
  for (let k = 0; k < 120; k++) {
    await sleep(500);
    if (await evalJs(`document.getElementById('loading').classList.contains('done')`)) break;
  }
  const click = (id) => evalJs(`document.getElementById('${id}').click()`);
  const assertPage = async (expr, message) => {
    if (!(await evalJs(expr))) throw new Error(`UI smoke check failed: ${message}`);
  };
  const layer = (id, on) => evalJs(`(()=>{const c=document.getElementById('ly-${id}'); c.checked=${on}; c.dispatchEvent(new Event('change'));})()`);
  const viewDist = (v) => evalJs(`(()=>{const r=document.getElementById('view-dist'); r.value='${v}'; r.dispatchEvent(new Event('input'));})()`);
  await sleep(1000);
  await assertPage(`document.getElementById('tablet').dataset.stage === 'destination' && document.getElementById('start').disabled`, 'destination is the initial state and EVA is unavailable');
  await shot('01_loaded.png');

  await evalJs(`(()=>{const s=document.getElementById('target');s.value='custom';s.dispatchEvent(new Event('change',{bubbles:true}));})()`);
  await sleep(500);
  await evalJs(`(()=>{const e=document.getElementById('tab-map'),r=e.getBoundingClientRect(),x=r.left+r.width/2,y=r.top+r.height/2;for(const type of ['pointerdown','pointerup'])e.dispatchEvent(new PointerEvent(type,{bubbles:true,clientX:x,clientY:y,pointerId:1,pointerType:'mouse'}));})()`);
  await sleep(500);
  await assertPage(`!document.getElementById('destination-summary').classList.contains('hidden') && document.getElementById('target-desc').textContent.startsWith('Custom goal at')`, 'custom map selection sets a destination');
  await evalJs(`(()=>{const s=document.getElementById('target'),o=[...s.options].find(x=>x.value&&x.value!=='custom');if(!o)return false;s.value=o.value;s.dispatchEvent(new Event('change',{bubbles:true}));return true})()`);
  await assertPage(`document.getElementById('tablet').dataset.stage === 'route-selection' && document.getElementById('start').disabled`, 'choosing a science target unlocks route planning but not EVA');
  await shot('01b_destination_selected.png');
  await click('plan');
  await sleep(2500);
  await assertPage(`document.getElementById('tablet').dataset.stage === 'route' && document.querySelector('.route-card.selected') && !document.getElementById('start').disabled`, 'route calculation selects a usable route and enables EVA');
  await shot('02_routes.png');
  await click('view-2d');
  await sleep(1500);
  await shot('02b_map2d_site.png');
  await click('extent-global');
  await sleep(4000);
  await shot('02c_map2d_global.png');
  await click('extent-regional');
  await new Promise((r) => setTimeout(r, 1500));
  await shot('02d_map2d_regional.png');
  await click('extent-local');
  await click('view-3d');
  await sleep(1500);
  await layer('hazard', true);
  await layer('coverage', true);
  await sleep(2500);
  await shot('03_layers_hazard_coverage.png');
  await layer('coverage', false);
  await layer('hazard', false);
  await viewDist(5);
  await evalJs(`(()=>{const m=window.__mm.S; })()`);
  await evalJs(`window.__mm.zoomOut && window.__mm.zoomOut()`);
  await sleep(2500);
  await shot('03b_region_view.png');
  await viewDist(2);
  await click('globe');
  await sleep(6000);
  await shot('03c_globe.png');
  await click('globe');
  await sleep(1000);
  await evalJs(`document.getElementById('autopilot').checked = true`);
  await click('start');
  await sleep(6000);
  await shot('04_eva_walking.png');
  await click('drift');
  await sleep(1500);
  await shot('05_drift_offroute.png');
  await sleep(4000);
  await shot('06_after_replan.png');
  await click('rockfall');
  await sleep(4000);
  await shot('07_rockfall_reroute.png');
  await click('leak');
  await sleep(4000);
  await shot('08_o2_leak_return.png');
  const logText = await evalJs(`document.getElementById('log').innerText`);
  console.log('--- mission log ---\n' + logText);
  console.log('--- page errors ---\n' + (errors.join('\n') || '(none)'));
} finally {
  chrome.kill();
}

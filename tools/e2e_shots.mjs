// SI-generated: end-to-end smoke test by Claude Code (SI tool).
// 用 headless Chrome（DevTools Protocol）跑完整 demo 流程並截圖：
//   node tools/e2e_shots.mjs <輸出資料夾>   （mars-server 需在 :8080 執行）
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
  await send('Page.navigate', { url: 'http://127.0.0.1:8080/' });
  await sleep(3000);
  await shot('01_loaded.png');
  await evalJs(`document.getElementById('plan').click()`);
  await sleep(2500);
  await shot('02_routes.png');
  await evalJs(`(()=>{const s=document.getElementById('layer'); s.value='hazard'; s.dispatchEvent(new Event('change'));})()`);
  await sleep(1500);
  await shot('03_hazard_layer.png');
  await evalJs(`document.querySelector('.route-card[data-key=science]').click()`);
  await evalJs(`document.getElementById('start').click()`);
  await sleep(2500);
  await shot('04_eva.png');
  await evalJs(`document.getElementById('rockfall').click()`);
  await sleep(2500);
  await shot('05_rockfall_reroute.png');
  await evalJs(`document.getElementById('leak').click()`);
  await sleep(2000);
  await evalJs(`(()=>{const s=document.getElementById('layer'); s.value='pnr'; s.dispatchEvent(new Event('change'));})()`);
  await sleep(2500);
  await shot('06_o2_leak_return.png');
  await sleep(6000);
  await shot('07_end.png');
  const logText = await evalJs(`document.getElementById('log').innerText`);
  console.log('--- mission log ---\n' + logText);
  console.log('--- page errors ---\n' + (errors.join('\n') || '(none)'));
} finally {
  chrome.kill();
}

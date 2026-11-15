// SI-generated: end-to-end test of the handheld-tablet explorer UI by Claude Code (SI tool).
// 用 headless Chrome（DevTools Protocol）跑完整 demo 流程並截圖：
//   node tools/e2e_shots.mjs <輸出資料夾> [網址]   （預設 http://127.0.0.1:8080/）
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
  const url = process.argv[3] || 'http://127.0.0.1:8080/';
  await send('Page.navigate', { url });
  for (let k = 0; k < 120; k++) {
    await sleep(500);
    if (await evalJs(`document.getElementById('loading').classList.contains('done')`)) break;
  }
  const click = (id) => evalJs(`document.getElementById('${id}').click()`);
  const layer = (id, on) => evalJs(`(()=>{const c=document.getElementById('ly-${id}'); c.checked=${on}; c.dispatchEvent(new Event('change'));})()`);
  const viewDist = (v) => evalJs(`(()=>{const r=document.getElementById('view-dist'); r.value='${v}'; r.dispatchEvent(new Event('input'));})()`);
  const key = async (k, code, ms = 60) => {
    await send('Input.dispatchKeyEvent', { type: 'keyDown', key: k, code });
    await sleep(ms);
    await send('Input.dispatchKeyEvent', { type: 'keyUp', key: k, code });
  };
  const pos = () => evalJs('JSON.stringify(window.__mm.S.walk.pos)');
  await sleep(1500);
  await shot('t1_explore_third.png');
  console.log('fps', await evalJs('new Promise(r=>{let n=0;const t=performance.now();const f=()=>{n++; if(performance.now()-t<1000) requestAnimationFrame(f); else r(n)};requestAnimationFrame(f)})'));
  console.log('probe', await evalJs(`(()=>{const S=window.__mm.S,p=S.walk.pos;return JSON.stringify({v0:S.meta.params.walk_speed_mps, slope:null, hz:null, heading:S.walk.heading})})()`));
  const p0 = await pos();
  await key('w', 'KeyW', 2500);
  console.log('walk', p0, '->', await pos());
  await key('Tab', 'Tab');
  await sleep(300);
  console.log('tablet raised:', await evalJs("document.getElementById('tablet').classList.contains('raised')"));
  // pick the first science target (the UI requires a goal before planning)
  await evalJs(`(()=>{const s=document.getElementById('target'); s.value=window.__mm.S.meta.targets[0].id; s.dispatchEvent(new Event('change'));})()`);
  console.log('goal:', await evalJs('JSON.stringify(window.__mm.S.goal)'));
  await click('plan');
  await sleep(3000);
  console.log('routes:', await evalJs('Object.keys(window.__mm.S.routes).join(",")'), 'eva after start btn enabled:', await evalJs("!document.getElementById('start').disabled"));
  await shot('t2_tablet_routes.png');
  await click('start');
  await sleep(3500);
  console.log('tablet after start raised:', await evalJs("document.getElementById('tablet').classList.contains('raised')"));
  await shot('t3_eva_third.png');
  await key('v', 'KeyV');
  await sleep(1500);
  await shot('t4_eva_first.png');
  await key('v', 'KeyV');
  await click('rockfall');
  await sleep(2500);
  console.log('tablet after rockfall raised:', await evalJs("document.getElementById('tablet').classList.contains('raised')"));
  await shot('t5_rockfall_tablet.png');
  const log = await evalJs("[...document.querySelectorAll('#log div')].slice(0,6).map(d=>d.textContent).join('\\n')");
  console.log(log);
} finally {
  console.log('--- page errors ---');
  console.log(errors.length ? errors.join('\n') : '(none)');
  ws?.close();
  chrome.kill();
}

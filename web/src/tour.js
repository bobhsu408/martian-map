// SI-generated: this file was written by Claude Code (Anthropic, SI tool); the team defined the tour flow and reviewed it.
// 新手高亮導覽：抬起平板 → 選目標 → 規劃路線 → 看路線 → 告訴使用者可以移動了。
// 每一步等使用者真的做了才前進（tourEvent），聚光燈每幀追蹤目標元素位置（平板有升降動畫、面板會捲動）。

const STEPS = [
  {
    targets: ['#sim-open-tablet', '#tab-bar'], on: 'tablet',
    en: 'Press <b>Tab</b> or <b>M</b> (or click here) to raise your Martian Map tablet.',
    zh: '按 <b>Tab</b> 或 <b>M</b>（或點這裡）舉起你的 Martian Map 平板。',
  },
  {
    targets: ['#step1'], on: 'goal', tablet: true,
    en: 'Pick where to go: a science stop from the list, or a custom point on the map.',
    zh: '選擇目的地：從清單選一個科學站點，或在地圖上點一個自訂地點。',
  },
  {
    targets: ['#plan'], on: 'planned', tablet: true,
    en: 'Calculate routes. Everything is computed on this device, with no link to Earth.',
    zh: '規劃路線。所有運算都在這台裝置上完成，不需要和地球連線。',
  },
  {
    targets: ['#routes'], next: true, tablet: true,
    en: 'Three choices: <b>Safe</b>, <b>Balanced</b>, <b>Science</b>. Compare distance, time and risk, then tap one.',
    zh: '三種選擇：<b>安全</b>、<b>平衡</b>、<b>科學</b>。比較距離、時間與風險，點一條來選。',
  },
  {
    targets: ['#start'], done: true, center: true,
    en: '<b>Route ready — you can move now!</b><br>Press <b>Tab</b> to lower the tablet, walk with <b>W A S D</b> / arrow keys, drag to look around, <b>V</b> switches view.<br>Or press <b>▶ Start EVA</b> to follow the route.',
    zh: '<b>路線已就緒 — 現在可以移動了！</b><br>按 <b>Tab</b> 放下平板，用 <b>W A S D</b>／方向鍵走路、拖曳看四周，<b>V</b> 切換視角。<br>或按 <b>▶ 開始 EVA</b> 沿路線前進。',
  },
];
const UI = {
  en: { skip: 'Skip tour', next: 'Next', done: 'Done' },
  zh: { skip: '略過導覽', next: '下一步', done: '完成' },
};

let step = -1;
let state = { tablet: () => false, goal: () => false, planned: () => false };
const tabletUp = () => state.tablet();
let spot, bubble, raf = 0, shownKey = '';

const lang = () => (document.documentElement.lang === 'zh-Hant' ? 'zh' : 'en');
const visible = (el) => { if (!el) return false; const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };

function ensureDom() {
  if (spot) return;
  spot = document.createElement('div'); spot.id = 'tour-spot';
  bubble = document.createElement('div'); bubble.id = 'tour-bubble';
  document.body.append(spot, bubble);
  bubble.addEventListener('click', (e) => {
    const a = e.target.closest('[data-act]')?.dataset.act;
    if (a === 'skip' || a === 'done') endTour();
    else if (a === 'next') go(step + 1);
  });
}

/** 目前實際要顯示的步驟：需要平板卻被放下時，退回「舉起平板」提示。 */
function effective() { return STEPS[step].tablet && !tabletUp() ? 0 : step; }

function render(i) {
  const s = STEPS[i], l = lang(), u = UI[l];
  const btn = s.done ? `<button class="primary" data-act="done">${u.done}</button>`
    : s.next ? `<button class="primary" data-act="next">${u.next}</button>` : '';
  // 文字直接用目前語言產生（切換語言時 frame() 會重畫）
  bubble.innerHTML = `<div class="tour-count">${i + 1} / ${STEPS.length}</div><div class="tour-text">${s[l]}</div>`
    + `<div class="tour-btns">${s.done ? '<span></span>' : `<button class="tour-skip" data-act="skip">${u.skip}</button>`}${btn}</div>`;
  bubble.classList.toggle('center', !!s.center);
}

function frame() {
  raf = requestAnimationFrame(frame);
  const i = effective(), s = STEPS[i];
  const key = `${i}|${lang()}`;
  if (key !== shownKey) { shownKey = key; render(i); }
  const el = s.targets.map((q) => document.querySelector(q)).find(visible);
  if (!el) { spot.style.opacity = 0; return; }
  const r = el.getBoundingClientRect(), pad = 6;
  Object.assign(spot.style, { opacity: 1, left: `${r.left - pad}px`, top: `${r.top - pad}px`, width: `${r.width + pad * 2}px`, height: `${r.height + pad * 2}px` });
  if (s.center) return; // 置中卡片由 CSS 定位
  const bw = bubble.offsetWidth, bh = bubble.offsetHeight, W = innerWidth, H = innerHeight, gap = 14;
  let x, y;
  if (r.right + gap + bw < W) { x = r.right + gap; y = r.top; } // 右側
  else if (r.bottom + gap + bh < H) { x = r.left; y = r.bottom + gap; } // 下方
  else { x = r.left; y = r.top - gap - bh; } // 上方
  bubble.style.left = `${Math.max(12, Math.min(x, W - bw - 12))}px`;
  bubble.style.top = `${Math.max(12, Math.min(y, H - bh - 12))}px`;
}

function go(i) {
  step = i;
  const on = STEPS[i].on;
  if (on && state[on]?.()) return go(i + 1); // 已經做到的步驟直接跳過
  shownKey = '';
}

/** state: { tablet, goal, planned } — 回傳目前是否已完成該動作的函式 */
export function startTour(st) {
  state = { ...state, ...st };
  ensureDom();
  document.body.classList.add('touring');
  go(0);
  cancelAnimationFrame(raf);
  frame();
}

export function tourEvent(name) {
  if (step < 0) return;
  if (STEPS[step].on === name) go(step + 1);
}

export function isTourActive() { return step >= 0; }

export function endTour() {
  step = -1;
  cancelAnimationFrame(raf);
  document.body.classList.remove('touring');
  if (spot) { spot.style.opacity = 0; bubble.innerHTML = ''; bubble.classList.remove('center'); }
  try { localStorage.setItem('mm_tour_done', '1'); } catch { /* storage unavailable */ }
}

export function tourDone() {
  try { return localStorage.getItem('mm_tour_done') === '1'; } catch { return false; }
}

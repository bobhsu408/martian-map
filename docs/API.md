<!-- SI-generated: drafted by Claude Code (SI tool); reviewed and maintained by the team. -->
# Martian Map Engine — API 契約 v1

規劃引擎 `mars-core` 有兩種執行方式，介面完全相同：
- **WebAssembly（預設）**：`mars-wasm` 在瀏覽器的 Web Worker 裡執行，網頁本身就是完整系統，可放在 GitHub Pages；載入後**拔網路也能用**。前端用 `web/src/api.js` 呼叫。
- **本機 server**：`mars-server`（Rust / axum），`http://localhost:8080`，同時提供 `web/dist` 靜態檔。網址加 `?server` 讓前端改用它。
本文件是前後端的唯一依據；要改請先改這份文件，並通知對方。

---

## 0. 共通約定

### 座標系
- 單位一律是**公尺**；原點在 DEM 的**西南角**；**x 朝東、y 朝北**。
- DEM 是 `width × height` 的網格，每格 `cell_m` 公尺。
- 格子 `(i, j)`（i 是欄、j 是**從南數起**的列）的中心座標是 `((i + 0.5)·cell_m, (j + 0.5)·cell_m)`。
- 高度 `z` 單位為公尺（火星基準面高程，數值可能是負的）。

### 二進位網格（terrain / layer）
- **列優先（row-major）**，第一列是**最南**的一列（j = 0），每一列由西到東。
- index = `j * w + i`。
- ⚠ Three.js 的 `PlaneGeometry` 頂點從**左上（北）**開始排，套用時要把列翻轉（`j_three = h - 1 - j`），或直接旋轉 mesh。
- 回應 header：`X-Width`、`X-Height`、`X-Cell-M`（降採樣後每格的公尺數）。

### mode
`"safe" | "balanced" | "science"`

### 錯誤格式
HTTP 4xx，body：`{"error": "<code>", "message": "<說明>"}`

| code | HTTP | 說明 |
|---|---|---|
| `bad_request` | 400 | 參數格式錯誤 |
| `out_of_bounds` | 400 | 座標超出地圖範圍 |
| `blocked` | 422 | 起點或終點落在危險區（hazard）裡 |
| `no_path` | 422 | 找不到可通行的路線 |
| `unknown_layer` | 404 | 圖層名稱不存在 |
| `bad_request` | 400 | （WASM）JSON 格式錯誤 |

---

## 1. `GET /api/meta`
啟動時呼叫一次，取得地圖和任務設定。

```json
{
  "name": "Mount Sharp boxwork site (Gale crater)",
  "source": "synthetic | HiRISE DTM <product id>",
  "width": 1024, "height": 1024, "cell_m": 2.0,
  "z_min": -4520.3, "z_max": -4310.8,
  "base": [400.0, 300.0],
  "targets": [
    {"id": "bx1", "name": "Boxwork ridge A", "x": 1500.0, "y": 1650.0,
     "science": 0.9, "desc": "Mineral-vein ridges from ancient groundwater", "image": null}
  ],
  "beacons": [
    {"id": "hab", "kind": "lora", "x": 315.2, "y": 245.8, "label": "Habitat mast"},
    {"id": "uwb4", "kind": "uwb", "x": 1434.6, "y": 1567.3, "label": "UWB boxwork center"}
  ],
  "params": {
    "slope_max_deg": 25.0,
    "walk_speed_mps": 1.0,
    "o2_capacity_min": 480,
    "o2_reserve_min": 30,
    "dose_msv_per_day": 0.7,
    "nav": {
      "lora": {"sigma_m": 2.0, "max_range_m": 1500.0},
      "uwb":  {"sigma_m": 0.15, "max_range_m": 150.0},
      "beacon_antenna_m": 2.0, "suit_antenna_m": 2.0,
      "dr_growth_per_m": 0.02,
      "offroute_warn_m": 15.0, "offroute_replan_m": 30.0, "hazard_buffer_m": 10.0
    }
  },
  "layers": {
    "slope":  {"unit": "deg", "min": 0, "max": 45},
    "rough":  {"unit": "m",   "min": 0, "max": 2},
    "hazard": {"unit": "bool"},
    "cost":   {"unit": "rel", "min": 1, "max": 20},
    "pnr":    {"unit": "bool"},
    "coverage": {"unit": "beacons", "min": 0, "max": 6}
  }
}
```
- `targets[].science`：科學價值，範圍 0–1。`image` 是 POV 照片的相對路徑或 `null`。
- `layers` 說明 u8 值要怎麼還原成實際數值：`value = min + (u8 / 254) · (max - min)`。**255 保留給「不可通行／無資料」**。`bool` 圖層：0 = 否，255 = 是。

## 2. `GET /api/terrain?step=4`
回傳 3D 地形 mesh 用的高度圖。

- `step`：降採樣倍率，預設 4。輸出寬度 = `ceil(width / step)`，高度同理。
- 回應：`application/octet-stream`，內容是 **little-endian f32** 陣列，排列方式見 §0。
- 前端用法：`new Float32Array(await res.arrayBuffer())`。

## 3. `GET /api/layer/{name}`
`name` ∈ `slope | rough | hazard | cost | pnr | coverage`

| query | 用於 | 預設 |
|---|---|---|
| `step` | 全部 | 1 |
| `mode` | `cost` | `balanced` |
| `x`, `y` | `pnr`：目前位置 | 基地 |
| `o2_min` | `pnr`：剩餘 O2（分鐘） | `o2_capacity_min` |
| `elapsed_min` | `pnr`（保留欄位） | 0 |

回應：`application/octet-stream`，**u8** 陣列，排列方式見 §0；值的意義見 `meta.layers`。
- `pnr` 圖層：255 代表「走得到、而且走得回基地」（安全區域），0 代表不安全。
- `coverage` 圖層：每格可見信標數（0–6，以 4×4 格為一區塊計算）。

## 4. `POST /api/route`
```json
// request
{"start": [400.0, 300.0], "goal": [1500.0, 1650.0], "mode": "safe"}
```
```json
// response 200
{
  "mode": "safe",
  "path": [[401.0, 301.0, -4480.2], [403.0, 303.0, -4480.0]],
  "length_m": 2134.5,
  "eta_min": 58.3,
  "dose_msv": 0.028,
  "max_slope_deg": 14.2,
  "min_clearance_m": 18.0,
  "risk": 0.21,
  "cost": 3412.7,
  "notes": ["Detour east to keep >15 m from 27° scarp"]
}
```
- `path`：每格中心的 `[x, y, z]`，已做簡化（Douglas–Peucker，容許誤差 1 格）。
- `min_clearance_m`：整條路線離危險區的最近距離。
- `risk`：0–1，是坡度、離危險距離、劑量的綜合分數，**越低越安全**。
- `notes`：給人看的繞道說明，最多 5 條。

## 5. `POST /api/routes/compare`
```json
// request
{"start": [400.0, 300.0], "goal": [1500.0, 1650.0]}
```
```json
// response 200
{"safe": {<Route>}, "balanced": {<Route>}, "science": {<Route>}}
```
`<Route>` 和 §4 的回應格式相同。如果某個模式找不到路線，該欄位為 `null`。

## 6. `POST /api/replan`
EVA 進行中發生狀況時呼叫：回報新障礙，或 O2 低於預期。
```json
// request
{
  "pos": [900.0, 1000.0],
  "goal": [1500.0, 1650.0],
  "mode": "safe",
  "obstacles": [{"x": 1000.0, "y": 1100.0, "r": 25.0}],
  "elapsed_min": 30,
  "o2_min": 120
}
```
```json
// response 200
{
  "route": {<Route>} | null,
  "must_return": false,
  "return_route": {<Route>} | null,
  "reason": "ok | obstacle_rerouted | goal_beyond_pnr | o2_low | no_path"
}
```
- 判斷規則：如果「走到目標」加上「從目標走回基地」的總時間，再加上 `o2_reserve_min`，超過 `o2_min`，就設 `must_return = true`。這時 `route` 為 `null`，並提供 `return_route`（從 `pos` 回基地的路線）。
- `obstacles` 會**累積**：前端每次都要傳**目前已知的全部**障礙，後端不保存狀態。

## 7. `POST /api/localize/sim` — 本地信標定位（**模擬量測**）
不靠地球、不靠 GPS：用基地／探測車／中繼站的 LoRa 信標（長距離）和沿路線佈設的 UWB 信標（短距離高精度）測距定位。
後端用 DEM 判斷哪些信標有視線，再把真實距離加上高斯雜訊當作「量測」——**這是模擬**，回應中 `simulated: true`。
```json
// request
{"true_pos": [900.0, 1000.0], "prev_estimate": [897.5, 1001.2], "prev_sigma": 2.1, "step_m": [3.0, 2.5], "seed": 42}
```
```json
// response 200
{
  "estimate": [899.4, 1000.8],
  "sigma_m": 1.9,
  "visible_beacons": [{"id": "hab", "kind": "lora", "x": 315.2, "y": 245.8, "range_m": 958.3}],
  "mode": "multilateration",
  "simulated": true
}
```
- `step_m`：自上次估計以來的位移 [dx, dy]（步數／慣性量測），航位推算用。
- 可見信標 ≥ 3 → `mode: "multilateration"`（Gauss–Newton 加權最小平方）；否則 `"dead_reckoning"`，`sigma_m` 每走 1 m 增加 `dr_growth_per_m`。
- 選填 `disabled: ["hab", ...]`：失聯的信標 id（例如和基地斷線）。選填 `extra_beacons: [{"id","kind","x","y","label"}]`：太空人途中自行布設的信標。
- 信標擠在一起導致幾何退化、多點定位誤差反而比航位推算大時，改回航位推算。

## 8. `POST /api/track` — 偏離路線偵測（HUD 用）
```json
// request
{"pos": [899.4, 1000.8], "sigma_m": 1.9, "path": [[x, y, z], ...], "lookahead_m": 25}
```
```json
// response 200
{
  "xte_m": 4.2, "along_m": 812.0, "remaining_m": 1588.0,
  "next": [915.0, 1018.0], "side": -1,
  "status": "on_route | off_route | replan", "reason": "on_route | off_route | far_off_route | off_route_near_hazard",
  "clearance_m": 41.0, "t_return_min": 19.5, "coverage": 3
}
```
- `xte_m`：到路線折線的垂直距離（cross-track error）。`next`：沿路線前方 `lookahead_m` 的導引點（給方向箭頭）。
- `side`：+1 = 太空人在路線左側（應往右修正）、−1 = 在右側（應往左修正）。
- 判斷規則：`xte > 30 m` → `replan`；`xte > 15 m` 且離危險區 `< 10 m` → `replan`；`xte > 15 m` 且 `> 2σ` → `off_route`；其餘 `on_route`。
  （危險緩衝條件只在已偏離時生效：science 路線本身就會經過離危險區 2 m 的地方。）
- `t_return_min`：從此處走回基地所需時間（不含新回報的障礙），HUD 用來判斷「必須返回」。

---

## WebAssembly 介面（`mars-wasm`）
`WasmEngine` 的方法與上面的端點一一對應，請求／回應都是同樣的 JSON 字串：
`meta()`、`terrain(step)`、`layer(name, query_json)`、`route(json)`、`compare(json)`、`replan(json)`、`localize_sim(json)`、`track(json)`。
二進位網格（terrain／layer）回傳 `Uint8Array`：前 12 bytes 是 header（`w: u32`、`h: u32`、`cell_m: f32`，little-endian），後面是資料。
錯誤以 JSON 字串丟出（格式同 §0）。前端只透過 `web/src/api.js` 呼叫，不需要知道是 WASM 還是 HTTP。

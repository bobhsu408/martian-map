<!-- SI-generated: drafted by Claude Code (SI tool); reviewed and maintained by the team. -->
# Martian Map Engine — API 契約 v1

後端：`mars-server`（Rust / axum），預設 `http://localhost:8080`。同一個 server 也提供 `web/dist` 靜態檔，**全程離線**。
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
  "params": {
    "slope_max_deg": 25.0,
    "walk_speed_mps": 1.0,
    "o2_capacity_min": 480,
    "o2_reserve_min": 30,
    "dose_msv_per_day": 0.7
  },
  "layers": {
    "slope":  {"unit": "deg", "min": 0, "max": 45},
    "rough":  {"unit": "m",   "min": 0, "max": 2},
    "hazard": {"unit": "bool"},
    "cost":   {"unit": "rel", "min": 1, "max": 20},
    "pnr":    {"unit": "bool"},
    "svf":    {"unit": "ratio", "min": 0, "max": 1}
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
`name` ∈ `slope | rough | hazard | cost | pnr | svf`（`svf` 是加分項，未實作時回 404）

| query | 用於 | 預設 |
|---|---|---|
| `step` | 全部 | 1 |
| `mode` | `cost` | `balanced` |
| `x`, `y` | `pnr`：目前位置 | 基地 |
| `o2_min` | `pnr`：剩餘 O2（分鐘） | `o2_capacity_min` |
| `elapsed_min` | `pnr`（保留欄位） | 0 |

回應：`application/octet-stream`，**u8** 陣列，排列方式見 §0；值的意義見 `meta.layers`。
- `pnr` 圖層：255 代表「走得到、而且走得回基地」（安全區域），0 代表不安全。

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

## 7. `POST /api/localize`（加分項，可能不實作）
```json
// request
{"odometry": [[dx, dy], ...], "sun_obs": [{"t_utc": "...", "azimuth_deg": 0.0}]}
// response
{"estimate": [x, y], "sigma_m": 12.0, "particles": [[x, y], ...]}
```

---

## 前端 mock 模式
後端完成前，前端照本文件用 `web/public/mock/` 下的假資料開發：
- `meta.json`、`route_safe.json`、`compare.json`、`replan_return.json`
- 二進位端點（terrain／layer）在 mock 模式由前端自己產生假的高度圖。
- 在 `api.js` 用 `const MOCK = true` 切換；切到真實後端時只改這個值。

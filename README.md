# Martian Map

火星全球／Mount Sharp 的離線地圖展示與 EVA 路徑規劃原型。

目前專案使用 NASA Viking global color mosaic 建立整個火星的衛星式總覽，使用 NASA MOLA 作為全球高程資料，再用真實 NASA HiRISE DTM 與正射影像提供 Mount Sharp 的高解析度局部細節；WASM 已接上 Rust `mars-core`，可在瀏覽器中使用真實局部 DEM 執行路徑規劃與 EVA 導航。

## 目前可以做什麼

- 使用真實 HiRISE DTM 顯示 Mount Sharp 局部地形。
- 3D terrain 模式：旋轉、平移、縮放，觀察立體高程。
- 2D map 模式：類似 Google Maps 的單一火星座標地圖，可拖曳平移與滾輪縮放，北方固定朝上。
- 切換 Terrain、Slope、Hazard 等圖層。
- 使用 HiRISE 正射影像作為衛星式地表底圖。
- 使用 NASA MOLA 全球高程與彩色陰影地形作為整個火星的總覽底圖。
- 使用 NASA Viking merged color mosaic 作為全球衛星式底圖。
- 2D 模式把 `Mars global`、`Gale MOC` 與 `Mount Sharp` 疊在同一個 simple cylindrical 座標系；按鈕只是快速跳到不同縮放層，不會切換成三張互不相干的地圖。
- 全球模式支援滑鼠拖曳、滾輪縮放與東西方向無縫循環；放大到 Gale 後可繼續看到 MOC，再放大到 Mount Sharp 時可看到 HiRISE 正射影像與導航路線。
- 離線載入 `data/processed`，不需要連線到 NASA API。
- Rust/WASM/Axum 共用 A*、坡度、粗糙度、PNR 與 route planner 介面；目前瀏覽器 WASM 已能執行真實 HiRISE DEM 的導航。

目前 2D/3D 地圖展示不需要 `cargo` 或 `rustc`；使用已建好的 `?wasm` 版本進行路徑規劃也不需要執行時安裝 Rust。只有重新編譯 WASM 或啟動 Axum server 時才需要 Rust toolchain。

## 技術架構

```text
NASA MOLA PDS3 MEGDR (.IMG)
        │
        ▼
tools/preprocess_mola.py
        │
        └── data/processed/global/
            ├── dem.f32              # 全球 4 pixels/degree 高程
            ├── ortho.jpg             # MOLA 彩色陰影地形
            ├── satellite.jpg         # Viking global color mosaic
            ├── valid_mask.u8
            └── meta.json

NASA HiRISE PDS3 DTM + ORTHO
        │
        ▼
tools/preprocess.py
        │
        └── data/processed/           # Mount Sharp 約 2 km × 2 km
            ├── dem.f32
            ├── ortho.jpg
            ├── valid_mask.u8
            └── meta.json

NASA MGS/MOC Atlas regional tile
        │
        ▼
tools/preprocess_moc.py
        │
        └── data/processed/regional/moc.jpg
                │
                ▼
        Vite + Three.js frontend
          ├── 3D terrain view
          ├── 2D map view
          └── local slope / roughness / hazard display

未來：
Rust mars-core → WASM worker 或 Axum server → route planner / EVA navigation
```

主要目錄：

```text
martian-map/
├── data/
│   ├── raw/official/hirise/       # NASA 原始資料，不進 Git
│   └── processed/                 # 前端展示用 DEM package
├── docs/
│   ├── API.md                     # 前後端 API 契約
│   └── HIRISE_PREPROCESS_PLAN.md  # 資料前處理企畫與待辦
├── tools/
│   ├── preprocess.py              # HiRISE .IMG → processed data
│   ├── preprocess_mola.py         # MOLA 全球 .IMG → global package
│   ├── preprocess_viking.py       # Viking global tiles → satellite.jpg
│   ├── preprocess_moc.py          # MOC regional tile → moc.jpg
│   └── validate_processed.py      # 資料完整性與座標方向驗證
├── engine/                        # Rust core / WASM / Axum
└── web/                           # Vite + Three.js frontend
```

## 快速開始：地圖展示

需求：Node.js 18 以上、Python 3.10 以上與 NumPy。

### 1. 安裝前端 dependency

```powershell
cd D:\NASAHackathon\martian-map\web
npm install
```

### 2. 確認處理後資料存在

```powershell
cd D:\NASAHackathon\martian-map
python tools\validate_processed.py data\processed
```

預期會看到 DEM 尺寸、解析度、有效資料比例，以及通過的檢查項目。

### 3. 啟動前端

```powershell
cd D:\NASAHackathon\martian-map\web
npm run dev
```

開啟 Vite 顯示的網址，通常是：

```text
http://localhost:5173/
```

開啟後：

1. 用左側 `3D terrain / 2D map` 切換閱讀方式。
2. 3D 模式拖曳旋轉、滾輪縮放。
3. 2D 模式拖曳平移、滾輪縮放，北方固定朝上。
4. 用 `Map layer` 切換地形或坡度圖層。
5. 在 `Map extent` 依序選 `Mars global`、`Gale MOC` 或 `Mount Sharp`；這三層分別是全球總覽、區域 orbital context 與公尺級局部 DEM。

### 4. 建立 production build

```powershell
cd D:\NASAHackathon\martian-map\web
npm run build
npm run preview
```

Vite build 會將局部、全球與 `data/processed/regional/` 內的地圖資產打包到 `dist/data/`。原始 `.IMG`、大型原始 PNG 不會被複製到前端。

## 全球火星資料

全球總覽使用 NASA/ASU Viking merged color mosaic 的衛星式影像，並搭配 NASA PDS 的 MOLA MEGDR 16 pixels/degree 地形資料；MOLA 前處理時降採樣為 4 pixels/degree，約為赤道 14.8 km/cell。全球衛星底圖目前由 8 張 5760×5760 官方瓦片縮成 8192×4096 texture，適合作為全球總覽，不是 CTX/HiRISE 導航解析度。

原始資料放在：

```text
data/raw/official/mola/meg016/megt90n000eb.img
data/raw/official/mola/meg016/megt90n000eb.lbl
data/raw/official/viking_large/*.png
```

重新產生全球 package：

```powershell
cd D:\NASAHackathon\martian-map
python tools\preprocess_mola.py `
  --input data\raw\official\mola\meg016\megt90n000eb.img `
  --label data\raw\official\mola\meg016\megt90n000eb.lbl `
  --output data\processed\global `
  --target-ppd 4 `
  --force
```

此輸出供全球瀏覽與定位使用；不可直接當成太空人尺度的路徑規劃網格。正式導航仍應切換到具有公尺級 DEM 的 HiRISE／CTX 局部資料。

### Gale 區域 MOC context

Mount Sharp 位於約 `137.3°E, 4.8°S`，本專案下載涵蓋 `120–150°E, 30°S–0°` 的 NASA MGS/MOC Atlas tile，並輸出為 `data/processed/regional/moc.jpg`。這一層是介於全球 Viking 與局部 HiRISE 之間的視覺與地理定位層，不直接提供公尺級路徑規劃 DEM。

```powershell
python tools\preprocess_moc.py `
  --input data\raw\official\moc\moc_256_N-30_120.png `
  --output data\processed\regional `
  --force
```

重新產生全球衛星式底圖：

```powershell
python tools\preprocess_viking.py `
  --input data\raw\official\viking_large `
  --output data\processed\global `
  --max-width 8192 `
  --force
```

## 重新產生 HiRISE processed data

如果要換資料或重新裁切區域：

```powershell
cd D:\NASAHackathon\martian-map

python tools\preprocess.py `
  --input data\raw\official\hirise\DTEEC_001488_1750_001752_1750_U02.IMG `
  --output data\processed `
  --crop-width-m 2000 `
  --crop-height-m 2000 `
  --center-lat -4.83 `
  --center-lon 137.30 `
  --name "Mount Sharp HiRISE local navigation DEM" `
  --base-x 1000 `
  --base-y 1000 `
  --ortho-input data\raw\official\hirise\PSP_001488_1750_RED_C_01_ORTHO.JP2
```

前處理工具會：

- 解析 PDS3 label。
- 讀取 32-bit little-endian HiRISE 高程。
- 依經緯度裁切區域。
- 轉成專案使用的 south-first row-major 格式。
- 產生 `dem.f32`、`valid_mask.u8`、`meta.json`。
- 若提供 `--ortho-input`，同步產生裁切後的 `ortho.jpg`，供 Three.js GPU texture 使用。
- 記錄原始檔 SHA-256。
- 遇到 nodata 時預設停止，避免未知地形被誤當成平地。

## 執行模式

### Local DEM viewer（目前預設）

```text
http://localhost:5173/
```

使用 JavaScript 直接讀取 processed DEM，適合現在的地圖展示工作，不需要 Rust toolchain。

### WASM engine

```text
http://localhost:5173/?wasm
```

目前 `web/src/wasm/` 已包含建好的 WASM runtime。此模式會在 Web Worker 中載入真實的 `data/processed/meta.json` 與 `dem.f32`，使用 Rust `mars-core` 計算坡度、粗糙度、危險區、三種路線與 EVA 導航，不需要在執行時安裝 `cargo` 或 `rustc`。

使用方式：

1. 切換到 `Mount Sharp` 局部範圍。
2. 點擊局部 DEM 設定導航目標。
3. 按 `Plan routes (3 modes)` 比較 Safe、Balanced、Science 路線。
4. 選擇路線後按 `Start EVA`；可開啟 Autopilot，或使用方向鍵／WASD 移動。

`Mars global` 與 `Gale MOC` 是定位與上下文影像層，不會在低解析度資料上誤算太空人尺度路徑；必須切回 `Mount Sharp` 才能規劃路線。

### Axum server

```powershell
cd D:\NASAHackathon\martian-map\engine
$env:MARS_DATA = "..\data\processed"
cargo run --release -p mars-server
```

再開啟：

```text
http://localhost:8080/?server
```

此模式需要 `cargo`、`rustc` 與 Rust dependencies。

## 地圖資料格式

`dem.f32` 是 little-endian IEEE-754 `float32`，以 row-major 儲存。座標慣例：

- 原點：裁切區西南角
- `x`：向東，單位公尺
- `y`：向北，單位公尺
- 第 0 列：最南側
- `cell_m`：每格的實際公尺數

`valid_mask.u8`：

- `255`：有效高程
- `0`：nodata 或無效高程

目前 2 km crop 的有效比例為 100%。正式導航前仍需要讓 Rust core 讀取 `valid_mask.u8`，把無效格直接視為 hazard。

## 驗證

資料驗證：

```powershell
python tools\validate_processed.py data\processed
```

前端 production build：

```powershell
cd web
npm run build
```

Rust 測試（環境安裝 Rust 後）：

```powershell
cd engine
cargo test
```

## 目前限制與下一步

- 目前地圖展示已使用真實 HiRISE DEM。
- 全球 `Mars global` 已使用 Viking merged color mosaic 作為衛星式底圖，並支援水平無縫循環。
- 全球底圖仍是低解析度總覽；Gale MOC 是區域 context，尚不是 CTX/HiRISE 級別的全球光學瓦片。
- `?wasm` 模式已能使用真實 HiRISE DEM 執行路徑規劃與 EVA 導航；不帶參數的 local viewer 仍只負責展示與圖層瀏覽。
- `valid_mask.u8` 尚未被 Rust core 讀取。
- 尚未接入 CTX／HRSC 全球或區域光學影像瓦片，也尚未建立真正的多解析度 tile pyramid。

建議下一步：

1. 安裝 Rust toolchain，驗證 `World::load_processed`。
2. 讓 `valid_mask.u8` 進入 hazard 計算。
3. 讓 `valid_mask.u8` 進入 WASM/Rust hazard 計算，並補上無效區域測試。
4. 加入 CTX 全球 mosaic 的按需瓦片，提高全球縮放後的細節。

詳細資料執行狀態請看：[HiRISE 前處理企畫書](docs/HIRISE_PREPROCESS_PLAN.md)。


---

<!-- The section below is the Rust/WASM planning-engine README (merged). -->

<!-- SI-assisted: drafted by Hermes Agent (SI tool), updated by Claude Code (SI tool), reviewed by the team. -->
# Martian Map — Offline EVA Route Planner

NASA Space Apps Challenge 2026 project for the challenge "Interplanetary Survival Guide: Martian Map". It plans safe Marswalk routes for astronauts at the Mount Sharp boxwork site (Gale crater) and runs fully offline, because the Earth–Mars signal delay is 4–24 minutes.

## Features

- Penalty-based cost map (slope, roughness, buffer around hazards, science bonus)
- A* route planning in three modes (safe, balanced, science) with distance, ETA, max slope, hazard clearance, radiation dose and risk
- Point-of-no-return safe zone based on remaining suit oxygen
- On-board re-planning when a rockfall is reported or oxygen runs low
- Local radio-beacon positioning without GPS or Earth (LoRa + UWB ranging, line-of-sight on the terrain model, Gauss–Newton multilateration, dead reckoning fallback); ranges are simulated
- Off-route detection (cross-track error) with automatic re-planning from the estimated position
- Walkable 3D Mars scene (Three.js): control an astronaut, direction arrow, safety status, return-to-base warning, one-tap "return to base"
- Haptic and audio guidance: pulse pattern = which way to steer, pulse rate = how far off route, long buzz = hazard, SOS = return now
- Stackable map layers with per-layer opacity: slope, hazards, cost (safe/science), beacon coverage, point-of-no-return
- Three nested levels of detail with a view-distance slider: 2 m HiRISE EVA site → 463 m MOLA Gale crater region → whole-Mars MOLA globe

## Architecture

- engine/ is a Rust workspace: mars-core = algorithms; mars-wasm = WebAssembly build that runs the whole engine inside the browser (Web Worker); mars-server = optional axum HTTP server on 127.0.0.1:8080
- web/ is a Vite + Three.js front-end
- docs/API.md is the API contract

## Run

The web app is self-contained: the planning engine runs in the browser as WebAssembly, so it works offline once loaded.

```
cd web && npm install && npm run build && npx vite preview
```

then open the printed http://localhost:4173 URL.

Re-run data preprocessing (after downloading the raw files into `data/raw/`, see the source of `preprocess.rs`):

```
cd engine && cargo run --release -p mars-core --example preprocess -- ..
```

Rebuild the WebAssembly engine after changing Rust code (needs `rustup target add wasm32-unknown-unknown` and `cargo install wasm-bindgen-cli --version 0.2.130`):

```
./tools/build_wasm.sh
```

Optional native server: `cd engine && cargo run --release -p mars-server`, then open http://127.0.0.1:8080/?server

## Test

```
cd engine && cargo test
node tools/e2e_shots.mjs <output-dir> http://localhost:4173/   # headless Chrome walkthrough + screenshots
```

## Data (all NASA, bundled in `web/public/data/` so the app works offline)

| Level | Product | Resolution | Coverage |
|---|---|---|---|
| EVA site | MRO HiRISE DTM `DTEEC_019698_1750_019988_1750_U01` (NASA/JPL/University of Arizona, PDS) | 1.01 m, resampled to 2.02 m | 2 km × 2 km on lower NW Mount Sharp, 4.866–4.901°S, 137.358–137.393°E |
| Region | MGS MOLA global DEM 463 m (USGS Astrogeology mosaic), Gale crater crop | 463 m | 4° × 4° (≈237 km) around Gale crater |
| Globe | Same MOLA DEM, every 32nd sample | ≈15 km | Whole planet |

Only the needed rows were downloaded with HTTP range requests, then converted by `engine/crates/core/examples/preprocess.rs`.
Base, science stops and beacons on the real site are auto-selected from slope/roughness (candidates, not confirmed boxwork exposures).
A synthetic terrain generator is kept for tests and can be forced with `?synthetic`.
Beacon ranges are simulated from the terrain model. Radiation dose uses a modelled surface rate of about 0.7 mSv/day (order of Curiosity RAD measurements). All parameters are assumptions and adjustable.

## Use of SI (AI) tools

Claude Code (Anthropic) generated most of the code, marked with a "SI-generated" or "SI-assisted" comment at the top of each file; Hermes Agent drafted this README; the team chose the idea, scope, science target and design decisions, specified the beacon positioning and off-route rules, designed the guidance UI and haptic/audio encoding, and wrote hazard_mask in cost.rs; full log in docs/AI_USAGE.md.

## Team

TODO: team name and members.

# HiRISE DTM 前處理與分層導航地圖執行企畫書

## 1. 目的

本企畫將 NASA/JPL/University of Arizona 的 HiRISE Digital Terrain Model（DTM）轉換成目前 `mars-core`、Axum server、WASM 與 Three.js 前端可以直接使用的離線資料。

最終目標不是只顯示一張火星圖片，而是建立能支援太空人 EVA 導航的分層地圖：

- 地形高度（DEM）
- 坡度
- 地表粗糙度
- 岩石與障礙物
- 不可通行區域
- 路徑成本
- 通訊信標覆蓋
- Point of No Return（剩餘氧氣能否安全返回）
- 科學目標與影像

## 2. 目前資料與限制

本專案目前使用的資料：

- DTM：`data/raw/official/hirise/DTEEC_001488_1750_001752_1750_U02.IMG`
- 正射影像：`data/raw/official/hirise/PSP_001488_1750_RED_C_01_ORTHO.JP2`
- 地點：Gale Crater 的 Mount Sharp 中央山丘附近
- 原始解析度：約 1.01 m/pixel
- 原始尺寸：6,736 × 13,375
- 高程基準：Mars 2000 datum，單位為公尺
- 投影：Equirectangular，planetocentric latitude，east-positive longitude

全球總覽另外使用 NASA MOLA MEGDR：

- 原始資料：`data/raw/official/mola/meg016/megt90n000eb.img` 與 `.lbl`
- 原始解析度：16 pixels/degree
- 前端 package：`data/processed/global/`
- 目前展示解析度：4 pixels/degree，赤道約 14.8 km/cell
- 用途：整個火星的範圍瀏覽與定位，不直接用於公尺級 EVA 路徑規劃

全球視覺底圖另外使用 NASA/ASU Viking merged color mosaic：

- 原始資料：`data/raw/official/viking_large/*.png`
- 下載 8 張 5760×5760 的官方全球瓦片，約 263 MB
- 輸出：`data/processed/global/satellite.jpg`，8192×4096
- 用途：全球衛星式視覺總覽；不取代 MOLA DEM 或局部 HiRISE 導航資料

Mount Sharp 區域另外接入 NASA MGS/MOC Atlas：

- 原始 tile：`data/raw/official/moc/moc_256_N-30_120.png`
- 覆蓋範圍：120–150°E、30°S–0°，包含 Mount Sharp 約 137.3°E、4.8°S
- 原始解析度：256 pixels/degree，約 230 m/pixel
- 輸出：`data/processed/regional/moc.jpg`
- 用途：全球總覽與 HiRISE 局部之間的區域定位，不直接用於公尺級路徑規劃

原始 `.IMG` 是 PDS3 格式，不是普通的裸資料檔。檔案開頭有 label，label 會描述影像資料的偏移量、寬高、資料型別、投影與 nodata 值。直接從 byte 0 讀取會把 label 誤當成高程，因此必須先解析 PDS label。

## 3. 輸出格式

工具為 `tools/preprocess.py`，輸出到 `data/processed/`：

```text
data/processed/
├── dem.f32          # little-endian float32，row-major
├── valid_mask.u8    # 255=有效，0=nodata
└── meta.json        # 引擎設定、座標、來源與處理紀錄
```

全球總覽使用相同的 DEM package 格式，但放在獨立目錄：

```text
data/processed/global/
├── dem.f32
├── ortho.jpg        # MOLA 彩色陰影地形，不是光學衛星影像
├── satellite.jpg    # Viking merged color mosaic
├── valid_mask.u8
└── meta.json
```

區域 MOC package：

```text
data/processed/regional/
├── moc.jpg
└── meta.json
```

`meta.json` 的核心欄位必須符合 `engine/crates/core/src/world.rs` 的 `ProcessedMeta`：

```json
{
  "name": "HiRISE local navigation DEM",
  "source": "HiRISE DTM DTEEC_001488_1750_001752_1750_U02",
  "width": 1977,
  "height": 1977,
  "cell_m": 1.0117468,
  "base": [0.0, 0.0],
  "targets": [],
  "beacons": []
}
```

座標慣例與 API 契約一致：原點在裁切區西南角，`x` 向東、`y` 向北；資料列的第 0 列是最南側。這也是為什麼工具預設會把 HiRISE 原始的 north-to-south image lines 垂直翻轉成 south-first。

## 4. 執行方式

### 4.1 安裝 NumPy

工具只使用 Python 標準函式庫與 NumPy。若環境尚未安裝 NumPy：

```powershell
python -m pip install numpy
```

### 4.2 建立 2 km × 2 km 局部導航區

以下指令以資料中心附近為中心，建立 2 km × 2 km、約 1 m/cell 的資料：

```powershell
python tools/preprocess.py `
  --input data/raw/official/hirise/DTEEC_001488_1750_001752_1750_U02.IMG `
  --output data/processed `
  --crop-width-m 2000 `
  --crop-height-m 2000 `
  --center-lat -4.83 `
  --center-lon 137.30 `
  --name "Mount Sharp HiRISE local navigation DEM" `
  --base-x 1000 `
  --base-y 1000
```

若輸出目錄已有產物，工具預設拒絕覆寫；確認資料來源正確後才使用 `--force`。

### 4.3 建立較小的示範資料

開發期間可以降低解析度，將每 2×2 個原始像素平均成一格：

```powershell
python tools/preprocess.py `
  --input data/raw/official/hirise/DTEEC_001488_1750_001752_1750_U02.IMG `
  --output data/processed-2m `
  --crop-width-m 2000 `
  --crop-height-m 2000 `
  --center-lat -4.83 `
  --center-lon 137.30 `
  --sample-step 2
```

2 m/cell 通常比 1 m/cell 更適合瀏覽器展示與 A* 原型測試；最後是否使用 1 m 或 2 m，應以路徑規劃效能與任務需求測量決定。

## 5. 前處理流程

```text
HiRISE PDS3 .IMG
        │
        ├─ 解析 PDS label
        │    ├─ RECORD_BYTES / ^IMAGE
        │    ├─ LINES / LINE_SAMPLES
        │    ├─ SAMPLE_TYPE / SAMPLE_BITS
        │    ├─ MAP_SCALE / bounds
        │    └─ MISSING_CONSTANT / valid range
        │
        ├─ memory-map 高程資料
        ├─ 依經緯度裁切區域
        ├─ 翻成 south-first row-major
        ├─ 選擇原始解析度或 block mean 降採樣
        ├─ 建立 valid mask
        └─ 輸出 dem.f32、valid_mask.u8、meta.json
```

工具不會修改或覆寫 `data/raw` 的 NASA 原始檔。產物若已存在，也必須明確指定 `--force` 才會覆寫。

MOLA 全球總覽流程：

```text
MOLA PDS3 MEGDR 16 ppd
        │
        ├─ 解析 label，確認 2880 × 5760、MSB 16-bit 整數
        ├─ 轉成 south-first、little-endian float32
        ├─ block mean 降採樣至 4 ppd
        ├─ 產生 MOLA 彩色陰影總覽 texture
        └─ 輸出 data/processed/global/
```

Viking 全球衛星式底圖流程：

```text
NASA/ASU Viking merged color mosaic
        │
        ├─ 下載北、南半球各 4 張 90° 經度瓦片
        ├─ 依 0–360° 經度縮放並拼接成 8192×4096 texture
        └─ 輸出 satellite.jpg
```

MOC 區域 context 流程：

```text
NASA MGS/MOC Atlas 30°×30° tile
        │
        ├─ 驗證來源 SHA-256 與座標範圍
        ├─ 轉成瀏覽器使用的 JPEG texture
        └─ 輸出 data/processed/regional/moc.jpg + meta.json
```

## 6. 與現有系統的整合

### Rust core

`World::load_processed` 會讀取：

```text
meta.json
dem.f32
```

載入後，現有 `mars-core` 可以接著計算：

```text
DEM
 ├─ slope_deg()
 ├─ roughness()
 ├─ hazard_mask()
 ├─ cost map
 ├─ A* route
 └─ PNR / coverage / replan
```

### Axum server

設定 `MARS_DATA` 指向輸出目錄：

```powershell
$env:MARS_DATA = "..\data\processed"
cd engine
cargo run --release -p mars-server
```

若沒有 `meta.json`，server 會退回 synthetic terrain；有輸出檔案後，啟動 log 應顯示 HiRISE source 與實際網格尺寸。

### WASM / Three.js

WASM 路徑使用相同的 `meta.json + dem.f32` 格式。Three.js 顯示時要注意 API 契約中的列方向：Three.js 的平面頂點常以北側開始排列，若視覺方向顛倒，應在前端翻轉 y row，而不是修改原始 DEM。

## 7. Nodata 與導航安全

這是本企畫最重要的安全限制。

工具預設遇到 nodata 會停止，避免把未知地形誤當成平坦地面。只有在確認後才可使用：

```powershell
--allow-nodata
```

此模式會把沒有有效高程的格子寫成 `NaN`，並另外輸出 `valid_mask.u8`。目前 `mars-core` 的 `ProcessedMeta` 尚未讀取 `valid_mask.u8`，因此在正式導航前必須再完成其中一種方案：

1. 在 core 載入 valid mask，將無效格直接標記成 hazard；或
2. 只使用完全沒有 nodata 的局部裁切區；或
3. 以經過驗證的鄰近高程補洞，並保留補洞區域的風險標記。

目前建議採用第 2 種方案做 MVP，確保路徑規劃不會穿過未知區域。

## 8. 驗證計畫

### 資料格式驗證

- PDS `SAMPLE_BITS=32` 且 `SAMPLE_TYPE=PC_REAL`。
- `dem.f32` 位元組數等於 `width × height × 4`。
- `valid_mask.u8` 位元組數等於 `width × height`。
- `meta.json` 的 `width`、`height`、`cell_m` 與實際檔案一致。
- 高程最小值與最大值落在 PDS label 宣告範圍內。

### 座標驗證

- 西南角的 local coordinate 應接近 `(0, 0)`。
- 東西方向增加時，經度應增加。
- 南北方向增加時，planetocentric latitude 應增加。
- 影像翻轉後，`dem.f32` 第 0 列必須是最南側。
- 用 HiRISE 正射影像檢查明顯地形是否上下顛倒。

### 引擎驗證

```powershell
cd engine
cargo test
```

再以 `MARS_DATA=..\data\processed` 啟動 server，確認：

- `/api/meta` 回傳 HiRISE source。
- `/api/terrain` 可讀取高度。
- `/api/layer/slope` 與 `/api/layer/rough` 不全為 0。
- 起點與終點落在有效地形時可以產生路線。
- nodata 不會被規劃成可通行區域。

## 9. 分層地圖後續工作

### MVP 必做

1. 完成 HiRISE DTM 轉換。
2. 以 DTM 產生坡度與粗糙度。
3. 將 nodata 視為 hazard 或限制在完全有效的 crop。
4. 接上現有 Rust route planner。
5. 在 Three.js 顯示 DEM、slope、hazard 與 route。

### 第二階段

1. 加入 HiRISE orthophoto 作為視覺紋理。
2. 完成 MOLA 全球總覽與 Mount Sharp 局部範圍切換。
3. 用 CTX 或 USGS Gale mosaic 建立光學區域背景。
4. 加入 Curiosity 實景影像與 boxwork 科學目標。

### 第三階段

1. 加入 CRISM 礦物圖層。
2. 加入 THEMIS 熱慣量圖層。
3. 將科學圖層轉成 route cost 的 science bonus，而不是直接當成 hazard。
4. 建立多解析度瓦片與離線 package。
5. 以實際任務情境測量 WASM 記憶體、A* 時間與前端 FPS。

## 10. 成功標準

本階段完成條件：

- 一行指令可以由 HiRISE `.IMG` 產生 `dem.f32` 與 `meta.json`。
- 產生的資料可以被 `World::load_processed` 讀取。
- 輸出座標符合專案的西南角原點、東北方向與 south-first 慣例。
- 原始資料保持不變且有 SHA-256 provenance 紀錄。
- 有 nodata 時工具預設停止，不會靜默產生可能誤導導航的地圖。
- 現有合成地形功能仍可作為沒有真實資料時的 fallback。

## 11. 執行追蹤與待辦事項

### 已完成

- [x] 解析 HiRISE PDS3 label：資料偏移、寬高、型別、投影、nodata。
- [x] 建立 `tools/preprocess.py`，支援經緯度中心裁切、south-first 轉換與降採樣。
- [x] 建立 2 km × 2 km 的 `data/processed` HiRISE 局部 DEM。
- [x] 產生 `dem.f32`、`valid_mask.u8` 與含 SHA-256 provenance 的 `meta.json`。
- [x] 驗證 DEM 與 mask 的位元組大小、finite 值和有效格比例。
- [x] 驗證 1 m/cell 輸出第一列為來源南側、最後一列為來源北側。
- [x] 預設遇到 nodata 時停止，避免未知地形被誤當成可通行地面。
- [x] 建立 `tools/validate_processed.py`，讓資料驗證可以重複執行。
- [x] 建立不依賴 Rust/WASM 的 Three.js 本地 DEM viewer backend。
- [x] Vite 只提供 `data/processed` 與 `data/processed/global`，不公開原始 HiRISE/MOLA `.IMG`。
- [x] Three.js 載入真實 HiRISE DEM，支援 OrbitControls 縮放與旋轉。
- [x] 瀏覽器驗證地形展示與 Slope 圖層切換。
- [x] 由匹配的 HiRISE 正射影像產生裁切後 `ortho.jpg`。
- [x] 將正射影像接入 Three.js 2D/3D 地圖材質並納入 Vite build。

### 尚待完成

- [ ] 讓 `mars-core` 載入並使用 `valid_mask.u8`，將無效格直接標成 hazard。
- [ ] 用 `World::load_processed` 實際載入 `data/processed`。
- [ ] 啟動 Axum server，確認 `/api/meta`、`/api/terrain`、`/api/layer/slope` 與 `/api/layer/rough`。
- [ ] 在有 Rust toolchain 後，用 `cargo test` 與 Axum server 直接確認 HiRISE DEM 的坡度、粗糙度與 A* 路徑結果。
- [x] 讓瀏覽器 WASM 使用 `WasmEngine::from_processed` 載入真實 HiRISE `meta.json + dem.f32`。
- [x] 將 WASM 路徑規劃接回真實 DEM，支援 Safe、Balanced、Science 三種路線與 EVA 導航。
- [x] 在 Three.js 顯示真實 DEM，確認影像與地形沒有上下或東西方向顛倒。
- [x] 將 HiRISE 正射影像接成視覺紋理。
- [x] 下載 NASA PDS MOLA 16 ppd 全球地形與 label。
- [x] 建立 `tools/preprocess_mola.py`，輸出 4 ppd 全球 DEM package。
- [x] 將 MOLA 全球資料、Viking 衛星式底圖、Gale MOC 區域 context、局部 HiRISE 與 2D 範圍切換接入 Three.js/Vite。
- [x] 全球 2D 地圖支援滑鼠拖曳、滾輪縮放與東西方向無縫循環。
- [x] 將 Viking、MOC、HiRISE 三層 2D 影像統一到同一個 simple cylindrical 火星座標系，改為同一張可連續縮放的地圖。
- [ ] 建立科學目標 `targets.json`，並以來源連結與座標紀錄每一個目標。
- [x] 加入 NASA MGS/MOC Atlas 作為 Gale 區域光學背景。
- [ ] 以 CTX 或 USGS Gale mosaic 升級區域光學背景解析度。
- [ ] 將全球 Viking/MOC/CTX 影像升級為多解析度 tile pyramid。
- [ ] 將 CTX global mosaic 以按需 4°×4° tile 接入，避免下載 TB 級完整資料。
- [ ] 在 Rust 工具鏈可用後重新執行 `cargo test` 與資料整合測試。

### 本次執行紀錄

2026-11-14：已完成前處理工具、2 km 局部資料產生、MOLA 全球資料下載與 4 ppd package、Viking 全球衛星式底圖下載與拼接、Gale MOC 區域 context、格式驗證、座標列方向驗證、Three.js 單一火星座標 2D 地圖、HiRISE 正射影像與多層 texture pipeline，以及瀏覽器 WASM 使用真實 HiRISE DEM 的路徑規劃與 EVA 導航接入。已完成 Vite production build，並用 Node WASM runtime 實際建立 1977×1977 DEM engine、比較三種路線；尚未執行 `cargo test` 或 Axum server 整合測試，因當前環境沒有 `cargo`/`rustc` 指令。CTX 5 m/pixel 全球 mosaic 因完整資料達 TB 級，保留為按需 tile 的後續工作。

資料驗證指令：

```powershell
python tools/validate_processed.py data/processed
```

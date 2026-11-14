# 專案地圖資料目錄

本文整理目前專案納入地圖展示與導航原型的資料。解析度與範圍依專案 metadata 記錄；全球概覽資料不應被當成太空人步行導航精度。

## 資料總覽

| 資料 | 來源與範圍 | 專案內解析度／尺寸 | 用途與限制 |
|---|---|---|---|
| HiRISE DTM（Mount Sharp） | NASA/JPL/University of Arizona HiRISE DTM `DTEEC_001488_1750_001752_1750_U02`；Mount Sharp/Gale 局部裁切，約 2 km × 2 km | 約 1.012 m/cell；1977 × 1977 | 局部 3D 地形、坡度／粗糙度／危險圖層及 Rust 路徑規劃輸入。這是目前具有公尺級高程的導航區域，不代表全火星都有同等精度。 |
| HiRISE 正射影像 | 與 Mount Sharp HiRISE DTM 配對的 orthophoto，處理後輸出 JPEG | 約 2 km × 2 km；實際輸出影像像素尺寸未由此 metadata 記載 | 局部衛星式視覺底圖，與 DTM 對應；影像本身不提供高程。 |
| HiRISE DTM（NW Mount Sharp） | NASA/JPL/University of Arizona HiRISE DTM `DTEEC_019698_1750_019988_1750_U01`，西北 Mount Sharp 局部裁切 | 2.023 m/cell；1024 × 1024 | 第二個局部站點資料。若用於導航，須確保導航引擎已載入此站的配套 terrain、metadata 與圖層。 |
| MOLA 全球高程 | NASA MGS MOLA MEGDR，來源 16 pixels/degree，專案降採樣至 4 pixels/degree；全火星 | 1440 × 720；約 14.8 km/cell（赤道附近） | 全球地形概覽與地貌定位；解析度不適合步行路線規劃。 |
| Viking 全球彩色鑲嵌 | ASU/NASA Viking MDIM merged color mosaic，由全球影像瓦片拼接 | 專案 `satellite.jpg` 為 8192 × 4096；來源瓦片 5760 × 5760 | 全球衛星式底圖，適合瀏覽與定位；不含高程，也不是公尺級導航影像。 |
| MOLA 彩色陰影地形影像 | 由全球 MOLA 高程著色與陰影處理產生 | 全球範圍，與 MOLA 高程同尺度 | 全球地貌視覺化底圖；呈現的是地形高程，不是光學衛星照片。 |
| Gale MOC Atlas 區域影像 | NASA MGS/MOC Atlas 廣角可見光區域鑲嵌；120–150°E、30°S–0° | 256 pixels/degree；7680 × 7680 | 全球與局部 HiRISE 之間的區域背景，用於 Gale 定位；不是高程 DEM，不能獨立計算安全路線。 |

## 專案中的資料檔

| 路徑 | 內容 |
|---|---|
| `data/processed/dem.f32` | Mount Sharp HiRISE 高程；little-endian float32、row-major、south-first。 |
| `data/processed/valid_mask.u8` | HiRISE 有效資料遮罩；255 有效、0 無效。 |
| `data/processed/ortho.jpg` | HiRISE 局部正射影像。 |
| `data/processed/meta.json` | HiRISE 尺寸、解析度、座標範圍、來源與處理資訊。 |
| `data/processed/global/dem.f32` | 全球 MOLA 高程的 float32 處理版本。 |
| `data/processed/global/valid_mask.u8` | 全球 MOLA 有效資料遮罩。 |
| `data/processed/global/ortho.jpg` | MOLA 彩色陰影地形影像。 |
| `data/processed/global/satellite.jpg` | Viking 全球彩色鑲嵌影像。 |
| `data/processed/global/meta.json` | 全球資料來源、範圍、解析度與 provenance。 |
| `data/processed/regional/moc.jpg` | Gale MOC Atlas 區域影像。 |
| `data/processed/regional/meta.json` | MOC 覆蓋範圍、投影、解析度與來源資訊。 |
| `web/public/data/site/` | 前端預設 HiRISE 站點的 `dem.f32` 與 `meta.json`。 |
| `web/public/data/site_nw/` | NW Mount Sharp 站點的 `dem.f32` 與 `meta.json`。 |
| `web/public/data/global/` | 全球 MOLA `mars.i16` 及 metadata，供前端球面地形使用。 |
| `web/public/data/region/` | Gale 區域 `gale.i16` 及 metadata，供前端區域地形使用。 |

## 座標、用途與限制

- 局部 HiRISE DEM 的 `x` 向東、`y` 向北，原點在裁切區西南角；輸出 DEM 第 0 列位於南側。
- 全球 MOLA 與 Gale MOC 使用簡單圓柱投影，東經為正；MOLA metadata 記錄 south-first，MOC 記錄 north-first。
- MOLA 的約 14.8 km/cell 是全球概覽尺度。MOC 的 pixels/degree 是角度解析度，換算成地面距離會隨緯度改變。
- Viking 與 MOC 是影像；只有 DEM 提供高程。安全路線計算需要對齊且有效的高程資料。
- 目前分層地圖以全球及區域資料提供情境與定位，導航計算範圍限於局部 HiRISE DEM 覆蓋區。

## 資料來源

- [NASA PDS Geosciences Node：MGS MOLA MEGDR](https://pds-geosciences.wustl.edu/missions/mgs/megdr.html)
- [NASA/ASU：Viking MDIM Color Mosaic](https://www.mars.asu.edu/data/mdim_color/)
- [NASA/ASU：MOC Atlas](https://www.mars.asu.edu/data/moc_256/)
- HiRISE 產品識別碼及原始檔 provenance 記錄於 `data/processed/meta.json`；原始檔位址依工作站而異。

## 驗證

可執行 `python tools/validate_processed.py data/processed` 檢查主要 processed DEM 的尺寸、檔案大小、有效遮罩、來源雜湊、列方向與正射影像。metadata 內記錄的來源與解析度不等於已完成導航安全或幾何精度驗證。

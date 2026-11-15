<!-- SI-generated: drafted by Claude Code (Anthropic, SI tool); the team chose the architecture and division of work and reviewed it. -->
# 開發計畫：Martian Map 離線 EVA 任務規劃系統（Rust 後端 + Three.js 前端）

## Context
- 比賽：NASA Space Apps 2026「Interplanetary Survival Guide: Martian Map」，**提交截止 2026-11-15 23:59**（約 30 小時）。
- 目標：做出一個 **完全離線** 的火星 EVA 規劃系統 demo。主軸是「地火通訊延遲 4–24 分鐘，計算必須在本地完成」。
- 分工：使用者負責後端演算法（Rust）。前端規劃來不及等，先由本計畫定好 **API 契約** 和 Three.js 骨架，前端隊友照契約接手。
- 目前狀態：專案資料夾只有 `比賽資料整理.md`；**本機沒有 Rust**（要先裝 rustup），也沒有 GDAL；已有 Node 25 和 Python 3.14。
- Demo 為主：功能求「跑得動、看得懂、說得清」，不求完整。
- **科學目標（已決定）**：研究 Gale 撞擊坑 **Mount Sharp 的 boxwork 網格狀礦脈構造**（好奇號 2025 年研究過的地區，代表古地下水活動和可居住性）。
- **Demo 故事**：太空人從基地出發，選擇路線前往 boxwork 採樣點 → 途中遇到落石，系統自動改道 → O2 消耗比預期快，安全範圍縮小，系統提示提早返回。

## ⚠ 分工調整（2026-11-14，依台灣評審公告）
評審重視原創、要求完整揭露 AI 使用。**本節優先於下方所有分工描述。**
- **團隊親自完成**：科學目標與地點理由、`cost.rs` 的權重和門檻（附理由）、情境參數（基地、落石、O2）、路線比較與 replan 的判斷邏輯、Demo 故事、英文提交初稿。
- **Claude**：解釋原理、寫骨架（簽名、結構、標成 `#[ignore]` 的測試加提示）、審查、除錯、英文文法潤飾（不改內容）。
- **Hermes**：只做 README、格式整理；**不再負責翻譯或起草英文提交內容**（原 H4 取消，H5 改為只整理格式）。
- 每一步的 AI 使用都記錄在 `docs/AI_USAGE.md`；團隊自己的修改由自己 commit。

## 架構總覽
```
[一次性前處理 Python] DEM GeoTIFF ─► data/processed/dem.f32 + meta.json + targets.json
                                          │
[Rust engine]  mars-core（演算法 lib） ◄───┘
               mars-server（axum，localhost:8080）── 同時提供 /api/* 和 web/dist 靜態檔
                                          │  單一執行檔，拔網路也能跑
[Three.js web] Vite 建置 ─► 3D 地形 + 圖層疊加 + 路線 + 情境操作面板
```
- **Rust 不依賴任何 C 函式庫**（不用 gdal crate）：DEM 先由 Python 轉成 raw little-endian f32 和 JSON，Rust 直接讀，編譯快也穩。
- 圖層以 **raw u8 二進位** 傳給前端，用 `THREE.DataTexture` 加色階上色，所以後端不需要影像處理 crate。

## 專案結構
```
nasa/
  docs/API.md                 # API 契約（Phase 0 第一件事）
  tools/preprocess.py         # GeoTIFF → dem.f32 / meta.json（rasterio + numpy）
  data/raw/ (gitignore)  data/processed/
  scenarios/*.json            # 預先算好的情境結果：golden test 用，也是 demo 備案
  engine/                     # Cargo workspace
    crates/core/src/
      grid.rs      # Grid<T>、座標換算（格 ↔ 公尺）、讀 dem.f32
      synth.rs     # 合成地形（value noise + 坑 + 岩塊），真資料到手前就能開發和測試
      terrain.rs   # 坡度（Horn 法）、粗糙度（局部標準差）、rayon 平行化
      edt.rs       # 精確歐氏距離轉換（Felzenszwalb 兩趟法，O(n)）
      cost.rs      # 懲罰成本圖：硬限制 + 軟懲罰 + 緩衝區；Mode 權重表
      astar.rs     # 8 鄰接 A*，邊成本 = 距離 × 兩格平均成本
      dijkstra.rs  # 從基地出發的全圖 Dijkstra（返回時間場）
      eva.rs       # 步行速度模型（依坡度修正的 Tobler 函數）、O2 消耗、劑量
      pnr.rs       # 不歸點：可達且能返回的區域
      route.rs     # 路線統計：長度、ETA、最大坡度、最小離危險距離、劑量、風險分數、繞道原因
      replan.rs    # 加入新障礙（圓盤）→ 局部更新 hazard、EDT、cost → 重跑 A*
      sun.rs       # [加分] Mars24 太陽位置
      svf.rs       # [加分] 天空可視角（輻射遮蔽、陰影）
      localize.rs  # [加分] 粒子濾波（航位推算 + 太陽方位）
    crates/core/tests/  benches/
    crates/server/src/{main.rs, state.rs, api.rs}
  web/                        # Vite + three
    src/{main.js, api.js, terrain.js, layers.js, route.js, hud.js, scenarios.js}
```

### 主要 crate
`axum`、`tokio`、`tower-http`（ServeDir、CORS）、`serde`/`serde_json`、`rayon`、`anyhow`；
測試用 `proptest`、`insta`（快照）、`criterion`（benchmark），以及 `pathfinding`（**只當測試 oracle**，拿來驗證自寫的 A*）。

## 核心演算法規格
- **坡度門檻與權重全部放在 `cost.rs` 的 `Params` 裡**，簡報時說明是可調參數。
- 成本函數（每格）：
  ```
  hazard = slope > 25° ∪ rock_mask ∪ 回報障礙   → cost = ∞
  cost = 1 + W_slope·(slope/25)² + W_rough·rough_norm
           + W_buf·exp(-d/σ)  (d = EDT 到 hazard 的距離, 單位 m)
           + W_rad·rad_norm + W_comm·comm_dead − W_sci·science_bonus（下限 0.1）
  ```
- 三種 Mode：`safe`（W_buf、W_slope 高，σ=20m）、`balanced`、`science`（W_sci 高，σ=8m）。
- A* 的啟發函數 = 歐氏距離 × 最小格成本（0.1），保證 admissible。
- **PNR**：先做 `T_ret = dijkstra(基地, 時間成本)`。某格「安全」的條件是 `t_elapsed + t(當前→該格) + T_ret(該格) + reserve ≤ O2_remaining`。
- **Replan**：新障礙寫進 hazard，重算 EDT 和 cost（整張圖重算，目標 < 200 ms），再從目前位置跑 A*；若目標已超出 PNR 範圍，回傳 `must_return=true` 和回基地的路線。
- 劑量：地表基準約 0.7 mSv/天（Curiosity RAD 量級）× 時間 × svf 修正（**明確標示為模型推估**）。

## API 契約（docs/API.md；座標一律用公尺，原點在 DEM 左下角，x 朝東、y 朝北）
| Method | Path | 說明 |
|---|---|---|
| GET | `/api/meta` | `{width,height,cell_m,z_min,z_max,base:[x,y],targets:[{id,name,x,y,science,desc}]}` |
| GET | `/api/terrain?step=4` | binary f32 高度（降採樣後給 mesh 用），header 帶 `X-Width`/`X-Height` |
| GET | `/api/layer/{slope\|rough\|hazard\|cost\|pnr\|svf}?mode=&o2_min=` | binary u8（0–255），前端自己套色階 |
| POST | `/api/route` | `{start,goal,mode}` → `{path:[[x,y,z]],length_m,eta_min,dose_mSv,max_slope_deg,min_clearance_m,risk,notes:[...]}` |
| POST | `/api/routes/compare` | `{start,goal}` → `{safe,balanced,science}` 三條路線 |
| POST | `/api/replan` | `{pos,goal,mode,obstacles:[{x,y,r}],elapsed_min,o2_min}` → `{route,must_return,return_route?}` |
| POST | `/api/localize` | [加分] `{odometry,sun_obs}` → `{particles,estimate,sigma_m}` |

## 前端（Three.js）功能
1. 用 `PlaneGeometry` 和 `/api/terrain` 做位移，產生 3D 地形；搭配 OrbitControls；z 軸可以誇張化。
2. 圖層切換：DataTexture 加 shader 色階，疊在地形上（坡度、危險區、成本、PNR）。
3. 點選起點和終點（或選科學目標），畫出三條比較路線（TubeGeometry，三種顏色），旁邊顯示統計卡片。
4. 情境按鈕：「▶ 開始 EVA」讓太空人標記沿路線移動；「⚠ 前方落石」加障礙並 replan；「O2 消耗加速」讓 PNR 範圍縮小，系統提示返回。
5. 畫面右上角標示「OFFLINE · 本地運算 · 延遲 0 ms」，強化主軸。
- 只用 npm 安裝的套件（three、lil-gui），不從 CDN 載入，確保完全離線。

## 執行方式（已決定：Claude 做核心，Hermes 做雜務，不派 Claude 子代理以節省 token）
- 本機有 Hermes Agent v0.23.1（`/Users/bobhsu/.local/bin/hermes`），模型**維持免費的 `upstage/solar-mini4:free`**。
- 因為是小型模型，只交給它**格式化、樣板、文字類**的工作；演算法和需要正確性的程式碼都由我寫。

### 分工
| 誰 | 負責 |
|---|---|
| **Claude（我）** | B0 環境、**B1 API 契約**、B2 合成地形、B3 server、**全部演算法 B4–B11**、測試 B12–B13、`tools/preprocess.py`（D2）、前端最小骨架（F1 + F8 + F2，讓前端隊友能接手擴充）、整合與離線驗收、審查 Hermes 的產出 |
| **Hermes（免費模型）** | H1–H6，見下表 |
| **前端隊友** | 在我的骨架上依 `docs/API.md` 做 F3–F7、F9 |
| **資料／簡報隊友** | D1 下載 DTM、D3–D5、P1、P5、P6 |

### 交給 Hermes 的任務
| ID | 任務 | 依賴 |
|---|---|---|
| H1 | `README.md`（專案介紹、安裝和執行步驟）、`.gitignore` | B0 |
| H2 | 依 `docs/API.md` 產生前端 mock 資料 `web/public/mock/*.json` | B1 |
| H3 | HUD 風格的 `web/src/style.css`（深色、等寬字體、OFFLINE 標示） | F1 |
| H4 | 把我寫的中文重點翻成英文提交草稿：Summary、Project Details（P2） | B8 之後 |
| H5 | 整理 References、NASA 資料清單、AI（SI）使用說明的格式（P3） | 持續 |
| H6 | 情境展示用的文字：科學點位說明、警告訊息的英文文案 | D3 |

### 呼叫與審查流程
1. 交辦前先 `git commit`，確保 Hermes 改壞了可以直接還原。
2. 在背景執行：`hermes -z "<精確規格：檔名、格式、驗收條件>" --in <repo路徑> --yolo --usage-file <scratchpad>/hermes-<ID>.json`。`--yolo` 只用在 repo 內的寫檔任務。
3. 我用 `git diff` 檢查產出：
   - JSON 用 `node -e 'JSON.parse(...)'` 驗證格式；
   - 前端用 `npm run build` 驗證；
   - 英文內容抽查有沒有捏造的數據或連結。
4. 品質不合格時：小問題由我直接修；問題太多就 `git checkout` 還原，改由我自己做（不重複丟給 Hermes 超過 1 次）。

## 任務分配表
圖例：🟢 現在就能開始（沒有前置依賴）｜🟡 要等「依賴」欄的任務完成｜⭐ 關鍵路徑（延誤會拖到整體進度）

### B｜後端演算法（Rust）— 使用者負責
| ID | 任務 | 依賴 | 狀態 |
|---|---|---|---|
| B0 | 安裝 rustup、`git init`、建立 Cargo workspace | — | 🟢⭐ |
| B1 | 寫 `docs/API.md`（**解鎖前端，最優先**） | — | 🟢⭐ |
| B2 | `synth.rs` 合成地形 | B0 | 🟢 |
| B3 | server 骨架：`/api/meta`、`/api/terrain` | B0, B2 | 🟡 |
| B4 | `terrain.rs` 坡度、粗糙度與測試 | B0 | 🟢⭐ |
| B5 | `edt.rs` 距離轉換與暴力法比對測試 | B0 | 🟢 |
| B7 | `astar.rs` 與 proptest（用隨機網格，不必等 cost） | B0 | 🟢⭐ |
| B9 | `eva.rs` 速度模型、O2、劑量 | B0 | 🟢 |
| B6 | `cost.rs` 懲罰成本圖、三種 mode；`/api/layer/*` | B4, B5 | 🟡⭐ |
| B8 | `route.rs` 統計；`/api/route`、`/compare` | B6, B7 | 🟡⭐ |
| B10 | `dijkstra.rs` 與 `pnr.rs`；PNR 圖層 | B7, B9 | 🟡 |
| B11 | `replan.rs`；`/api/replan` | B6, B8, B10 | 🟡⭐ |
| B12 | API 整合測試、insta 快照 | B8 | 🟡 |
| B13 | criterion benchmark | B11 | 🟡 |
| B14 | 輸出 `scenarios/*.json`（golden 測試與 demo 備案） | B11 | 🟡 |
| B15 | [加分] svf／劑量 → sun → localize | B6 | 🟡 |

### D｜資料與科學 — 適合不寫程式的隊友
| ID | 任務 | 依賴 | 狀態 |
|---|---|---|---|
| D1 | 下載 Mount Sharp boxwork 一帶的 HiRISE DTM（uahirise.org/dtm 或 Mars Trek） | — | 🟢⭐ |
| D2 | `tools/preprocess.py` → `dem.f32` + `meta.json`（裁切 2 km 見方） | D1 | 🟡⭐ |
| D3 | 整理 boxwork 科學點位（先收集經緯度、說明和 NASA 來源連結）→ 轉成 `targets.json` | 收集 🟢／轉座標要等 D2 | 🟢 |
| D4 | 為每個科學點挑好奇號實拍照片（POV） | — | 🟢 |
| D5 | 情境參數設計：基地位置、落石位置、O2 容量和消耗率、坡度門檻依據 | — | 🟢 |
| D6 | [選] THEMIS 熱慣量、CRISM 礦物圖層 | D2 | 🟡 |

### F｜前端（Three.js）
| ID | 任務 | 依賴 | 狀態 |
|---|---|---|---|
| F1 | Vite + three 專案、OrbitControls、基本場景 | — | 🟢 |
| F8 | `api.js` 加上 mock 模式（照 B1 契約回傳假資料），讓前端不用等後端 | B1 | 🟢⭐ |
| F2 | 地形 mesh（先用假高度圖，之後改接 `/api/terrain`） | F1 | 🟢 |
| F3 | 圖層 DataTexture 加色階 shader | F1, F8 | 🟢 |
| F4 | 三條路線 TubeGeometry 加統計卡片 | F8 | 🟢 |
| F5 | 點選起訖點、科學目標標記、POV 照片彈窗 | F2, D3, D4 | 🟡 |
| F6 | 情境按鈕與動畫：開始 EVA、落石、O2 加速 | F4, B11 | 🟡 |
| F7 | HUD 風格、「OFFLINE · 本地運算」標示 | F1 | 🟢 |
| F9 | 切換成真實 API，`npm run build` 後交給 server 提供 | B8, F2–F4 | 🟡 |

### P｜簡報與提交
| ID | 任務 | 依賴 | 狀態 |
|---|---|---|---|
| P1 | 故事腳本：30 秒影片分鏡，或 7 頁投影片大綱 | — | 🟢 |
| P2 | 英文 Summary 和 Project Details 草稿 | — | 🟢 |
| P3 | **持續記錄**：用到的 NASA 資料、References、AI（SI）使用說明 | — | 🟢 |
| P4 | 建立 GitHub repo（公開）和 README | B0 | 🟢 |
| P5 | 錄影、剪輯、英文字幕；或製作投影片 | F6 整合完成（約 11/15 15:00） | 🟡 |
| P6 | 填寫提交頁、用無痕視窗測試所有連結、**22:00 前 Submit** | P2, P3, P5 | 🟡⭐ |

### 建議的人力配置（隊伍最多 6 人）
- **後端（你）**：B0 → B1 → B4/B5/B7 平行 → B6 → B8 → B10 → B11。
  - B1 要在開工後 1 小時內推給前端。
  - B2、B9 這類小任務可以穿插做。
- **前端 1–2 人**：F1 → F8 → F2/F3/F4。要等的部分是 F5、F6、F9。
- **資料 1 人**：D1 → D2 最急，因為要解鎖真實地形；D3、D4、D5 同時進行。
- **簡報 1 人**：P1–P4 現在就能做，P3 要全程持續記錄。
- 人數不夠的話，資料和簡報可以由同一人負責。

### 現在立刻能開工的任務（全部 🟢）
B0、B1、B4、B5、B7、B9 ｜ D1、D3（收集）、D4、D5 ｜ F1、F2、F7（F8 等 B1 完成）｜ P1、P2、P3、P4

## 時程（今天 11/14 下午 → 明天 11/15 22:00 提交）
| 階段 | 時間 | 內容 | 完成標準 |
|---|---|---|---|
| **P0 骨架** | 11/14 17–18 | 安裝 rustup、`git init`、建 workspace、寫 `docs/API.md`、`synth.rs`、server 的 `/api/meta` 和 `/api/terrain` | 前端拿合成地形就能開工 |
| **P1 地形與成本** | 18–21 | 下載 Gale/Mount Sharp DEM 並跑 `preprocess.py`；寫 terrain、edt、cost 和單元測試 | `cargo test` 通過；`/api/layer/*` 可用 |
| **P2 路徑** | 21–24 | astar、route 統計、三種 mode；proptest 對照 oracle；`/api/route`、`/compare` | 合成和真實 DEM 上都畫得出三條路線 |
| 前端（同步） | 11/14 晚 | 地形 mesh、圖層、路線繪製 | 能在瀏覽器看到結果 |
| **P3 安全** | 11/15 09–12 | eva、dijkstra、pnr、replan；整合測試；benchmark | replan < 200 ms；PNR 圖層正確 |
| **P4 整合** | 12–15 | 情境流程、HUD 風格、server 提供 `web/dist`；把 golden 情境輸出到 `scenarios/` | 拔網路完整跑一遍 demo |
| P5 加分 | 15–17 | svf/劑量 → sun → localize，依剩餘時間取捨 | 不影響主線 |
| **🔒 功能凍結** | **17:00** | 之後只修 bug | |
| **P6 提交** | 17–22 | 錄 30 秒影片（英文字幕）或做 7 頁投影片、英文提交內容、AI 使用說明、References、GitHub 設為公開 | **22:00 前按下 Submit**，保留 2 小時緩衝 |

## 資料（來源皆為 NASA，對應 Relevance 分數）
- **地形**：Gale 撞擊坑／Mount Sharp 一帶的 HiRISE DTM（uahirise.org/dtm），或 Mars Trek 匯出的 DEM GeoTIFF。裁切約 2 km × 2 km，解析度 1–2 m/格。
- **岩石／粗糙度**：先由 DTM 推導；有時間再疊 THEMIS 熱慣量。
- **科學目標**：手動標記 Mount Sharp 的 boxwork 觀察點（好奇號 2025 年研究過的地點），寫進 `targets.json`（附 NASA 來源連結）；有時間再加 CRISM 圖層。
- **POV 影像**：好奇號／毅力號原始影像，點選目標時顯示。
- **備案**：真實資料抓不到時，用 `synth.rs` 的合成地形照常 demo。

## 測試計畫
1. **單元測試（cargo test）**
   - 坡度：在已知斜率的平面上計算，結果誤差 < 0.1°；平地的坡度要是 0。
   - EDT：和暴力法逐格比對（隨機小網格）。
   - cost：hazard 格必定是 ∞；離危險越遠，成本單調不增。
   - eva：平地速度等於 v0；坡度越大速度越慢。
2. **性質測試（proptest，隨機網格）**
   - A* 的總成本 == `pathfinding::dijkstra` 的總成本（最佳性）。
   - 路線不會經過 hazard 格；路徑連續（相鄰格）；起訖點正確。
   - `safe` 模式的 min_clearance ≥ `science` 模式的 min_clearance。
   - replan 後的路線避開所有新障礙。
   - PNR：O2 越少，安全區域越小（單調）。
3. **快照測試（insta）**：固定合成地形種子和固定起訖點，鎖定路線統計，防止改權重時意外改變結果。
4. **API 整合測試**：用 `tower::ServiceExt::oneshot` 打每個 endpoint，檢查狀態碼、JSON schema 和二進位長度 = w×h。
5. **效能（criterion）**：2048² 網格上 cost 重算 < 100 ms、A* < 150 ms、PNR Dijkstra < 300 ms（release 模式）。
6. **端到端與離線驗收（手動 checklist）**：關掉 Wi-Fi → `cargo run --release -p mars-server` → 瀏覽器開 localhost:8080 → 依序跑完 3 個情境，無報錯、DevTools 沒有任何外部請求。
7. 前端不寫自動化測試，只靠上面的 checklist，加上 `npm run build` 必須成功。

## 驗證（每階段結束時）
- `cd engine && cargo fmt --check && cargo clippy -- -D warnings && cargo test`
- `cargo bench -p mars-core`（P3 之後）
- `cd web && npm run build`，再用 server 提供靜態檔，走一遍離線 checklist
- 每個階段完成就 git commit，出問題時方便回退

## 風險與對策
| 風險 | 對策 |
|---|---|
| 團隊不熟 Rust，進度落後 | 演算法保持單純的 2D 陣列操作；P2 結束時若落後，把情境結果預先算成 `scenarios/*.json`，前端直接讀檔 |
| DEM 格式或下載出問題 | 有合成地形備案；前處理只在 Python 端處理一次 |
| 前端隊友來不及 | 前端先做最小可行版（地形 + 路線 + 3 個按鈕），HUD 美化放到最後 |
| 提交程序出包 | 22:00 硬截止，保留 2 小時緩衝；提交前用無痕視窗測試所有連結 |

<!-- SI-assisted: first drafted by Hermes Agent (SI tool), rewritten by Claude Code (Anthropic, SI tool) from the project's facts; reviewed by the team. -->
# Martian Map — Offline EVA Route Planner

**Team It Worked on Earth!!!** (YI-FAN YU, PO-TING HSU) · NASA Space Apps Challenge 2026 · Challenge: *Interplanetary Survival Guide: Martian Map*

**Live demo (runs in the browser, no install):** https://bobhsu408.github.io/martian-map/

Martian Map is an offline navigation tablet for an astronaut walking on Mars. It turns NASA terrain data from Mount Sharp in Gale crater into safe walking routes. For each walk it shows three choices (safe, balanced, science) with distance, time, risk and an estimated radiation dose. During the walk it tracks the **point of no return**, the moment after which the oxygen left is not enough to get home. If a rockfall blocks the path or the suit starts leaking oxygen, it re-plans on the spot or orders a return to base. It finds the astronaut's position from radio beacons instead of GPS. A message to Earth takes 4 to 24 minutes, so every calculation runs on the device.

A first-time spotlight tour walks new users through raising the tablet, picking a destination and planning routes.

## How to try it

1. Open the demo and press **Start**. The tour guides you through it.
2. Press **Tab** or **M** to raise the tablet, pick a science stop, and press **Calculate routes**.
3. Press **▶ Start EVA**, then try the emergencies: **Rockfall**, **O₂ leak**, **Drift off route**, **Lose base link**.
4. Walk yourself with **W A S D**, drag to look around, and press **V** to switch first or third person. The **Map Layers** button shows slope, hazards, cost, beacon coverage and the point of no return.

## Features

- Penalty-based cost map (slope, roughness, buffer around hazards, science bonus) and A* route planning in three modes
- Point of no return from the remaining suit oxygen, shown as a countdown and as a red boundary on the map
- On-board re-planning after a rockfall, a drift off the route, or an oxygen leak (return to base)
- Positioning without GPS: LoRa/UWB beacon ranging, line of sight on the terrain, Gauss–Newton multilateration, dead reckoning; after losing the base link the astronaut can drop new beacons (key **B**)
- Walkable 3D Mars scene with a handheld tablet, minimap, haptic and audio guidance
- Nested map scales: 2 m HiRISE site → Gale crater region → whole Mars globe and 2D map
- English / 中文 interface toggle

## Architecture

- `engine/`: Rust workspace. `mars-core` holds the algorithms, `mars-wasm` builds them to WebAssembly, which runs in a Web Worker in the browser, and `mars-server` is an optional local HTTP server.
- `web/`: Vite + Three.js front end. `src/main.js` is the app, `src/tour.js` the onboarding tour and `src/i18n.js` the language toggle.
- `tools/*.py`: one-time Python scripts that turn raw NASA PDS files into `data/processed/`. The app does not need them to run.
- `.github/workflows/pages.yml`: builds `web/` and deploys it to GitHub Pages on every push to `main`.

## Run locally

```
cd web && npm install && npm run build && npx vite preview
```

Open the printed `http://localhost:4173` URL. The engine runs inside the browser, so the app works offline once it has loaded.

Rebuild the WebAssembly engine after changing Rust code: `./tools/build_wasm.sh`. This needs the `wasm32-unknown-unknown` target and `wasm-bindgen-cli 0.2.130`.

## Test

```
cd engine && cargo test                                          # 45 Rust tests
node tools/e2e_tablet.mjs <out-dir> "http://localhost:4173/?nointro"   # plan → EVA → rockfall
node tools/e2e_tour.mjs <out-dir> http://localhost:4173/              # onboarding tour
node tools/e2e_shots.mjs <out-dir> "http://localhost:4173/?nointro"    # full walkthrough with screenshots
```

## NASA data

| Data | Used for |
|---|---|
| **HiRISE DTM** `DTEEC_001488_1750_001752_1750_U02` and orthophoto (NASA/JPL/University of Arizona) | 3D walking terrain at about 2 m, slope, roughness, no-go areas, route planning, ground imagery |
| **MGS MOLA** MEGDR (global, and the Gale region at 463 m) | Mars globe, Gale crater context, far terrain |
| **Viking MDIM** colour mosaic (NASA/ASU) | Global satellite base map |
| **MGS MOC Atlas** (256 px/deg) | Regional image of Gale crater |
| Curiosity **RAD** surface dose rate (published value) | Radiation dose estimate per route |

Details: [docs/DATA_CATALOG.md](docs/DATA_CATALOG.md).

**Honest limitations:** beacon ranges are simulated, science stops are candidates picked automatically from the terrain, and the radiation dose is an estimate from an average dose rate.

## Use of SI (AI) tools

- **Claude Code (Anthropic)** wrote most of the code: the Rust engine, the WebAssembly build, the Three.js interface, the onboarding tour, the tests and the deployment. It also drafted documentation and the submission text.
- **Codex (OpenAI)** explained the tech stack, researched Mars map data, wrote the Python preprocessing tools, built the zoomable 2D map, and rebuilt the tablet interface from our reference designs.
- **Antigravity AI** proposed the tablet redesign plan from our reference images. Codex finished the work.
- **Hermes Agent** drafted the first README.
- **ChatGPT, Google Translate and Grammarly** helped translate and polish our English text.
- The team chose the problem, the site and the offline-tablet concept, designed the experience, chose and preprocessed the NASA data, wrote `hazard_mask` by hand, and tested and approved every change.
- Every file written or assisted by SI says so on its first line (`SI-generated` or `SI-assisted`). We used no SI-generated images, video or audio.
- Full step-by-step log: [engDocs/SI_usage.md](engDocs/SI_usage.md) (English) and [docs/AI_USAGE.md](docs/AI_USAGE.md) (Chinese).

## Team

**It Worked on Earth!!!**: YI-FAN YU, PO-TING HSU

## More

- Submission text: [engDocs/SUBMISSION.md](engDocs/SUBMISSION.md)
- Development log with screenshots (Chinese): [docs/DEVLOG.md](docs/DEVLOG.md)
- Chinese README with data preprocessing details: [docs/README.zh.md](docs/README.zh.md)

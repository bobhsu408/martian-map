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

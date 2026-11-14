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
- Map layers: slope, hazards, cost, beacon coverage, point-of-no-return

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

## Data

The current demo uses a synthetic terrain generator as a stand-in; the pipeline is designed for NASA HiRISE digital terrain models of Gale crater. Radiation dose uses a modelled surface rate of about 0.7 mSv/day (order of Curiosity RAD measurements). All parameters are assumptions and adjustable.

## Use of SI (AI) tools

Claude Code (Anthropic) generated most of the code, marked with a "SI-generated" or "SI-assisted" comment at the top of each file; Hermes Agent drafted this README; the team chose the idea, scope, science target and design decisions, specified the beacon positioning and off-route rules, designed the guidance UI and haptic/audio encoding, and wrote hazard_mask in cost.rs; full log in docs/AI_USAGE.md.

## Team

TODO: team name and members.

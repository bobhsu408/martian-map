<!-- SI-assisted: drafted by Hermes Agent (SI tool), reviewed by the team. -->
# Martian Map — Offline EVA Route Planner

NASA Space Apps Challenge 2026 project for the challenge "Interplanetary Survival Guide: Martian Map". It plans safe Marswalk routes for astronauts at the Mount Sharp boxwork site (Gale crater) and runs fully offline, because the Earth–Mars signal delay is 4–24 minutes.

## Features

- Penalty-based cost map (slope, roughness, buffer around hazards, science bonus)
- A* route planning in three modes (safe, balanced, science) with distance, ETA, max slope, hazard clearance, radiation dose and risk
- Point-of-no-return safe zone based on remaining suit oxygen
- On-board re-planning when a rockfall is reported or oxygen runs low
- 3D Three.js map with layers (slope, hazards, cost, PNR)

## Architecture

- engine/ is a Rust workspace (crate mars-core = algorithms, crate mars-server = axum HTTP server on 127.0.0.1:8080 that also serves the web UI)
- web/ is a Vite + Three.js front-end
- docs/API.md is the API contract

## Run

```
cd web && npm install && npm run build && cd ..
cd engine && cargo run --release -p mars-server
```

then open http://127.0.0.1:8080

## Test

```
cd engine && cargo test
```

## Data

The current demo uses a synthetic terrain generator as a stand-in; the pipeline is designed for NASA HiRISE digital terrain models of Gale crater. Radiation dose uses a modelled surface rate of about 0.7 mSv/day (order of Curiosity RAD measurements). All parameters are assumptions and adjustable.

## Use of SI (AI) tools

Claude Code (Anthropic) generated most of the code, marked with a "SI-generated" or "SI-assisted" comment at the top of each file; Hermes Agent drafted this README; the team chose the idea, scope, science target and design decisions and wrote hazard_mask in cost.rs; full log in docs/AI_USAGE.md.

## Team

TODO: team name and members.

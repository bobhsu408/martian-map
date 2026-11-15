<!-- SI-generated: first draft written by Claude Code (Anthropic, SI tool) from the team's notes; the team reviews and edits before submitting. -->
# Martian Map — Space Apps 2026 submission draft

Challenge: **Interplanetary Survival Guide: Martian Map**
Team: It Worked on Earth!!! (YI-FAN YU, PO-TING HSU)
Demo (runs in the browser, no install): https://bobhsu408.github.io/martian-map/
Repository: https://github.com/bobhsu408/martian-map

---

## High-Level Summary

Martian Map is an offline navigation tablet for an astronaut walking on Mars. It turns the terrain data from Mount Sharp in Gale crater into safe walking routes. For each walk it shows three choices (safe, balanced and science) with distance, time, risk and estimated radiation dose. During the walk it keeps track of the point of no return, the moment after which the oxygen left is not enough to get home. If a rockfall blocks the path or the suit starts leaking oxygen, it re-plans on the spot or orders a return to base. It finds the astronaut's position from radio beacons instead of GPS. A message to Earth takes 4 to 24 minutes, so every calculation runs on the device, with no link to Earth.

---

## Project Details

### What it does

You play an astronaut on the slopes of Mount Sharp. The ground you walk on is a real NASA HiRISE terrain model. Our system is the tablet the astronaut carries. Press Tab or M to raise it.

1. **Pick a goal.** Choose a science stop, or tap any point on the tablet map.
2. **Pick a route.** The tablet works out three routes in under a second:
   - **Safe** keeps far away from cliffs and boulders.
   - **Balanced** is shorter and takes moderate risk.
   - **Science** is the shortest and accepts steeper ground.

   Each route card shows the length, the walking time, a risk score, the steepest section, the closest approach to a hazard and an estimated radiation dose.
3. **Go on EVA.** Walk the route yourself (W A S D) or let autopilot walk it. With the tablet lowered, the astronaut still sees:
   - a compass and how dangerous the ground underfoot is;
   - a "turn back in N min" countdown;
   - vibration and sound cues: one pulse means steer left, two pulses mean steer right, a long buzz means a hazard is close, and SOS means return now.

You can trigger emergencies to see how the system reacts:
- **Rockfall ahead:** the tablet adds the new obstacle and computes a new route from where you are.
- **Oxygen leak:** oxygen drops and burns three times faster. The system recomputes the point of no return. If the goal is now out of reach, it switches to the safest way home.
- **Drift off route:** the astronaut is pushed sideways. The tablet notices the cross-track error and re-plans from the estimated position.
- **Lose base link:** the long-range beacons at the habitat, rover and relay go silent. The astronaut can drop their own UWB beacons (key B, four per EVA). With three or more beacons in line of sight, the position fix comes back. More beacons give a smaller error circle.

After reaching the goal, the astronaut can walk around the site and then ask for a route home.

### How it works

- **Terrain → cost map.** From the HiRISE elevation model (2.02 m cells, about 2 km × 2 km) we compute:
  - slope, using Horn's method;
  - roughness, as how far each cell sits above or below its 3 × 3 neighbourhood, averaged again over 3 × 3. A tilted plane scores zero, so this measures bumpiness, not slope.

  Cells steeper than 25° or rougher than 0.30 m are no-go. Every other cell gets a cost that grows with slope and roughness and with how close it is to a no-go cell (from an exact Euclidean distance transform). The three route modes use different weights for these terms.
- **Routes.** We run A\* on the 8-connected grid. Walking time comes from a symmetric Tobler hiking function, `v = v0 · exp(−3.5 · tan θ)`, slowed further on rough ground.
- **Point of no return.** A Dijkstra pass from the habitat gives the time to return home from every cell. A cell is safe to visit when:

  > time to reach it + time to return home + a 30-minute reserve ≤ oxygen left

  This region is recomputed whenever oxygen or position changes. It is drawn on the terrain as a red boundary that shrinks as oxygen runs out.
- **Re-planning.** A reported obstacle is written into the hazard map. The cost map is then updated and A\* runs again from the astronaut's position. If the goal is beyond the point of no return, the engine returns a route to base instead.
- **Positioning without GPS.**
  - The engine checks line of sight to each beacon against the terrain. Long-range LoRa beacons sit at the base, the rover and the relay; short-range UWB beacons sit along the route or are dropped by the astronaut.
  - With three or more ranges, it solves the position by weighted Gauss–Newton multilateration and reports a 1-sigma error.
  - With fewer than three, it falls back to dead reckoning, whose error grows with distance walked.
  - Beacon ranges in the demo are simulated from the terrain.
- **Radiation.** Dose is a model estimate: walking time × 0.7 mSv/day, the order of magnitude Curiosity's RAD instrument measured on the surface. It is not a radiation map.
- **Offline by design.** The engine is written in Rust and compiled to WebAssembly. It runs in a Web Worker inside the browser, so the whole site works with the network unplugged and can be served as static files. The same engine also builds as a small local HTTP server.
- **Context maps.** NASA MOLA, the Viking colour mosaic and the MOC Atlas give a zoomable view from the whole planet down to the walking site. This shows where the EVA happens.

### Benefits

- **Hyperlocal.** Existing Mars maps work at regional or global scale. Ours works at the scale of one walk, where what matters is whether the next few metres are safe.
- **NASA data drives the decisions.** The terrain model directly decides where the routes can and cannot go.
- **Built for survival.** Oxygen, return time and hazards are checked every moment, and the system decides to turn back before it is too late.
- **Works without Earth and without GPS.** Planning, re-planning and positioning all run on the device.
- **Designed around the astronaut.** The tablet stays out of the way and comes up by itself in an emergency. Feedback can be felt, not only seen.

### What we hope to achieve

We want to show that NASA's orbital data, combined on a small device, can give a crew practical answers during an EVA: where to walk, what to avoid and when to turn back.

Next steps:
- Stream terrain tiles around the astronaut and use a coarse grid for long-range planning, so the whole HiRISE DTM (about 7 × 18 km) can be covered.
- Feed real suit telemetry (O₂ tank pressure and consumption rate) into the same point-of-no-return logic.
- Add bearing measurements so that one or two beacons are enough for a position fix.
- Add thermal inertia and mineral layers (THEMIS, CRISM) to choose science stops.

### Tools and languages

- **Rust:** route engine. Crates: rayon for parallel grid computation, serde for JSON, axum and tokio for the optional local server, wasm-bindgen for WebAssembly.
- **JavaScript:** Three.js for the 3D terrain and the tablet interface, Vite for the build.
- **Python** (numpy, Pillow), used only to preprocess the NASA files.
- **Testing:** 45 automated Rust tests, including property tests that check A\* against a reference shortest-path solver. A headless Chrome script runs the full demo end to end.

### Honest limitations

- The walkable area is the 2 km × 2 km HiRISE crop.
- Science stops are candidates picked from slope and roughness. They are not confirmed boxwork exposures.
- Beacon ranges are simulated.
- The radiation dose is an estimate from an average dose rate.

---

## Use of SI (AI)

<!-- SI-assisted: this section was drafted by Claude Code from the team's AI usage log at the team's request; the team reviews and edits it. -->
We used SI tools heavily, and we kept a log of every step (`docs/AI_USAGE.md` in Chinese, `engDocs/SI_usage.md` in English).

**Tools we used**
- **Claude Code (Anthropic)** wrote most of the code: the Rust route-planning engine, its WebAssembly build, the Three.js interface, the onboarding tour, the automated tests and the deployment setup. It also drafted documentation and this submission text.
- **Codex (OpenAI)** explained the tech stack to one of us, researched which Mars map data to use, wrote the Python tools that preprocess the NASA data, built the zoomable 2D map, and rebuilt the tablet interface from reference designs we chose.
- **Hermes Agent** (a free local model) drafted the first README from an outline we gave it.
- **Antigravity AI** read our interface and proposed a tablet redesign plan from four reference images we chose. Codex finished the work.
- **ChatGPT, Google Translate and Grammarly** helped translate our notes and logs into English and polish the wording. We checked the translations.

**What we did ourselves**
- We chose the problem, the site (Mount Sharp, Gale crater) and the idea of a fully offline EVA tablet.
- We designed how it should feel: a handheld tablet, a compass and danger colour when idle, first-person walking, dropping radio beacons after losing the base link, and making the point of no return visible.
- We picked the NASA datasets, ran the preprocessing, and checked the results.
- We wrote the `hazard_mask` logic in the engine by hand.
- We tested every change in the browser, reported what felt wrong, and decided what to keep and merge.

**Labelling**
- Every file written or assisted by SI says so on its first line (`SI-generated` or `SI-assisted`).
- We used no SI-generated images, video or audio. All terrain and imagery come from NASA data, and the screenshots are from the app itself.

---

## Space Agency Data

| Data | Used for |
|---|---|
| NASA/JPL/University of Arizona **HiRISE DTM** `DTEEC_001488_1750_001752_1750_U02` and matching orthophoto (Mount Sharp, Gale crater) | 3D walking terrain, slope, roughness, no-go areas, route planning, point of no return, ground imagery |
| HiRISE DTM `DTEEC_019698_1750_019988_1750_U01` (NW Mount Sharp) | Second test site |
| NASA MGS **MOLA** MEGDR (global, and the Gale region at 463 m) | Planet-scale globe, Gale crater context, far terrain beyond the walking area |
| NASA/ASU **Viking MDIM** colour mosaic | Global satellite base map |
| NASA MGS **MOC Atlas** (256 px/deg, 120–150°E, 30°S–0°) | Regional image of Gale crater between the globe and the site |
| Curiosity **RAD** surface dose rate (published value) | Radiation dose estimate per route |

Full details: `docs/DATA_CATALOG.md`.

---

## References

Data:
- HiRISE DTMs and orthophotos — University of Arizona / NASA / JPL. https://www.uahirise.org/dtm/
- MGS MOLA MEGDR — NASA PDS Geosciences Node. https://pds-geosciences.wustl.edu/missions/mgs/megdr.html
- Viking MDIM colour mosaic — ASU / NASA. https://www.mars.asu.edu/data/mdim_color/
- MOC Atlas — ASU / NASA. https://www.mars.asu.edu/data/moc_256/

Papers:
- McEwen, A. S., et al. (2007). Mars Reconnaissance Orbiter's High Resolution Imaging Science Experiment (HiRISE). *JGR Planets*, 112, E05S02.
- Kirk, R. L., et al. (2008). Ultrahigh resolution topographic mapping of Mars with MRO HiRISE stereo images. *JGR Planets*, 113, E00A24.
- Smith, D. E., et al. (2001). Mars Orbiter Laser Altimeter: Experiment summary after the first year of global mapping of Mars. *JGR*, 106(E10).
- Hassler, D. M., et al. (2014). Mars' surface radiation environment measured with the Mars Science Laboratory's Curiosity rover. *Science*, 343(6169).
- Hart, P. E., Nilsson, N. J., & Raphael, B. (1968). A formal basis for the heuristic determination of minimum cost paths. *IEEE Trans. SSC*, 4(2).
- Felzenszwalb, P. F., & Huttenlocher, D. P. (2012). Distance transforms of sampled functions. *Theory of Computing*, 8.
- Tobler, W. (1993). Three presentations on geographical analysis and modeling. NCGIA Technical Report 93-1.
- Horn, B. K. P. (1981). Hill shading and the reflectance map. *Proc. IEEE*, 69(1).

Software:
- Three.js, Vite, Rust, wasm-bindgen, axum, tokio, rayon, serde, numpy, Pillow.

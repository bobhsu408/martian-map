<!-- SI-assisted: drafted by Claude Code (Anthropic, SI tool) from the team's notes, design decisions and test feedback; the team reviews and edits it. -->
# Mars EVA Planner

Challenge: Interplanetary Survival Guide: Martian Map
Team: It Worked on Earth!!! (YI-FAN YU, PO-TING HSU)
Demo (runs in the browser, no install): https://bobhsu408.github.io/martian-map/
Source code: https://github.com/bobhsu408/martian-map

---

## High-Level Summary

Mars EVA Planner is an offline navigation tablet for an astronaut walking on Mars. It uses a NASA HiRISE terrain model of Mount Sharp in Gale crater to plan safe walking routes. For each walk it offers three routes (safe, balanced, science) and shows the distance, time, risk and an estimated radiation dose. During the walk it keeps track of the point of no return: the moment the oxygen left is only just enough to get home. If a rockfall blocks the path or the suit starts leaking, it re-plans on the spot or sends the astronaut back to base. It finds the astronaut's position from radio beacons instead of GPS. A message to Earth takes 4 to 24 minutes, so every calculation runs on the device.

---

## Project Details

### What it does

You play an astronaut on the lower slopes of Mount Sharp. The ground is a real NASA HiRISE terrain model. Our system is the tablet the astronaut carries. Press Tab or M to raise it. First-time users get a short spotlight tour that walks them through the first plan.

1. Pick a goal: a science stop from the list, or Custom Point and then a tap on the map.
2. Calculate routes. The tablet finds three routes in about a second. Safe stays far from cliffs and boulders, Balanced is shorter with moderate risk, and Science is the shortest and accepts steeper ground. Each card shows length, walking time, risk, the steepest slope, the closest hazard and the estimated dose.
3. Start the EVA. Walk it yourself with W A S D, or turn on autopilot.

With the tablet lowered you still see a compass, your position and how dangerous the ground under you is. During the EVA the point-of-no-return boundary is drawn in red on the ground, and vibration and sound tell you where to steer: one pulse for left, two for right, a long buzz near a hazard, and SOS when you must go back. Raise the tablet to see oxygen, the "turn back in" countdown, the position error and how many beacons you can hear.

You can trigger four emergencies:
- Rockfall: the new obstacle goes into the map and a new route is computed from where you stand.
- Oxygen leak: you are down to 40 minutes and using oxygen three times as fast. If the goal is now out of reach, the tablet sends you home and raises itself.
- Drift off route: you are pushed sideways. The tablet sees how far off the path you are and re-plans from your estimated position.
- Lose base link: the long-range beacons at the habitat, rover and relay go quiet. You can drop up to four UWB beacons of your own (key B). With three in line of sight your position fix comes back, and every extra beacon makes it tighter.

After reaching the goal you can walk around freely and ask for a route home. Map layers show slope, hazards, cost, beacon coverage and the point of no return. A 2D map and a globe let you zoom out from the walking site to Gale crater and the whole planet. The interface switches between English and Chinese.

### How it works

- Terrain to cost map. From the HiRISE model, resampled to 2.02 m cells over about 2 km by 2 km, we compute slope with Horn's method and roughness: how far each cell sits above or below its 3 by 3 neighbourhood, averaged again. A tilted plane has zero roughness, so this measures bumpiness rather than slope. Ground steeper than 25 degrees or rougher than 0.30 m is no-go. Every other cell costs more the steeper and rougher it is, and the closer it is to a no-go cell (an exact Euclidean distance transform). The three route modes weight these terms differently.
- Routes. A* on an 8-connected grid. Walking speed follows a symmetric Tobler hiking function, v = v0 x exp(-3.5 x tan(slope)), slowed further on rough ground.
- Point of no return. One Dijkstra pass from the habitat gives the time home from every cell. A cell is safe to visit when the time to get there, plus the time home, plus a 30-minute reserve, fits in the oxygen left. This is recomputed as oxygen drops.
- Re-planning. A reported obstacle is written into the hazard map, the cost map is updated and A* runs again from your position. If the goal is past the point of no return, the engine returns a route to base instead.
- Positioning without GPS. The engine checks line of sight from you to each beacon over the terrain. Long-range LoRa beacons sit at the habitat, rover and relay, and short-range UWB beacons sit along the route or are dropped by you. With three or more ranges it solves your position by weighted Gauss-Newton multilateration and reports the error. With fewer, it falls back to dead reckoning, whose error grows as you walk. In the demo the ranges are simulated from the terrain.
- Radiation. The dose is walking time multiplied by 0.7 mSv per day, the level Curiosity's RAD instrument measured on the surface. It is an estimate, not a radiation map.
- Offline. The engine is written in Rust and compiled to WebAssembly. It runs in a Web Worker in the browser, so the site keeps working with the network unplugged. The same engine also builds as a small local server.

### How the design changed while we tested it

Most of our design decisions came from playing the demo ourselves:
- At first the point of no return was only a number, and we could not feel it while walking. We added the "turn back in" countdown and the red boundary on the ground.
- We wanted the astronaut to look at the ground, not at a screen. That led to the handheld tablet that stays lowered until you need it, and to steering by vibration.
- When we imagined the base link failing, we wanted the astronaut to be able to fix it alone, so we added beacons they can drop themselves.
- After reaching the goal the astronaut got stuck in place, so we let them walk freely after arrival.
- People trying it did not know where to start, so we added the spotlight tour.

### Why it matters

Mars maps today are regional or global. On a walk, what matters is whether the next few metres are safe and whether there is enough oxygen to get back. Our tablet answers that from NASA terrain data, on the device, without Earth and without GPS.

### What we want to do next

- Stream terrain tiles around the astronaut, so the whole HiRISE model can be covered instead of a 2 km crop.
- Use real suit telemetry for oxygen in the point-of-no-return calculation.
- Add bearing measurements, so one or two beacons are enough for a position fix.
- Add thermal and mineral layers (THEMIS, CRISM) to choose science stops.

### Tools

Rust (rayon, serde, axum, tokio, wasm-bindgen), JavaScript with Three.js and Vite, and Python (NumPy, Pillow) to preprocess the NASA files. 45 automated Rust tests, including property tests that compare our A* with a reference solver, and headless-Chrome scripts that play through the demo and the tour.

### Limitations

- The walkable area is a 2 km by 2 km crop.
- Science stops are candidates picked from the terrain, not confirmed boxwork outcrops.
- Beacon ranges are simulated.
- The radiation dose is an average-rate estimate.

### Use of SI

We used SI tools heavily and logged every step (engDocs/SI_usage.md in our repository). Claude Code wrote most of the code and drafted our documents. Codex wrote the data preprocessing tools, the 2D map and the redesigned tablet interface. Antigravity proposed the interface redesign plan. Hermes Agent drafted the first README. ChatGPT, Google Translate and Grammarly helped with English. We chose the problem and the site, designed the experience, picked and processed the NASA data, wrote the hazard mask by hand, and tested and approved every change. Every SI-written file says so on its first line. We used no SI-generated images, video or audio.

---

## NASA Data

| Data | Used for |
|---|---|
| HiRISE DTM DTEEC_001488_1750_001752_1750_U02 and orthophoto (NASA/JPL/University of Arizona) | Walking terrain, slope, roughness, no-go areas, routes, point of no return, ground imagery |
| HiRISE DTM DTEEC_019698_1750_019988_1750_U01 (NW Mount Sharp) | Second test site |
| MGS MOLA MEGDR | Globe of Mars |
| MGS MOLA 463 m global DEM (USGS Astrogeology mosaic), Gale crop | Gale crater region and far terrain |
| Viking MDIM colour mosaic (NASA/ASU) | Global base map |
| MGS MOC Wide Angle Atlas, 256 px/deg | Gale crater regional image |
| Curiosity RAD surface dose rate (Hassler et al. 2014) | Radiation dose estimate |

Link-by-link list for the form: engDocs/SUBMISSION_FORM.txt.

## References

Papers:
- McEwen, A. S., et al. (2007). Mars Reconnaissance Orbiter's High Resolution Imaging Science Experiment (HiRISE). JGR Planets, 112, E05S02.
- Kirk, R. L., et al. (2008). Ultrahigh resolution topographic mapping of Mars with MRO HiRISE stereo images. JGR Planets, 113, E00A24.
- Smith, D. E., et al. (2001). Mars Orbiter Laser Altimeter: Experiment summary after the first year of global mapping of Mars. JGR, 106(E10).
- Hassler, D. M., et al. (2014). Mars' surface radiation environment measured with the Mars Science Laboratory's Curiosity rover. Science, 343(6169).
- Hart, P. E., Nilsson, N. J., & Raphael, B. (1968). A formal basis for the heuristic determination of minimum cost paths. IEEE Trans. SSC, 4(2).
- Felzenszwalb, P. F., & Huttenlocher, D. P. (2012). Distance transforms of sampled functions. Theory of Computing, 8.
- Tobler, W. (1993). Three presentations on geographical analysis and modeling. NCGIA Technical Report 93-1.
- Horn, B. K. P. (1981). Hill shading and the reflectance map. Proc. IEEE, 69(1).

Software: Three.js, Vite, Rust, wasm-bindgen, axum, Tokio, Rayon, Serde, pathfinding, proptest, NumPy, Pillow.

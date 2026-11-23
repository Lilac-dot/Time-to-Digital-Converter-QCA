# Coarse counter TDC (wide-range stage)

The delay-line TDCs in this repo cover only 4 clock periods (16 ps at a 4 ps clock). Timing
jobs like time-of-flight imaging need nanosecond ranges, so this folder adds the usual
fix: a **coarse counter** that counts whole clock periods between START and STOP.

- **Range:** 2^n periods. 4 bits = 0-15 periods (60 ps, 245 cells); 8 bits = 0-255 periods (1.02 ns, 473 cells).
- **Resolution:** one clock period (4 ps).
- **Single layer:** no crossings or vias, so it doesn't depend on how a tool handles
  multilayer files.

Not yet run in the QCADesigner GUI. All results below come from the QCADesigner-E engine
source run from the command line.

## How it works

`counter_lib.py` builds everything from the ADDLL's verified 2:1 MUX (`addll/addll_lib.mux`).

- **Toggle bit:** the MUX is closed into a one-period loop, `X' = S ? !X : X`. The I1
  branch feeds back `!X` through an inverting diagonal placed on a clock-zone boundary. The
  counted bit is `b = !X`.
- **Carry:** `carry = S . b` (b before the update), from a separate majority gate. Bits
  are stacked downwards (each 12 rows below and 2 columns east of the last), so the carry
  drops straight down a 7-cell wire into the next bit's S line about one period later. A ripple counter only needs every carry
  to arrive, not to arrive in the same period, so the count is exact once the carries settle.
- **Window:** `EN = START . !STOP` feeds the LSB. START and STOP are level steps: each
  rises and then holds until the clear.
- **Clear:** `CLRk` replaces the fixed -1 in each MUX's lower AND gate. `CLR = 1` while
  `EN = 0` forces `X = 1` (b = 0). In the test files `CLR0..CLRn` are separate input cells
  driven together. On a real chip they would be one net.

**Reading the count:** `b_k = 1` when output `Xk` is negative; count = sum of `b_k * 2^k`.
Read after the carries settle: 18 periods after STOP is enough for 4 bits, 30 for 8.

## Results

The STOP edge comes N periods after START; the count read back should equal N.

| Layout | Engine | N tested | Result |
|---|---|---|---|
| `coarse_tdc4.qca` (245 cells, 0.38 um^2) | classic, r = 65 nm | 0, 3, 9, 14, 7, 15 | all exact |
| `coarse_tdc4.qca` | classic, r = 80 nm | 0, 3, 9, 14, 7, 15 | all exact |
| `coarse_tdc4.qca` | Gaussian clock (energy), r = 80 nm | 0, 3, 9, 14, 7, 15 | all exact; 6.69 meV per cycle (error +/- 0.56) |
| `coarse_tdc8.qca` (473 cells, 1.05 um^2) | classic, r = 65 nm | 200, 77 | both exact (engine overflow patched, see `../simulation/README.md`) |

Version 1 of this design (first commit on this branch) chained the bits side by side with
the carries looping over the top: 328 cells / 7.70 meV per cycle for 4 bits and 664 cells
for 8. It passed the same tests. Stacking the bits removed most of the carry wiring.

### Against published QCA counters

The counter alone (no window gate) is 221 cells for 4 bits. A published 4-bit asynchronous
QCA counter built from D-latches is 207 cells and 0.22 um^2 (Gholami group, Eur. Phys. J.
Plus, 2024). This one is about 7% larger. In its favour:

- It has a clear and a START/STOP window.
- It's one layer.
- It passes at two radii and under a Gaussian clock.

Logs: `results/`. Without the window gate (EN driven directly), the 4-bit counter also
counted 5, 11, 15 and 6 exactly.


## Asynchronous capture (coarse + fine)

`fine_lib.py` adds the fine stage, so START and STOP no longer have to land on clock
edges. Resolution goes from one period (4 ps) to one clock zone (a quarter period, 1 ps).

**How it works, per edge:**
- The input is sampled in the window's reference zone (zone 0 for START, zone 3 for STOP)
  and also m = 1, 2, 3 quarters earlier.
- A gate forms `f_m = X_ref . !X_early`. It is 1 only in the first period the reference
  sample sees the edge, and only if the edge came within the last m quarters.
- A one-gate set-latch, `q' = M(q, f, CLRn)` in a one-period loop (13 cells), holds each
  `f_m`. The held bits `F1..F3` form a thermometer code.

**Result, in quarter periods:** `Q = 4*count + sum(F_P) - sum(F_S) + 1`. The +1 is a fixed
offset: the window samples STOP one zone after START.

**Testing it:** the classic engine ties one input vector to one clock period, so it can't
place an edge mid-period. The Gaussian-clock energy engine has a separate input period.
With `per_vector=0.25` the inputs change every quarter period, and `test_async.py` steps
START at each of the 4 quarter phases.

| `async_tdc4.qca`: 413 cells, 0.77 um^2 | r = 80 nm | r = 65 nm |
|---|---|---|
| START at quarters 0, 1, 2, 3 with D = 9 | Q - D = 1 for all four | Q - D = 1 for all four |
| (s, D) = (2, 47) and (1, 30) | Q - D = 1 for both | Q - D = 1 for both |
| Energy (Gaussian clock) | 11.40 meV per cycle (error +/- 0.98) | |

The first version placed the fine blocks further out and used 3-cell zone segments on the
early-sample wires: 425 cells, 0.93 um^2, 11.60 meV per cycle, same results. Cutting the
segments to 2 cells works; 1-cell segments do not (the thermometer collapses).

**Caveats:**
- Each sampler has its own input cell (`START_R1`, `START_E1`, ...). This models one pad
  fanned out to the samplers; the fan-out wiring is not in the cell count. The test bench
  drives them together, and the GUI vector table would need them set together too.
- **No GUI test:** QCADesigner 2.0.3 can't run this test, because its classic engine ties
  inputs to the clock. Only the QCADesigner-E energy engine, with an input period of a
  quarter clock period, can.
- **Metastability isn't modelled.** An edge that lands exactly while a sampler is switching
  is resolved by the engine's deterministic maths, not by noise.

## Why not the delay-line TDC as the fine stage

With clock-aligned inputs, the repo's thermometer TDC
(`qca-layouts/07_conventional_tdc.qca`) adds nothing on top of the counter: every interval
is a whole number of periods, and the counter already resolves those. Asynchronous capture
above replaces it as the fine stage. It samples zone by zone instead of stage by stage, so
it gets quarter-period resolution in 84 cells per edge.

## Why: medical imaging

Single-photon timing (time-correlated single-photon counting, time-of-flight PET,
fluorescence lifetime imaging) needs a TDC per pixel or channel.

- **PET:** these detectors run at room temperature, where QCA as simulated here (1 K)
  doesn't fit.
- **Better fit, superconducting single-photon detectors (SNSPDs):**
  - They already sit at 1-4 K.
  - Cooling limits how many wires can leave the cryostat, so time-tagging near the
    detector matters.
  - Today this is done with cryo-CMOS or superconducting logic.

The pitch is a QCA coarse/fine TDC as an on-chip cryogenic time-tagger. Caveat: QCA is
simulation-only; nobody fabricates QCA circuits at this scale.

## GUI test

`gui_test/coarse_tdc4.qca` with `gui_test/coarse_tdc4_test.vt`.

1. Simulation Engine Setup: **Coherence Vector** with the settings in
   `../vector_tables/README.md`.
2. Type **Total Simulation Time = `4.28e-10`** exactly (107 vectors x 4 ps).
3. **Screenshot the setup dialog before you press Start.** A total time 10x too short is
   enough to break a sequential circuit like this one.

| Read near | Expected X3 X2 X1 X0 (sign) | b3..b0 | Count |
|---|---|---|---|
| 112 ps (26% along) | + + - - | 0011 | 3 |
| 256 ps (60% along) | - + + - | 1001 | 9 |
| 420 ps (98% along) | - - - + | 1110 | 14 |

## Files

| File | What |
|---|---|
| `counter_lib.py` | Toggle bit, counter chain, START/STOP window |
| `test_bit.py` | One bit: clear, count, carry pulses |
| `test_counter.py` | n-bit coarse TDC (`NB=8`, `ENGINE=gauss` and `WAIT=` via env) |
| `fine_lib.py` | Fine stage: samplers, f gate, set-latch, `async_tdc()` |
| `test_fine.py` | One edge's fine stage, edge swept over 4 quarter phases |
| `test_async.py` | Full coarse + fine TDC with asynchronous edges |
| `make_gui.py` | Writes the layouts and the GUI vector table (needs `../simulation/qde_driver`) |

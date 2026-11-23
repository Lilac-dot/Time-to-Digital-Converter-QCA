# Coarse counter TDC (wide-range stage)

The delay-line TDCs in this repo cover only 4 clock periods (16 ps at a 4 ps clock). Timing
jobs like time-of-flight imaging need nanosecond ranges, so this folder adds the usual
fix: a **coarse counter** that counts whole clock periods between START and STOP.

- **Range:** 2^n periods. 4 bits = 0-15 periods (60 ps); 8 bits = 0-255 periods (1.02 ns).
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
- **Carry:** `carry = S . b` (b before the update), from a separate majority gate. It
  reaches the next bit's S line a few periods later. A ripple counter only needs every carry
  to arrive, not to arrive in the same period, so the count is exact once the carries settle.
- **Window:** `EN = START . !STOP` feeds the LSB. START and STOP are level steps: each
  rises and then holds until the clear.
- **Clear:** `CLRk` replaces the fixed -1 in each MUX's lower AND gate. `CLR = 1` while
  `EN = 0` forces `X = 1` (b = 0). In the test files `CLR0..CLRn` are separate input cells
  driven together. On a real chip they would be one net.

**Reading the count:** `b_k = 1` when output `Xk` is negative; count = sum of `b_k * 2^k`.
Read after the carries settle: 18 periods after STOP is enough for 4 bits, 40 for 8.

## Results

The STOP edge comes N periods after START; the count read back should equal N.

| Layout | Engine | N tested | Result |
|---|---|---|---|
| `coarse_tdc4.qca` (328 cells, 0.48 um^2) | classic, r = 65 nm | 0, 3, 9, 14, 7, 15 | all exact |
| `coarse_tdc4.qca` | classic, r = 80 nm | 0, 3, 9, 14, 7, 15 | all exact |
| `coarse_tdc4.qca` | Gaussian clock (energy), r = 80 nm | 0, 3, 9, 14, 7, 15 | all exact; 7.70 meV per cycle (error +/- 0.60) |
| `coarse_tdc8.qca` (664 cells, 0.98 um^2) | classic, r = 65 nm | 200, 77 | both exact (engine overflow patched, see `../simulation/README.md`) |

Logs: `results/`. Without the window gate (EN driven directly), the 4-bit counter also
counted 5, 11, 15 and 6 exactly.

## Coarse + fine

The full design is `time = 4 * coarse + fine`, with the existing thermometer TDC
(`qca-layouts/07_conventional_tdc.qca`) as the fine stage. **In QCADesigner this gains
nothing:** vector-table inputs can only change on clock-period boundaries, so every
START-STOP interval is a whole number of periods, and the counter already resolves those.
A fine stage only pays off if START/STOP arrive asynchronously. For example, a detector
edge sampled by the delay line's clock-zone taps could resolve a quarter period. That
can't be shown in this simulator.

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
| `make_gui.py` | Writes the layouts and the GUI vector table (needs `../simulation/qde_driver`) |

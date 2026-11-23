# QCA ADDLL (work in progress)

A one-shot all-digital delay-locked loop built around the conventional QCA TDC, after the
architecture in Fig. 1(b) of Modanlou and Gholami (Sci. Rep., 2025). REF passes through a
digitally controlled delay line to DOUT. DOUT is fed back as START, STOP is REF gated by EN,
and the TDC code selects the delay. It calibrates once while EN is on, then holds that delay.
It does not track REF continuously.

None of this has been confirmed in the QCADesigner GUI yet. Results below come from the
QCADesigner-E engine source run from the command line.

## For GUI testing

**`addll_gated.qca` failed in the GUI (2026-11-23).** In both tests of `gui_test_gated/`, DOUT
never went high (peak +0.04) and the codes did not match: Test 1 ended at 0000 instead of 1110,
and in Test 2 only OUT2 ever read 1. The screenshots are `test1_output.png` and
`test2_output.png` on `main`. The cause is not known yet. Run `gui_diag/` next: three short
tests (a three-layer crossing, the delay line alone, and the ADDLL with EN held on) that
show where the signal stops.

The command-line results below come from the same engine source but have not been reproduced in
the GUI, so treat them as unconfirmed.

## Layouts

| File | What | Cells | Status |
|---|---|---|---|
| `addll.qca` | Full ADDLL; needs a clear pulse and flush before each measurement | 749 | Passes in the classic engine at 65 nm (see below) |
| `addll_comp.qca` | Gated ADDLL with START delayed 24 ps so DOUT lands one REF period after REF | 1037 | Passes the strict check in the classic engine at 65 nm; other settings not run; not tested in the GUI |
| `addll_gated.qca` | Gated selects, no clear pulse needed; DOUT is 24 ps late (see below) | 971 | Codes pass in 4 engine settings |
| `delay_line.qca` | Four switchable delay stages | 277 | Passes in 4 engine settings |
| `stage.qca` | One switchable delay stage | 64 | Passes in 4 engine settings |
| `stage_gated.qca` | One delay stage with a gated select | 89 | Passes in the 2 settings tested |
| `cross.qca` | Three-layer wire crossing | - | Passes in 4 engine settings |

## `addll_comp.qca`

`addll_gated.qca` has a fixed loop latency of 24 ps, so its DOUT comes one REF period plus
24 ps after REF (see below). `addll_comp.qca` delays the START feedback by 24 ps after the DOUT
tap to cancel it. The code becomes k = T - 9 stages, where T is the REF period in clock periods,
and DOUT lands one REF period after REF to within 0.2 ps for T = 9 to 13 (classic engine,
65 nm radius). Area is 1.37 um^2.

`verify_comp_abs.py` checks absolute DOUT delay (from an isolated REF pulse after
calibration, not modulo the REF period) and the exact thermometer pattern. Results so far, classic
engine at 65 nm only (`verify_comp_abs_fast.log`):

| T (clock periods) | Code | DOUT delay | Target 4T | Error | Result |
|---|---|---|---|---|---|
| 8 | 0000 | 36.0 ps | 32 ps | +4.0 ps | Out of range (saturated) |
| 9 | 0000 | 36.1 ps | 36 ps | +0.1 ps | Pass |
| 10 | 1000 | 40.2 ps | 40 ps | +0.2 ps | Pass |
| 11 | 1100 | 44.2 ps | 44 ps | +0.2 ps | Pass |
| 12 | 1110 | 48.1 ps | 48 ps | +0.1 ps | Pass |
| 13 | 1111 | 52.2 ps | 52 ps | +0.2 ps | Pass |
| 14 | 1111 | 52.2 ps | 56 ps | -3.8 ps | Out of range (saturated) |

In every run the code held after the isolated pulse, exactly one DOUT pulse followed it, no
stray DOUT pulse appeared in the quiet gap, and the measuring REF edge saw the 36 ps bypass delay.
The other engine settings, recalibration sequences, EN timing and probe runs were stopped
before finishing. An earlier run at 80 nm radius (classic engine) showed no DOUT pulse at T = 9;
the new START wire passes about two cell pitches from a fixed cell of the first stage's MUX,
which may be the cause. Not yet confirmed.

## `addll_gated.qca`

While EN is on, every stage bypasses, so the stored code cannot affect the measurement. The
code gives k = T - 3 stages.

An earlier version of this README gave the DOUT delay as 24 ps. That was a misreading of
phases taken modulo the REF period. A direct isolated-pulse test gives D = 36 + 4k ps, which is
one REF period plus 24 ps, so DOUT is aligned with REF only at T = 6 (where 24 ps is exactly one
period). The codes below are still correct.

| REF period | Code | DOUT phase mod T, classic engine | DOUT phase mod T, Gaussian clock |
|---|---|---|---|
| 3 (12 ps) | 0000 | 0.1 ps (classic 65 nm only) | Not run |
| 4 (16 ps) | 1000 | 8.1 to 8.2 ps | 9.7 ps |
| 5 (20 ps) | 1100 | 4.0 to 4.1 ps | 5.5 to 5.6 ps (80 nm) |
| 6 (24 ps) | 1110 | 0.1 ps | 1.6 ps (80 nm) |
| 7 (28 ps) | 1111 | 24.1 to 24.3 ps | 25.7 to 25.8 ps |
| 8 (32 ps) | 1111 | 20.0 to 20.1 ps: out of range (classic 65 nm only) | Not run |

Readings are taken after one settling cycle. It also recalibrated up and down in one run
through periods 6, 7, 5, 4 and 7, in the classic engine at 65 nm and under the Gaussian clock
at 80 nm. Energy is 21.1 to 21.7 meV per clock cycle, with an engine balance error of 1.57 to
1.63 meV, averaged over each whole test run. Area is 1.21 um^2.

## `addll.qca` with the clear-then-measure sequence

Classic engine, 65 nm radius, one period of the 4 ps clock per vector.

| REF period (clock periods) | Code | DOUT delay after REF |
|---|---|---|
| 5 | 1000 | 20 ps (one REF period) |
| 6 | 1100 | 20.1 ps |
| 7 | 1110 | 20.1 ps |
| 8 | 1111 | 20.1 ps |
| 9 | 1111 | 16 ps (out of range) |

It also recalibrated up and down in one run. Under the Gaussian clock at 80 nm, only periods
6 and 8 have been checked: same codes, delay 21.6 to 21.7 ps.

Do not use `addll_sweep.json` or `addll_verify.json` as lock results. Those runs started from
a stale start-up code, so their lock range is wrong. They are kept as a record.

## Scripts

`build_addll.py`, `build_addll_gated.py` and `build_addll_comp.py` generate the layouts. They need
`../qca-layouts/` and, for simulation, the compiled driver from `../simulation/`.
`preclear_sweep.py`, `verify_gated.py` and `verify_comp_abs.py` run the main checks.
`build_comp_probe.py` makes a copy of `addll_comp.qca` with internal probe outputs (ENB, Q and
select of each stage, and START). `make_gui_diag.py` builds `gui_diag/`.

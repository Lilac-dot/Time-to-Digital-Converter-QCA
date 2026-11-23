# QCA ADDLL (work in progress)

A one-shot all-digital delay-locked loop built around the conventional QCA TDC, after the
architecture in Fig. 1(b) of Modanlou and Gholami (Sci. Rep., 2025). REF passes through a
digitally controlled delay line to DOUT. DOUT is fed back as START, STOP is REF gated by EN,
and the TDC code selects the delay. It calibrates once while EN is on, then holds that delay.
It does not track REF continuously.

None of this has been confirmed in the QCADesigner GUI yet. Results below come from the
QCADesigner-E engine source run from the command line.

## For GUI testing

Download `addll_gated_gui_test.zip` first and follow the `README.md` inside it. That is the
main version. `addll_gui_test.zip` is the older, smaller version.

## Layouts

| File | What | Cells | Status |
|---|---|---|---|
| `addll.qca` | Full ADDLL; needs a clear pulse and flush before each measurement | 749 | Passes in the classic engine at 65 nm (see below) |
| `addll_comp.qca` | Gated ADDLL with START delayed 24 ps so DOUT lands one REF period after REF | 1037 | Passes in the classic engine at 65 nm; full check pending |
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

`verify_comp.py` runs the full set: the period sweep in four engine settings and recalibration
in one run. Its results are not in yet, so treat this layout as checked in one setting only.

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
`preclear_sweep.py`, `verify_gated.py` and `verify_comp.py` run the main checks.

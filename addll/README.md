# QCA ADDLL (work in progress)

A one-shot all-digital delay-locked loop built around the conventional QCA TDC, after the
architecture in Fig. 1(b) of Modanlou and Gholami (Sci. Rep., 2025). REF passes through a
digitally controlled delay line to DOUT. DOUT is fed back as START, STOP is REF gated by EN,
and the TDC code selects the delay. It calibrates once while EN is on, then holds that delay.
It does not track REF continuously.

None of this has been confirmed in the QCADesigner GUI yet. Results below come from the
QCADesigner-E engine source run from the command line.

## For GUI testing

Download `addll_gui_test.zip` and follow the `README.md` inside it.

## Layouts

| File | What | Cells | Status |
|---|---|---|---|
| `addll.qca` | Full ADDLL; needs a clear pulse and flush before each measurement | 749 | Passes in the classic engine at 65 nm (see below) |
| `addll_gated.qca` | Full ADDLL with gated selects; no clear pulse needed | 971 | Full check still in progress |
| `delay_line.qca` | Four switchable delay stages | 277 | Passes in 4 engine settings |
| `stage.qca` | One switchable delay stage | 64 | Passes in 4 engine settings |
| `stage_gated.qca` | One delay stage with a gated select | 89 | Passes in the 2 settings tested |
| `cross.qca` | Three-layer wire crossing | - | Passes in 4 engine settings |

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

`build_addll.py` and `build_addll_gated.py` generate the layouts. They need
`../qca-layouts/` and, for simulation, the compiled driver from `../simulation/`.
`preclear_sweep.py` and `verify_gated.py` run the main checks.

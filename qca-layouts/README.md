# QCA layouts

Every file here passes simulation (see `../simulation/RESULTS.md`).

| File | What | Cells |
|---|---|---|
| `01_majority_gate.qca` | Majority gate | 5 |
| `02_wire_inverter.qca` | Wire + inverter | 11 |
| `07_conventional_tdc.qca` | Conventional TDC, paper Fig. 1(b) | 256 |
| `08_mux2to1_fig2c.qca` | 2:1 MUX, paper Fig. 2(c) | 12 |
| `DFlipFlop.qca` | Hand-built D-latch (level-sensitive, despite the name) | 22 |

`qca_gen.py` writes the file format, `build_conventional_tdc.py` and `build_mux_fig2c.py`
generate 07 and 08, and `preview.py` renders a `.qca` to PNG. `01` and `02` come from
`../archive/build.py`. Generated files have been run in the engine but not yet opened in
the QCADesigner GUI.

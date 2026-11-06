# Time-to-Digital-Converter-QCA
Reproduction and implementation of a low-power Time-to-Digital Converter (TDC) using Quantum-dot Cellular Automata (QCA), based on Modanlou & Gholami, IEEE Access, 2025.

| Path | What |
|---|---|
| `qca-layouts/07_conventional_tdc.qca` | Conventional TDC (paper Fig. 1b): 256 cells |
| `qca-layouts/08_mux2to1_fig2c.qca` | 2:1 MUX (paper Fig. 2c): 12 cells |
| `DFlipFlop` | Hand-built MUX-based D-latch: 22 cells |
| `TDC-final` | Hand-built proposed TDC (paper Fig. 3b): 187 cells + 1 stray |
| `qca-layouts/` | Other blocks and the Python generators |
| `simulation/` | Solver, test script, energy results: start at `simulation/RESULTS.md` |

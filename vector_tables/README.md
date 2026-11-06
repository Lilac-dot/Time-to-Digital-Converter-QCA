# Vector tables for QCADesigner

Each `.vt` loads with its matching layout. Input order is set by the design, so keep each
pair together. Every vector lasts one clock period, so set
**Total Simulation Time = vectors x 4e-12 s**.

| Layout | Vector table | Vectors | Total Simulation Time | Expected result |
|---|---|---|---|---|
| `qca-layouts/07_conventional_tdc.qca` | `07_conventional_tdc.vt` | 115 | 4.6e-10 | OUT0..3 latch 1000, 1100, 1110, 1111 in turn |
| `qca-layouts/08_mux2to1_fig2c.qca` | `08_mux2to1_fig2c.vt` | 24 | 9.6e-11 | OUT = I1 when S=1, I0 when S=0 |
| `DFlipFlop` | `DFlipFlop.vt` | 32 | 1.28e-10 | OUT follows D while CLK=1, holds while CLK=0 |
| `qca-layouts/01_majority_gate.qca` | `01_majority_gate.vt` | 24 | 9.6e-11 | OUT = majority of A, B, C |
| `TDC-final` | `TDC-final.vt` | 115 | 4.6e-10 | **Known problem:** gives 1110 for every gap |

## Steps

1. File > Open the layout.
2. Simulation > Simulation Engine Setup: choose **Coherence Vector**, then open its options
   and enter the values below.
3. Simulation > Simulation Type Setup: choose **Vector Table**, then open the matching
   `.vt` file.
4. Simulation > Start Simulation. The results window opens when it finishes.

| Option | Value |
|---|---|
| Temperature | 1 K |
| Relaxation time | 1e-15 s |
| Time step | 1e-16 s |
| Total simulation time | see table above |
| Clock high / low | 9.8e-22 / 3.8e-23 J |
| Clock shift | 0 |
| Clock amplitude factor | 2 |
| Radius of effect | 65 nm |
| Relative permittivity | 12.9 |
| Layer separation | 11.5 nm |
| Algorithm | Euler |

The expected results above were checked headlessly with the same coherence-vector engine
source from QCADesigner-E, not in the Windows QCADesigner GUI.

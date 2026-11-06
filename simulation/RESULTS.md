# Results

All numbers come from `run_all.py` with this repo's solver, **not QCADesigner or
QCADesigner-E** (see `README.md`). Raw values are in `results/results.json`.

## Conventional TDC (paper Fig. 1b)

256 cells, 0.292 um^2. Cell positions and clock zones were read from the vector drawing
in the paper's PDF. Zones the figure hides (input, output, fixed and 3 kinds of unlabelled
yellow cell) were inferred from neighbours and the mirrored cell.

| STOP after START | OUT0..3 |
|---|---|
| 0 periods | 1000 |
| 1 period | 1100 |
| 2 periods | 1110 |
| 3 periods | 1111 |

This matches the sequence in the paper's Fig. 7(a), with output polarization of +/-0.953
(paper: 0.953). One code step per clock period gives 4 ps resolution at a 4 ps clock.

![Waveforms](results/conventional_tdc_waveforms.png)

## Energy per clock cycle, whole circuit

E_bath is the energy dissipated to the thermal bath. The error is |E_bath + E_clk + E_io|,
which would be zero if energy balanced exactly in each cycle.

| Settings | Correct codes | E_bath (meV) | Error (meV) | P at 1 GHz (pW) | P at 250 GHz (nW) |
|---|---|---|---|---|---|
| Gaussian clock, r = 80 nm (QCADesigner-E style) | yes | 7.40 | 0.63 | 1.19 | 0.296 |
| Gaussian clock, r = 65 nm | yes | 7.38 | 0.62 | 1.18 | 0.296 |
| Cosine clock, r = 65 nm (QCADesigner 2.0.3 style) | yes | 14.77 | 0.96 | 2.37 | 0.592 |
| Cosine clock, r = 80 nm | yes | 14.76 | 0.96 | 2.37 | 0.591 |

P = E x f (paper eq. 6). Energy was simulated at a 4 ps clock only, so 250 GHz is the
self-consistent column. The 1 GHz column is arithmetic for comparison with the paper; a
slower clock would really dissipate less per cycle.

### Clock-high sweep (kink energy Ek = 1.484 meV between adjacent cells)

| Clock high | Correct codes | E_bath (meV) |
|---|---|---|
| 0.5 Ek | no (all 0000) | 0.63 |
| 1.0 Ek | no (stops at 1100) | 3.35 |
| 1.5 Ek | yes | 7.10 |
| default (9.8e-22 J = 4.1 Ek) | yes | 7.40 |

### Temperature (Gaussian clock, r = 80 nm)

| T (K) | Correct codes | Smallest peak polarization | E_bath (meV) |
|---|---|---|---|
| 1 | yes | 0.953 | 7.40 |
| 5 | no (all 1111) | 0.902 | 5.69 |
| 10 | no (all 1111) | 0.618 | 3.44 |
| 20 | no (all 1111) | 0.026 | 2.45 |

Energy values in rows marked "no" describe a circuit that is not working, so do not quote
them as operating figures.

### Where the energy goes

The hottest cells (0.225 meV per cycle each) are in the edge converters, next to the
diagonal inverter. The paper's Fig. 7(b) also shows dark cells around the edge converters.

![Energy map](results/conventional_tdc_energy_map.png)

## Blocks

| Block | Cells | Area (um^2) | Works | E_bath (meV/cycle) |
|---|---|---|---|---|
| Majority gate | 5 | 0.0034 | yes | 0.158 |
| Wire + inverter | 11 | 0.0218 | yes | 0.617 |
| 2:1 MUX, paper Fig. 2(c) | 12 | 0.0096 | yes | 0.633 |
| D-latch, hand-built (`DFlipFlop`) | 22 | 0.0186 | yes | 0.315 |
| 2:1 MUX, generated | 51 | 0.1075 | **no** | - |
| D-latch, generated | 73 | 0.1210 | **no** | - |
| Edge converter, generated | 27 | 0.0246 | **no** | - |
| DFF, generated | 103 | 0.1926 | **no** | - |

Energy depends on the input pattern, so block values are for an exhaustive or
latch-exercising sequence, not a worst case.

## Comparison with the paper's Table 3

These cannot be compared directly, so no percentage is claimed here.

- Paper, conventional TDC: switching 0.33 / 0.302 / 0.2518 and leakage 0.066 / 0.216 / 0.4
  at 0.5 / 1 / 1.5 Ek. The table header says meV but the text says eV.
- The paper does not name its energy tool. A switching/leakage split at those Ek levels is
  the format QCAPro reports, while this solver reports bath dissipation, which is a
  different quantity. Reproducing Table 3 needs the tool the authors actually used.
- The paper's Table 4 reports working operation at 5 K and above for its proposed TDC,
  whereas the conventional TDC fails at 5 K in this solver. That has not been checked in
  QCADesigner.

## Open issue: `TDC-final`

187 connected cells and 0.178 um^2 (paper: 187 cells, 0.18 um^2), plus one stray cell at
x = 440, y = 640 that is not connected to anything.

In this solver it gives 1110 for every gap under the Gaussian/80 nm and both cosine
settings, and 1100 for gap 0 under Gaussian/65 nm, so it fails in all four. The edge
pulse and delay ring both work. The fault traced is at the mid-wire taps (17,17) and
(0,17) on the cell grid: the branch cell stays at -1 while the wire is +1, because the tap
shares clock zone 0 with the latch below it. The paper's Fig. 3(b) has the same structure,
so this needs checking in QCADesigner before concluding the layout is wrong. No energy is
reported for it, and no conventional-vs-proposed saving is claimed.

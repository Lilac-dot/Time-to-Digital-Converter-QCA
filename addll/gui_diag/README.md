# ADDLL GUI diagnostic

In the GUI run of `addll_gated.qca`, DOUT never went high (peak +0.04) and the codes were
wrong. These three short tests find where the signal stops. Run them in order and send back a
screenshot of each results window.

Use the same Coherence Vector settings as `../gui_test_gated/README.md` (1 K, relaxation
1e-15 s, time step 1e-16 s, clock 9.8e-22 / 3.8e-23 J, amplitude factor 2, radius of effect
65 nm, permittivity 12.9, layer separation 11.5 nm, Euler). Only the total simulation time
changes. Each vector lasts one clock period, 4 ps.

Please also send, once:
- a screenshot of the layout after loading `addll_gated.qca`, showing the cell count
- a screenshot of the Simulation Engine Setup dialog
- the QCADesigner version (Help > About)

## Diag 1: three-layer wire crossing

`cross.qca` with `diag1_cross.vt`, Total Simulation Time `4.8e-11` (12 vectors).

Wire A runs on the main layer and wire B crosses over it on the crossover layer. Inputs (A, B)
step through 00, 01, 10, 11, three vectors each. XA must follow A only and XB must follow B
only: by the end of each step, XA reads 0, 0, 1, 1 and XB reads 0, 1, 0, 1.

If this fails, the GUI is not handling the via and crossover layers the way the command-line
engine does, and every ADDLL layout will fail for that reason.

## Diag 2: delay line alone

`delay_line.qca` with `diag2_delay_line.vt`, Total Simulation Time `8.8e-10` (220 vectors).

One D pulse in each of five blocks, with 0, 1, 2, 3 and 4 stages selected (S0 to S3 set as a
thermometer code). D rises at 80, 256, 432, 608 and 784 ps. Q should rise once per block, each
time 4 ps later relative to D than the block before. In the command-line engine the delays are
28.2, 32.1, 36.2, 40.0 and 44.1 ps, so Q rises near 108, 288, 468, 648 and 828 ps.

If Q never goes high, the fault is in the delay stages.

## Diag 3: gated ADDLL with EN held on

`addll_gated.qca` with `diag3_gated_en_on.vt`, Total Simulation Time `4.88e-10` (122 vectors).

EN turns on at 56 ps and stays on, so every stage is bypassed. REF then pulses six times,
rising at 136, 184, 232, 280, 328 and 376 ps. DOUT should go high once after each REF pulse,
about 36 ps later (near 172, 220, 268, 316, 364 and 412 ps), peaking near +0.95.

If Diags 1 and 2 pass but this fails, the fault is in the ADDLL's own wiring (REF input,
DOUT tap or feedback), not in the parts.

## What we already know

The expected values come from the same QCADesigner-E source, compiled and run from the
command line. The ADDLL layouts are the first three-layer files to be run in the GUI; the
conventional TDC, which passed in the GUI, uses one layer.

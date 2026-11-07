# Gated ADDLL GUI test

Please run these in QCADesigner and send back the results. This is the main version of the
circuit. Expected values come from the QCADesigner-E classic coherence-vector engine run from
the command line. It has not been opened in the GUI before.

## Setup

1. Open `addll_gated.qca`. **Check first:** it should show 971 cells on three layers, with
   inputs REF and EN and outputs OUT0, OUT1, OUT2, OUT3 and DOUT. Tell us if it fails to load.
2. Simulation > Simulation Engine Setup: choose **Coherence Vector** and enter:

| Option | Value |
|---|---|
| Temperature | 1 K |
| Relaxation time | 1e-15 s |
| Time step | 1e-16 s |
| Total simulation time | see the test below |
| Clock high / low | 9.8e-22 / 3.8e-23 J |
| Clock shift | 0 |
| Clock amplitude factor | 2 |
| Radius of effect | 65 nm |
| Relative permittivity | 12.9 |
| Layer separation | 11.5 nm |
| Algorithm | Euler |

3. Simulation > Simulation Type Setup: choose **Vector Table** and open the test's `.vt` file.
4. Simulation > Start Simulation. These are large runs, so expect them to take a while.

## Test 1: one calibration (start here)

File `gated_test1_period6.vt`, Total Simulation Time `4.16e-10`.

Near the end of the run (about 404 ps, or 97% of the way along the trace), OUT0 to OUT3
should read **1110**. A positive pulse is 1 and a negative pulse is 0. Peaks should be
about +/-0.95.

## Test 2: recalibration up and down

File `gated_test2_recalibrate.vt`, Total Simulation Time `2.04e-09`.

| REF period | Read near | OUT0 to OUT3 |
|---|---|---|
| 24 ps | 404 ps (20% along) | 1110 |
| 28 ps | 860 ps (42% along) | 1111 |
| 20 ps | 1236 ps (61% along) | 1100 |
| 16 ps | 1572 ps (77% along) | 1000 |
| 28 ps | 2028 ps (99% along) | 1111 |

## What to send back

- Whether the file loaded, and any error text
- A screenshot of the design and of the full results window for each test
- The codes you read, and any setting you had to change

If a result doesn't match, don't change the layout. Send the screenshot and settings.

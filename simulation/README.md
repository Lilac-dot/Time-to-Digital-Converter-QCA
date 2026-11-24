# Simulation

| File | What |
|---|---|
| `qde_driver.c`, `build_qde.sh` | Run the real QCADesigner-E engines headless with a chosen input pattern |
| `run_qde.py` | Energy numbers and tests through QCADesigner-E: `results/qde_results.json` |
| `test_classic.py` | Working layouts in the classic coherence-vector engine |
| `test_proposed_fig8.py` | Authors' proposed TDC with the stimulus from their Fig. 8(a) |
| `plot_qde.py` | Figures from QCADesigner-E output |
| `qca_sim.c`, `run_all.py` | Independent solver, used as a cross-check |

Get the sources from https://github.com/FSillT/QCADesigner-E, then:

    brew install glib
    ./build_qde.sh /path/to/QCADesigner-E/QCADesignerE/src
    python3 run_qde.py

On macOS, if linking fails with an SDK error, set `SDK=/Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk`.

Defaults: T = 1 K, relaxation 1e-15 s, time step 1e-16 s, clock 4 ps, clock high/low
9.8e-22 / 3.8e-23 J, Gaussian ramp 1 ps, radius 80 nm, epsilon_r 12.9.

QCADesigner-E: F. Sill Torres, R. Wille, P. Niemann, R. Drechsler, IEEE TCAD 37(12), 2018.
QCADesigner: K. Walus et al., IEEE Trans. Nanotechnology 3, 2004.

## Long vector tables: engine overflow

The classic coherence-vector engine picks the current input vector with
`(j * vectors) / samples` (`coherence_vector.c`, line 350 in QCADesigner-E; the same code is
in QCADesigner 2.0.3). `j` and `vectors` are `int`, so the product is a signed 32-bit value
and overflows at 2^31. At 40,000 samples per vector (4 ps clock, 1e-16 s step) that is about
231 vectors. The wrapped product is then converted to `unsigned long` for the division
(`samples` is `unsigned long`):

- Linux/macOS 64-bit builds (this driver): `unsigned long` is 64 bits, so the negative product
  becomes a huge index. The run segfaults past about 231 vectors.
- Windows builds: `unsigned long` is 32 bits, so the conversion gives the product mod 2^32,
  which is still right up to 2^32, about 327 vectors. Past that, the inputs would restart from
  vector 0 partway through the run (worked out from the code, not observed in the GUI).

For long runs here, patch that line to
`((unsigned long long)j * pvt->vectors->icUsed) / number_samples` before building. In the
GUI, keep a vector table under about 320 vectors at this clock, or split the test.

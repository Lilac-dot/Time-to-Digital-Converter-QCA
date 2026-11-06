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

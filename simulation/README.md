# Simulation

`qca_sim.c` is an independent coherence-vector solver with the per-cycle energy integrals
of Sill Torres et al. (TCAD 2018), using QCADesigner-E's constants and clock waveform.
**It is not QCADesigner-E.** It has not been compared numerically with QCADesigner or
QCADesigner-E, so confirm any number you publish in the real tool.

    cc -O2 -o qca_sim qca_sim.c -lm
    python3 run_all.py        # needs numpy and matplotlib; writes results/

On macOS, if linking fails with an SDK error, add
`-isysroot /Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk`.

Defaults: T = 1 K, relaxation 1e-15 s, time step 1e-16 s, clock 4 ps, clock high/low
9.8e-22 / 3.8e-23 J, Gaussian ramp 1 ps, radius 80 nm, epsilon_r 12.9.

Model references: Tougaw & Lent, J. Appl. Phys. 80 (1996); Timler & Lent, J. Appl. Phys.
91 (2002); Sill Torres et al., IEEE TCAD 37 (2018).

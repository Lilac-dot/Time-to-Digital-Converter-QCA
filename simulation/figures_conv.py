#!/usr/bin/env python3
"""Rendered layout and waveform plot for the conventional TDC, in the same style as
coarse_tdc/figures.py. Waveforms come from the QCADesigner-E run saved by run_qde.py
(results/qde_conv_trace.npz). Writes PNG and SVG into results/."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "coarse_tdc"))
import figures as F  # noqa: E402

F.OUT = os.path.join(HERE, "results")
F.layout(os.path.join(HERE, "..", "qca-layouts", "07_conventional_tdc.qca"),
         "layout_conventional_tdc", "Conventional delay-line TDC")
F.waves(os.path.join(HERE, "results", "qde_conv_trace.npz"), "waves_conventional_tdc",
        "Conventional TDC in QCADesigner-E (Gaussian clock): STOP 0 to 3 periods after START",
        [("IN", "START (IN)", "in"), ("CLK", "STOP (CLK)", "in"), ("OUT0", "OUT0", "out"),
         ("OUT1", "OUT1", "out"), ("OUT2", "OUT2", "out"), ("OUT3", "OUT3", "out")],
        marks=[(70, "1000"), (168, "1100"), (270, "1110"), (375, "1111")], env=True)

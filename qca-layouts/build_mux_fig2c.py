#!/usr/bin/env python3
"""build_mux_fig2c.py - 12-cell 2:1 MUX from Modanlou & Gholami Fig. 2(c), right-hand
layout, read from the vector drawing in the PDF. All cells are in clock zone 0.
OUT = S.I1 + !S.I0 (eq. 2)."""
from qca_gen import Layout, PITCH

GRID = ["...T.",
        ".m00.",
        "S0.0O",
        ".p00.",
        "...B."]
KEY = {"T": ("input", "I0"), "B": ("input", "I1"), "S": ("input", "S"), "O": ("output", "OUT")}


def build(path="08_mux2to1_fig2c.qca"):
    L = Layout()
    for r, row in enumerate(GRID):
        for c, ch in enumerate(row):
            x, y = c * PITCH + 40.0, r * PITCH + 40.0
            if ch == "0":
                L.add(x, y, 0)
            elif ch == "m":
                L.add(x, y, 0, "fixed", pol=-1)
            elif ch == "p":
                L.add(x, y, 0, "fixed", pol=1)
            elif ch in KEY:
                L.add(x, y, 0, KEY[ch][0], name=KEY[ch][1])
    L.write(path)


if __name__ == "__main__":
    build()

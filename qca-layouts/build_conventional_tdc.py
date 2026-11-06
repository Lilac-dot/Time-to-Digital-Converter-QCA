#!/usr/bin/env python3
"""
build_conventional_tdc.py - the CONVENTIONAL delay-line TDC of Modanlou & Gholami
(IEEE Access 2025), Fig. 1(b): the benchmark, not the proposed design of Fig. 3.

The grid below was read from the vector drawing in the paper's PDF (cell rectangles
and their fill colours), so positions and clock zones are the paper's own: 256 cells
on a 32 x 23 grid at 20 nm pitch.

Key: 0-3 clock zone | I input | F fixed | O output | . empty
     a-g cells whose colour in the figure hides the clock zone (see HIDDEN)

Each output is a flip-flop  Q+ = EDGE.D + !EDGE.Q  built from three majority gates,
with its own level-to-edge converter EDGE = CLK . !CLK(t-1). The flip-flops tap a
delay line one clock period apart, so OUT0..OUT3 form a thermometer code.
"""
from qca_gen import Layout, PITCH

GRID = """
.......3332221110000333333333332
.......3.............3.........2
.......3.............3.........2
.......a.............a.........2
....F..0.............0..F......2
O33221000F.........F00012233O..2
..3.2..0.3.........3.0..2.3....2
..0.1..033333323333330..1.0....2
..01110..3..0.2.0..3..01110....2
....1....2..0.2.0..2....1......2
....1....211..2..112....1......1
....F.........2.........F......1
....1.........I.........1......1
....1....211..2..11b....1......1
....1....2..0.2.0..2....1......1
..01110..3..0.2.0..3..01110....1
..0.1..033333323a3333c..1.0....1
..3.2..0.3.........3.0..2.3....1
O33221000F.........F00012233O..0
....F..0.............0..F......0
.......a.............a.........0
.......3.............3.........0
..I22233300001111222233333000000
"""

# Yellow in the figure, with no label: unnamed probe cells on the wires. Fig. 7 plots
# only OUT0-3, so they are plain wire cells here. Zones come from the neighbours and
# from the left/right mirror cell, which is coloured.
HIDDEN = {"a": 3, "b": 2, "c": 0}

OUTPUTS = {(18, 0): "OUT0", (18, 28): "OUT1", (5, 28): "OUT2", (5, 0): "OUT3"}
INPUTS = {(22, 2): "IN", (12, 14): "CLK"}
FIXED_PLUS = {(4, 4), (19, 4), (4, 24), (19, 24)}   # labelled 1.00; the other six are -1.00

# Input, output and fixed colours also hide the zone, so use the zone they feed.
# The engine holds input and fixed cells at their set value whatever the zone.
SPECIAL_ZONE = {(22, 2): 2, (12, 14): 2,
                (18, 0): 3, (18, 28): 3, (5, 28): 3, (5, 0): 3,
                (4, 4): 2, (19, 4): 2, (4, 24): 2, (19, 24): 2,
                (11, 4): 1, (11, 24): 1,
                (5, 9): 0, (5, 19): 0, (18, 9): 0, (18, 19): 0}


def build(path="07_conventional_tdc.qca"):
    L = Layout()
    for r, row in enumerate(GRID.strip().splitlines()):
        for c, ch in enumerate(row):
            if ch == ".":
                continue
            x, y = c * PITCH + 40.0, r * PITCH + 40.0
            rc = (r, c)
            if ch == "I":
                L.add(x, y, SPECIAL_ZONE[rc], "input", name=INPUTS[rc])
            elif ch == "O":
                L.add(x, y, SPECIAL_ZONE[rc], "output", name=OUTPUTS[rc])
            elif ch == "F":
                L.add(x, y, SPECIAL_ZONE[rc], "fixed", pol=1 if rc in FIXED_PLUS else -1)
            elif ch in HIDDEN:
                L.add(x, y, HIDDEN[ch], "normal")
            else:
                L.add(x, y, int(ch), "normal")
    L.write(path)
    return L


if __name__ == "__main__":
    build()

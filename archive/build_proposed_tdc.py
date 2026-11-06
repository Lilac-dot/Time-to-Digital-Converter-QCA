#!/usr/bin/env python3
"""
build_proposed_tdc.py - the PROPOSED delay-line TDC of Modanlou & Gholami (IEEE Access
2025), Fig. 3(b): 187 cells on a 25 x 18 grid at 20 nm pitch.

The grid below was read from the vector drawing in the paper's PDF, so positions and
clock zones are the authors'. Key: 0-3 clock zone | I input | F fixed (-1.00) | O output.
Input, output and fixed colours hide the clock zone, so those come from SPECIAL_ZONE.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "qca-layouts"))
from qca_gen import Layout, PITCH

GRID = """
....033322211100000003333
....0............0......3
....0............0......3
.F000000333322230000F...3
..0.0........2...0.0....3
30000........1...00003..3
3...1...00I..1...1...3..2
322O1..1..2..1...1O223..2
.......1..3..0..........2
.......2233330..........2
322O1.....3..0...1O223..2
3...1.....F..2...1...3..2
30000........2...00003..1
..0.0........2...0.0....1
.F000003333332330000F...1
....0............0......1
....0............0......1
....I00111222333000000111
"""

OUTPUTS = {(10, 3): "OUT0", (10, 18): "OUT1", (7, 18): "OUT2", (7, 3): "OUT3"}
INPUTS = {(17, 4): "IN", (6, 10): "CLK"}
SPECIAL_ZONE = {(17, 4): 0, (6, 10): 0,
                (3, 1): 0, (14, 1): 0, (3, 20): 0, (14, 20): 0, (11, 10): 3}


def build(path="09_proposed_tdc.qca", out_zone=2):
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
                L.add(x, y, out_zone, "output", name=OUTPUTS[rc])
            elif ch == "F":
                L.add(x, y, SPECIAL_ZONE[rc], "fixed", pol=-1)
            else:
                L.add(x, y, int(ch), "normal")
    L.write(path)


if __name__ == "__main__":
    build(*sys.argv[1:2])

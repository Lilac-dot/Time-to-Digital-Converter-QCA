#!/usr/bin/env python3
"""Full one-shot ADDLL, after Fig. 1(b) of Modanlou & Gholami (Sci. Rep. 2025):
REF -> DCDL -> DOUT, fed back as START; STOP = REF.EN; the TDC code selects the DCDL delay."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "qca-layouts"))
from addll_lib import delay_line, via, zones
from build_conventional_tdc import FIXED_PLUS, GRID, HIDDEN, OUTPUTS, SPECIAL_ZONE
from qca_ml import ML

OFF, R, COLS = 3, 35, [13, 26, 39, 52]


def tdc(L):
    for r, row in enumerate(GRID.strip().splitlines()):
        for c, ch in enumerate(row):
            if ch == ".":
                continue
            rc, p = (r, c), (r, c + OFF)
            if ch == "I":
                L.add(*p, SPECIAL_ZONE[rc])                      # IN and CLK are now driven
            elif ch == "O":
                L.add(*p, SPECIAL_ZONE[rc], "output", name=OUTPUTS[rc])
            elif ch == "F":
                L.add(*p, SPECIAL_ZONE[rc], "fixed", pol=1 if rc in FIXED_PLUS else -1)
            elif ch in HIDDEN:
                L.add(*p, HIDDEN[ch])
            else:
                L.add(*p, int(ch))


def route(L, start, segs):
    """segs: list of (layer, [cells]). The last cell of each segment before a layer change
    is a via. Zones run across the whole route."""
    cells = [(l, p) for l, ps in segs for p in ps]
    for (l, p), z in zip(cells, zones(len(cells), start[0], start[1])):
        L.add(p[0], p[1], z, layer=l)
        if l == 0 and any(q == p and m == 2 for m, q in cells):
            L.add(p[0], p[1], z, layer=1)
    return cells


def line(a, b):
    dr, dc = (b[0] > a[0]) - (b[0] < a[0]), (b[1] > a[1]) - (b[1] < a[1])
    out = [a]
    while out[-1] != b:
        out.append((out[-1][0] + dr, out[-1][1] + dc))
    return out


def build(path="addll.qca"):
    L = ML()
    tdc(L)
    (fr, fc), a, vias, (or_, oc), g = delay_line(L, R, COLS)
    v = {c + 1: (p, z) for c, (p, z) in zip(COLS, vias)}

    # --- thermometer code to the select lines; zones end at each via
    def sel(start_zone, segs, col):
        p, z = v[col]
        route(L, (start_zone, z), segs)
    sel(3, [(0, line((5, 2), (5, 1)) + line((6, 1), (26, 1))), (2, [(26, 1)] + line((26, 2), (26, 14)) + line((27, 14), (32, 14)))], 14)
    sel(3, [(0, line((19, 3), (24, 3))), (2, [(24, 3)] + line((24, 4), (24, 27)) + line((25, 27), (32, 27)))], 27)
    sel(3, [(0, line((19, 31), (20, 31))), (2, [(20, 31)] + line((21, 31), (26, 31)) + line((26, 32), (26, 40)) + line((27, 40), (32, 40)))], 40)
    sel(3, [(0, [(5, 32)]), (2, [(5, 32)] + line((5, 33), (5, 36))), (0, [(5, 36)] + line((6, 36), (24, 36))),
            (2, [(24, 36)] + line((24, 37), (24, 53)) + line((25, 53), (32, 53)))], 53)

    # --- START: DCDL output west then north into the TDC's IN cell, with a DOUT tap
    st = line((or_, oc - 1), (or_, 5)) + line((or_ - 1, 5), (23, 5))
    zs = zones(len(st), g, 1)
    for p, z in zip(st, zs):
        L.add(p[0], p[1], z)
    i = st.index((30, 5))
    L.add(30, 4, zs[i])
    L.add(30, 3, (zs[i] + 1) % 4, "output", name="DOUT")

    # --- REF: east input, fork to the DCDL and north to the STOP gate
    L.add(fr, 61, 0, "input", name="REF")
    for c in (60, 59):
        L.add(fr, c, 0)
    for c, z in zip(range(58, fc, -1), [1, 1]):
        L.add(fr, c, (a - 1) % 4)
    G = 0                                                   # zone of the STOP gate
    n = line((fr - 1, 59), (15, 59))
    for p, z in zip(n, zones(len(n), 0, (G - 2) % 4)):
        L.add(p[0], p[1], z)
    for rr in (14, 13):
        L.add(rr, 59, (G - 1) % 4)
    for rr, fn in ((11, "normal"), (10, "input")):
        L.add(rr, 59, (G - 1) % 4, fn, name="EN" if fn == "input" else None)
    L.add(12, 59, G)
    L.add(12, 60, (G - 1) % 4)
    L.add(12, 61, (G - 1) % 4, "fixed", pol=-1)
    y = (G + 1) % 4
    L.add(12, 58, y)
    via(L, 12, 57, y)
    w = line((12, 56), (12, 18))
    for p, z in zip(w, zones(len(w), y, 1)):
        L.add(p[0], p[1], z, layer=2)
    via(L, 12, 17, 2)
    print("cells", L.count(), "area_um2", round(L.area_um2(), 4))
    return L.write(path), L


if __name__ == "__main__":
    build()

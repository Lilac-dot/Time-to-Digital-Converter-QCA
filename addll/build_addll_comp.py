#!/usr/bin/env python3
"""Compensated gated ADDLL. As build_addll_gated.py, but the START feedback is delayed by
24 ps after the DOUT tap. That cancels the loop's fixed 24 ps latency, so the code becomes
k = T - 9 and DOUT lands exactly one REF period after REF (T = 9 to 13 clock periods)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "qca-layouts"))
from addll_lib import via, zones, zones_t
from addll_lib_gated import delay_line_gated
from build_addll import line, route, tdc
from qca_ml import ML

R, COLS = 35, [13, 30, 47, 64]
EXTRA = 24   # ps of extra START delay = the fixed latency to cancel
EAST = 33


def build(path="addll_comp.qca"):
    L = ML()
    tdc(L)
    st, (or_, oc), g = delay_line_gated(L, R, COLS)
    z = 0
    (fr, fc), a = st[-1][0], st[-1][1]

    # thermometer code to the gates; every route ends in zone z at its via
    route(L, (3, z), [(0, line((5, 2), (5, 1)) + line((6, 1), (26, 1))), (2, [(26, 1)] + line((26, 2), (26, 16)) + line((27, 16), (29, 16)))])
    route(L, (3, z), [(0, line((19, 3), (24, 3))), (2, [(24, 3)] + line((24, 4), (24, 33)) + line((25, 33), (29, 33)))])
    route(L, (3, z), [(0, [(5, 32)]), (2, [(5, 32)] + line((5, 33), (5, 36))), (0, [(5, 36)] + line((6, 36), (24, 36))),
                      (2, [(24, 36)] + line((24, 37), (24, 50)) + line((25, 50), (29, 50)))])
    route(L, (3, z), [(0, line((19, 31), (20, 31))), (2, [(20, 31)] + line((20, 32), (20, 67)) + line((21, 67), (29, 67)))])

    # START and the DOUT tap
    # The old START wire, kept only to copy its timing: DOUT left it at (30, 5).
    s0 = line((or_, oc - 1), (or_, 5)) + line((or_ - 1, 5), (23, 5))
    z0 = zones(len(s0), g, 1)
    t0 = sum(1 for a, b in zip([g] + z0, z0) if a != b)
    i0 = s0.index((30, 5))
    t_tap = sum(1 for a, b in zip([g] + z0[:i0 + 1], z0[:i0 + 1]) if a != b)

    # New START: south from the line output, DOUT tapped at (or_+4, oc-1) with the same
    # number of zone steps as before, then a serpentine below the delay line (east along
    # row or_+6, west along row or_+8) and north up column 5 into the TDC. The wire after
    # the tap gets EXTRA more zone steps, which delays START by EXTRA ps and only START.
    head = line((or_, oc - 1), (or_ + 4, oc - 1))
    tail = (line((or_ + 5, oc - 1), (or_ + 6, oc - 1)) + line((or_ + 6, oc), (or_ + 6, EAST))
            + line((or_ + 7, EAST), (or_ + 8, EAST)) + line((or_ + 8, EAST - 1), (or_ + 8, 5))
            + line((or_ + 7, 5), (23, 5)))
    zh = zones_t(len(head), g, t_tap)
    assert zh[-1] == z0[i0], (zh, z0[i0])
    zt = zones_t(len(tail), zh[-1], t0 - t_tap + EXTRA)
    assert zt[-1] == z0[-1] == 1, (zt[-1], z0[-1])
    assert max(len(list(g_)) for _, g_ in __import__("itertools").groupby(zt)) <= 5
    for p, q in zip(head + tail, zh + zt):
        L.add(p[0], p[1], q)
    tr, tc = head[-1]
    L.add(tr, tc + 1, zh[-1])
    L.add(tr, tc + 2, (zh[-1] + 1) % 4, "output", name="DOUT")
    print("START zone steps", t0, "->", t0 + EXTRA, "tail cells", len(tail))

    # REF: east input, fork to the delay line and north to the STOP gate
    L.add(fr, 78, 0, "input", name="REF")
    for c in (77, 76):
        L.add(fr, c, 0)
    for c in (75, 74, 73):
        L.add(fr, c, (a - 1) % 4)
    G = 0
    n = line((fr - 1, 76), (15, 76))
    for p, q in zip(n, zones(len(n), 0, (G - 2) % 4)):
        L.add(p[0], p[1], q)
    for r in (14, 13, 11):
        L.add(r, 76, (G - 1) % 4)
    L.add(10, 76, (G - 1) % 4, "input", name="EN")
    L.add(12, 76, G)
    L.add(12, 77, (G - 1) % 4)
    L.add(12, 78, (G - 1) % 4, "fixed", pol=-1)
    y = (G + 1) % 4
    via(L, 12, 75, y)
    w = line((12, 74), (12, 18))
    for p, q in zip(w, zones(len(w), y, 1)):
        L.add(p[0], p[1], q, layer=2)
    via(L, 12, 17, 2)

    # ENB: EN taken west, south, inverted on a diagonal, then a bus along row 26
    e = line((10, 75), (10, 73)) + line((11, 73), (23, 73))
    for p, q in zip(e, zones(len(e), (G - 1) % 4, 3)):
        L.add(p[0], p[1], q)
    L.add(24, 73, 0)
    L.add(25, 73, 0)
    bus = line((26, 72), (26, 19))
    bz = [1, 1] + zones(len(bus) - 2, 1, 2)
    zone_at = {}
    for p, q in zip(bus, bz):
        L.add(p[0], p[1], q)
        zone_at[p[1]] = q
    for C in COLS:
        c = C + 6
        via(L, 26, c, zone_at[c])
        tap = line((27, c), (32, c))
        for p, q in zip(tap, zones(len(tap), zone_at[c], z)):
            L.add(p[0], p[1], q, layer=2)
    print("cells", L.count(), "area_um2", round(L.area_um2(), 4))
    return L.write(path)


if __name__ == "__main__":
    build()

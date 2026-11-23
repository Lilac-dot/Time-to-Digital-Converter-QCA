#!/usr/bin/env python3
"""Building blocks for the coarse counter: a toggle bit with a systolic carry.

Each bit is the ADDLL's verified 2:1 MUX (addll_lib.mux) closed into a one-period loop:
    X' = S ? !X : X        (S = carry in, X = loop value)
The counted bit is b = !X, taken from the inverted branch that feeds I1, so
    carry_out = S . b      (b before the update)
is the same product the MUX's own upper AND gate forms. Carry reaches the next bit some
whole number of periods later; a ripple counter only needs every carry to arrive, not to
arrive in the same period, so the count is exact once the last carry has landed.

CLR replaces the fixed -1 of the MUX's lower AND gate. CLR = 1 with S = 0 forces X = 1,
so b = 0. Coordinates are grid (row, col), y down; zones as in addll_lib.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "addll"))
sys.path.insert(0, os.path.join(HERE, "..", "qca-layouts"))
from addll_lib import mux  # noqa: E402


def run(L, cells, zones):
    for p, z in zip(cells, zones):
        L.add(p[0], p[1], z)


def toggle_bit(L, R, C, z, k):
    """One counter bit around a MUX at (R, C) in zone z (gate zones as in addll_lib.mux).
    Returns dict with the S feed point (cell east of the S line, which must be driven in
    zone p = z-1 or earlier), the carry-out cell and its zone, and the X output cell."""
    p, y, g = (z - 1) % 4, (z + 1) % 4, (z + 2) % 4
    mux(L, R, C, z)
    # CLR input where the lower AND gate's fixed -1 was
    L.layers[0].pop((R - 5, C - 3), None)
    L.add(R - 5, C - 3, z, "input", name=f"CLR{k}")

    # loop: OUT (R, C-4) in zone g forks at (R, C-5)
    L.add(R, C - 5, g)
    # I0 branch: north to (R-3, C-5), which is the I0 cell (zone z)
    run(L, [(R - 1, C - 5), (R - 2, C - 5)], [p, p])
    # X probe off the I0 branch
    L.add(R - 2, C - 6, p, "output", name=f"X{k}")
    # I1 branch: south to row R+3 in zone g, then an inverting diagonal step into zone p
    # at (R+4, C-4) (a zone boundary, like the ADDLL's ENB inverter), east along row R+4
    # and a normal corner up column C into the MUX's I1 cells
    down = [(R + r, C - 5) for r in range(1, 4)]
    run(L, down, [g] * len(down))
    east = [(R + 4, c) for c in range(C - 4, C + 1)]
    run(L, east, [p] * len(east))
    run(L, [(R + 3, C)], [p])
    # (R+2, C) and (R+1, C) are the MUX's I1 cells (zone p), already placed by mux()

    # S line: from the east along row R-2 into the MUX's S cell (R-2, C)
    sl = [(R - 2, c) for c in range(C + 1, C + 6)]
    run(L, sl, [p] * len(sl))
    # carry gate at (R+4, C+5): N = S line down column C+5, W = b continuing east along
    # row R+4 past the corner at (R+4, C), S = fixed -1 through a buffer, out E
    down_s = [(r, C + 5) for r in range(R - 1, R + 4)]
    run(L, down_s, [p] * len(down_s))
    tap = [(R + 4, c) for c in range(C + 1, C + 5)]
    run(L, tap, [p] * len(tap))
    L.add(R + 4, C + 5, z)
    L.add(R + 5, C + 5, p)
    L.add(R + 6, C + 5, p, "fixed", pol=-1)
    return {"s_feed": (R - 2, C + 6), "s_zone": p,
            "carry": (R + 4, C + 6), "carry_zone": y, "x": (R - 2, C - 6)}


def line(a, b):
    dr, dc = (b[0] > a[0]) - (b[0] < a[0]), (b[1] > a[1]) - (b[1] < a[1])
    out = [a]
    while out[-1] != b:
        out.append((out[-1][0] + dr, out[-1][1] + dc))
    return out


def counter(L, R, C0, n, z=0, pitch=15):
    """n toggle bits, LSB west, each fed from the north by the previous bit's carry, which
    climbs column C+7 to row R-8 and runs east. Returns the LSB's S feed (driven from the
    east, zone p), the final carry cell and zone, and the bit list."""
    from addll_lib import zones
    bits = [toggle_bit(L, R, C0 + i * pitch, z, i) for i in range(n)]
    for i in range(n - 1):
        C, Cn = C0 + i * pitch, C0 + (i + 1) * pitch
        b = bits[i]
        path = [b["carry"]] + line((R + 4, C + 7), (R - 8, C + 7))[0:]
        path += line((R - 8, C + 8), (R - 8, Cn + 5)) + line((R - 7, Cn + 5), (R - 3, Cn + 5))
        zs = zones(len(path) - 1, b["carry_zone"], bits[i + 1]["s_zone"])
        L.add(*b["carry"], b["carry_zone"])
        run(L, path[1:], zs)
    return bits


def window(L, bit0, R, C):
    """EN = START . !STOP, fed into the LSB's S line from the north at (R-3, C+3).
    Gate at (R-10, C+3); START from the west, STOP from the north through an inverting
    diagonal on a zone boundary, fixed -1 above. Rows above R-8 are clear of carry routes."""
    from addll_lib import zones
    gr, gc = R - 10, C + 3
    p = bit0["s_zone"]
    # main branch down column C+3 into the S line; fork at (R-7, C+3) one zone before p
    # so the carry gate gets its own branch down column C+5 (a T inside zone p is weak)
    for q in [(R - 2, C + 4), (R - 2, C + 5)]:
        L.layers[0].pop(q, None)
    run(L, line((gr + 1, gc), (R - 7, gc)), [(p - 1) % 4] * 3)
    run(L, line((R - 6, gc), (R - 3, gc)), [p] * 4)
    run(L, [(R - 7, gc + 1), (R - 7, gc + 2), (R - 6, gc + 2), (R - 5, gc + 2)], [(p - 1) % 4] * 4)
    run(L, line((R - 4, gc + 2), (R - 2, gc + 2)), [p] * 3)
    L.add(gr, gc, 1)
    L.add(gr - 1, gc, 0)
    L.add(gr - 2, gc, 0, "fixed", pol=-1)
    run(L, [(gr, gc - 2), (gr, gc - 1)], [0, 0])
    L.add(gr, gc - 3, 0, "input", name="START")
    run(L, [(gr, gc + 1), (gr, gc + 2)], [0, 0])
    run(L, line((gr - 3, gc + 3), (gr - 1, gc + 3)), [3, 3, 3])   # (gr-1, gc+3) -> (gr, gc+2) inverts
    L.add(gr - 4, gc + 3, 3, "input", name="STOP")

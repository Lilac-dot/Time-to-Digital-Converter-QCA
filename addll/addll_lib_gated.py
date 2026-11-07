#!/usr/bin/env python3
"""Delay stage with its select gated: S = Q.ENB. While EN is on, ENB is low and the stage
bypasses, so a stale TDC code cannot affect the measuring edge."""
from addll_lib import mux, via, zones_t


def stage_gated(L, R, C, z):
    """Fork at (R-7, C+8). Q arrives on the crossover layer down column C+3 to a via at
    (R-5, C+3); ENB arrives down column C+6 to a via at (R-2, C+6). Returns fork, fork zone,
    Q via position and ENB via position; both vias are in zone z."""
    mux(L, R, C, z)
    a = (z - 2) % 4
    byp = [(R - 7, c) for c in range(C + 7, C - 6, -1)] + [(r, C - 5) for r in range(R - 6, R - 3)]
    for p, q in zip(byp, zones_t(len(byp), a, 1)):
        L.add(p[0], p[1], q)
    lng = [(r, C + 8) for r in range(R - 6, R + 4)] + [(R + 3, c) for c in range(C + 7, C - 1, -1)]
    for p, q in zip(lng, zones_t(len(lng), a, 4)):
        L.add(p[0], p[1], q)
    L.add(R - 7, C + 8, a)
    c1, c2 = (z + 1) % 4, (z + 2) % 4
    L.add(R - 2, C + 3, c1)                                 # gate centre
    for dr, dc in [(-3, 3), (-4, 3), (-1, 3), (-2, 4), (-2, 5)]:
        L.add(R + dr, C + dc, z)                            # two-cell inputs and fixed buffer
    L.add(R, C + 3, z, "fixed", pol=-1)
    L.add(R - 2, C + 2, c2)
    L.add(R - 2, C + 1, c2)
    via(L, R - 5, C + 3, z)
    via(L, R - 2, C + 6, z)
    return (R - 7, C + 8), a, (R - 5, C + 3), (R - 2, C + 6)


def delay_line_gated(L, R, cols, z=0):
    """Stages flowing west. Each next fork sits at C-9 of the stage east of it."""
    st = [stage_gated(L, R, C, z) for C in cols]
    g = (z + 2) % 4
    for C, s in zip(cols[1:], st[:-1]):
        (fr, fc), a = s[0], s[1]
        path = [(R, c) for c in range(C - 5, C - 8, -1)] + [(r, C - 7) for r in range(R - 1, R - 8, -1)]
        path += [(R - 7, c) for c in range(C - 8, fc, -1)]
        for p, q in zip(path, zones_t(len(path), g, 4)):
            L.add(p[0], p[1], q)
    return st, (R, cols[0] - 4), g

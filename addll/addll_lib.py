#!/usr/bin/env python3
"""Building blocks for the QCA ADDLL. Coordinates are grid (row, col); data in the delay
line flows west. See addll/README.md for the architecture."""
import math


def zones_t(n, start, t):
    """Zones for n cells after a cell in zone `start`, with exactly t zone transitions."""
    if t > n:
        raise ValueError(f"{n} cells cannot make {t} zone steps")
    return [(start + 1 + (i * t) // n) % 4 for i in range(n)]


def zones(n, start, end, group=5):
    """Zones for n cells after zone `start`, ending in zone `end`, with no more than
    `group` cells in one zone."""
    t = (end - start) % 4
    if t == 0:
        t = 4
    while math.ceil(n / t) > group:
        t += 4
    z = zones_t(n, start, t)
    z[-1] = end
    return z


def mux(L, R, C, z):
    """2:1 MUX, OUT = S.I1 + !S.I0, output west at (R, C-4) in zone z+2. The floor plan is
    the latch inside the paper's conventional TDC, whose gates have three real inputs.
    The zones differ: every gate here switches one zone after all of its inputs. The TDC's
    latch shares zones between a gate and its inputs, which only works for one-period
    pulses. With a held select the gates drive their own inputs backwards.
    I1 cell: (R+1, C), zone z-1, driven from the south.
    I0 cell: (R-3, C-5), zone z, driven from the north.
    S  cell: (R-2, C), zone z-1, driven from the east."""
    p, y, g = (z - 1) % 4, (z + 1) % 4, (z + 2) % 4
    # Cell polarization follows its neighbours almost instantly, so a gate input has to be
    # two cells in one zone: they keep each other held after the zone before them releases.
    for dr, dc in [(2, 0), (1, 0), (-1, 0), (-2, 0)]:
        L.add(R + dr, C + dc, p)
    for dr, dc in [(0, 0), (-3, -1), (-3, -2), (-3, -4), (-3, -5)]:
        L.add(R + dr, C + dc, z)
    L.add(R, C + 1, p)                      # buffers: a fixed cell touching a gate would
    L.add(R, C + 2, p, "fixed", pol=-1)     # pull the gate's other inputs through the diagonal
    for dr, dc in [(0, -1), (0, -2), (-3, -3), (-2, -3), (-1, -3)]:
        L.add(R + dr, C + dc, y)
    L.add(R - 4, C - 3, z)
    L.add(R - 5, C - 3, z, "fixed", pol=-1)
    for dr, dc in [(0, -3), (0, -4)]:
        L.add(R + dr, C + dc, g)
    L.add(R + 1, C - 3, y)
    L.add(R + 2, C - 3, y, "fixed", pol=1)


def stage(L, R, C, z):
    """One switchable delay stage. Data enters at the fork (R-7, C+4).
    S=0: bypass to I0. S=1: long path to I1, exactly 4 zone steps (one period) longer.
    The select arrives on the crossover layer, down column C+1, to a via at (R-2, C+1).
    Returns (fork position, fork zone, via position, via zone)."""
    mux(L, R, C, z)
    a = (z - 2) % 4
    byp = [(R - 7, c) for c in range(C + 3, C - 6, -1)] + [(r, C - 5) for r in range(R - 6, R - 3)]
    for p, q in zip(byp, zones_t(len(byp), a, 1)):
        L.add(p[0], p[1], q)
    lng = [(r, C + 4) for r in range(R - 6, R + 4)] + [(R + 3, c) for c in range(C + 3, -1 + C, -1)] 
    for p, q in zip(lng, zones_t(len(lng), a, 4)):
        L.add(p[0], p[1], q)
    L.add(R - 7, C + 4, a)
    v = (z - 2) % 4
    return (R - 7, C + 4), a, (R - 2, C + 1), v


def via(L, r, c, z):
    L.add(r, c, z)
    L.add(r, c, z, layer=1)
    L.add(r, c, z, layer=2)


def edges(t, y, th=0.5):
    """Exact threshold-crossing times of a pulsed QCA output, as (rise list, fall list)."""
    ri, fa = [], []
    st = None
    for a, b in zip(t, y):
        if st != 1 and b > th:
            if st is not None:
                ri.append(round(float(a), 1))
            st = 1
        elif st != -1 and b < -th:
            if st is not None:
                fa.append(round(float(a), 1))
            st = -1
    return ri, fa


def delay_line(L, R, cols, z=0):
    """Chain of stages flowing west; cols lists each stage's C from west to east. Each
    bypassed stage costs 8 zone steps (2 periods) and a selected stage 12 (3 periods).
    Returns (east fork, its zone, list of (via position, via zone), output cell, its zone),
    with vias in the same west-to-east order."""
    vias, forks = [], []
    for C in cols:
        f, a, v, vz = stage(L, R, C, z)
        via(L, v[0], v[1], vz)
        forks.append((f, a))
        vias.append((v, vz))
    g = (z + 2) % 4
    for C, nxt in zip(cols[1:], forks[:-1]):
        (fr, fc), a = nxt
        path = [(R, c) for c in range(C - 5, C - 8, -1)] + [(r, C - 7) for r in range(R - 1, R - 8, -1)]
        path += [(R - 7, c) for c in range(C - 8, fc, -1)]
        for p, q in zip(path, zones_t(len(path), g, 4)):
            L.add(p[0], p[1], q)
    return forks[-1][0], forks[-1][1], vias, (R, cols[0] - 4), g

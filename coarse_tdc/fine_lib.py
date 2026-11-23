#!/usr/bin/env python3
"""Asynchronous edge capture: a quarter-period (one clock zone) fine stage.

For an input X that steps 0 -> 1 at any time, sample it in the reference zone `ref` and
m quarters earlier (zone ref-m), in the same clock period. Then
    f_m = X_ref . !X_(ref-m)
is 1 only in the first period the reference sample sees the edge, and only if the edge
came within the last m quarters before that sample. A set-latch holds f_m:
    q' = M(q, f, CLRn)    CLRn = +1: q' = q OR f ;  CLRn = -1 (with f = 0): q' = 0
For m = 1, 2, 3 the held bits form a thermometer; their sum says how many quarters before
the reference sample the edge arrived.

Every sampler is its own input cell (X_R, X_E): one input pad fanned out to the
samplers. In the test benches these cells are driven together.
"""
from counter_lib import run


def set_latch(L, R, C, z, clr_name, q_name):
    """Majority set-latch with its gate at (R, C) in zone z. Data enters from the west
    ((R, C-1) must be zone z-1), CLRn from the south, loop over the top (one period),
    q probe north of the loop."""
    L.add(R, C, z)
    L.add(R + 1, C, (z - 1) % 4)
    L.add(R + 2, C, (z - 1) % 4, "input", name=clr_name)
    run(L, [(R, C + 1), (R, C + 2), (R - 1, C + 2)], [(z + 1) % 4] * 3)
    run(L, [(R - 2, C + 2), (R - 3, C + 2), (R - 3, C + 1)], [(z + 2) % 4] * 3)
    run(L, [(R - 3, C), (R - 2, C), (R - 1, C)], [(z + 3) % 4] * 3)
    L.add(R - 4, C + 1, (z + 2) % 4, "output", name=q_name)


def fine_bit(L, R, C, ref, m, x_name, clr_name, q_name, seg=2):
    """f_m gate at (R, C) in zone ref+1, latched at (R, C+3). The reference sample comes
    down from the north; the early sample runs along row R+1 from the west and steps up
    diagonally (inverting) into the gate's west input at a zone boundary."""
    a = (ref + 1) % 4
    L.add(R, C, a)
    L.add(R - 3, C, ref, "input", name=f"{x_name}_R{m}")
    run(L, [(R - 2, C), (R - 1, C)], [ref, ref])
    L.add(R + 1, C, ref)
    L.add(R + 2, C, ref, "fixed", pol=-1)
    run(L, [(R, C - 2), (R, C - 1)], [ref, ref])             # !X_early, zone ref
    cells, zones = [], []
    for s in range(m):                                          # s = 0 nearest the gate
        zz = (ref - 1 - s) % 4
        for c in range(C - 3 - seg * s, C - 3 - seg * (s + 1), -1):
            cells.append((R + 1, c))
            zones.append(zz)
    run(L, cells, zones)                                        # (R+1, C-3) -> (R, C-2) inverts
    L.add(R + 1, C - 3 - seg * m, (ref - m) % 4, "input", name=f"{x_name}_E{m}")
    run(L, [(R, C + 1), (R, C + 2)], [(a + 1) % 4] * 2)
    set_latch(L, R, C + 3, (a + 2) % 4, clr_name, q_name)


def fine_edge(L, R, C, ref, x_name, tag, pitch=8):
    """Three fine bits (m = 1, 2, 3) for one edge, stacked downwards."""
    for m in (1, 2, 3):
        fine_bit(L, R + (m - 1) * pitch, C, ref, m, x_name, f"CLRN_{tag}{m}", f"F{tag}{m}")


def async_tdc(L, nb, R=12, C=12):
    """Coarse counter + START/STOP window + fine stages. The window samples START in zone 0
    and STOP in zone 3, so those are the fine stages' reference zones.
    Result in quarter periods: Q = 4*count + sum(F_P) - sum(F_S) + constant."""
    from counter_lib import counter, window
    bits = counter(L, R, C, nb)
    window(L, bits[0], R, C)
    fine_edge(L, R - 8, C - 14, 0, "START", "S")
    fine_edge(L, R + 18, C - 14, 3, "STOP", "P")
    return bits


def async_inputs(nb):
    names = ["START", "STOP"] + [f"CLR{k}" for k in range(nb)]
    names += [f"START_{k}{m}" for m in (1, 2, 3) for k in "RE"]
    names += [f"STOP_{k}{m}" for m in (1, 2, 3) for k in "RE"]
    names += [f"CLRN_{t}{m}" for t in "SP" for m in (1, 2, 3)]
    return names

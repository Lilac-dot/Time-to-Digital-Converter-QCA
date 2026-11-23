#!/usr/bin/env python3
"""Self-re-arming coarse + fine TDC channel.

START and STOP are pulses (at least 2 clock periods wide). Each sets a one-gate latch
(S_L, P_L), so the counter window EN = S_L . !P_L is a held level.
P_L also feeds a delay line:
- after W_VALID periods it raises VALID: the count and fine bits are ready to read;
- after W_CLR periods it drives CLR, which clears the counter bits (active high, bus 1),
  every fine latch and S_L/P_L themselves (active low, bus 2 and two inverted taps).
Clearing P_L empties the delay line, so CLR drops W_CLR periods later and the channel is
armed again. RST (a pad) is OR'd into CLR for power-up.

Grid placement for a channel with its counter at (R0, C0); everything sits within
rows R0-28 .. bottom and columns C0-34 .. C0+48.
"""
from counter_lib import counter, line, run
from fine_lib import fine_edge
from addll_lib import zones

W_VALID, W_CLR = 5, 7


def zone_steps(n, start, steps):
    """n cells carrying `steps` zone increments, spread evenly (start cell = start)."""
    return [(start + (i * steps) // n) % 4 for i in range(n)]


def ramp(n, z_before, z_end, forced=(), group=4):
    """Zones for n cells following a cell in zone z_before and ending in z_end. Each cell
    is the same zone as the one before or one more; `forced` indices must step (an
    inverting diagonal must sit on a zone boundary); no run longer than `group`."""
    forced = set(forced)
    T = (z_end - z_before) % 4
    while T < len(forced) or (T and -(-n // T) > group) or (T == 0 and n > group):
        T += 4
    if T > n:
        raise ValueError(f"{n} cells cannot make {T} steps")
    steps = set(forced)
    free = [i for i in range(n) if i not in steps]
    need = T - len(steps)
    for j in range(need):
        steps.add(free[(j * len(free)) // need])
    out, z = [], z_before
    for i in range(n):
        if i in steps:
            z = (z + 1) % 4
        out.append(z)
    return out


def latch_down(L, R, C, clr_end):
    """Set-latch, gate at (R, C) in zone 1, data from the west (zone 0), CLRn from the
    north through a buffer, loop below. Corners (R, C+2) zone 2 and (R+3, C+2) zone 3."""
    L.add(R, C, 1)
    L.add(R - 1, C, 0)                                  # CLRn buffer
    L.add(*clr_end, 0)                                  # CLRn end cell (R-2, C): a driven
                                                        # gate input needs 2 cells in its zone
    run(L, [(R, C + 1), (R, C + 2), (R + 1, C + 2)], [2] * 3)
    run(L, [(R + 2, C + 2), (R + 3, C + 2), (R + 3, C + 1)], [3] * 3)
    run(L, [(R + 3, C), (R + 2, C), (R + 1, C)], [0] * 3)


def channel(L, R0, C0, nb, tag=""):
    t = tag
    bits = counter(L, R0, C0, nb, tag=tag)
    gr, gc = R0 - 10, C0 + 2

    # ---- window gate EN = S_L . !P_L into the LSB (as counter_lib.window) ----
    p = bits[0]["s_zone"]
    L.layers[0].pop((R0 - 2, C0 + 3), None)
    L.add(gr, gc, 1)
    run(L, line((gr + 1, gc), (R0 - 7, gc)), [(p - 1) % 4] * 3)
    run(L, line((R0 - 6, gc), (R0 - 3, gc)), [p] * 4)
    run(L, [(R0 - 7, gc + 1), (R0 - 7, gc + 2), (R0 - 6, gc + 2), (R0 - 5, gc + 2)], [(p - 1) % 4] * 4)
    run(L, [(R0 - 4, gc + 2), (R0 - 3, gc + 2)], [p] * 2)
    L.add(gr - 1, gc, 0)
    L.add(gr - 2, gc, 0, "fixed", pol=-1)
    run(L, [(gr, gc - 2), (gr, gc - 1)], [0, 0])                 # S_L arrives here
    run(L, [(gr, gc + 1), (gr, gc + 2)], [0, 0])                 # !P_L (diagonal below)

    # ---- S_L: START latch west of the window, tap east into (gr, gc-2) ----
    sc = gc - 8
    latch_down(L, gr, sc, (gr - 2, sc))
    run(L, [(gr, sc - 1), (gr, sc - 2)], [0, 0])
    L.add(gr, sc - 3, 0, "input", name=f"START{t}")
    run(L, [(gr, sc + 3), (gr, sc + 4), (gr, sc + 5)], [2, 3, 3])

    # ---- P_L: STOP latch north of the window, tap down column gc+3 ----
    pr, pc = gr - 9, gc + 1
    latch_down(L, pr, pc, (pr - 2, pc))
    run(L, [(pr, pc - 1), (pr, pc - 2)], [0, 0])
    L.add(pr, pc - 3, 0, "input", name=f"STOP{t}")
    run(L, line((pr + 4, pc + 2), (gr - 1, pc + 2)), [0, 1, 2, 3, 3])   # (gr-1, gc+3) -> (gr, gc+2) inverts

    # ---- delay line from P_L's corner: east, up column pc+9, hairpin west and back over
    # the CLR line, down into the OR gate (with RST) at (rc, pc+4). VALID taps it. ----
    rc = pr - 7
    up = pc + 9
    xw = pc - 8                                                  # hairpin west end
    path = line((pr, pc + 3), (pr, up)) + line((pr - 1, up), (rc - 6, up))
    path += line((rc - 6, up - 1), (rc - 6, xw)) + line((rc - 5, xw), (rc - 4, xw))
    path += line((rc - 3, xw), (rc - 3, pc + 4)) + line((rc - 2, pc + 4), (rc - 1, pc + 4))
    zs = zone_steps(len(path) - 1, 2, 4 * W_CLR)
    zs.append(zs[-1])                                            # 2 cells feed the gate
    run(L, path, zs)
    iv = (len(path) * W_VALID) // W_CLR
    vr, vc = path[iv]
    taken = set(L.layers[0]) | set(path)
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        q = (vr + dr, vc + dc)
        near = [(q[0] + a, q[1] + b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)]
        if q not in taken and all(n == (vr, vc) or n not in taken for n in near if abs(n[0] - q[0]) + abs(n[1] - q[1]) == 1):
            break
    L.add(*q, (zs[iv] + 1) % 4, "output", name=f"VALID{t}")
    g = (rc, pc + 4)                                             # OR gate, delay enters from N
    gz = (zs[-1] + 1) % 4
    L.add(*g, gz)
    L.add(g[0] + 1, g[1], zs[-1])                                # RST from the south
    L.add(g[0] + 2, g[1], zs[-1], "input", name=f"RST{t}")
    L.add(g[0], g[1] + 1, zs[-1])                                # +1 from the east
    L.add(g[0], g[1] + 2, zs[-1], "fixed", pol=1)

    # ---- CLR line west along row g[0]; taps for P_L, S_L (inverted), bus 1, bus 2 ----
    b1, b2 = C0 - 12, C0 - 15
    cl = line((rc, g[1] - 1), (rc, b2 + 1))
    i_p, i_s = cl.index((rc, pc + 1)), cl.index((rc, sc + 1))   # tap junctions: zone 1
    czs = ramp(i_p + 1, gz, 1) + ramp(i_s - i_p, 1, 1) + ramp(len(cl) - i_s - 1, 1, 0)
    run(L, cl, czs)
    L.add(rc - 1, cl[3][1], czs[3], "output", name=f"CLR{t}")
    zc = dict(zip(cl, czs))

    def inv_tap(col, end):
        """From the CLR line at (rc, col+1) down column col+1, diagonal (inverting) into
        column col, down to just above the CLRn end cell `end` (zone 0)."""
        path = line((rc + 1, col + 1), (rc + 2, col + 1)) + line((rc + 3, col), (end[0] - 1, col))
        run(L, path, ramp(len(path), zc[(rc, col + 1)], 3, forced=[2]))

    inv_tap(pc, (pr - 2, pc))
    inv_tap(sc, (gr - 2, sc))

    # bus 1 (active high) down column b1, stubs east to each bit's CLR cell (R-5, C-3)
    bus1_top = zc[(rc, b1)]
    bus1 = line((rc + 1, b1), (R0 + 12 * (nb - 1) - 5, b1))
    zb1 = ramp(len(bus1), bus1_top, 0)
    run(L, bus1, zb1)
    z1 = dict(zip(bus1, zb1))
    for k in range(nb):
        R, C = R0 + 12 * k, C0 + 2 * k
        L.layers[0].pop((R - 5, C - 3), None)                    # was input CLRk
        stub = line((R - 5, b1 + 1), (R - 5, C - 3))
        run(L, stub, ramp(len(stub), z1[(R - 5, b1)], 0))   # end cell in the buffer's zone

    # bus 2 (active low): diagonal off the line's west end, down column b2
    z2s = zc[(rc, b2 + 1)]
    drop = [(rc + 1, b2 + 1), (rc + 2, b2 + 1)]
    bus2 = line((rc + 3, b2), (R0 + 18 + 16 + 2, b2))
    zb2 = ramp(len(drop) + len(bus2), z2s, 0, forced=[2])  # diagonal on a zone boundary
    run(L, drop + bus2, zb2)
    z2 = dict(zip(drop + bus2, zb2))

    # ---- fine stages (reference zone 0 for both: S_L and P_L sample in zone 0) ----
    cf = C0 - 24
    for rr, x, tg in ((R0 - 8, f"START{t}", f"S{t}"), (R0 + 18, f"STOP{t}", f"P{t}")):
        fine_edge(L, rr, cf, 0, x, tg)
        for m in range(3):
            R = rr + 8 * m
            lc = cf + 3                                           # latch gate column
            L.layers[0].pop((R + 2, lc), None)                    # was input CLRN
            stub = line((R + 2, b2 - 1), (R + 2, lc))
            run(L, stub, ramp(len(stub), z2[(R + 2, b2)], 2))   # end cell in the buffer's zone
    return bits


def channel_inputs(nb, tag=""):
    t = tag
    names = [f"START{t}", f"STOP{t}", f"RST{t}"]
    names += [f"START{t}_{k}{m}" for m in (1, 2, 3) for k in "RE"]
    names += [f"STOP{t}_{k}{m}" for m in (1, 2, 3) for k in "RE"]
    return names

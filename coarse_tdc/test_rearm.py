#!/usr/bin/env python3
"""Self-re-arming channel: RST once, then a train of events with no external clear.
Each event: START pulse at quarter s of a period, STOP pulse D quarters later (pulses
PULSE quarters wide). The test reads the count and fine bits when VALID rises, checks
Q - D is the same for every event, and reports the dead time (STOP to the end of CLR).
Inputs change every quarter period (Gaussian-clock energy engine, per_vector = 0.25)."""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "simulation"))
from rearm_lib import channel, channel_inputs  # noqa: E402
from qca_ml import ML  # noqa: E402
from qde_tools import run_qde  # noqa: E402
from test_fine import peak  # noqa: E402

NB = int(os.environ.get("NB", 4))
PULSE = int(os.environ.get("PULSE", 8))          # quarters
GAP = int(os.environ.get("GAP", 100))            # quarters from STOP to the next START


def build(path, nb=NB, tags=("",)):
    L = ML()
    for i, t in enumerate(tags):
        channel(L, 40, 40 + i * 50, nb, t)
    L.write(path)
    return L


def stimulus(events, tags=("",), rst=48, tail=100):
    """events: list of (s, D) per tag, i.e. events[tag_index] = [(s, D), ...] aligned in
    time across channels (same START times, per-channel STOP offsets)."""
    names = sum((channel_inputs(NB, t) for t in tags), [])
    n_ev = len(events[0])
    rows, marks = [], []
    t0 = rst + int(os.environ.get("POST_RST", 64))   # clear must finish reaching every latch
    starts = []
    for e in range(n_ev):
        base = t0 + 4 * (e and 0)
        starts.append(t0)
        D_max = max(ev[e][0] + ev[e][1] for ev in events)
        t0 += ((D_max + PULSE + GAP) // 4 + 1) * 4
    total = t0 + tail
    val = {n: np.zeros(total, int) for n in names}
    for t in tags:
        val[f"RST{t}"][:rst] = 1
    for ci, t in enumerate(tags):
        for e, (s, D) in enumerate(events[ci]):
            a = starts[e] + s
            b = a + D
            for x, at in ((f"START{t}", a), (f"STOP{t}", b)):
                val[x][at:at + PULSE] = 1
                for m in (1, 2, 3):
                    for k in "RE":
                        val[f"{x}_{k}{m}"][at:at + PULSE] = 1
            marks.append((ci, e, s, D, b))
    rows = [[int(val[n][i]) for n in names] for i in range(total)]
    return names, rows, marks


def analyse(c, marks, tags=("",)):
    t, res = c["t_ps"], []
    for ci, e, s, D, b in marks:
        tg = tags[ci]
        # VALID is a clocked output: call it risen at the first period after STOP whose
        # full-period peak is high, followed by another such period; read one period later
        k0 = int(b // 4) + 1
        kmax = int(t[-1] // 4) - 2
        k = next((k for k in range(k0, kmax) if peak(c, f"VALID{tg}", 4 * k + 3) > 0.5
                  and peak(c, f"VALID{tg}", 4 * k + 7) > 0.5), None)
        if k is None:
            res.append((ci, e, s, D, None, "VALID never rose"))
            continue
        i = 4 * k + 7 + 4
        X = [peak(c, f"X{k}{tg}", i) for k in range(NB)]
        cnt = sum((x < 0) << k for k, x in enumerate(X))
        fs = [peak(c, f"FS{tg}{m}", i) > 0 for m in (1, 2, 3)]
        fp = [peak(c, f"FP{tg}{m}", i) > 0 for m in (1, 2, 3)]
        Q = 4 * cnt + sum(fp) - sum(fs)
        clr = c[f"CLR{tg}"]
        hi = np.where((t >= b) & (clr > 0.5))[0]
        dead = None
        if len(hi):
            lo = np.where((t > t[hi[0]]) & (clr < -0.5))[0]
            # CLR is clocked: take the last high sample before it stays low for a period
            j = hi[0]
            while j < len(t) and not np.all(clr[j:j + 400] < 0.5):
                j += 1
            dead = round(float(t[min(j, len(t) - 1)] - b), 1)
        res.append((ci, e, s, D, Q, f"count={cnt} F_S={''.join(str(int(x)) for x in fs)} "
                    f"F_P={''.join(str(int(x)) for x in fp)} valid@{4 * k}ps (STOP@{b}ps) dead={dead}ps"))
    return res


def main():
    ev = [tuple(map(int, a.split(","))) for a in sys.argv[1:]] or [(1, 9), (3, 22), (0, 41)]
    q = os.path.join(HERE, os.environ.get("QCA", f"rearm_tdc{NB}.qca"))
    L = build(q)
    print("cells", L.count(), "area_um2", round(L.area_um2(), 4))
    names, rows, marks = stimulus([ev])
    kw = dict(per_vector=0.25, radius_of_effect=float(os.environ.get("RADIUS", 80)))
    c, e, _ = run_qde(q, names, rows, **kw)
    if os.environ.get("SAVE"):
        import numpy as _np
        _np.savez_compressed(os.environ["SAVE"], **{k: _np.asarray(v, dtype=_np.float32) for k, v in c.items()})
    if e.get("avg_reported_eV"):
        print(f"energy {e['avg_reported_eV']*1e3:.2f} meV/cycle (error +/- {abs(e['avg_error_reported_eV'])*1e3:.2f})")
    for ci, en, s, D, Q, info in analyse(c, marks):
        print(f"event {en}: s={s} D={D:2d} Q={Q} Q-D={None if Q is None else Q - D}  {info}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""One edge's fine stage on its own. Inputs change every quarter period (Gaussian-clock
energy engine, per_vector = 0.25). For each offset s = 0..3 quarters: clear, step X up at
quarter s of a period, hold, read the three latched bits."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "simulation"))
from fine_lib import fine_edge  # noqa: E402
from qca_ml import ML  # noqa: E402
from qde_tools import run_qde  # noqa: E402

REF = int(os.environ.get("REF", 0))


def peak(c, name, i, qp=1.0):
    """Largest-magnitude value over the full period (4 quarters) ending at quarter i."""
    t, v = c["t_ps"], c[name]
    seg = v[(t >= (i - 3) * qp) & (t < (i + 1) * qp)]
    return float(seg[abs(seg).argmax()])


def main():
    L = ML()
    fine_edge(L, 10, 14, REF, "X", "S")
    q = os.path.join(HERE, "fine_edge.qca")
    L.write(q)
    print("cells", L.count())
    names = [f"X_{k}{m}" for m in (1, 2, 3) for k in "RE"] + [f"CLRN_S{m}" for m in (1, 2, 3)]
    x, clr, reads = [], [], []
    for s in range(4):
        x += [0] * 24; clr += [0] * 16 + [1] * 8          # 6 periods: 4 clear, 2 idle
        x += [0] * s + [1] * (40 - s); clr += [1] * 40    # edge at quarter s, hold 10 periods
        reads.append(len(x) - 2)
    rows = [[xx] * 6 + [cc] * 3 for xx, cc in zip(x, clr)]
    c, e, _ = run_qde(q, names, rows, per_vector=0.25, radius_of_effect=float(os.environ.get("RADIUS", 80)))
    for s, i in zip(range(4), reads):
        bits = [peak(c, f"FS{m}", i) for m in (1, 2, 3)]
        print(f"edge at quarter {s}: F1..F3 = {[round(b, 2) for b in bits]} "
              f"-> {sum(b > 0 for b in bits)}")


if __name__ == "__main__":
    main()

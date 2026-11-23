#!/usr/bin/env python3
"""One counter bit: clear, then count EN periods. Prints X (b = !X) and carry per period."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "simulation"))
from counter_lib import toggle_bit  # noqa: E402
from qca_ml import ML  # noqa: E402
from qde_tools import run_qde  # noqa: E402


def build(path):
    L = ML()
    R, C, z = 10, 12, 0
    io = toggle_bit(L, R, C, z, 0)
    L.add(*io["s_feed"], io["s_zone"], "input", name="EN")
    L.add(*io["carry"], io["carry_zone"], "output", name="CY")
    print("cells", L.count())
    return L.write(path)


def per_period(c, name, n):
    t, v = c["t_ps"], c[name]
    out = []
    for i in range(n):
        m = (t >= 4 * i) & (t < 4 * i + 4)
        seg = v[m]
        out.append(round(float(seg[abs(seg).argmax()]), 2))
    return out


if __name__ == "__main__":
    q = build(os.path.join(HERE, "bit.qca"))
    en = [0] * 8 + [0] * 4 + [1] * 5 + [0] * 6 + [1] * 3 + [0] * 8
    clr = [1] * 8 + [0] * (len(en) - 8)
    rows = list(zip(en, clr))
    kw = dict(engine="cv", radius_of_effect=float(sys.argv[1]) if len(sys.argv) > 1 else 65)
    c, _, _ = run_qde(q, ["EN", "CLR0"], rows, **kw)
    n = len(rows)
    print("EN ", en)
    for k in ("X0", "CY"):
        print(k, per_period(c, k, n))

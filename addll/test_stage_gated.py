#!/usr/bin/env python3
"""Gated stage: one period extra only when Q=1 and ENB=1."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "simulation"))
from addll_lib import edges, zones
from addll_lib_gated import stage_gated
from qca_ml import ML
from qde_tools import run_qde
L = ML(); R, C, z = 36, 8, 0
f, a, qv, ev = stage_gated(L, R, C, z)
L.add(f[0], f[1] + 1, (a - 1) % 4); L.add(f[0], f[1] + 2, (a - 1) % 4, "input", name="D")
g = (z + 2) % 4
L.add(R, C - 5, g); L.add(R, C - 6, (g + 1) % 4, "output", name="X")
for name, v in (("Q", qv), ("ENB", ev)):
    top = f[0] - 3
    L.add(top, v[1], (z - 3) % 4, "input", name=name, layer=2)
    path = [(r, v[1]) for r in range(top + 1, v[0])]
    for q, w in zip(path, zones(len(path), (z - 3) % 4, z)):
        L.add(q[0], q[1], w, layer=2)
print("cells", L.count()); L.write("stage_gated.qca")
pat = [0]*8+[1]*6+[0]*6
rows = []; starts = {}
for q, e in [(0,0),(1,0),(0,1),(1,1)]:
    rows += [(0,q,e)]*8; starts[(q,e)] = len(rows); rows += [(d,q,e) for d in pat]
for name, kw in [("classic", {"engine":"cv","radius_of_effect":65}), ("Gaussian", {})]:
    c,_,_ = run_qde("stage_gated.qca", ["D","Q","ENB"], rows, **kw)
    ri, fa = edges(c["t_ps"], c["X"])
    print(name, {k: [round(x-v*4,1) for x in ri if v*4 < x < (v+18)*4][:1] for k, v in starts.items()}, "peak", round(float(abs(c["X"][300:]).max()),3))

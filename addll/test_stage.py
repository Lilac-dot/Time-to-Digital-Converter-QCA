#!/usr/bin/env python3
"""One delay stage: output follows the data, exactly one period (4 ps) later when S=1."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "simulation"))
from addll_lib import edges, stage, via, zones
from qca_ml import ML
from qde_tools import run_qde

def build(p):
    L = ML(); R, C, z = 36, 8, 0
    fork, a, v, vz = stage(L, R, C, z)
    L.add(fork[0], fork[1] + 2, (a - 1) % 4, "input", name="D")
    L.add(fork[0], fork[1] + 1, (a - 1) % 4)
    g = (z + 2) % 4
    L.add(R, C - 5, g); L.add(R, C - 6, (g + 1) % 4, "output", name="Q")
    via(L, v[0], v[1], vz)
    path = [(r, v[1]) for r in range(fork[0] - 2, v[0])]
    start = (vz - 3) % 4
    L.add(fork[0] - 3, v[1], start, "input", name="S", layer=2)
    for q, w in zip(path, zones(len(path), start, vz)): L.add(q[0], q[1], w, layer=2)
    print("cells", L.count(), "area", round(L.area_um2(), 4))
    return L.write(p)

p = build(sys.argv[1] if len(sys.argv) > 1 else "stage.qca")
pat = [0]*6+[1]*6+[0]*6+[1]*6+[0]*6
rows = [(d, 0) for d in pat] + [(0,1)]*6 + [(d, 1) for d in pat]
T0 = 36 * 4.0
for kw in [{}, {"radius_of_effect":65}, {"engine":"cv","radius_of_effect":65}, {"engine":"cv","radius_of_effect":80}]:
    c,e,_ = run_qde(p, ["D","S"], rows, **kw)
    r, f = edges(c["t_ps"], c["Q"])
    r0=[x for x in r if x<T0-8]; r1=[round(x-T0,1) for x in r if x>T0]
    f0=[x for x in f if x<T0-8]; f1=[round(x-T0,1) for x in f if x>T0]
    print(kw,"\n  S=0 rise",r0,"fall",f0,"\n  S=1 rise",r1,"fall",f1,"| peak",round(float(abs(c["Q"][300:]).max()),3))

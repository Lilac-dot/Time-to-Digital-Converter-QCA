#!/usr/bin/env python3
"""Four stages in a chain: each selected stage must add exactly one period (4 ps)."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "simulation"))
from addll_lib import delay_line, edges, zones
from qca_ml import ML
from qde_tools import run_qde

R = 36; COLS = [10, 23, 36, 49]

def build(p):
    L = ML()
    (fr, fc), a, vias, (or_, oc), g = delay_line(L, R, COLS)
    L.add(fr, fc + 1, (a - 1) % 4); L.add(fr, fc + 2, (a - 1) % 4, "input", name="D")
    L.add(or_, oc - 1, g); L.add(or_, oc - 2, (g + 1) % 4, "output", name="Q")
    for i, (v, vz) in enumerate(vias):
        top = fr - 3
        start = (vz - 3) % 4
        L.add(top, v[1], start, "input", name=f"S{i}", layer=2)
        path = [(r, v[1]) for r in range(top + 1, v[0])]
        for q, w in zip(path, zones(len(path), start, vz)):
            L.add(q[0], q[1], w, layer=2)
    print("cells", L.count(), "area", round(L.area_um2(), 4), flush=True)
    return L.write(p)

p = build(sys.argv[1] if len(sys.argv) > 1 else "delay_line.qca")
SEG = 44
rows = []
for k in range(5):
    s = [1 if i < k else 0 for i in range(4)]
    rows += [(0, *s)] * 20 + [(1, *s)] * 16 + [(0, *s)] * 8
res = {}
for name, kw in [("Gaussian r=80", {}), ("Gaussian r=65", {"radius_of_effect": 65}), ("classic r=65", {"engine": "cv", "radius_of_effect": 65}), ("classic r=80", {"engine": "cv", "radius_of_effect": 80})]:
    c, e, _ = run_qde(p, ["D", "S0", "S1", "S2", "S3"], rows, **kw)
    ri, fa = edges(c["t_ps"], c["Q"])
    d = []
    for k in range(5):
        t0 = (k * SEG + 20) * 4.0
        cand = [x for x in ri if t0 < x < t0 + 24 * 4]
        d.append(round(cand[0] - t0, 1) if cand else None)
    steps = [round(b - a, 1) if a is not None and b is not None else None for a, b in zip(d, d[1:])]
    res[name] = {"delay_ps": d, "steps_ps": steps, "ok": steps == [4.0] * 4 or all(s is not None and abs(s - 4) < 0.3 for s in steps), "E_bath_meV": None if e.get("avg_reported_eV") is None else round(e["avg_reported_eV"] * 1e3, 3)}
    print(name, res[name], flush=True)
json.dump(res, open("delay_line_result.json", "w"), indent=1)

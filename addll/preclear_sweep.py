#!/usr/bin/env python3
"""Clean-clear protocol: clear pulse, flush, then measure. Period sweep and one recalibration
sequence, classic engine at 65 nm and Gaussian clock at 80 nm."""
import json
from concurrent.futures import ThreadPoolExecutor
from verify_addll_lib import SET, code_at, lats, run_qde, stim
from trace_lib import preclear
def run(name, Ts):
    rows, marks = [], []
    for T in Ts:
        rows += preclear()
        r, rises = stim(T)
        base = len(rows); rows += r
        marks.append((T, len(rows) - 3, [base + x for x in rises[3:]]))
    c, _, _ = run_qde("addll.qca", ["REF", "EN"], rows, **SET[name])
    o = {"setting": name, "steps": [{"T": T, "code": code_at(c, len(rows), i), "lat_ps": lats(c, rs)} for T, i, rs in marks]}
    print(json.dumps(o), flush=True); return o
jobs = [("classic r=65", (T,)) for T in range(5, 10)] + [("classic r=65", (6, 8, 5, 7)), ("Gaussian r=80", (6,)), ("Gaussian r=80", (8,))]
with ThreadPoolExecutor(8) as ex:
    res = list(ex.map(lambda j: run(*j), jobs))
json.dump(res, open("preclear_sweep.json", "w"), indent=1)

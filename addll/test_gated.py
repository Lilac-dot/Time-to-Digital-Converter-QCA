#!/usr/bin/env python3
"""Gated ADDLL: no clear pulse and no flush. Sweep periods, then recalibrate up and down."""
import json, sys
from concurrent.futures import ThreadPoolExecutor
from build_addll_gated import build
from verify_addll_lib import SET, code_at, lats, run_qde, stim
Q = "addll_gated.qca"
def seq(Ts):
    rows, marks = [], []
    for T in Ts:
        rows += [(0, 0)] * 14
        r, rises = stim(T)
        base = len(rows); rows += r
        marks.append((T, len(rows) - 3, [base + x for x in rises[3:]]))
    return rows, marks
def run(j):
    name, Ts = j
    rows, marks = seq(Ts)
    c, e, _ = run_qde(Q, ["REF", "EN"], rows, **SET[name])
    o = {"setting": name, "steps": [{"T": T, "code": code_at(c, len(rows), i), "lat_ps": lats(c, rs)} for T, i, rs in marks]}
    print(json.dumps(o), flush=True); return o
build(Q)
Ts = [int(x) for x in sys.argv[1].split(",")]
with ThreadPoolExecutor(8) as ex:
    res = list(ex.map(run, [("classic r=65", (T,)) for T in Ts]))
json.dump(res, open("gated_sweep.json", "w"), indent=1)

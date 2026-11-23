#!/usr/bin/env python3
"""Recalibration with EN raised only after REF has been low long enough to clear the STOP
path. Without this guard EN rises while the delayed REF is still high at the STOP gate."""
import json, sys
from verify_addll_lib import SET, code_at, lats, run_qde, stim
GUARD = 14
name = sys.argv[1]
rows, marks = [], []
for T in (7, 10, 6, 9):
    r, rises = stim(T)
    base = len(rows) + GUARD
    rows += [(0, 0)] * GUARD + r
    marks.append((T, len(rows) - 3, [base + x for x in rises[3:]]))
c, e, _ = run_qde("addll.qca", ["REF", "EN"], rows, **SET[name])
res = {"setting": name, "steps": [{"T": T, "code": code_at(c, len(rows), i), "lat_ps": lats(c, rs)} for T, i, rs in marks]}
print(res, flush=True)
json.dump(res, open(f"recal_guarded_{name.split()[0]}.json", "w"), indent=1)

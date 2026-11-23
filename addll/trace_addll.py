#!/usr/bin/env python3
"""Trace the TDC code period by period, to see when calibration goes wrong."""
import json, sys
from concurrent.futures import ThreadPoolExecutor
from verify_addll_lib import SET, code_at, lats, run_qde, stim
from qca_tools import peak_per_period

KW = SET["classic r=65"]

def preclear(flush=16):
    """REF pulse with EN on while the line is low clears the code, then REF stays low until
    the delay line has flushed, so the measuring edge runs through the bypass paths."""
    return [(0, 0)] * 14 + [(0, 1)] * 6 + [(1, 1)] * 4 + [(0, 1)] * flush

def run(name, rows, marks=None):
    c, _, _ = run_qde("addll.qca", ["REF", "EN"], rows, **KW)
    p = [peak_per_period(c["t_ps"], c[f"OUT{k}"], n=len(rows)) for k in range(4)]
    codes = ["".join("1" if q[i] > 0 else "0" for q in p) for i in range(len(rows))]
    changes = [(i, codes[i]) for i in range(1, len(codes)) if codes[i] != codes[i - 1]]
    out = {"name": name, "n": len(rows), "code_changes": changes}
    if marks:
        out["steps"] = [{"T": T, "code": codes[i], "lat_ps": lats(c, rs)} for T, i, rs in marks]
    print(json.dumps(out), flush=True)
    return out

def seq(Ts, pre):
    rows, marks = [], []
    for T in Ts:
        if pre:
            rows += preclear()
        else:
            rows += [(0, 0)] * 14
        r, rises = stim(T)
        base = len(rows)
        rows += r
        marks.append((T, len(rows) - 3, [base + x for x in rises[3:]]))
    return rows, marks

jobs = []
r, _ = stim(7); jobs.append(("fresh T=7", r, None))
jobs.append(("guarded T=7", *seq((7,), False)))
jobs.append(("guarded T=7,10", *seq((7, 10), False)))
jobs.append(("preclear T=7", *seq((7,), True)))
jobs.append(("preclear T=7,10", *seq((7, 10), True)))
jobs.append(("preclear T=7,10,6,9", *seq((7, 10, 6, 9), True)))
with ThreadPoolExecutor(6) as ex:
    res = list(ex.map(lambda j: run(*j), jobs))
json.dump(res, open("trace.json", "w"), indent=1)

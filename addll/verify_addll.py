#!/usr/bin/env python3
"""Verify the ADDLL: lock over the REF period range in each engine setting, recalibration
to a new period up and down in the same run, and whole-circuit energy."""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "simulation"))
from addll_lib import edges
from qca_tools import peak_per_period
from qde_tools import run_qde
from test_addll import IDLE, W, stim

SET = {"classic r=65": {"engine": "cv", "radius_of_effect": 65}, "classic r=80": {"engine": "cv", "radius_of_effect": 80},
       "Gaussian r=80": {}, "Gaussian r=65": {"radius_of_effect": 65}}

def lats(c, rises):
    ri, _ = edges(c["t_ps"], c["DOUT"])
    out = []
    for x in rises:
        t = x * 4.0; cand = [a for a in ri if a > t - 0.5]
        out.append(round(cand[0] - t, 1) if cand else None)
    return out

def code_at(c, n, i):
    return "".join("1" if peak_per_period(c["t_ps"], c[f"OUT{k}"], n=n)[i] > 0 else "0" for k in range(4))

def lock(name, T):
    rows, rises = stim(T)
    c, e, _ = run_qde("addll.qca", ["REF", "EN"], rows, **SET[name])
    return {"setting": name, "T": T, "code": code_at(c, len(rows), -3), "lat_ps": lats(c, rises[3:]),
            "E_bath_meV": round(e["avg_reported_eV"] * 1e3, 2) if e.get("avg_reported_eV") else None,
            "E_err_meV": round(abs(e["avg_error_reported_eV"]) * 1e3, 2) if e.get("avg_error_reported_eV") else None}

def recal(name, Ts=(7, 10, 6, 9)):
    rows, marks = [], []
    for T in Ts:
        r, rises = stim(T)
        base = len(rows)
        rows += r
        marks.append((T, len(rows) - 3, [base + x for x in rises[3:]]))
    c, e, _ = run_qde("addll.qca", ["REF", "EN"], rows, **SET[name])
    return {"setting": name, "steps": [{"T": T, "code": code_at(c, len(rows), i), "lat_ps": lats(c, rs)} for T, i, rs in marks]}

jobs = [(lock, n, T) for n in SET for T in range(6, 11)] + [(recal, "classic r=65", None), (recal, "Gaussian r=80", None)]
def go(j):
    f, n, T = j
    r = f(n, T) if T else f(n)
    print(r, flush=True)
    return r
with ThreadPoolExecutor(os.cpu_count()) as ex:
    res = list(ex.map(go, jobs))
json.dump(res, open("addll_verify.json", "w"), indent=1)

#!/usr/bin/env python3
"""Full check of the compensated ADDLL: period sweep in four engine settings and recalibration in
one run, with no clear pulse or flush. Expected: k = T - 9 and DOUT phase 0 (one REF period)."""
import json
from concurrent.futures import ThreadPoolExecutor
from verify_addll_lib import code_at, lats, run_qde
Q = "addll_comp.qca"
W, RUNS = 2, 7
SET = {"classic r=65": {"engine": "cv", "radius_of_effect": 65}, "classic r=80": {"engine": "cv", "radius_of_effect": 80},
       "Gaussian r=80": {}, "Gaussian r=65": {"radius_of_effect": 65}}

def stim(T):
    """EN on, REF low; a rise; a second rise T later is the STOP that measures; EN drops 3
    periods after it; then free-running REF of period T."""
    n = 14 + 20 + 2 * T + (RUNS + 1) * T + 10
    ref = [0] * n
    t0 = 34
    rises = [t0 + k * T for k in range(RUNS + 2)]
    for r in rises:
        for i in range(r, r + T - W):
            ref[i] = 1
    en = [1 if 14 <= i < rises[1] + 3 else 0 for i in range(n)]
    return list(zip(ref, en)), rises

def seq(Ts):
    rows, marks = [], []
    for T in Ts:
        r, rises = stim(T)
        base = len(rows); rows += r
        marks.append((T, len(rows) - 3, [base + x for x in rises]))
    return rows, marks

def phase(lat, T):
    return None if lat is None else round(lat % (T * 4.0), 1)

def run(j):
    name, Ts = j
    rows, marks = seq(Ts)
    c, e, _ = run_qde(Q, ["REF", "EN"], rows, **SET[name])
    steps = []
    for T, i, rs in marks:
        code = code_at(c, len(rows), i)
        steps.append({"T": T, "code": code, "k": code.count("1"), "phase_mod_T_ps": [phase(x, T) for x in lats(c, rs[-5:])]})
    o = {"setting": name, "steps": steps}
    if e.get("avg_reported_eV"):
        o["E_bath_meV"] = round(e["avg_reported_eV"] * 1e3, 2); o["E_err_meV"] = round(abs(e["avg_error_reported_eV"]) * 1e3, 2)
    print(json.dumps(o), flush=True)
    return o

if __name__ == "__main__":
    jobs = [("classic r=65", (T,)) for T in (8, 9, 10, 11, 12, 13, 14)] + [("classic r=65", (12, 13, 11, 10, 13))]
    jobs += [("classic r=80", (T,)) for T in (9, 10, 11, 12, 13)] + [("Gaussian r=80", (T,)) for T in (9, 10, 11, 12, 13)]
    jobs += [("Gaussian r=65", (T,)) for T in (9, 13)] + [("Gaussian r=80", (12, 13, 11, 10, 13))]
    with ThreadPoolExecutor(9) as ex:
        res = list(ex.map(run, jobs))
    json.dump(res, open("comp_verify.json", "w"), indent=1)

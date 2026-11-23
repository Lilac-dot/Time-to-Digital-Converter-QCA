#!/usr/bin/env python3
"""Sweep the REF period: one calibration, then free running with EN=0. The TDC code must
step with the period and DOUT must keep a fixed phase to the next REF edge."""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "simulation"))
from addll_lib import edges
from build_addll import build
from qca_tools import peak_per_period
from qde_tools import run_qde

W, IDLE, RUNS = 2, 20, 4

def stim(T):
    """Returns rows of (REF, EN) and the REF rise times in periods."""
    rows = [(0, 1)] * IDLE
    t0 = len(rows)
    rows += [(1, 1)] * (T - W) + [(0, 1)] * W            # first rise clears the TDC
    rows += [(1, 1)] * 3                                 # second rise is the STOP that measures
    en0 = len(rows)
    rows += [(1, 0)] * (T - W - 3) + [(0, 0)] * W
    rises = [t0, t0 + T]
    for k in range(RUNS):
        rises.append(len(rows))
        rows += [(1, 0)] * (T - W) + [(0, 0)] * W
    return rows + [(1, 0)] * 14, rises

def one(T, kw):
    rows, rises = stim(T)
    c, e, _ = run_qde("addll.qca", ["REF", "EN"], rows, **kw)
    code = "".join("1" if peak_per_period(c["t_ps"], c[f"OUT{i}"], n=len(rows))[-3] > 0 else "0" for i in range(4))
    ri, _f = edges(c["t_ps"], c["DOUT"])
    lat = []
    for x in rises[2:]:
        t = x * 4.0; cand = [a for a in ri if a > t]
        lat.append(round(cand[0] - t, 1) if cand else None)
    return {"T": T, "code": code, "k": code.count("1"), "lat_ps": lat}

if __name__ == "__main__":
    build()
    Ts = [int(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else list(range(5, 14))
    kw = {"engine": "cv", "radius_of_effect": 65}
    with ThreadPoolExecutor(os.cpu_count()) as ex:
        res = list(ex.map(lambda t: one(t, kw), Ts))
    for r in res:
        print(r, flush=True)
    json.dump(res, open("addll_sweep.json", "w"), indent=1)

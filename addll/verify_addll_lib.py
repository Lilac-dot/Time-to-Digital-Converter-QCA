import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "simulation"))
from addll_lib import edges
from qca_tools import peak_per_period
from qde_tools import run_qde
from test_addll import stim
SET = {"classic r=65": {"engine": "cv", "radius_of_effect": 65}, "Gaussian r=80": {}}
def lats(c, rises):
    ri, _ = edges(c["t_ps"], c["DOUT"])
    out = []
    for x in rises:
        t = x * 4.0; cand = [a for a in ri if a > t - 0.5]
        out.append(round(cand[0] - t, 1) if cand else None)
    return out
def code_at(c, n, i):
    return "".join("1" if peak_per_period(c["t_ps"], c[f"OUT{k}"], n=n)[i] > 0 else "0" for k in range(4))

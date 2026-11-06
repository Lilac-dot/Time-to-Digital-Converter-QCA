#!/usr/bin/env python3
"""Check the working layouts in the classic coherence-vector engine, using the same
patterns as vector_tables/. Writes results/classic_engine.json."""
import itertools
import json
import os

from qca_tools import peak_per_period
from qde_tools import run_qde
from run_all import CONV, EXPECT, LATCH, LATCH_Q, LAY, OUTS, RES, tdc_pattern

res = {}
rows, marks = tdc_pattern()
for r in (65, 80):
    c, _, _ = run_qde(CONV, ["IN", "CLK"], rows, engine="cv", radius_of_effect=r)
    p = [peak_per_period(c["t_ps"], c[n], n=len(rows)) for n in OUTS]
    codes = {g: "".join("1" if q[m + 6] > 0 else "0" for q in p) for g, m in marks}
    res[f"Conventional TDC, r={r} nm"] = {"codes": codes, "ok": codes == EXPECT}
for r in (65, 80):
    m3 = [v for v in itertools.product([0, 1], repeat=3) for _ in range(3)]
    for name, f, inp, fn in [("MUX Fig. 2(c)", "08_mux2to1_fig2c.qca", ["S", "I0", "I1"], lambda s, a, b: b if s else a),
                             ("Majority gate", "01_majority_gate.qca", ["A", "B", "C"], lambda a, b, d: int(a + b + d >= 2))]:
        c, _, _ = run_qde(os.path.join(LAY, f), inp, m3, engine="cv", radius_of_effect=r)
        pk = peak_per_period(c["t_ps"], c["OUT"], n=len(m3))[2::3] > 0
        res[f"{name}, r={r} nm"] = {"ok": [int(x) for x in pk] == [fn(*v) for v in m3[::3]]}
    l = [v for v, n in LATCH for _ in range(n)]
    c, _, _ = run_qde(os.path.join(LAY, "DFlipFlop.qca"), ["CLK", "D"], l, engine="cv", radius_of_effect=r)
    pk = peak_per_period(c["t_ps"], c["OUT"], n=len(l))[3::4] > 0
    res[f"D-latch, r={r} nm"] = {"ok": [int(x) for x in pk] == LATCH_Q}
json.dump(res, open(os.path.join(RES, "classic_engine.json"), "w"), indent=1)
print({k: v["ok"] for k, v in res.items()})

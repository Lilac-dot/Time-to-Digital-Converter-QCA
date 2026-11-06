#!/usr/bin/env python3
"""run_qde.py - run the same tests as run_all.py through the real QCADesigner-E engine
(qde_driver, see build_qde.sh). Writes results/qde_results.json."""
import itertools
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from qca_tools import area_um2, parse_qca, peak_per_period
from qde_tools import run_qde
from run_all import CONV, DFF, DFF_Q, EXPECT, FINAL, LATCH, LATCH_Q, LAY, OUTS, RES, kink_energy_J, tdc_pattern

SETTINGS = {"Gaussian clock, r=80 nm (QCADesigner-E default)": {},
            "Gaussian clock, r=65 nm": {"radius_of_effect": 65},
            "Cosine clock, r=65 nm": {"clock_type": 1, "radius_of_effect": 65},
            "Cosine clock, r=80 nm": {"clock_type": 1}}


def energy(e):
    return {"E_bath_eV": e["bath_mean_eV"], "E_error_eV": e["error_mean_eV"],
            "E_clk_eV": float(e["clk_per_cycle"].mean()),
            "avg_reported_eV": e["avg_reported_eV"], "avg_error_reported_eV": e["avg_error_reported_eV"]}


def tdc(path, **opts):
    rows, marks = tdc_pattern()
    c, e, log = run_qde(path, ["IN", "CLK"], rows, **opts)
    peaks = [peak_per_period(c["t_ps"], c[n], n=len(rows)) for n in OUTS]
    codes = {g: "".join("1" if p[m + 6] > 0 else "0" for p in peaks) for g, m in marks}
    return dict(codes=codes, ok=codes == EXPECT, min_abs_pol=round(float(min(np.abs(p[6:]).min() for p in peaks)), 3), **energy(e)), c, log


def truth(name, f, inputs, out, fn, hold=3):
    rows = [r for r in itertools.product([0, 1], repeat=len(inputs)) for _ in range(hold)]
    p = os.path.join(LAY, f)
    c, e, _ = run_qde(p, inputs, rows)
    pk = peak_per_period(c["t_ps"], c[out], n=len(rows))
    got = [int(pk[i * hold + hold - 1] > 0) for i in range(len(rows) // hold)]
    want = [fn(*rows[i * hold]) for i in range(len(rows) // hold)]
    return block(name, p, got == want, e)


def seq(name, f, inputs, out, steps, want):
    rows = [v for v, n in steps for _ in range(n)]
    p = os.path.join(LAY, f)
    c, e, _ = run_qde(p, inputs, rows)
    pk = peak_per_period(c["t_ps"], c[out], n=len(rows))
    got = [int(pk[k] > 0) for k in np.cumsum([n for _, n in steps]) - 1]
    return block(name, p, got == want, e)


def edge():
    p = os.path.join(LAY, "../archive/05_edge_converter.qca")
    rows = [(0,)] * 6 + [(1,)] * 6 + [(0,)] * 6 + [(1,)] * 6
    c, e, _ = run_qde(p, ["CLK"], rows)
    pk = peak_per_period(c["t_ps"], c["EDGE"], n=len(rows))
    return block("Edge converter, generated", p, (pk > 0).sum() in range(2, 5), e)


def wire():
    p = os.path.join(LAY, "02_wire_inverter.qca")
    rows = [r for r in itertools.product([0, 1], repeat=2) for _ in range(3)]
    c, e, _ = run_qde(p, ["IN_W", "IN_I"], rows)
    w = peak_per_period(c["t_ps"], c["OUT_W"], n=len(rows))[2::3] > 0
    i = peak_per_period(c["t_ps"], c["NOT_I"], n=len(rows))[2::3] > 0
    return block("Wire + inverter", p, list(w) == [False, False, True, True] and list(i) == [True, False, True, False], e)


def block(name, path, ok, e):
    cells = parse_qca(path)
    return dict(block=name, file=os.path.basename(path), cells=len(cells), area_um2=round(area_um2(cells), 4), ok=bool(ok), **energy(e))


def cell_map(log):
    """Per-cell E_bath from the engine's cell report (cell_diss=1)."""
    out = []
    for m in re.finditer(r"Cell \[ \d+ \] \[ \d+ \] \(([\d.e+-]+) ; ([\d.e+-]+)\), idx = \d+[ \t]*\nE_bath:[ \t]*([^\n]*)", log):
        v = [float(x) for x in m.group(3).split()]
        out.append({"x": float(m.group(1)), "y": float(m.group(2)), "meV": float(np.mean(v)) * 1e3 if v else None})
    return out


def main():
    Ek = kink_energy_J()
    jobs = {}
    with ThreadPoolExecutor(max_workers=max(2, (os.cpu_count() or 4) - 2)) as ex:
        for k, v in SETTINGS.items():
            jobs["conv", "settings", k] = ex.submit(tdc, CONV, **v)
            jobs["final", "settings", k] = ex.submit(tdc, FINAL, **v)
        for k in (0.5, 1.0, 1.5):
            jobs["conv", "gamma", f"{k} Ek"] = ex.submit(tdc, CONV, clock_high=k * Ek)
            jobs["final", "gamma", f"{k} Ek"] = ex.submit(tdc, FINAL, clock_high=k * Ek)
        for t in (1, 5, 10, 20):
            jobs["conv", "temperature", str(t)] = ex.submit(tdc, CONV, T=t)
        base = ex.submit(tdc, CONV, cell_diss=1)
        mux = lambda s, a, b: b if s else a
        blocks = [ex.submit(truth, "Majority gate", "01_majority_gate.qca", ["A", "B", "C"], "OUT", lambda a, b, c: int(a + b + c >= 2)),
                  ex.submit(wire),
                  ex.submit(truth, "2:1 MUX, generated", "../archive/03_mux2to1.qca", ["S", "I0", "I1"], "OUT", mux),
                  ex.submit(truth, "2:1 MUX, paper Fig. 2(c)", "08_mux2to1_fig2c.qca", ["S", "I0", "I1"], "OUT", mux),
                  ex.submit(seq, "D-latch, generated", "../archive/04_dlatch_mux.qca", ["CLK", "D"], "Q", LATCH, LATCH_Q),
                  ex.submit(seq, "D-latch, hand-built", "DFlipFlop.qca", ["CLK", "D"], "OUT", LATCH, LATCH_Q),
                  ex.submit(seq, "DFF, generated", "../archive/06_dff.qca", ["CLK", "D"], "Q", DFF, DFF_Q),
                  ex.submit(edge)]
        res = {"engine": "QCADesigner-E (FSillT/QCADesigner-E, master), coherence vector energy engine",
               "Ek_meV": Ek / 1.602176462e-19 * 1e3, "blocks": [b.result() for b in blocks],
               "conventional": {"settings": {}, "gamma": {}, "temperature": {}}, "TDC_final": {"settings": {}, "gamma": {}}}
        for (who, group, k), j in jobs.items():
            res["conventional" if who == "conv" else "TDC_final"][group][k] = j.result()[0]
        b, c, log = base.result()
    res["conventional"]["cell_map"] = cell_map(log)
    json.dump(res, open(os.path.join(RES, "qde_results.json"), "w"), indent=1)
    np.savez_compressed(os.path.join(RES, "qde_conv_trace.npz"), **{k.replace("/", "_"): v for k, v in c.items()})
    print("done")


if __name__ == "__main__":
    main()

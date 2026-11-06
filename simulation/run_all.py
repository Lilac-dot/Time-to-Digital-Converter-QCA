#!/usr/bin/env python3
"""run_all.py - functional tests and energy numbers for every layout in this repo.
Writes results/results.json and the figures. Build first:  cc -O2 -o qca_sim qca_sim.c -lm"""
import itertools
import json
import math
import os
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from qca_tools import area_um2, energy_summary, parse_qca, peak_per_period, simulate

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LAY = os.path.join(ROOT, "qca-layouts")
RES = os.path.join(HERE, "results")
os.makedirs(RES, exist_ok=True)
TMP = tempfile.mkdtemp()
CONV = os.path.join(LAY, "07_conventional_tdc.qca")
FINAL = os.path.join(ROOT, "archive", "TDC-final.qca")
OUTS = ["OUT0", "OUT1", "OUT2", "OUT3"]
EXPECT = {0: "1000", 1: "1100", 2: "1110", 3: "1111"}
EV = 1.602176462e-19
INK, MUTED, FILL = "#1f2933", "#7b8794", "#2f6db3"


def kink_energy_J(epsr=12.9, pitch=20.0, off=4.5):
    """Kink energy between two side-by-side cells."""
    K = (EV / 2) ** 2 / (4 * math.pi * 8.8541878e-12 * epsr) * 1e9
    dx, dy, q = [1, 1, -1, -1], [-1, 1, 1, -1], [-1, 1, -1, 1]
    diff = same = 0.0
    for a in range(4):
        for b in range(4):
            d = math.hypot(pitch + off * (dx[a] - dx[b]), off * (dy[a] - dy[b]))
            diff += q[a] * -q[b] / d
            same += q[a] * q[b] / d
    return K * (diff - same)


def tdc_pattern(gaps=(0, 1, 2, 3), stop=3, idle=6, settle=6):
    """Clear; then for each gap: IN rises, CLK (STOP) rises `gap` periods later;
    read the code; drop IN; clear again with another CLK pulse."""
    rows = [(0, 0)] * 4 + [(0, 1)] * stop + [(0, 0)] * idle
    marks = []
    for g in gaps:
        rows = rows + [(1, 0)] * g
        marks.append((g, len(rows)))
        rows = rows + [(1, 1)] * stop + [(1, 0)] * settle + [(0, 0)] * idle + [(0, 1)] * stop + [(0, 0)] * idle
    return rows, marks


def run_tdc(path, tag, **opts):
    rows, marks = tdc_pattern()
    prefix = os.path.join(TMP, tag)
    c, cells = simulate(path, ["IN", "CLK"], OUTS, rows, prefix, **opts)
    peaks = [peak_per_period(c["t"], c[n], n=len(rows)) for n in OUTS]
    codes = {g: "".join("1" if p[m + 6] > 0 else "0" for p in peaks) for g, m in marks}
    worst = float(min(np.abs(p[6:]).min() for p in peaks))
    e = energy_summary(prefix)
    return {"codes": codes, "pass": codes == EXPECT, "min_abs_pol": round(worst, 3),
            "E_bath_eV": e["bath"], "E_clk_eV": e["clk"], "E_io_eV": e["io"],
            "E_err_eV": abs(e["bath"] + e["clk"] + e["io"])}, c, rows, prefix, cells


def truth(path, inputs, output, fn, hold=3, **opts):
    rows = [r for r in itertools.product([0, 1], repeat=len(inputs)) for _ in range(hold)]
    prefix = os.path.join(TMP, os.path.basename(path))
    c, _ = simulate(path, inputs, [output], rows, prefix, **opts)
    p = peak_per_period(c["t"], c[output], n=len(rows))
    got = [int(p[i * hold + hold - 1] > 0) for i in range(len(rows) // hold)]
    want = [fn(*rows[i * hold]) for i in range(len(rows) // hold)]
    settled = abs(p[hold - 1::hold]).min() > 0.5
    return bool(got == want and settled), prefix


def seq_test(path, inputs, output, seq, want, **opts):
    """seq is (values, periods) steps; want[i] is the output at the end of step i."""
    rows = [v for v, n in seq for _ in range(n)]
    prefix = os.path.join(TMP, os.path.basename(path))
    c, _ = simulate(path, inputs, [output], rows, prefix, **opts)
    p = peak_per_period(c["t"], c[output], n=len(rows))
    ends = np.cumsum([n for _, n in seq]) - 1
    got = [int(p[e] > 0) for e in ends]
    return got == want, prefix


LATCH = [((1, 1), 4), ((0, 1), 4), ((0, 0), 4), ((1, 0), 4), ((0, 0), 4), ((0, 1), 4), ((1, 1), 4), ((0, 1), 4)]
LATCH_Q = [1, 1, 1, 0, 0, 0, 1, 1]
DFF = [((0, 1), 5), ((1, 1), 4), ((0, 0), 4), ((1, 0), 4), ((0, 1), 4), ((1, 1), 4)]
DFF_Q = [0, 1, 1, 0, 0, 1]


def edge_test(path):
    rows = [(0,)] * 6 + [(1,)] * 6 + [(0,)] * 6 + [(1,)] * 6
    prefix = os.path.join(TMP, "edge")
    c, _ = simulate(path, ["CLK"], ["EDGE"], rows, prefix)
    p = peak_per_period(c["t"], c["EDGE"], n=len(rows))
    return bool((p > 0).sum() in range(2, 5)), prefix   # one pulse per rising edge


def block_row(name, f, cells, ok, prefix, note=""):
    e = energy_summary(prefix)
    return {"block": name, "file": f, "cells": len(cells), "area_um2": round(area_um2(cells), 4),
            "pass": bool(ok), "E_bath_meV": round(e["bath"] * 1e3, 4), "note": note}


def main():
    out = {"Ek_J": kink_energy_J(), "Ek_meV": kink_energy_J() / EV * 1e3}
    Ek = out["Ek_J"]

    # ---- blocks
    blocks = []
    for name, f, inp, o, fn in [
        ("Majority gate", "01_majority_gate.qca", ["A", "B", "C"], "OUT", lambda a, b, c: int(a + b + c >= 2)),
        ("2:1 MUX, generated", "../archive/03_mux2to1.qca", ["S", "I0", "I1"], "OUT", lambda s, a, b: b if s else a),
        ("2:1 MUX, paper Fig. 2(c)", "08_mux2to1_fig2c.qca", ["S", "I0", "I1"], "OUT", lambda s, a, b: b if s else a),
    ]:
        p = os.path.join(LAY, f)
        ok, pre = truth(p, inp, o, fn)
        blocks.append(block_row(name, f, parse_qca(p), ok, pre))
    p = os.path.join(LAY, "02_wire_inverter.qca")
    rows = [r for r in itertools.product([0, 1], repeat=2) for _ in range(3)]
    pre = os.path.join(TMP, "wi")
    c, cells = simulate(p, ["IN_W", "IN_I"], ["OUT_W", "NOT_I"], rows, pre)
    w = peak_per_period(c["t"], c["OUT_W"], n=len(rows))[2::3] > 0
    i = peak_per_period(c["t"], c["NOT_I"], n=len(rows))[2::3] > 0
    ok = list(w) == [False, False, True, True] and list(i) == [True, False, True, False]
    blocks.append(block_row("Wire + inverter", "02_wire_inverter.qca", cells, ok, pre))
    for name, f, inp, o, seq, want in [
        ("D-latch, generated", "../archive/04_dlatch_mux.qca", ["CLK", "D"], "Q", LATCH, LATCH_Q),
        ("D-latch, hand-built", "DFlipFlop.qca", ["CLK", "D"], "OUT", LATCH, LATCH_Q),
        ("DFF, generated", "../archive/06_dff.qca", ["CLK", "D"], "Q", DFF, DFF_Q),
    ]:
        p = os.path.join(LAY, f)
        ok, pre = seq_test(p, inp, o, seq, want)
        blocks.append(block_row(name, f, parse_qca(p), ok, pre))
    p = os.path.join(LAY, "../archive/05_edge_converter.qca")
    ok, pre = edge_test(p)
    blocks.append(block_row("Edge converter, generated", "../archive/05_edge_converter.qca", parse_qca(p), ok, pre))
    out["blocks"] = blocks

    # ---- conventional TDC
    cells = parse_qca(CONV)
    out["conventional"] = {"cells": len(cells), "area_um2": round(area_um2(cells), 4)}
    base, c, rows, prefix, _ = run_tdc(CONV, "conv")
    out["conventional"]["baseline"] = base

    settings = {"QCADesigner-E style (Gaussian clock, r=80 nm)": {},
                "Gaussian clock, r=65 nm": {"radius": 65},
                "QCADesigner 2.0.3 style (cosine clock, r=65 nm)": {"clock_cos": 1, "radius": 65},
                "Cosine clock, r=80 nm": {"clock_cos": 1, "radius": 80}}
    out["conventional"]["settings"] = {k: run_tdc(CONV, "s", **v)[0] for k, v in settings.items()}
    out["conventional"]["gamma_sweep"] = {f"{k} Ek": run_tdc(CONV, "g", clock_high=k * Ek)[0] for k in (0.5, 1.0, 1.5)}
    out["conventional"]["temperature"] = {str(t): run_tdc(CONV, "t", T=t)[0] for t in (1, 5, 10, 20)}

    # ---- hand-built proposed TDC, as committed (the stray cell is left in the file)
    fcells = parse_qca(FINAL)
    stray = [i for i, x in enumerate(fcells) if x["y"] > 600]
    live = [x for x in fcells if x["y"] <= 600]
    r = run_tdc(FINAL, "final")[0]
    out["TDC_final"] = {"cells_in_file": len(fcells), "cells_connected": len(live),
                        "area_um2_without_stray": round(area_um2(live), 4), "baseline": r,
                        "settings": {k: run_tdc(FINAL, "fs", **v)[0] for k, v in settings.items()}}

    # ---- figures
    fig, ax = plt.subplots(6, 1, figsize=(10, 7), sharex=True)
    for a, n in zip(ax, ["IN", "CLK"] + OUTS):
        a.plot(c["t"], c[n], color=INK if n in OUTS else FILL, lw=0.7)
        a.set_ylabel(n, rotation=0, ha="right", va="center", color=INK)
        a.set_yticks([-1, 1]); a.set_ylim(-1.2, 1.2)
        a.tick_params(colors=MUTED, labelsize=8)
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
    rows_, marks = tdc_pattern()
    for g, m in marks:
        ax[0].annotate(f"gap {g}: {EXPECT[g]}", (m * 4 + 24, 1.25), fontsize=8, color=INK, ha="center", annotation_clip=False)
    ax[-1].set_xlabel("time (ps)", color=INK)
    fig.suptitle("Conventional TDC: outputs for STOP arriving 0, 1, 2, 3 clock periods after START", color=INK, y=0.97)
    fig.savefig(os.path.join(RES, "conventional_tdc_waveforms.png"), dpi=130, bbox_inches="tight")
    plt.close(fig)

    per = {}
    for ln in open(prefix + ".energy.csv").read().splitlines()[1:]:
        i, cy, b, *_ = ln.split(",")
        per.setdefault(int(i), []).append(float(b))
    fig, a = plt.subplots(figsize=(9, 6.2))
    vals = {i: np.mean(v) * 1e3 for i, v in per.items()}
    vmax = max(vals.values())
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("one", ["#dbe9f6", "#0b3c74"])
    for i, x in enumerate(cells):
        if i in vals:
            a.add_patch(plt.Rectangle((x["x"] - 9, -x["y"] - 9), 18, 18, color=cmap(vals[i] / vmax)))
        else:
            a.add_patch(plt.Rectangle((x["x"] - 9, -x["y"] - 9), 18, 18, fill=False, ec=MUTED, lw=0.8))
    a.autoscale_view(); a.set_aspect("equal"); a.axis("off")
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, vmax))
    fig.colorbar(sm, ax=a, shrink=0.7, label="mean bath energy per cell per cycle (meV)")
    a.set_title("Conventional TDC: where the energy goes (outlined = input/fixed, not simulated)", color=INK, fontsize=11)
    fig.savefig(os.path.join(RES, "conventional_tdc_energy_map.png"), dpi=130, bbox_inches="tight")
    plt.close(fig)
    top = sorted(((v, i) for i, v in vals.items()), reverse=True)[:5]
    out["conventional"]["hottest_cells_meV"] = [
        {"x": cells[i]["x"], "y": cells[i]["y"], "meV": round(v, 4)} for v, i in top]

    json.dump(out, open(os.path.join(RES, "results.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

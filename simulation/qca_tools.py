#!/usr/bin/env python3
"""Parse .qca files and drive qca_sim."""
import csv
import os
import re
import subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIND = {"NORMAL": 0, "INPUT": 1, "OUTPUT": 2, "FIXED": 3}


def parse_qca(path):
    """Return cells as dicts: x, y, zone, kind, pol, name."""
    text = open(path, errors="replace").read()
    cells = []
    for b in re.findall(r"\[TYPE:QCADCell\](.*?)\[#TYPE:QCADCell\]", text, flags=re.S):
        kind = re.search(r"cell_function=QCAD_CELL_(\w+)", b).group(1)
        charges = [float(q) for q in re.findall(r"charge=([-\d.e+]+)", b)]
        total = sum(charges) or 1.0
        label = re.search(r"psz=(.*)", b)
        cells.append({
            "x": float(re.search(r"\nx=([-\d.]+)", b).group(1)),
            "y": float(re.search(r"\ny=([-\d.]+)", b).group(1)),
            "zone": int(re.search(r"cell_options\.clock=(\d)", b).group(1)),
            "kind": KIND[kind],
            "pol": (charges[0] + charges[2] - charges[1] - charges[3]) / total,
            "name": label.group(1).strip() if label else None,
        })
    return cells


def area_um2(cells):
    xs = [c["x"] for c in cells]
    ys = [c["y"] for c in cells]
    return (max(xs) - min(xs) + 18) * (max(ys) - min(ys) + 18) / 1e6


def simulate(qca, inputs, outputs, rows, prefix, **opts):
    """inputs/outputs are name lists that set column order; rows are 0/1 tuples."""
    cells = parse_qca(qca)
    lines = [str(len(cells))]
    for c in cells:
        i = inputs.index(c["name"]) if c["kind"] == 1 else -1
        o = outputs.index(c["name"]) if c["kind"] == 2 and c["name"] in outputs else -1
        kind = c["kind"]
        if kind == 2 and o < 0:
            kind = 0
        lines.append(f'{c["x"]} {c["y"]} {c["zone"]} {kind} {c["pol"]} {i} {o}')
    with open(prefix + ".cells", "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(prefix + ".pat", "w") as f:
        f.write(f"{len(inputs)} {len(rows)}\n")
        for r in rows:
            f.write(" ".join(map(str, r)) + "\n")
    args = [os.path.join(HERE, "qca_sim"), prefix + ".cells", prefix + ".pat", prefix]
    args += [f"{k}={v}" for k, v in opts.items()]
    subprocess.run(args, check=True)
    os.remove(prefix + ".cells")
    os.remove(prefix + ".pat")
    data = np.loadtxt(prefix + ".trace.csv", delimiter=",")
    cols = {"t": data[:, 0]}
    for i, n in enumerate(inputs + outputs):
        cols[n] = data[:, 1 + i]
    return cols, cells


def energy_summary(prefix, skip=()):
    """Average per-cycle totals over the cycles every cell has."""
    rows = list(csv.DictReader(open(prefix + ".energy.csv")))
    by = {}
    for r in rows:
        if int(r["cell"]) in skip:
            continue
        t = by.setdefault(int(r["cycle"]), [0.0, 0.0, 0.0])
        t[0] += float(r["E_bath_eV"])
        t[1] += float(r["E_clk_eV"])
        t[2] += float(r["E_io_eV"])
    cycles = sorted(by)[:-1]          # the last window is not complete for every zone
    a = np.array([by[k] for k in cycles])
    return {"cycles": len(cycles), "bath": a[:, 0].mean(), "clk": a[:, 1].mean(),
            "io": a[:, 2].mean(), "bath_std": a[:, 0].std(), "total_bath": a[:, 0].sum()}


def peak_per_period(t, y, period=4.0, n=None):
    """Largest-magnitude polarization in each clock period, signed."""
    n = n or int(round(t[-1] / period + 0.5))
    out = []
    for k in range(n):
        s = y[(t >= k * period) & (t < (k + 1) * period)]
        out.append(s[np.argmax(np.abs(s))] if len(s) else 0.0)
    return np.array(out)

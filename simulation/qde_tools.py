#!/usr/bin/env python3
"""Drive the real QCADesigner-E engine through qde_driver and parse its report."""
import os
import re
import subprocess
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DRIVER = os.path.join(HERE, "qde_driver")


def run_qde(qca, inputs, rows, **opts):
    """Return (columns dict, energy dict, raw log). Runs in a temp dir because the
    engine writes QCADesignerE_Diss.trace to its working directory."""
    with tempfile.TemporaryDirectory() as d:
        pat, csv = os.path.join(d, "p.txt"), os.path.join(d, "o.csv")
        with open(pat, "w") as f:
            f.write(" ".join(inputs) + "\n")
            f.writelines(" ".join(map(str, r)) + "\n" for r in rows)
        args = [DRIVER, os.path.abspath(qca), pat, csv] + [f"{k}={v}" for k, v in opts.items()]
        r = subprocess.run(args, cwd=d, capture_output=True, text=True, errors="replace")
        log = r.stdout + "\n" + r.stderr
        if r.returncode:
            raise RuntimeError(f"qde_driver exit {r.returncode}: {log[-800:]}")
        with open(csv) as f:
            names = f.readline().strip().split(",")
        data = np.loadtxt(csv, delimiter=",", skiprows=1)
    cols = {n: data[:, i] for i, n in enumerate(names)}
    return cols, parse_energy(log), log


def parse_energy(log):
    def row(tag):
        m = re.search(tag + r":[ \t]*([^\n]*)", log)
        return np.array([float(v) for v in m.group(1).split()]) if m else np.array([])
    bath, clk, err = row("E_bath_total"), row("E_clk_total"), row("E_Error_total")
    avg = re.search(r"Avg_Ebath\): ([\d.e+-]+) eV \(Error: \+/- ([\d.e+-]+) eV\)", log)
    total = re.search(r"Sum_Ebath\): ([\d.e+-]+) eV \(Error: \+/- ([\d.e+-]+) eV\)", log)
    return {"bath_per_cycle": bath, "clk_per_cycle": clk, "error_per_cycle": err,
            "bath_mean_eV": float(bath.mean()) if len(bath) else None,
            "error_mean_eV": float(err.mean()) if len(err) else None,
            "avg_reported_eV": float(avg.group(1)) if avg else None,
            "avg_error_reported_eV": float(avg.group(2)) if avg else None,
            "sum_reported_eV": float(total.group(1)) if total else None}

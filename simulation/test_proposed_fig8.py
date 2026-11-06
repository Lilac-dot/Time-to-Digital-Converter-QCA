#!/usr/bin/env python3
"""Test the authors' proposed TDC (archive/09_proposed_tdc.qca) with the stimulus read from
the paper's Fig. 8(a) vector drawing. Writes results/proposed_fig8.json and the .vt file."""
import json
import os
import subprocess
import tempfile

from qca_tools import peak_per_period
from qde_tools import DRIVER, run_qde
from run_all import OUTS, RES, ROOT

N = 120
IN = [(13, 17), (35, 39), (55, 59), (75, 79), (99, 103)]
CLK = [(1, 2), (13, 17), (27, 28), (36, 40), (50, 51), (57, 60), (68, 69), (78, 82), (91, 92), (103, 107)]
READS = [13, 36, 57, 78, 103]
WANT = ["0000", "1000", "1100", "1110", "1111"]   # the codes marked on Fig. 8(a)
QCA = os.path.join(ROOT, "archive", "09_proposed_tdc.qca")
SETTINGS = {"Coherence vector, r=65 nm": {"engine": "cv", "radius_of_effect": 65},
            "Coherence vector, r=80 nm": {"engine": "cv", "radius_of_effect": 80},
            "QCADesigner-E, Gaussian, r=80 nm": {},
            "QCADesigner-E, cosine, r=65 nm": {"clock_type": 1, "radius_of_effect": 65}}


def main():
    rows = [[0, 0] for _ in range(N)]
    for a, b in IN:
        for k in range(a, b):
            rows[k][0] = 1
    for a, b in CLK:
        for k in range(a, b):
            rows[k][1] = 1
    res = {"want": WANT}
    for name, opts in SETTINGS.items():
        c, _, _ = run_qde(QCA, ["IN", "CLK"], rows, **opts)
        p = [peak_per_period(c["t_ps"], c[o], n=N) for o in OUTS]
        got = ["".join("1" if q[r + 6] > 0 else "0" for q in p) for r in READS]
        res[name] = {"codes": got, "ok": got == WANT}
    json.dump(res, open(os.path.join(RES, "proposed_fig8.json"), "w"), indent=1)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("IN CLK\n" + "".join(f"{a} {b}\n" for a, b in rows))
    vt = os.path.join(ROOT, "archive", "09_proposed_tdc_fig8.vt")
    subprocess.run([DRIVER, QCA, f.name, os.devnull, f"vt_out={vt}"], check=True, capture_output=True)
    os.remove(f.name)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()

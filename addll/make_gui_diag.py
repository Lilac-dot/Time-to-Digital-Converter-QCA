#!/usr/bin/env python3
"""GUI diagnostic package (gui_diag/): three small tests that localize a GUI failure of the
gated ADDLL. Writes each .vt with the driver, runs it in the classic coherence-vector engine
at 65 nm (the GUI's default engine settings), and records the expected outputs."""
import json, os, shutil, subprocess, tempfile, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "simulation"))
from qca_tools import peak_per_period
from qde_tools import run_qde, DRIVER
from addll_lib import edges

OUT = "gui_diag"
CV = {"engine": "cv", "radius_of_effect": 65}


def vt(qca, inputs, rows, name):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(" ".join(inputs) + "\n")
        f.writelines(" ".join(map(str, r)) + "\n" for r in rows)
    subprocess.run([DRIVER, qca, f.name, os.devnull, f"vt_out={OUT}/{name}.vt"], check=True, capture_output=True)
    os.unlink(f.name)


def main():
    os.makedirs(OUT, exist_ok=True)
    res = {}

    # 1. three-layer crossing: each output follows only its own input
    rows = [(a, b) for a in (0, 1) for b in (0, 1) for _ in range(3)]
    vt("cross.qca", ["A", "B"], rows, "diag1_cross")
    c, _, _ = run_qde("cross.qca", ["A", "B"], rows, **CV)
    n = len(rows)
    res["diag1_cross"] = {"vectors": n, "total_time_s": n * 4e-12,
                          "XA_per_input": [int(x > 0) for x in peak_per_period(c["t_ps"], c["XA"], n=n)[2::3]],
                          "XB_per_input": [int(x > 0) for x in peak_per_period(c["t_ps"], c["XB"], n=n)[2::3]]}

    # 2. delay line alone: D pulse, k = 0..4 stages selected; Q delay grows 4 ps per stage
    rows = []
    for k in range(5):
        s = [1 if i < k else 0 for i in range(4)]
        rows += [(0, *s)] * 20 + [(1, *s)] * 16 + [(0, *s)] * 8
    vt("delay_line.qca", ["D", "S0", "S1", "S2", "S3"], rows, "diag2_delay_line")
    c, _, _ = run_qde("delay_line.qca", ["D", "S0", "S1", "S2", "S3"], rows, **CV)
    ri, _ = edges(c["t_ps"], c["Q"])
    d = []
    for k in range(5):
        t0 = (k * 44 + 20) * 4.0
        cand = [x for x in ri if t0 < x < t0 + 96]
        d.append(round(cand[0], 1) if cand else None)
    res["diag2_delay_line"] = {"vectors": len(rows), "total_time_s": len(rows) * 4e-12,
                               "D_rise_ps": [(k * 44 + 20) * 4.0 for k in range(5)], "Q_rise_ps": d}

    # 3. gated ADDLL with EN held on: every stage bypassed, DOUT must follow each REF pulse
    rows = [(0, 0)] * 14 + [(0, 1)] * 20
    for _ in range(6):
        rows += [(1, 1)] * 8 + [(0, 1)] * 4
    rows += [(0, 1)] * 16
    vt("addll_gated.qca", ["REF", "EN"], rows, "diag3_gated_en_on")
    c, _, _ = run_qde("addll_gated.qca", ["REF", "EN"], rows, **CV)
    ri, _ = edges(c["t_ps"], c["DOUT"])
    res["diag3_gated_en_on"] = {"vectors": len(rows), "total_time_s": len(rows) * 4e-12,
                                "REF_rise_ps": [(34 + 12 * m) * 4.0 for m in range(6)], "DOUT_rise_ps": ri,
                                "DOUT_max": round(float(c["DOUT"].max()), 3)}

    for q in ("cross.qca", "delay_line.qca", "addll_gated.qca"):
        shutil.copy(q, OUT)
    json.dump(res, open(f"{OUT}/expected.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()

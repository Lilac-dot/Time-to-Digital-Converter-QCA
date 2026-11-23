#!/usr/bin/env python3
"""Write the vector tables for the QCADesigner GUI test of addll.qca, and print the expected
results from the classic-engine run of the same vectors."""
import json, os, subprocess, tempfile
from verify_addll_lib import code_at, lats, run_qde, stim, SET
from trace_lib import preclear
from qde_tools import DRIVER
os.makedirs("gui_test", exist_ok=True)
def seq(Ts):
    rows, marks = [], []
    for T in Ts:
        rows += preclear()
        r, rises = stim(T)
        base = len(rows); rows += r
        marks.append((T, len(rows) - 3, [base + x for x in rises[3:]]))
    return rows, marks
out = {}
for name, Ts in [("addll_test1_period7", (7,)), ("addll_test2_recalibrate", (6, 8, 5, 7))]:
    rows, marks = seq(Ts)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("REF EN\n" + "".join(f"{a} {b}\n" for a, b in rows))
    subprocess.run([DRIVER, "addll.qca", f.name, os.devnull, f"vt_out=gui_test/{name}.vt"], check=True, capture_output=True)
    os.remove(f.name)
    c, _, _ = run_qde("addll.qca", ["REF", "EN"], rows, **SET["classic r=65"])
    out[name] = {"vectors": len(rows), "time_s": f"{len(rows)*4e-12:.3g}", "steps": [{"T": T, "code": code_at(c, len(rows), i), "read_ps": i*4, "ref_rises_ps": [x*4 for x in rs], "lat_ps": lats(c, rs)} for T, i, rs in marks]}
    print(name, json.dumps(out[name]), flush=True)
json.dump(out, open("gui_test/expected.json", "w"), indent=1)

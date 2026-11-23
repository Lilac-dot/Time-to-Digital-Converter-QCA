#!/usr/bin/env python3
"""Strict check of the compensated ADDLL (addll_comp.qca).

Each calibration segment, for a REF period of T clock periods (4 ps each):
  1. EN on, REF quiet for 20 periods, so the line is bypassed and flushed.
  2. Free-running REF from t0: rises at t0, t0+T, ... (NFREE rises). The rise at t0+T is
     the STOP that measures. EN drops d periods after that rise (default 3).
  3. REF quiet for 30 periods, then one isolated REF pulse at tp, then 30 quiet periods.

Checks, all on absolute times (no modulo):
  - the code, read before and after the isolated pulse, is exactly the expected
    thermometer pattern for T (k = T - 9: 0000, 1000, 1100, 1110, 1111 for T = 9..13);
    T outside 9..13 is reported as out of range, never as a pass;
  - DOUT delay of the isolated pulse is 4T ps; the error in ps is reported;
  - exactly one DOUT rise follows the isolated pulse, and none occur in the quiet gap;
  - during calibration DOUT follows the first REF rise by the bypass delay (36 ps,
    the k = 0 delay), whatever code was stored before.
With the probe layout it also checks ENB, the stage selects S = Q.ENB and START directly.
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from addll_lib import edges
from verify_addll_lib import run_qde
from qca_tools import peak_per_period

CLK = 4.0
W = 2                    # REF low for W periods of each REF period
NFREE = 4
VALID = {9: "0000", 10: "1000", 11: "1100", 12: "1110", 13: "1111"}
BYPASS_PS = 36.0
TOL = 1.0                # ps
SET = {"classic r=65": {"engine": "cv", "radius_of_effect": 65},
       "classic r=80": {"engine": "cv", "radius_of_effect": 80},
       "Gaussian r=80": {}, "Gaussian r=65": {"radius_of_effect": 65}}


def segment(T, d=3, lead=0):
    s = lead
    t0 = s + 20
    rises = [t0 + m * T for m in range(NFREE)]
    r1 = rises[1]
    last = rises[-1]
    tp = last + T + 30
    n = tp + T + 30
    ref, en = [0] * n, [0] * n
    for r in rises + [tp]:
        for i in range(r, r + T - W):
            ref[i] = 1
    for i in range(s, r1 + d):
        en[i] = 1
    return ref, en, dict(T=T, d=d, s=s, t0=t0, r1=r1, en_off=r1 + d, last=last, tp=tp, end=n)


def sequence(Ts, d=3):
    ref, en, segs = [0] * 14, [0] * 14, []
    for T in Ts:
        r, e, m = segment(T, d, lead=0)
        base = len(ref)
        ref += r[0:]
        en += e[0:]
        segs.append({k: (v + base if k not in ("T", "d") else v) for k, v in m.items()})
    return list(zip(ref, en)), segs


def level(c, name, n, a, b):
    """Sign of the signal over clock periods a..b-1: fraction of periods with a
    positive peak, and the weakest peak magnitude."""
    p = peak_per_period(c["t_ps"], c[name], n=n)[a:b]
    return round(float(np.mean(p > 0)), 2), round(float(np.min(np.abs(p))), 2)


def code(c, n, i):
    return "".join("1" if peak_per_period(c["t_ps"], c[f"OUT{k}"], n=n)[i] > 0 else "0" for k in range(4))


def check(c, n, m, probe):
    T, tp = m["T"], m["tp"]
    ri, _ = edges(c["t_ps"], c["DOUT"])
    exp = VALID.get(T)
    c1, c2 = code(c, n, tp - 2), code(c, n, m["end"] - 2)
    after = [x - tp * CLK for x in ri if tp * CLK - 0.5 < x < tp * CLK + 100]
    gap = [x for x in ri if (m["last"] + 16) * CLK < x < tp * CLK - 0.5]
    cal = [x - m["t0"] * CLK for x in ri if x > m["t0"] * CLK - 0.5]
    dly = round(after[0], 1) if after else None
    o = {"T": T, "d": m["d"], "code": c1, "code_after_pulse": c2,
         "expected_code": exp or "out of range",
         "abs_delay_ps": dly, "target_ps": T * CLK,
         "error_ps": None if dly is None else round(dly - T * CLK, 1),
         "dout_rises_after_pulse": len(after), "dout_rises_in_gap": len(gap),
         "bypass_delay_ps": round(cal[0], 1) if cal else None}
    if exp is None:
        o["verdict"] = "OUT OF RANGE (saturated)"
    else:
        ok = (c1 == exp and c2 == exp and dly is not None and abs(dly - T * CLK) <= TOL
              and len(after) == 1 and not gap and cal and abs(cal[0] - BYPASS_PS) <= TOL)
        o["verdict"] = "PASS" if ok else "FAIL"
    if probe:
        on = (m["s"] + 8, m["en_off"])           # EN settled on
        off = (m["en_off"] + 10, m["end"])        # EN settled off
        o["ENB_on"] = [level(c, f"ENB{i}", n, *on) for i in range(4)]
        o["ENB_off"] = [level(c, f"ENB{i}", n, *off) for i in range(4)]
        o["S_on"] = [level(c, f"S{i}", n, *on) for i in range(4)]
        o["Q_off"] = "".join("1" if level(c, f"Q{i}", n, *off)[0] > 0.5 else "0" for i in range(4))
        o["S_off"] = "".join("1" if level(c, f"S{i}", n, *off)[0] > 0.5 else "0" for i in range(4))
        sr, _ = edges(c["t_ps"], c["START"])
        if dly is not None:
            st = [x for x in sr if x > tp * CLK + dly - 0.5]
            o["START_after_DOUT_ps"] = round(st[0] - tp * CLK - dly, 1) if st else None
        o["START_rises_after_pulse"] = len([x for x in sr if x > tp * CLK - 0.5])
    return o


def run(job):
    name, Ts, d, q = job
    rows, segs = sequence(Ts, d)
    c, e, _ = run_qde(q, ["REF", "EN"], rows, **SET[name])
    n = len(rows)
    res = {"layout": q, "setting": name, "sequence": list(Ts),
           "dout_peak": round(float(np.max(c["DOUT"])), 2),
           "steps": [check(c, n, m, "probe" in q) for m in segs]}
    print(json.dumps(res), flush=True)
    return res


JOBS = {
    "sweep": [(s, (T,), 3, "addll_comp.qca") for s in ("classic r=65", "Gaussian r=80") for T in range(8, 15)]
             + [(s, (T,), 3, "addll_comp.qca") for s in ("classic r=80", "Gaussian r=65") for T in range(9, 14)],
    "recal": [(s, seq, 3, "addll_comp.qca") for s in ("classic r=65", "Gaussian r=80")
              for seq in ((9, 10, 11, 12, 13), (13, 12, 11, 10, 9), (12, 13, 11, 9, 13, 10))],
    "en": [("classic r=65", (T,), d, "addll_comp.qca") for T in (10, 13) for d in (1, 2, 5, 8, 15)],
    "probe": [("classic r=65", seq, 3, "addll_comp_probe.qca") for seq in ((13, 9), (9, 11, 13, 10))]
             + [("Gaussian r=80", (13, 9), 3, "addll_comp_probe.qca")],
}

# Priority subset: exact codes and absolute delay first, then recalibration and one probe run.
FAST = ([JOBS["probe"][0]] + [("classic r=65", (T,), 3, "addll_comp.qca") for T in range(8, 15)]
        + [("Gaussian r=80", (T,), 3, "addll_comp.qca") for T in range(9, 14)]
        + JOBS["recal"][:2] + [("classic r=80", (9,), 3, "addll_comp.qca")])
JOBS["rest"] = [j for k in ("probe", "sweep", "recal", "en") for j in JOBS[k] if j not in FAST]
JOBS["fast"] = FAST

if __name__ == "__main__":
    which = sys.argv[1:] or ["fast", "rest"]
    jobs = [j for w in which for j in JOBS[w]]
    with ThreadPoolExecutor(9) as ex:
        res = list(ex.map(run, jobs))
    json.dump(res, open("comp_abs_verify_%s.json" % "_".join(which), "w"), indent=1)

#!/usr/bin/env python3
"""Coarse + fine TDC with asynchronous edges. Inputs change every quarter period
(Gaussian-clock energy engine, per_vector = 0.25). Each case: clear, START rises at quarter
s of a period, STOP rises D quarters later, both held, read after the carries settle.
Q = 4*count + sum(F_P) - sum(F_S) should equal D plus one constant for every case."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "simulation"))
from fine_lib import async_tdc, async_inputs  # noqa: E402
from qca_ml import ML  # noqa: E402
from qde_tools import run_qde  # noqa: E402
from test_fine import peak  # noqa: E402

NB = int(os.environ.get("NB", 4))
WAIT = int(os.environ.get("WAIT", 10))          # periods after STOP before reading


def build(path):
    L = ML()
    async_tdc(L, NB)
    L.write(path)
    return L


def stimulus(cases):
    rows, reads = [], []
    names = async_inputs(NB)
    for s, D in cases:
        n_clear, n_idle = 16, 8                  # quarters: 4 periods clear, 2 idle
        n_run = s + D + 4 * WAIT
        for i in range(n_clear + n_idle + n_run):
            clr = i < n_clear
            t = i - n_clear - n_idle
            st = int(t >= s)
            sp = int(t >= s + D)
            v = {"START": st, "STOP": sp}
            for k in range(NB):
                v[f"CLR{k}"] = int(clr)
            for m in (1, 2, 3):
                for kk in "RE":
                    v[f"START_{kk}{m}"] = st
                    v[f"STOP_{kk}{m}"] = sp
                for tg in "SP":
                    v[f"CLRN_{tg}{m}"] = int(not clr)
            rows.append([v[n] for n in names])
        reads.append(len(rows) - 2)
    return names, rows, reads


def main():
    cases = [tuple(map(int, a.split(","))) for a in sys.argv[1:]] or [(0, 9), (1, 9), (2, 9), (3, 9), (2, 47)]
    q = os.path.join(HERE, f"async_tdc{NB}.qca")
    L = build(q)
    print("cells", L.count(), "area_um2", round(L.area_um2(), 4))
    names, rows, reads = stimulus(cases)
    c, e, _ = run_qde(q, names, rows, per_vector=0.25, radius_of_effect=float(os.environ.get("RADIUS", 80)))
    if e.get("avg_reported_eV"):
        print(f"energy {e['avg_reported_eV']*1e3:.2f} meV/cycle (error +/- {abs(e['avg_error_reported_eV'])*1e3:.2f})")
    for (s, D), i in zip(cases, reads):
        X = [peak(c, f"X{k}", i) for k in range(NB)]
        cnt = sum((x < 0) << k for k, x in enumerate(X))
        fs = [peak(c, f"FS{m}", i) > 0 for m in (1, 2, 3)]
        fp = [peak(c, f"FP{m}", i) > 0 for m in (1, 2, 3)]
        Q = 4 * cnt + sum(fp) - sum(fs)
        print(f"s={s} D={D:2d}: count={cnt:2d} F_S={''.join(map(str, map(int, fs)))} "
              f"F_P={''.join(map(str, map(int, fp)))} Q={Q:3d} Q-D={Q - D}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""4-bit coarse counter: for each N, clear, hold EN for N periods, wait, read X3..X0.
Count = sum(2^k * b_k) with b_k = !X_k."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "simulation"))
from counter_lib import counter, window
from qca_ml import ML
from qde_tools import run_qde
from test_bit import per_period

NB = int(os.environ.get("NB", 4))

def build(path):
    L = ML()
    bits = counter(L, 12, 12, NB)
    window(L, bits[0], 12, 12)
    print("cells", L.count(), "area_um2", round(L.area_um2(), 4))
    return L.write(path)

def stim(Ns, wait=int(os.environ.get("WAIT", 18))):
    """Per measurement: clear with START = STOP = 0, then START rises, STOP rises N periods
    later, both held; read just before the next clear."""
    st, sp, clr, reads = [], [], [], []
    for N in Ns:
        st += [0] * 9; sp += [0] * 9; clr += [1] * 6 + [0] * 3
        st += [1] * (N + wait); sp += [0] * N + [1] * wait; clr += [0] * (N + wait)
        reads.append(len(st) - 2)
    return st, sp, clr, reads

if __name__ == "__main__":
    q = build(os.path.join(HERE, f"coarse_tdc{NB}.qca"))
    Ns = [int(x) for x in sys.argv[2:]] or [5, 11, 15, 6]
    st, sp, clr, reads = stim(Ns)
    en = st
    names = ["START", "STOP"] + [f"CLR{k}" for k in range(NB)]
    rows = [[a, b] + [c] * NB for a, b, c in zip(st, sp, clr)]
    eng = os.environ.get("ENGINE", "cv")
    kw = {"radius_of_effect": float(sys.argv[1]) if len(sys.argv) > 1 else 65}
    if eng == "cv":
        kw["engine"] = "cv"
    c, e, _ = run_qde(q, names, rows, **kw)
    if e.get("avg_reported_eV"):
        print(f"energy {e['avg_reported_eV']*1e3:.2f} meV/cycle (error +/- {abs(e['avg_error_reported_eV'])*1e3:.2f})")
    X = {k: per_period(c, f"X{k}", len(en)) for k in range(NB)}
    ok = True
    for N, i in zip(Ns, reads):
        b = [1 if X[k][i] < 0 else 0 for k in range(NB)]
        got = sum(v << k for k, v in enumerate(b))
        ok &= got == N % (1 << NB)
        print(f"N={N:2d} read={got:2d} bits(b3..b0)={''.join(map(str, b[::-1]))} peaks={[X[k][i] for k in range(NB)]}")
    print("PASS" if ok else "FAIL")

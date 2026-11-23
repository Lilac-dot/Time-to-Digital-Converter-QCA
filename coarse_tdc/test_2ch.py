#!/usr/bin/env python3
"""Two self-re-arming channels on one clock. Shared event times, each channel with its own
START phase and STOP delay; both must read Q - D = constant, independently."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "simulation"))
from test_rearm import build, stimulus, analyse  # noqa: E402
from qde_tools import run_qde  # noqa: E402

TAGS = ("A", "B")


def main():
    evA = [(1, 9), (2, 30)]
    evB = [(3, 17), (0, 6)]
    q = os.path.join(HERE, os.environ.get("QCA", "rearm_2ch.qca"))
    L = build(q, tags=TAGS)
    print("cells", L.count(), "area_um2", round(L.area_um2(), 4))
    names, rows, marks = stimulus([evA, evB], tags=TAGS)
    c, e, _ = run_qde(q, names, rows, per_vector=0.25, radius_of_effect=80)
    if os.environ.get("SAVE"):
        import numpy as _np
        _np.savez_compressed(os.environ["SAVE"], **{k: _np.asarray(v, dtype=_np.float32) for k, v in c.items()})
    if e.get("avg_reported_eV"):
        print(f"energy {e['avg_reported_eV']*1e3:.2f} meV/cycle (error +/- {abs(e['avg_error_reported_eV'])*1e3:.2f})")
    for ci, en, s, D, Q, info in analyse(c, marks, TAGS):
        print(f"ch {TAGS[ci]} event {en}: s={s} D={D:2d} Q={Q} Q-D={None if Q is None else Q - D}  {info}")


if __name__ == "__main__":
    main()

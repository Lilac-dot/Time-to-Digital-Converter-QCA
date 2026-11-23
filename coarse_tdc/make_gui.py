#!/usr/bin/env python3
"""Write the layouts and a QCADesigner vector table for a GUI check of the 4-bit coarse TDC.
Needs ../simulation/qde_driver (it writes the .vt from the design's own input order)."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "simulation"))
from counter_lib import counter, window  # noqa: E402
from qca_ml import ML  # noqa: E402

GUI = os.path.join(HERE, "gui_test")


def build(nb, path):
    L = ML()
    window(L, counter(L, 12, 12, nb)[0], 12, 12)
    L.write(path)
    print(f"{os.path.basename(path)}: {L.count()} cells, {L.area_um2():.3f} um^2")


def main():
    os.makedirs(GUI, exist_ok=True)
    build(4, os.path.join(HERE, "coarse_tdc4.qca"))
    build(8, os.path.join(HERE, "coarse_tdc8.qca"))
    build(4, os.path.join(GUI, "coarse_tdc4.qca"))
    from test_counter import stim
    Ns = [3, 9, 14]
    st, sp, clr, reads = stim(Ns)
    pat = os.path.join(GUI, "pattern.txt")
    with open(pat, "w") as f:
        f.write("START STOP " + " ".join(f"CLR{k}" for k in range(4)) + "\n")
        for a, b, c in zip(st, sp, clr):
            f.write(f"{a} {b} " + " ".join([str(c)] * 4) + "\n")
    vt = os.path.join(GUI, "coarse_tdc4_test.vt")
    subprocess.run([os.path.join(HERE, "..", "simulation", "qde_driver"),
                    os.path.join(GUI, "coarse_tdc4.qca"), pat, "/dev/null", f"vt_out={vt}"], check=True)
    os.remove(pat)
    n = len(st)
    print(f"vectors {n}, total time {n * 4e-12:.3e} s, reads at vectors {reads}")


if __name__ == "__main__":
    main()

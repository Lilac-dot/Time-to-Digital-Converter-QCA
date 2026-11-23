#!/usr/bin/env python3
"""Figures for the README: layout renders of each .qca and waveform plots of saved
simulation traces (results/waves/*.npz, written by the test scripts with SAVE=...).
Writes PNG (200 dpi) and SVG into figures/."""
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.patches as mp  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "figures")

# validated categorical slots (light surface), one per clock zone
ZONE = {0: "#2a78d6", 1: "#eb6834", 2: "#1baf7a", 3: "#eda100"}
FIXED = "#8a8984"
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
ROLE = {"in": "#2a78d6", "out": "#eb6834", "ctl": "#1baf7a"}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": INK2,
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
})


def parse(path):
    t = open(path).read()
    cells = []
    for blk in t.split("[TYPE:QCADCell]")[1:]:
        x = float(re.search(r"\nx=([-\d.]+)", blk).group(1))
        y = float(re.search(r"\ny=([-\d.]+)", blk).group(1))
        clk = int(re.search(r"cell_options\.clock=(\d+)", blk).group(1))
        fn = re.search(r"cell_function=QCAD_CELL_(\w+)", blk).group(1)
        nm = re.search(r"psz=(\w+)", blk)
        cells.append((x, y, clk, fn, nm.group(1) if nm else None))
    return cells


def layout(qca, name, title, label_every=True):
    cells = parse(qca)
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    w, h = (max(xs) - min(xs)) / 20 + 4, (max(ys) - min(ys)) / 20 + 6
    s = min(11 / w, 13 / h)
    fig, ax = plt.subplots(figsize=(max(5.5, w * s), max(4.5, h * s)))
    for x, y, clk, fn, nm in cells:
        fc = FIXED if fn == "FIXED" else ZONE[clk]
        ec = INK if fn in ("INPUT", "OUTPUT") else "none"
        ax.add_patch(mp.Rectangle((x - 9, -y - 9), 18, 18, facecolor=fc, edgecolor=ec,
                                  linewidth=1.4 if ec != "none" else 0))
        if nm and label_every:
            ax.text(x, -y + 13, nm, ha="center", va="bottom", fontsize=6.5, color=INK)
    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.margins(0.06)
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    x0, y0 = min(xs), -max(ys) - 40
    ax.plot([x0, x0 + 100], [y0, y0], color=INK, lw=2)
    ax.text(x0 + 50, y0 - 8, "100 nm", ha="center", va="top", fontsize=8, color=INK)
    handles = [mp.Patch(color=c, label=f"clock zone {z}") for z, c in ZONE.items()]
    handles += [mp.Patch(color=FIXED, label="fixed cell"),
                mp.Patch(facecolor="white", edgecolor=INK, label="input / output")]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=6,
              fontsize=7.5, frameon=False)
    area = (max(xs) - min(xs) + 18) * (max(ys) - min(ys) + 18) / 1e6
    ax.set_title(f"{title}\n{len(cells)} cells, {area:.2f} um\u00b2", fontsize=10.5, color=INK, loc="left")
    save(fig, name)


def save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(os.path.join(OUT, f"{name}.{ext}"), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def envelope(t, v, period=4.0):
    """Per-clock-period value of a clocked output: the largest-magnitude sample in each
    period, held as a step. This is the value a reader samples."""
    k = np.floor(t / period).astype(int)
    out = np.empty_like(v)
    for kk in np.unique(k):
        m = k == kk
        seg = v[m]
        out[m] = seg[np.abs(seg).argmax()]
    return out


def waves(npz, name, title, rows, t0=None, t1=None, marks=(), env=False):
    """rows: list of (trace, label, role). Each trace in its own strip, polarization -1..1.
    env=True plots clocked (non-input) traces as their per-period value."""
    d = np.load(npz)
    t = d["t_ps"]
    m = np.ones_like(t, bool)
    if t0 is not None:
        m &= t >= t0
    if t1 is not None:
        m &= t <= t1
    fig, axs = plt.subplots(len(rows), 1, figsize=(10, 0.62 * len(rows) + 1.0), sharex=True)
    for ax, (k, lab, role) in zip(axs, rows):
        y = envelope(t, d[k]) if env and role != "in" else d[k]
        ax.plot(t[m], y[m], color=ROLE[role], lw=1.2)
        ax.set_ylim(-1.25, 1.25)
        ax.set_yticks([-1, 1])
        ax.set_yticklabels(["-1", "+1"], fontsize=6.5)
        ax.axhline(0, color=GRID, lw=0.8, zorder=0)
        ax.set_ylabel(lab, rotation=0, ha="right", va="center", fontsize=8.5, color=INK)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for x, txt in marks:
            ax.axvline(x, color=INK2, lw=0.8, ls=(0, (3, 3)), zorder=0)
    for j, (x, txt) in enumerate(marks):
        axs[0].text(x, 1.45 + 0.9 * (j % 2), txt, fontsize=7.5, color=INK2, ha="center", va="bottom")
    axs[-1].set_xlabel("time (ps)")
    handles = [mp.Patch(color=ROLE["in"], label="input"), mp.Patch(color=ROLE["out"], label="output"),
               mp.Patch(color=ROLE["ctl"], label="internal / control")]
    roles = {r for _, _, r in rows}
    fig.legend(handles=[h for h, r in zip(handles, ("in", "out", "ctl")) if r in roles],
               loc="upper right", ncol=3, frameon=False, fontsize=8)
    fig.suptitle(title, x=0.01, ha="left", fontsize=11, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    save(fig, name)


if __name__ == "__main__":
    which = sys.argv[1:] or ["layouts", "waves"]
    if "layouts" in which:
        layout(os.path.join(HERE, "coarse_tdc4.qca"), "layout_coarse_tdc4",
               "4-bit coarse TDC (counter + START/STOP window)")
        layout(os.path.join(HERE, "async_tdc4.qca"), "layout_async_tdc4",
               "4-bit asynchronous coarse + fine TDC")
        if os.path.exists(os.path.join(HERE, "rearm_tdc4.qca")):
            layout(os.path.join(HERE, "rearm_tdc4.qca"), "layout_rearm_tdc4",
                   "Self-re-arming channel (pulse capture, VALID, internal clear)")
        if os.path.exists(os.path.join(HERE, "rearm_2ch.qca")):
            layout(os.path.join(HERE, "rearm_2ch.qca"), "layout_rearm_2ch",
                   "Two self-re-arming channels on one clock", label_every=False)
    W = os.path.join(HERE, "results", "waves")
    if "waves" in which:
        f = os.path.join(W, "counter4_sync.npz")
        if os.path.exists(f):
            waves(f, "waves_counter4_sync", "4-bit coarse TDC, classic engine: STOP 9 periods after START",
                  [("START", "START", "in"), ("STOP", "STOP", "in"), ("CLR0", "CLR", "in"),
                   ("X0", "X0", "out"), ("X1", "X1", "out"), ("X2", "X2", "out"), ("X3", "X3", "out")])
        f = os.path.join(W, "async4.npz")
        if os.path.exists(f):
            waves(f, "waves_async4", "Asynchronous capture (Gaussian clock, inputs change every 1 ps)",
                  [("START", "START", "in"), ("STOP", "STOP", "in"), ("FS1", "F_S1", "out"),
                   ("FS2", "F_S2", "out"), ("FS3", "F_S3", "out"), ("FP1", "F_P1", "out"),
                   ("FP2", "F_P2", "out"), ("FP3", "F_P3", "out"), ("X0", "X0", "out"), ("X1", "X1", "out")])
        f = os.path.join(W, "rearm4.npz")
        if os.path.exists(f):
            waves(f, "waves_rearm4", "Self-re-arming channel: three events, no external clear",
                  marks=[(122, "STOP"), (144, "VALID"), (257, "STOP"), (280, "VALID"), (409, "STOP"), (432, "VALID")],
                  env=True, rows=
                  [("RST", "RST", "in"), ("START", "START", "in"), ("STOP", "STOP", "in"), ("VALID", "VALID", "ctl"),
                   ("CLR", "CLR", "ctl"), ("X0", "X0", "out"), ("X1", "X1", "out"),
                   ("X2", "X2", "out"), ("X3", "X3", "out"), ("FS3", "F_S3", "out"), ("FP3", "F_P3", "out")])

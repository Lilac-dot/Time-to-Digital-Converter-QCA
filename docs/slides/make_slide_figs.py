#!/usr/bin/env python3
"""Clean slide figures: digital timing diagrams (logic levels per clock period) from the saved
QCADesigner-E traces, and QCA building-block layout renders. Writes PNGs next to this file."""
import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, os.path.join(ROOT, "coarse_tdc"))
import figures as F  # noqa: E402

TEAL, RED, INK, GREY, GRID = "#0e7c7b", "#c1272d", "#0b3b40", "#5f6b6d", "#e3e8e8"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 15})

def logic(t, v):  # per-period value, then threshold
    return (F.envelope(t, v) > 0).astype(float)

def timing(name, t, rows, marks=(), xlabel="time (ps)", t1=None, t0=None):
    """rows: (label, y, kind) with kind 'in'|'out'|'ctl'|'bus' (bus = integer value)."""
    m = np.ones_like(t, bool)
    if t1 is not None: m &= t <= t1
    if t0 is not None: m &= t >= t0
    n = len(rows)
    fig, ax = plt.subplots(figsize=(13.3, 0.62 * n + 1.3), dpi=150, facecolor="white")
    ax.set_facecolor("white")
    for i, (lab, y, kind) in enumerate(rows):
        base = (n - 1 - i) * 1.25
        col = {"in": TEAL, "out": RED, "ctl": INK, "bus": INK}[kind]
        if kind == "bus":
            ax.plot(t[m], np.full(m.sum(), base + 0.45), color=GRID, lw=0)
            tt, yv = t[m], y[m]
            edges = np.flatnonzero(np.diff(yv) != 0)
            seg = np.split(np.arange(len(tt)), edges + 1)
            span = tt[-1] - tt[0]
            for s_ in seg:
                x0, x1 = tt[s_[0]], tt[min(s_[-1] + 1, len(tt) - 1)]
                short = x1 - x0 < 6.0
                ax.fill_between([x0, x1], base + 0.05, base + 0.85, color="#d5dcdc" if short else "#e4f1f0", lw=0)
                ax.plot([x0, x1], [base + 0.05] * 2, color=INK, lw=1.4)
                ax.plot([x0, x1], [base + 0.85] * 2, color=INK, lw=1.4)
                if not short and x1 - x0 > span * 0.03:
                    ax.text((x0 + x1) / 2, base + 0.45, str(int(yv[s_[0]])), ha="center", va="center",
                            fontsize=14, color=INK, fontweight="bold")
        else:
            yy = base + 0.8 * y[m]
            ax.fill_between(t[m], base, yy, step=None, color=col, alpha=0.12, lw=0)
            ax.plot(t[m], yy, color=col, lw=2.2)
        ax.text(-0.012, base + 0.4, lab, transform=ax.get_yaxis_transform(), ha="right", va="center",
                fontsize=15, color=INK, fontweight="bold")
    for x, txt in marks:
        ax.axvline(x, color=GREY, lw=1, ls=(0, (4, 4)), zorder=0)
        ax.text(x, n * 1.25 + 0.25, txt, ha="center", va="bottom", fontsize=13, color=GREY)
    ax.set_ylim(-0.3, n * 1.25 + 0.6)
    ax.set_yticks([])
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GREY)
    ax.tick_params(colors=GREY)
    ax.set_xlabel(xlabel, color=GREY)
    ax.set_xlim(t[m][0], t[m][-1])
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, name + ".png"), facecolor="white")
    plt.close(fig)
    print("wrote", name)

def count_of(d, t, nb=4):
    return sum(((F.envelope(t, d[f"X{k}"]) < 0).astype(int)) << k for k in range(nb))

# conventional TDC
d = np.load(os.path.join(ROOT, "simulation/results/qde_conv_trace.npz")); t = d["t_ps"]
timing("slide_conv_waves", t,
       [("START", (d["IN"] > 0).astype(float), "in"), ("STOP", (d["CLK"] > 0).astype(float), "in")] +
       [(f"OUT{k}", logic(t, d[f"OUT{k}"]), "out") for k in range(4)],
       marks=[(70, "1000"), (168, "1100"), (270, "1110"), (375, "1111")])

# asynchronous capture, single event
d = np.load(os.path.join(ROOT, "coarse_tdc/results/waves/async4.npz")); t = d["t_ps"]
timing("slide_async_waves", t,
       [("START", (d["START"] > 0).astype(float), "in"), ("STOP", (d["STOP"] > 0).astype(float), "in"),
        ("count", count_of(d, t), "bus")] +
       [(f"F_S{k}", logic(t, d[f"FS{k}"]), "out") for k in (1, 2, 3)] +
       [(f"F_P{k}", logic(t, d[f"FP{k}"]), "out") for k in (1, 2, 3)],
       marks=[(25, "START"), (34, "STOP")], t0=8)

# self-re-arming channel
d = np.load(os.path.join(ROOT, "coarse_tdc/results/waves/rearm4.npz")); t = d["t_ps"]
timing("slide_rearm_waves", t,
       [("RST", (d["RST"] > 0).astype(float), "in"), ("START", (d["START"] > 0).astype(float), "in"),
        ("STOP", (d["STOP"] > 0).astype(float), "in"), ("VALID", logic(t, d["VALID"]), "ctl"),
        ("CLR", logic(t, d["CLR"]), "ctl"), ("count", count_of(d, t), "bus")],
       marks=[(122, "event 1"), (257, "event 2"), (409, "event 3")], t0=25)

# QCA building blocks

# QCA basics: cell polarization, majority gate, inverter, four clock zones
import matplotlib.patches as mp  # noqa: E402
ZC = {0: "#2a78d6", 1: "#eb6834", 2: "#1baf7a", 3: "#eda100"}

def cell(ax, x, y, p=None, fc="white", ec=INK, s=1.0, label=None, lab_pos="above"):
    ax.add_patch(mp.FancyBboxPatch((x - s / 2, y - s / 2), s, s, boxstyle="round,pad=0,rounding_size=0.08",
                                   fc=fc, ec=ec, lw=2))
    d = 0.24 * s
    for dx, dy in ((-d, -d), (d, -d), (d, d), (-d, d)):
        on = p is not None and ((p > 0 and dx * dy > 0) or (p < 0 and dx * dy < 0))
        ax.add_patch(mp.Circle((x + dx, y + dy), 0.11 * s, fc=INK if on else "white", ec=INK, lw=1.5))
    if label:
        ax.text(x, y + (0.75 if lab_pos == "above" else -0.75) * s, label, ha="center",
                va="bottom" if lab_pos == "above" else "top", fontsize=15, color=INK, fontweight="bold")

fig, axs = plt.subplots(1, 4, figsize=(16, 4.6), dpi=150, facecolor="white",
                        gridspec_kw={"width_ratios": [1.1, 1.5, 1.6, 2.1]})
for ax in axs:
    ax.set_aspect("equal"); ax.axis("off")
ax = axs[0]
cell(ax, 0, 0, +1, label="P = +1  (logic 1)", lab_pos="below")
cell(ax, 0, 2.4, -1, label="P = −1  (logic 0)", lab_pos="below")
ax.set_xlim(-1.4, 1.4); ax.set_ylim(-1.5, 3.2); ax.set_title("QCA cell", color=INK, fontsize=17, fontweight="bold")
ax = axs[1]
for (x, y, l) in ((-1.1, 0, "A"), (0, 1.1, "B"), (0, -1.1, "C")):
    cell(ax, x, y, None, fc="#e4f1f0", label=l, lab_pos="above" if y >= 0 else "below")
cell(ax, 0, 0, None, fc="#f5dede"); cell(ax, 1.1, 0, None, fc="white", label="OUT")
ax.text(0.2, -3.3, "OUT = M(A, B, C)\nC = 0 → AND,  C = 1 → OR", ha="center", fontsize=14, color=INK)
ax.set_xlim(-2, 2.2); ax.set_ylim(-4.2, 2.3); ax.set_title("Majority gate", color=INK, fontsize=17, fontweight="bold")
ax = axs[2]
for i in range(3):
    cell(ax, i * 1.1 - 1.6, 0.55, +1)
cell(ax, 1.65, -0.55, -1); cell(ax, 2.75, -0.55, -1)
ax.text(0.6, -2.0, "a diagonal step flips the polarization\n(NOT gate)", ha="center", fontsize=14, color=INK)
ax.set_xlim(-2.3, 3.4); ax.set_ylim(-2.8, 1.6); ax.set_title("Inverter", color=INK, fontsize=17, fontweight="bold")
ax = axs[3]
for z in range(4):
    for k in range(2):
        cell(ax, z * 2.3 + k * 1.05, 0, None, fc=ZC[z])
    ax.text(z * 2.3 + 0.52, -0.95, f"zone {z}", ha="center", fontsize=14, color=INK)
ax.annotate("", xy=(8.0, 1.05), xytext=(0, 1.05), arrowprops=dict(arrowstyle="-|>", lw=2.2, color=INK))
ax.text(4.0, 1.35, "data moves one zone per quarter period", ha="center", fontsize=14, color=INK)
ax.text(4.0, -2.2, "4 zones = 1 clock period = 4 ps\nso 1 zone = 1 ps", ha="center", fontsize=14, color=INK)
ax.set_xlim(-0.8, 8.9); ax.set_ylim(-3.0, 2.0); ax.set_title("Four-phase clock", color=INK, fontsize=17, fontweight="bold")
fig.tight_layout()
fig.savefig(os.path.join(HERE, "slide_qca_basics.png"), facecolor="white")
print("wrote slide_qca_basics")

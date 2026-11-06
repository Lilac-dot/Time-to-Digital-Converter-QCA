#!/usr/bin/env python3
"""Figures for the conventional TDC from QCADesigner-E output (results/qde_*)."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from run_all import CONV, EXPECT, FILL, INK, MUTED, OUTS, RES, tdc_pattern
from qca_tools import parse_qca

tr = np.load(os.path.join(RES, "qde_conv_trace.npz"))
fig, ax = plt.subplots(6, 1, figsize=(10, 7), sharex=True)
for a, n in zip(ax, ["IN", "CLK"] + OUTS):
    a.plot(tr["t_ps"], tr[n], color=INK if n in OUTS else FILL, lw=0.7)
    a.set_ylabel(n, rotation=0, ha="right", va="center", color=INK)
    a.set_yticks([-1, 1]); a.set_ylim(-1.2, 1.2)
    a.tick_params(colors=MUTED, labelsize=8)
    for s in ("top", "right"):
        a.spines[s].set_visible(False)
for g, m in tdc_pattern()[1]:
    ax[0].annotate(f"gap {g}: {EXPECT[g]}", (m * 4 + 24, 1.25), fontsize=8, color=INK, ha="center", annotation_clip=False)
ax[-1].set_xlabel("time (ps)", color=INK)
fig.suptitle("Conventional TDC, plotted from QCADesigner-E vector-table output", color=INK, y=0.97)
fig.savefig(os.path.join(RES, "conventional_tdc_waveforms.png"), dpi=130, bbox_inches="tight")
plt.close(fig)

cmap = matplotlib.colors.LinearSegmentedColormap.from_list("one", ["#dbe9f6", "#0b3c74"])
m = {(c["x"], c["y"]): c["meV"] for c in json.load(open(os.path.join(RES, "qde_results.json")))["conventional"]["cell_map"]}
vmax = max(v for v in m.values() if v is not None)
fig, a = plt.subplots(figsize=(9, 6.2))
for c in parse_qca(CONV):
    v = m.get((c["x"], c["y"]))
    if v is None:
        a.add_patch(plt.Rectangle((c["x"] - 9, -c["y"] - 9), 18, 18, fill=False, ec=MUTED, lw=0.8))
    else:
        a.add_patch(plt.Rectangle((c["x"] - 9, -c["y"] - 9), 18, 18, color=cmap(v / vmax)))
a.autoscale_view(); a.set_aspect("equal"); a.axis("off")
fig.colorbar(plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, vmax)), ax=a, shrink=0.7, label="mean E_bath per cell per cycle (meV)")
a.set_title("Conventional TDC energy map from QCADesigner-E (outlined = input/fixed, not simulated)", color=INK, fontsize=11)
fig.savefig(os.path.join(RES, "conventional_tdc_energy_map.png"), dpi=130, bbox_inches="tight")

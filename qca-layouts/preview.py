#!/usr/bin/env python3
"""Render each generated .qca to a PNG so the layout can be eyeballed
without QCADesigner. Colour = clock zone; markers = cell function."""
import glob
import re
import matplotlib.pyplot as plt
import matplotlib.patches as mp

ZONE_COLOR = {0: "#2e7d32", 1: "#c62828", 2: "#1565c0", 3: "#f9a825"}
FUNC_EDGE = {"NORMAL": "none", "INPUT": "black", "OUTPUT": "black", "FIXED": "black"}


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


def render(path):
    cells = parse(path)
    fig, ax = plt.subplots(figsize=(11, 8))
    for x, y, clk, fn, nm in cells:
        fc = ZONE_COLOR[clk]
        if fn == "FIXED":
            fc = "#555"
        r = mp.Rectangle((x - 9, -y - 9), 18, 18, facecolor=fc,
                         edgecolor=FUNC_EDGE[fn], linewidth=1.6 if fn != "NORMAL" else 0)
        ax.add_patch(r)
        if nm:
            ax.text(x, -y + 16, nm, ha="center", va="bottom", fontsize=9, weight="bold")
        if fn == "FIXED":
            ax.text(x, -y, "0/1", ha="center", va="center", fontsize=6, color="w")
    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.set_title(path)
    handles = [mp.Patch(color=c, label=f"zone {z}") for z, c in ZONE_COLOR.items()]
    handles.append(mp.Patch(color="#555", label="fixed const"))
    ax.legend(handles=handles, loc="upper left", fontsize=8, ncol=5)
    ax.margins(0.1)
    out = path.replace(".qca", ".png")
    fig.savefig(out, dpi=110, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out)


if __name__ == "__main__":
    for f in sorted(glob.glob("*.qca")):
        render(f)

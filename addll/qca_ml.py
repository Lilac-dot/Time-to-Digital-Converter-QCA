#!/usr/bin/env python3
"""qca_ml.py - multilayer layout writer for the ADDLL work. Reuses qca_gen's cell format.
Layer 0 is the main cell layer. A crossing climbs to layer 2 through a via cell on layer 1."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "qca-layouts"))
from qca_gen import PITCH, cell  # noqa: E402

_PRI = {"normal": 0, "fixed": 1, "output": 2, "input": 3}


class ML:
    def __init__(self):
        self.layers = {0: {}, 1: {}, 2: {}}

    def add(self, r, c, zone, fn="normal", name=None, pol=1, layer=0):
        """Grid coordinates: row r, column c."""
        cur = self.layers[layer].get((r, c))
        if cur and cur[1] != "normal" and _PRI[fn] <= _PRI[cur[1]]:
            return
        if cur and cur[1] == "normal" and fn == "normal" and cur[0] != zone:
            raise ValueError(f"zone clash at {(r, c)} layer {layer}: {cur[0]} vs {zone}")
        self.layers[layer][(r, c)] = (zone, fn, name, pol)

    def wire(self, pts, zones, layer=0):
        """Follow straight segments through pts; zones is one zone, or a list with one
        value per cell along the path (start cell included)."""
        path = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            if a[0] != b[0] and a[1] != b[1]:
                raise ValueError(f"diagonal segment {a} {b}")
            dr = (b[0] > a[0]) - (b[0] < a[0])
            dc = (b[1] > a[1]) - (b[1] < a[1])
            p = a
            while p != b:
                p = (p[0] + dr, p[1] + dc)
                path.append(p)
        if isinstance(zones, int):
            zones = [zones] * len(path)
        if len(zones) != len(path):
            raise ValueError(f"{len(path)} cells but {len(zones)} zones from {pts}")
        for p, z in zip(path, zones):
            self.add(p[0], p[1], z, layer=layer)
        return path

    def via(self, r, c, zone):
        self.add(r, c, zone, layer=1)
        self.add(r, c, zone, layer=2)

    def count(self):
        return sum(len(v) for v in self.layers.values())

    def area_um2(self):
        k = [p for v in self.layers.values() for p in v]
        rs, cs = [p[0] for p in k], [p[1] for p in k]
        return ((max(cs) - min(cs)) * PITCH + 18) * ((max(rs) - min(rs)) * PITCH + 18) / 1e6

    def write(self, path):
        names = {0: "Main Cell Layer", 1: "Via Layer", 2: "Crossover Layer"}
        out = "[VERSION]\nqcadesigner_version=2.000000\n[#VERSION]\n[TYPE:DESIGN]\n"
        for i in (0, 1, 2):
            if not self.layers[i]:
                continue
            out += f"[TYPE:QCADLayer]\ntype=1\nstatus=0\npszDescription={names[i]}\n"
            for (r, c), (z, fn, name, pol) in sorted(self.layers[i].items()):
                out += cell(c * PITCH + 40.0, r * PITCH + 40.0, z, fn, name, pol)
            out += "[#TYPE:QCADLayer]\n"
        out += "[#TYPE:DESIGN]\n"
        with open(path, "w", newline="\n") as f:
            f.write(out)
        return path

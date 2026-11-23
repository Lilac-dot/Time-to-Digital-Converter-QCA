#!/usr/bin/env python3
"""addll_comp.qca with internal probe points turned into output cells, for simulation only.
An output cell is simulated like a normal cell, so the circuit is unchanged.

Probes, for stages i = 0..3 at COLS[i]:
  ENB<i>  last crossover cell of the ENB tap before the stage's via, at (R-3, C+6)
  Q<i>    last crossover cell of the code bit before the stage's via, at (R-6, C+3)
  S<i>    gate centre of the select AND gate, at (R-2, C+3)
  START   main-layer cell on column 5 just before START enters the TDC, at (24, 5)
"""
import qca_ml
import build_addll_comp as b

PROBES = []
for i, C in enumerate(b.COLS):
    PROBES += [(2, (b.R - 3, C + 6), f"ENB{i}"), (2, (b.R - 6, C + 3), f"Q{i}"), (0, (b.R - 2, C + 3), f"S{i}")]
PROBES.append((0, (24, 5), "START"))


def build(path="addll_comp_probe.qca"):
    real = qca_ml.ML.write

    def write(self, p):
        for layer, rc, name in PROBES:
            z, fn, _, pol = self.layers[layer][rc]
            assert fn == "normal", (name, rc, fn)
            self.layers[layer][rc] = (z, "output", name, pol)
        return real(self, path)
    qca_ml.ML.write = write
    try:
        return b.build(path)
    finally:
        qca_ml.ML.write = real


if __name__ == "__main__":
    print(build())

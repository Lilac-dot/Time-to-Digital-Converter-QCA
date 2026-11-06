#!/usr/bin/env python3
"""
qca_gen.py - emit QCADesigner 2.0.3 .qca layout files.

REWRITE 2 (2026-09-01): now matched byte-for-byte against a real reference,
  C:\\Program Files (x86)\\QCADesigner\\share\\QCADesigner\\qca_cell_library\\sample.qca
(the file QCADesigner 2.0.3 ships). The earlier guesses were wrong in three
ways that stopped the file loading:
  * the cell layer must be  type=1  (not 0), and no substrate layer is needed
  * every [TYPE:QCADDesignObject] needs  bSelected=FALSE  +  clr.red/green/blue
    and must NOT carry bare cxWorld=/cyWorld= lines
  * dot offset is 4.5 nm (not 6.4); dot spin/potential print as plain
    0.000000 while charge prints in exponential form
  * a cell label is  psz=<name>  with no bLabelActive line

Geometry: 18 nm cells, 5 nm dots, 20 nm pitch. y increases downward.
Dot order 0..3 = TR, BR, BL, TL. Clock zones 0..3 = Switch/Hold/Release/Relax.
"""

CELL = 18.0
DOT_D = 5.0
DOT_OFF = 4.5
PITCH = 20.0
E = 1.602176e-19
HALF_E = 8.010880e-20            # e/2 : polarisation-0 dot charge

_FUNC = {
    "normal": "QCAD_CELL_NORMAL",
    "input": "QCAD_CELL_INPUT",
    "output": "QCAD_CELL_OUTPUT",
    "fixed": "QCAD_CELL_FIXED",
}
_CLR = {                          # (red, green, blue) 16-bit, cosmetic only
    "normal": (0, 65535, 0),
    "input": (0, 0, 65535),
    "output": (65535, 65535, 0),
    "fixed": (65535, 32768, 0),
}


def _design_object(x, y, clr, cx=CELL, cy=CELL):
    r, g, b = clr
    return (
        "[TYPE:QCADDesignObject]\n"
        f"x={x:.6f}\n"
        f"y={y:.6f}\n"
        "bSelected=FALSE\n"
        f"clr.red={r}\n"
        f"clr.green={g}\n"
        f"clr.blue={b}\n"
        f"bounding_box.xWorld={x - cx / 2:.6f}\n"
        f"bounding_box.yWorld={y - cy / 2:.6f}\n"
        f"bounding_box.cxWorld={cx:.6f}\n"
        f"bounding_box.cyWorld={cy:.6f}\n"
        "[#TYPE:QCADDesignObject]\n"
    )


def _dot(x, y, charge):
    return (
        "[TYPE:CELL_DOT]\n"
        f"x={x:.6f}\n"
        f"y={y:.6f}\n"
        f"diameter={DOT_D:.6f}\n"
        f"charge={charge:.6e}\n"
        "spin=0.000000\n"
        "potential=0.000000\n"
        "[#TYPE:CELL_DOT]\n"
    )


def _label(x, y, clr, psz):
    return (
        "[TYPE:QCADLabel]\n"
        "[TYPE:QCADStretchyObject]\n"
        + _design_object(x, y, clr, cx=14.0, cy=23.0)
        + "[#TYPE:QCADStretchyObject]\n"
        f"psz={psz}\n"
        "[#TYPE:QCADLabel]\n"
    )


def cell(x, y, clock=0, function="normal", name=None, pol=1):
    """One QCADCell block. function: normal|input|output|fixed.
    pol only used for 'fixed' (+1 => logic 1, -1 => logic 0)."""
    if function == "fixed":
        charges = [E, 0.0, E, 0.0] if pol >= 0 else [0.0, E, 0.0, E]
    else:
        charges = [HALF_E, HALF_E, HALF_E, HALF_E]
    dpos = [
        (DOT_OFF, -DOT_OFF),   # 0 top-right
        (DOT_OFF, DOT_OFF),    # 1 bottom-right
        (-DOT_OFF, DOT_OFF),   # 2 bottom-left
        (-DOT_OFF, -DOT_OFF),  # 3 top-left
    ]
    clr = _CLR[function]
    s = "[TYPE:QCADCell]\n"
    s += _design_object(x, y, clr)
    s += (
        f"cell_options.cxCell={CELL:.6f}\n"
        f"cell_options.cyCell={CELL:.6f}\n"
        f"cell_options.dot_diameter={DOT_D:.6f}\n"
        f"cell_options.clock={clock}\n"
        "cell_options.mode=QCAD_CELL_MODE_NORMAL\n"
        f"cell_function={_FUNC[function]}\n"
        "number_of_dots=4\n"
    )
    for (dx, dy), q in zip(dpos, charges):
        s += _dot(x + dx, y + dy, q)
    if function in ("input", "output") and name:
        s += _label(x - 2.0, y - 10.5, clr, name)
    s += "[#TYPE:QCADCell]\n"
    return s


_PRIORITY = {"normal": 0, "fixed": 1, "output": 2, "input": 3}


class Layout:
    def __init__(self):
        self.cells = []           # list of (x, y, block_str)
        self._at = {}             # (rx, ry) -> index into self.cells
        self._meta = {}           # (rx, ry) -> (function, clock)

    def add(self, x, y, clock=0, function="normal", name=None, pol=1):
        key = (round(x, 3), round(y, 3))
        block = cell(x, y, clock, function, name, pol)
        if key in self._at:
            # a cell already occupies this spot: keep the more specific one
            old_fn, _ = self._meta[key]
            if _PRIORITY[function] > _PRIORITY[old_fn]:
                self.cells[self._at[key]] = (x, y, block)
                self._meta[key] = (function, clock)
            return key
        self._at[key] = len(self.cells)
        self._meta[key] = (function, clock)
        self.cells.append((x, y, block))
        return (x, y)

    def hwire(self, x0, x1, y, clock, function="normal"):
        step = PITCH if x1 >= x0 else -PITCH
        x = x0
        while (step > 0 and x <= x1 + 1e-6) or (step < 0 and x >= x1 - 1e-6):
            self.add(x, y, clock, function)
            x += step

    def vwire(self, x, y0, y1, clock, function="normal"):
        step = PITCH if y1 >= y0 else -PITCH
        y = y0
        while (step > 0 and y <= y1 + 1e-6) or (step < 0 and y >= y1 - 1e-6):
            self.add(x, y, clock, function)
            y += step

    def render(self):
        out = "[VERSION]\nqcadesigner_version=2.000000\n[#VERSION]\n"
        out += "[TYPE:DESIGN]\n"
        out += "[TYPE:QCADLayer]\n"
        out += "type=1\nstatus=0\npszDescription=Main Cell Layer\n"
        for _, _, block in self.cells:
            out += block
        out += "[#TYPE:QCADLayer]\n"
        out += "[#TYPE:DESIGN]\n"
        return out

    def write(self, path):
        with open(path, "w", newline="\n") as f:
            f.write(self.render())
        print(f"wrote {path}  ({len(self.cells)} cells)")

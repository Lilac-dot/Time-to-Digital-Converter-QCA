#!/usr/bin/env python3
"""
build.py - generate draft .qca layouts for the QCA-TDC reproduction.

Run:  python build.py    (then  python preview.py  for PNGs)

Open in QCADesigner 2.0.3. For 01-03: Simulation -> coherence-vector engine
-> "Exhaustive Verification". For 04-06: a "Single" run with a four-phase
clock on CLK and a hand-drawn pattern on D; watch Q.

CONFIDENCE (see README.md):
  01 majority gate ... HIGH   - canonical 5-cell gate
  02 wire+inverter ... HIGH   - zone-crossing wire + single-corner inverter
  03 mux 2:1 ......... MEDIUM - hand-placed, >=2-cell spacing between nets
  04 mux D-latch ..... MEDIUM - 03 + Q->AND1.N feedback loop; loop = 4 zone
                               transitions = exactly one clock period (needed
                               for a stable hold)
  05 edge converter .. MEDIUM - EDGE = CLK . !CLK(t-1). Delay loop is 7 zone
                               transitions vs the direct path's 3, i.e. the
                               "!CLK(t-1)" input lags by 4 transitions = one
                               full clock period, as required. Still needs an
                               in-tool check of coplanar coupling, the corner
                               inverter, and rising-edge alignment.
  06 DFF ............. MEDIUM - 05 feeding the 04 latch select; same caveats

CLOCK ZONE vs CLOCK PHASE (they are different things):
  * A clock ZONE is a group of cells, tagged clock = 0/1/2/3 in QCADesigner.
    preview.py colours them green / red / blue / gold. Signal flows forward
    0 -> 1 -> 2 -> 3 -> 0, one zone per quarter period; crossing all four
    zones costs one full clock period.  <-- the fact 05's delay loop uses.
  * A clock PHASE is Switch -> Hold -> Release -> Relax, the sequence EVERY
    zone runs through EVERY period. The four zones are staggered 90 deg, so at
    any instant they are each in a different phase: while zone N is in Hold
    (driving) zone N+1 is in Switch (latching zone N's value).
  So "zone 0" is NOT "the Switch zone" - zone 0 is in Switch for one quarter,
  Hold the next, and so on.

WHAT 05/06 ACTUALLY DO: the converter turns a rising LEVEL TRANSITION on CLK
(0 -> 1, then held) into a single pulse one clock period wide. On a free-
running periodic clock CLK . !CLK(t-1) would cancel to 0; the TDC uses it on
the one-shot sampling path, where CLK is a level, not a square wave.

Grid unit P = 20 nm. Coordinates are (col,row); row increases DOWNWARD.
Majority gate at (c,r): device (c,r), terminals N(c,r-1) E(c+1,r) S(c,r+1)
W(c-1,r). Rule of thumb kept here: cells of different nets stay >= 2 grid
steps apart unless they are the 4 terminals of the same gate.
"""
from qca_gen import Layout, PITCH

P = PITCH


def g(k):
    return k * P


# ---------------------------------------------------------------------------
def majority_gate():
    L = Layout()
    L.add(0, 0, 0, "normal")
    L.add(-P, 0, 0, "input", name="A")
    L.add(0, -P, 0, "input", name="B")
    L.add(0, P, 0, "input", name="C")
    L.add(P, 0, 0, "output", name="OUT")
    L.write("01_majority_gate.qca")


# ---------------------------------------------------------------------------
def wire_inverter():
    L = Layout()
    L.add(g(0), 0, 0, "input", name="IN_W")
    L.hwire(g(1), g(5), 0, 0)
    L.add(g(6), 0, 0, "output", name="OUT_W")

    y = g(6)
    L.add(g(0), y, 0, "input", name="IN_I")
    L.add(g(1), y, 0, "normal")
    L.add(g(2), y + P, 0, "normal")          # diagonal / corner -> NOT
    L.add(g(3), y + P, 0, "output", name="NOT_I")
    L.write("02_wire_inverter.qca")


# ---------------------------------------------------------------------------
def _mg(L, c, r, zone):
    L.add(g(c), g(r), zone, "normal")
    L.add(g(c), g(r - 1), zone, "normal")    # N
    L.add(g(c + 1), g(r), zone, "normal")    # E
    L.add(g(c), g(r + 1), zone, "normal")    # S
    L.add(g(c - 1), g(r), zone, "normal")    # W


def _fix(L, c, r, zone, logic):
    L.add(g(c), g(r), zone, "fixed", pol=(1 if logic else -1))


def _run(L, pts, zones):
    """place normal cells at each (col,row) in pts; zones list left-to-right,
    last entry repeats."""
    for i, (c, r) in enumerate(pts):
        L.add(g(c), g(r), zones[min(i, len(zones) - 1)], "normal")


# ---------------------------------------------------------------------------
def mux_2to1(name="03_mux2to1.qca", dlatch=False, oc=0, sel_input=True,
             sel_name=None, L=None):
    """OUT = MAJ( MAJ(inA,!sel,0), MAJ(inB,sel,0), 1 )
    plain MUX: inA=I0  inB=I1  sel=S
    D-latch  : inA=Qfb inB=D   sel=CLK   (transparent when CLK=1)

    oc          - column offset (grid steps) applied to every cell, so the
                  block can be dropped next to another one (used by dff()).
    sel_input   - True: place the select cell as a labelled INPUT.
                  False: place it as a plain wire cell, so the caller can
                  drive the select net from elsewhere (dff() feeds EDGE in).
    sel_name    - label for the select input (default "CLK" latch / "S" mux).
    L           - reuse an existing Layout instead of making one; when given,
                  the file is NOT written here (caller does it)."""
    own = L is None
    if own:
        L = Layout()
    if sel_name is None:
        sel_name = "CLK" if dlatch else "S"

    # local wrappers that shift every column by `oc` grid steps
    def MG(c, r, z):
        _mg(L, c + oc, r, z)

    def FIX(c, r, z, lg):
        _fix(L, c + oc, r, z, lg)

    def RUN(pts, zs):
        _run(L, [(c + oc, r) for (c, r) in pts], zs)

    def ADD(c, r, z, fn, name=None, pol=1):
        L.add(g(c + oc), g(r), z, fn, name, pol)

    # ---- three majority gates (well separated) ----
    MG(4, 4, 1)            # AND1  device (4,4)   out E=(5,4)
    MG(4, 12, 1)           # AND2  device (4,12)  out E=(5,12)
    MG(12, 8, 2)           # OR    device (12,8)  out E=(13,8)
    FIX(4, 5, 1, 0)        # AND1.S = 0
    FIX(4, 11, 1, 0)       # AND2.N = 0
    FIX(11, 8, 2, 1)       # OR.W  = 1

    # ---- select input + inverter ----
    ADD(0, 8, 0, "input" if sel_input else "normal",
        name=(sel_name if sel_input else None))
    RUN([(0, 8), (1, 8), (2, 8)], [0])                     # sel bus, row 8
    # up branch -> !sel into AND1.W  (single-corner inverter at (2,5)->(3,4))
    RUN([(2, 7), (2, 6), (2, 5)], [0])
    ADD(3, 4, 1, "normal")                                 # corner => !sel = AND1.W
    # down branch -> sel straight into AND2.W
    RUN([(2, 9), (2, 10), (2, 11), (2, 12)], [0, 0, 0, 1])
    ADD(3, 12, 1, "normal")                                # AND2.W

    # ---- inA --> AND1.N (4,3) ----
    if dlatch:
        pass                                              # feedback added below
    else:
        ADD(4, 0, 0, "input", name="I0")
        RUN([(4, 1), (4, 2)], [0, 1])                      # -> AND1.N (4,3)

    # ---- inB --> AND2.S (4,13) from below ----
    ADD(4, 16, 0, "input", name=("D" if dlatch else "I1"))
    RUN([(4, 15), (4, 14)], [0, 1])                        # -> AND2.S (4,13)

    # ---- AND1.E (5,4) --> OR.N (12,7) ----
    RUN([(6, 4), (7, 4), (8, 4), (9, 4), (10, 4), (11, 4), (12, 4),
         (12, 5), (12, 6)], [1, 1, 1, 2])                  # -> OR.N (12,7)

    # ---- AND2.E (5,12) --> OR.S (12,9) ----
    RUN([(6, 12), (7, 12), (8, 12), (9, 12), (10, 12), (11, 12), (12, 12),
         (12, 11), (12, 10)], [1, 1, 1, 2])                # -> OR.S (12,9)

    # ---- OUT ----
    ADD(14, 8, 3, "normal")                                # OR.E is (13,8)
    ADD(15, 8, 3, "output", name=("Q" if dlatch else "OUT"))

    # ---- D-latch feedback: Q -> AND1.N ----
    if dlatch:
        # go far right of OUT, up, left across an empty row, down into AND1.N
        RUN([(16, 8), (16, 7), (16, 6), (16, 5), (16, 4), (16, 3),
             (16, 2), (16, 1), (16, 0), (16, -1)], [3])
        RUN([(15, -1), (14, -1), (13, -1), (12, -1), (11, -1), (10, -1),
             (9, -1), (8, -1), (7, -1), (6, -1), (5, -1), (4, -1)],
            [3, 3, 3, 3, 0])
        RUN([(4, 0), (4, 1), (4, 2)], [0, 0, 1])           # -> AND1.N (4,3)

    if own:
        L.write(name)
    return L


# ---------------------------------------------------------------------------
def _edge_conv(L, oc=0, place_clk=True, clk_name="CLK", out_name="EDGE"):
    """Level-to-edge converter  (paper Fig 5, eq 3, section III-B).

        EDGE = CLK . !CLK(t-1)     <- one-period pulse at a rising transition

    One AND gate MAJ(a, b, 0):
        a = CLK via the short 'direct' path  (3 zone transitions, into AND.N)
        b = CLK via the 'delay loop' (7 zone transitions) then inverted by the
            corner cell into AND.S
    b therefore lags a by 7 - 3 = 4 zone transitions = exactly one clock
    period, so b carries !CLK as it was one period ago. When CLK has just
    risen (1 now, 0 one period ago) EDGE = 1; it stays 1 for one clock period
    then falls. On a periodic square-wave CLK this expression is identically
    0 - the circuit is meant for the one-shot sampling path where CLK is a
    level that goes high and stays.

    Returns (col, row) grid coords of the EDGE node (already includes oc) so a
    caller can keep routing from it (dff() does).  If out_name is None the
    EDGE node is left as a plain wire cell instead of a labelled OUTPUT.

    CONFIDENCE MEDIUM: the one-period lag is set correctly by the zone counts
    above; still verify coplanar coupling, the corner inverter, and that the
    pulse lands cleanly inside one delay-line-stable period (README step 4)."""
    def MG(c, r, z):
        _mg(L, c + oc, r, z)

    def FIX(c, r, z, lg):
        _fix(L, c + oc, r, z, lg)

    def RUN(pts, zs):
        _run(L, [(c + oc, r) for (c, r) in pts], zs)

    def ADD(c, r, z, fn, name=None):
        L.add(g(c + oc), g(r), z, fn, name)

    # ---- AND gate  MAJ(N, S, W=0)  device (6,8) ----
    MG(6, 8, 3)                 # N=(6,7) S=(6,9) E=(7,8) W=(5,8)
    FIX(5, 8, 3, 0)             # W = const 0  =>  MAJ acts as AND(N, S)

    # ---- CLK input ----
    ADD(6, 4, 0, "input" if place_clk else "normal",
        name=(clk_name if place_clk else None))

    # ---- direct path: CLK -> AND.N  (3 zone transitions: z0->z1->z2->z3) ----
    RUN([(6, 5), (6, 6)], [1, 2])                       # -> N=(6,7) [zone 3]

    # ---- delay loop: CLK -> one full period later -> invert -> AND.S ----
    #   7 zone transitions (0->1->2->3->0->1->2->3); 7 - 3 = 4 = one period
    RUN([(6, 3), (5, 3), (4, 3), (3, 3),
         (3, 4), (3, 5), (3, 6), (3, 7), (3, 8), (3, 9), (3, 10), (3, 11),
         (4, 11), (5, 11), (6, 11), (7, 11), (7, 10)],
        [0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 0, 0, 1, 1, 2, 2, 3])
    #                       ^ (7,10) sits diagonally off S=(6,9): corner
    #                         coupling inverts it  => AND.S = !CLK(t-1)

    # ---- EDGE output: AND.E=(7,8) -> (8,8) -> (9,8) ----
    ADD(8, 8, 0, "normal")
    ADD(9, 8, 0, "output" if out_name else "normal", name=out_name)
    return (9 + oc, 8)


def edge_converter():
    L = Layout()
    _edge_conv(L)
    L.write("05_edge_converter.qca")


# ---------------------------------------------------------------------------
def dff():
    """Rising-edge D flip-flop  (paper Fig 5 / Fig 6a).

    = the 04 MUX-based D-latch, but its SELECT is driven by EDGE from the 05
    level-to-edge converter instead of the raw clock.  EDGE is high for one
    clock period at the rising transition, so the latch is transparent for
    that one period and holds the rest of the time => Q samples D once, at
    the rising edge.  (Not a sub-period window - see _edge_conv: clocked QCA
    cannot make two recombining paths differ by less than one full period.)

        CLK --[05 edge conv]--> EDGE --> sel of [04 mux latch] ;  D --> Q

    CONFIDENCE MEDIUM: inherits the 04 feedback-loop and 05 coplanar caveats.
    Verify in QCADesigner that Q updates exactly once per period and that the
    one-period EDGE window sits inside a single stable value of D."""
    L = Layout()
    ex, ey = _edge_conv(L, out_name=None)          # EDGE node at (9, 8)
    OM = 13                                        # mux/latch column offset
    mux_2to1(dlatch=True, oc=OM, sel_input=False, sel_name="EDGE", L=L)
    # EDGE (9,8) -> mux select bus entry (0,8)+OM = (13,8)
    _run(L, [(c, 8) for c in range(ex + 1, OM)], [0])
    L.write("06_dff.qca")


if __name__ == "__main__":
    majority_gate()
    wire_inverter()
    mux_2to1()
    mux_2to1(name="04_dlatch_mux.qca", dlatch=True)
    edge_converter()
    dff()
    print("done - open 01_majority_gate.qca first, then run: python preview.py")

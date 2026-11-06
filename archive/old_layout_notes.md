# QCA-TDC layouts

**Simulation status (see `../simulation/RESULTS.md`).** The sections below are the
original notes on the generated drafts. Since then every layout has been simulated:

| File | Result |
|---|---|
| `01_majority_gate`, `02_wire_inverter` | correct |
| `03_mux2to1`, `04_dlatch_mux`, `05_edge_converter`, `06_dff` | **fail**: output stuck, kept for reference only |
| `07_conventional_tdc` (paper Fig. 1b) | correct |
| `08_mux2to1_fig2c` (paper Fig. 2c) | correct: use this mux |

---

Draft `.qca` layouts for reproducing Modanlou & Gholami, *"A High-Performance
Time-to-Digital Converter in QCA Technology Employing a Low-Power D Flip-Flop"*
(IEEE Access, 2025).

These were generated **without access to QCADesigner**, from the documented
2.0.3 file format plus standard QCA gate constructions. So there are two
separate things to verify: (1) do the files *load*, (2) do the circuits
*simulate correctly*. Do them in order.

## Files

| File | What | Confidence | Verify with |
|---|---|---|---|
| `01_majority_gate.qca` | 3-input majority gate, all clock zone 0 | HIGH topology | Exhaustive Verification: `OUT = AB+AC+BC` |
| `02_wire_inverter.qca` | 7-cell wire + single-corner inverter | HIGH topology | `OUT_W = IN_W`, `NOT_I = !IN_I` |
| `03_mux2to1.qca` | 2:1 MUX = `OR(AND(I0,!S), AND(I1,S))`, 3 majority gates, zones 0→3 | MEDIUM | Exhaustive Verification: `OUT = S?I1:I0` |
| `04_dlatch_mux.qca` | MUX-based D-latch `Q = CLK·D + !CLK·Q` (paper Fig 4) | MEDIUM | 4-phase clock; Q follows D when CLK=1, holds when CLK=0 |
| `05_edge_converter.qca` | level-to-edge converter `EDGE = CLK·!CLK(t-1)` (paper Fig 5, eq 3) | MEDIUM | step CLK (rise and hold); EDGE = one pulse, one clock period wide, at the rise |
| `06_dff.qca` | rising-edge DFF = `04` latch with select driven by `05` EDGE (paper Fig 5/6a) | MEDIUM | Q samples D once per clock period, at the rising edge |

`qca_gen.py` — the file-format writer. `build.py` — circuit definitions
(edit + `python build.py` to regenerate). `preview.py` — renders each `.qca`
to a `.png` coloured by clock zone (no QCADesigner needed).

## Step 1 — does the format load?  (verified 2026-09-01)

The writer (`qca_gen.py`) was matched byte-for-byte against the reference
file QCADesigner ships,
`C:\Program Files (x86)\QCADesigner\share\QCADesigner\qca_cell_library\sample.qca`,
and every generated file now parses cleanly in QCADesigner's own engine:

```
"C:\Program Files (x86)\QCADesigner\bin\batch_sim.exe" -f 01_majority_gate.qca -e BISTABLE -o <opts> -n 1 -t 2
  -> "File opened in 0.00 seconds"
```

for `01`–`06`. Just open `01_majority_gate.qca` in the QCADesigner GUI to
confirm it draws (5 cells in a plus, A/B/C inputs + OUT).

Earlier versions would not open because the writer emitted a broken layer
tree (`type=0` cell layer + a stray substrate object under `[TYPE:DESIGN]`).
Fixed: single `type=1` "Main Cell Layer", every design object carries
`bSelected` + `clr.*`, dot offset 4.5 nm, dot `spin`/`potential` printed as
plain `0.000000`.

## Clock zone vs clock phase

Two different things, easy to conflate:

- A **clock zone** is a group of cells (`clock = 0/1/2/3` in QCADesigner;
  `preview.py` colours them green / red / blue / gold). Data flows forward
  `0 → 1 → 2 → 3 → 0`, one zone per quarter period. Crossing all four zones
  costs one full clock period — this is what `05`'s delay loop uses.
- A **clock phase** is `Switch → Hold → Release → Relax`, the cycle *every*
  zone runs through *every* period. The zones are staggered 90°, so at any
  instant the four zones are each in a different phase: while zone N is in
  Hold (driving), zone N+1 is in Switch (latching zone N's value).

So "zone 0" is not "the Switch zone" — it is in Switch for one quarter, Hold
the next, and so on.

## Step 2 — simulation settings (match the paper)

Simulation → Simulation Type Setup:
- Engine: **Coherence Vector** (the paper uses this), default parameters
- `01`–`03`: **Exhaustive Verification** (auto-sweeps all input combinations)
- `04`–`06`: **Single** run, draw a four-phase clock on CLK and a test
  pattern on D

For energy numbers later, use **QCADesigner-E** with the same layout and
sweep the kink-energy factor (0.5 / 1.0 / 1.5 Eₖ) to reproduce the paper's
Table 3.

## Step 3 — likely fixes for 03 / 04

Coplanar QCA routing is easy to get wrong without the tool's design-rule
check. If a block fails verification, check these first:

1. **Inverter** — `03`/`04` use a minimal single-corner inverter (one cell
   placed diagonally so only corners touch). If `OUT` comes out *non*-inverted
   (i.e. the MUX selects the wrong input, or the latch is transparent on the
   wrong CLK level), replace it with a robust inverter: split the signal into
   two parallel wires and rejoin them at a cell they both touch on adjacent
   corners.
2. **Clock zones** — signal must flow 0→1→2→3→0. In `03` the two AND gates are
   zone 1, the OR gate zone 2, output zone 3, inputs zone 0. If a gate reads a
   stale value, nudge the feed-wire zone boundaries.
3. **`04` feedback loop** — `Q` routes back to the AND1 north terminal around
   the top of the layout. The loop delay must be an integer number of clock
   periods or the latch won't hold. If Q oscillates or won't latch, adjust how
   many zone steps the feedback wire takes (currently 3→0→1). Add or remove
   cells on that wire one at a time.
4. **Spacing** — the generator keeps unrelated nets ≥2 grid cells (40 nm)
   apart. QCADesigner's default radius-of-effect is 65 nm, so a couple of
   spots may still couple. If an output is noisy, spread the offending wire
   out by one more cell.

## Step 4 — verify 05 / 06 in-tool

`05` and `06` are generated by `build.py`. The clock-zone counts are already
set so the delay loop lags the direct path by exactly one clock period (see
below); what still needs the GUI is coplanar coupling, the corner inverter,
and pulse alignment.

### 05 — level-to-edge converter (paper Fig 5, eq. 3, §III-B)

`EDGE = CLK · !CLK(t-1)`. Text of §III-B: "the converter processes both the
current clock signal and the inverted previous clock state through an AND
gate, generating an output exclusively during the rising edge."

- `MAJ(a, b, 0)` AND gate:
  - **a** = `CLK` via the direct path into `AND.N` — **3 zone transitions**
    (`z0→z1→z2→z3`).
  - **b** = `CLK` around the delay loop into `AND.S` via a corner inverter —
    **7 zone transitions** (`0→1→2→3→0→1→2→3`), then negated ⇒ `!CLK(t-1)`.
- `7 − 3 = 4` transitions = **one full clock period**, which is the minimum
  achievable: two paths that recombine at one majority gate must both arrive
  in the gate's own zone, so their delays can only differ by a whole number
  of periods. The loop zone list is
  `[0,0,0,0,1,1,2,2,3,3,0,0,1,1,2,2,3]` in `_edge_conv()`; change it only if
  the GUI waveform shows the lag is off.
- Because the lag is a full period, `CLK · !CLK(t-1)` is `0` for a
  free-running square wave. This block is for the **one-shot sampling path**:
  `CLK` is a level that rises once and stays, and `EDGE` is then a single
  pulse **one clock period wide** at that rising transition.

### 06 — D flip-flop

`05` feeding the **select** of the `04` MUX-latch instead of the raw clock,
so the latch is transparent for that one-period `EDGE` window ⇒ samples `D`
once at the rising edge. `build.py`: `_edge_conv()` at column 0,
`mux_2to1(dlatch=True, oc=13, sel_input=False)` to its right, `EDGE` wired
along row 8 into the select bus. Verify `Q` updates once per period, and that
the one-period `EDGE` window sits inside a single stable value of `D` (each
delay-line stage only changes at period boundaries, so this should hold once
the pulse is aligned).

## Then — the full TDC

Delay line = N identical delay stages, each spanning all four clock zones
(one clock period of delay per stage). START propagates down the line;
on STOP, each stage's `06` DFF samples the line → thermometer code. The paper
stops there (187 cells, 0.18 µm²). Your `paper.txt` has the full text; the
gaps worth publishing on are in the project memory / the earlier plan
(missing thermometer-to-binary encoder, real DNL/INL code-density test,
defect tolerance, or a Vernier QCA TDC).

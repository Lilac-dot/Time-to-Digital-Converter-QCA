# Archive: layouts that do not work

Kept for reference. None of these pass simulation; see `../simulation/RESULTS.md`.

| File | Problem |
|---|---|
| `03_mux2to1.qca` | Output stuck |
| `04_dlatch_mux.qca` | Output stuck |
| `05_edge_converter.qca` | Output stuck |
| `06_dff.qca` | Output stuck |
| `09_proposed_tdc.qca` | Authors' Fig. 3(b): does not reproduce their Fig. 8(a) |
| `TDC-final.qca` | Hand-built copy of Fig. 3(b), same fault, plus one stray cell at x=440, y=640 |

`09_proposed_tdc_fig8.vt` and `TDC-final.vt` are their vector tables. `build.py` generates
`01`-`06`, and `old_layout_notes.md` holds the original notes on those drafts.

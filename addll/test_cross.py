#!/usr/bin/env python3
"""Two wires crossing on three layers. Each output must follow only its own input."""
import itertools, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "simulation"))
from qca_ml import ML
from qca_tools import peak_per_period
from qde_tools import run_qde

def build(p, hz=(0,0,1,1,2,2,3,3,0), vz=(0,0,1,1,2,2,3,3,0), gap=2):
    L = ML()
    # horizontal A on the main layer through (5,c); vertical B climbs over it
    L.add(5,0,0,"input",name="A")
    L.wire([(5,1),(5,8)], list(hz[1:]))
    L.add(5,9,0,"output",name="XA")
    L.add(0,5,0,"input",name="B")
    z=[0,1,1]                 # r=1,2,3 on main
    L.wire([(1,5),(3,5)], z)
    L.via(3,5,1)
    L.wire([(3,5),(7,5)], [1,2,2,2,2], layer=2)
    L.via(7,5,2)
    L.wire([(7,5),(9,5)], [2,3,3])
    L.add(10,5,3,"output",name="XB")
    return L.write(p)

p = build("/tmp/x.qca") if 0 else build(sys.argv[1] if len(sys.argv)>1 else "cross.qca")
rows=[v for v in itertools.product([0,1],repeat=2) for _ in range(3)]
for eng,kw in [("energy",{}),("energy",{"radius_of_effect":65}),("cv",{"radius_of_effect":65}),("cv",{"radius_of_effect":80})]:
    c,e,log=run_qde(p,["A","B"],rows,engine=eng,**kw) if eng=="cv" else run_qde(p,["A","B"],rows,**kw)
    a=peak_per_period(c["t_ps"],c["XA"],n=len(rows)); b=peak_per_period(c["t_ps"],c["XB"],n=len(rows))
    print(eng,kw,[int(x>0) for x in a[2::3]],[int(x>0) for x in b[2::3]],[round(float(x),2) for x in b[2::3]],min(abs(a[3:]).min(),abs(b[3:]).min()).round(3))

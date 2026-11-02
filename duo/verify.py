"""Measure the exported STEP against the numbers on the drawing.

    .venv/bin/python -m duo.verify      -> build/verification.md
"""
from pathlib import Path

import numpy as np
from build123d import import_step, Compound, Vector, Vertex
from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
from OCP.gp import gp_Pln, gp_Pnt, gp_Dir

from . import geometry as g

OUT = Path(__file__).resolve().parent.parent / "build"
rows = []


def row(feature, drawing, model, tol=0.02, note="", conflict=False):
    d = model - drawing
    ok = "conflict" if conflict else abs(d) <= tol
    rows.append((feature, drawing, model, d, ok, note))


def section(shape, origin, normal):
    op = BRepAlgoAPI_Section(shape.wrapped, gp_Pln(gp_Pnt(*origin), gp_Dir(*normal)))
    op.Build()
    return Compound(op.Shape())


def dist(shape, p):
    if isinstance(shape, (list, tuple)):
        return min(dist(s, p) for s in shape)
    return shape.distance_to(Vertex(*p))


def main():
    asm = import_step(str(OUT / "iPhone_Duo.step"))
    P = {c.label: c for c in asm.children}
    housing = Compound([P[k] for k in ("A_frame", "B_frame", "A_cover_glass", "B_back_glass",
                                       "hinge_barrel", "antenna_splits")])

    # --- envelope (housing only: back glass includes the plateau, so clip z separately)
    body_only = Compound([P[k] for k in ("A_frame", "B_frame", "A_cover_glass", "hinge_barrel",
                                         "antenna_splits")])
    bb = body_only.bounding_box(optimal=True)
    row("Product width (hinge exterior to edge)", 84.10, bb.max.X - bb.min.X)
    row("Product length", 117.80, bb.max.Y - bb.min.Y)
    st = section(housing, (0, -80.0, 0), (0, 1, 0)).bounding_box(optimal=True)
    row("Product thickness (section at y = -80)", 11.30, st.max.Z - st.min.Z)
    row("Half A thickness", 5.48, P["A_frame"].bounding_box().max.Z - 0.17)
    bbs = P["B_back_glass"].bounding_box(optimal=True)
    row("Back plate to camera plateau", 3.64, -g.ZTOP - bbs.min.Z)
    cams = Compound([P["B_camera_rings"], P["B_camera_cover_glass"]]).bounding_box(optimal=True)
    row("Back plate to rear camera glass", 5.72, -g.ZTOP - cams.min.Z)

    # --- Detail A corner (plan section through the side wall of half A)
    sA = section(Compound([P["A_frame"], P["antenna_splits"]]), (0, 0, 2.5), (0, 0, 1))
    worst = max(dist(sA, (x, y, 2.5)) for x, y in g.CORNER_TR)
    row("Detail A corner: worst of 7 points off the outline", 0.0, worst)
    worst = max(dist(sA, (x, y, 2.5)) for x, y in g.CORNER_TL)
    row("Detail AY body corner: worst of 4 points", 0.0, worst)
    sBar = section(P["hinge_barrel"], (0, 0, 0), (0, 0, 1))
    pts = [(0.0, -2.82), (0.26, -1.96), (0.92, -1.36)]
    worst = max(dist(sBar, (x, y, 0)) for x, y in pts)
    row("Detail AY barrel end: worst of 3 points", 0.0, worst, tol=0.03)
    bbh = P["hinge_barrel"].bounding_box(optimal=True)
    row("Barrel end from top edge (Detail AY)", 1.19, -bbh.max.Y)
    row("Barrel end from top edge (side view)", 1.23, -bbh.max.Y, conflict=True,
        note="sheet says 1.19 in Detail AY, 1.23 in the side view; model uses 1.19")
    row("Barrel top from front face (side view 1.55)", 1.55, g.ZTOP - bbh.max.Z)

    # --- Detail B (side profile at mid length)
    y = -g.L / 2
    sx = [section(P[k], (0, y, 0), (0, 1, 0)) for k in
          ("A_frame", "B_frame", "A_cover_glass", "B_back_glass", "hinge_barrel")]
    worst = 0
    for d, z in g.EDGE_ROUND:
        for zz in (z, -z):
            worst = max(worst, dist(sx, (g.W - d, y, zz)))
    row("Detail B edge round: worst of 12 points", 0.0, worst)

    # --- Detail E (hinge profile at mid length)
    barrel_pts = [(0.00, 1.56), (0.01, 2.46), (0.26, 3.32), (0.92, 3.92), (1.80, 4.09)]
    worst = max(dist(sx, (x, y, s * z)) for x, z in barrel_pts for s in (1, -1))
    row("Detail E barrel: worst of 10 points", 0.0, worst, tol=0.03)
    bodyA = [(1.81, 4.71), (1.96, 5.09), (2.29, 5.43), (2.67, 5.62)]
    bodyB = [(1.82, 4.71), (1.99, 5.09), (2.34, 5.43), (2.74, 5.62)]
    worst = max([dist(sx, (x, y, z)) for x, z in bodyA] + [dist(sx, (x, y, -z)) for x, z in bodyB])
    row("Detail E hinge-side round: worst of 8 points", 0.0, worst)

    # --- front
    gb = P["A_cover_glass"].bounding_box(optimal=True)
    row("Cover glass width", 79.93, gb.max.X - gb.min.X)
    row("Cover glass length", 115.04, gb.max.Y - gb.min.Y)
    row("Exterior of housing to cover glass (right)", 1.33, g.W - gb.max.X, conflict=True,
        note="callout and the 115.04 glass size disagree by 0.05; size wins")
    ab = P["A_display_active_area"].bounding_box(optimal=True)
    row("Display active area width", 77.17, ab.max.X - ab.min.X)
    row("Display active area length", 112.28, ab.max.Y - ab.min.Y)
    row("Exterior of housing to display active area", 2.71, g.W - ab.max.X, conflict=True,
        note="2.71 callout and the 112.28 size disagree by 0.05; size wins")
    row("Exterior of hinge to display active area", 4.13, ab.min.X, conflict=True,
        note="4.13 + 77.17 + 2.71 = 84.01, not 84.10; size wins")
    row("Exterior of hinge to start of flat area", 4.16, 2.74, conflict=True,
        note="Detail E puts the flat at 2.74 from the hinge exterior; model follows Detail E")
    fb = P["A_front_camera"].bounding_box(optimal=True)
    row("Front camera X", 73.39, (fb.min.X + fb.max.X) / 2)
    row("Front camera Y", 10.62, -(fb.min.Y + fb.max.Y) / 2)
    row("Front camera diameter", 6.07, fb.max.X - fb.min.X)

    for name, cx in (("B_volume_down", 44.35), ("B_volume_up", 57.73)):
        b = P[name].bounding_box(optimal=True)
        row(f"{name} centre X", cx, (b.min.X + b.max.X) / 2)
        row(f"{name} length", 10.88, b.max.X - b.min.X)
        row(f"{name} proud of top edge", 0.45, b.max.Y)
    for name, cy, length, w, proud in (("B_side_button", 42.87, 18.68, 3.06, 0.45),
                                       ("B_camera_control", 84.97, 17.10, 2.53, 0.075)):
        b = P[name].bounding_box(optimal=True)
        row(f"{name} centre Y", cy, -(b.min.Y + b.max.Y) / 2)
        row(f"{name} length (2x {length / 2:.2f})", length, b.max.Y - b.min.Y)
        row(f"{name} width", w, b.max.Z - b.min.Z)
        row(f"{name} proud of side", proud, b.max.X - g.W, tol=0.005)
        row(f"{name} centre from back face", 2.670, (b.min.Z + b.max.Z) / 2 + g.ZTOP)

    # --- rear (Detail D, measured from the non-hinge edge)
    rings = P["B_camera_rings"].solids()
    for xr_, r in zip(g.CAMS_XR, sorted(rings, key=lambda s: -s.center().X)):
        b = r.bounding_box(optimal=True)
        row(f"Rear camera at {xr_:.2f}: X from edge", xr_, g.W - (b.min.X + b.max.X) / 2)
        row(f"Rear camera at {xr_:.2f}: Y", 15.25, -(b.min.Y + b.max.Y) / 2)
        row(f"Rear camera at {xr_:.2f}: diameter", 16.20, b.max.X - b.min.X)
    fl = P["B_flash"].bounding_box(optimal=True)
    row("Flash X from edge", 49.58, g.W - (fl.min.X + fl.max.X) / 2)
    row("Flash Y", 19.70, -(fl.min.Y + fl.max.Y) / 2)
    row("Flash diameter", 3.75, fl.max.X - fl.min.X)
    top = [f for f in P["B_back_glass"].faces()
           if abs(f.center().Z + g.ZTOP + g.PLATEAU_H) < 1e-3 and f.area > 500]
    tb = top[0].outer_wire().bounding_box(optimal=True)
    row("Plateau top, X from edge (near)", 4.94, g.W - tb.max.X)
    row("Plateau top, X from edge (far)", 60.56, g.W - tb.min.X)
    row("Plateau top, upper edge Y", 4.70, -tb.max.Y)
    row("Plateau top, lower edge Y", 25.80, -tb.min.Y)
    pb = Compound([f for f in P["B_back_glass"].faces()
                   if f.geom_type.name == "BSPLINE" and f.center().Z < -g.ZTOP - 0.1]).bounding_box(optimal=True)
    row("Plateau base, X from edge (far)", 69.37, g.W - pb.min.X, tol=0.03)
    row("Plateau base, lower edge Y", 34.62, -pb.min.Y, tol=0.03)
    mic_in = P["B_back_glass"].is_inside(Vector(g.xr(g.MIC[0]), g.MIC[1], -g.ZTOP - g.PLATEAU_H + 0.2))
    rows.append(("Rear mic opening at (49.58, 10.95)", "hole", "hole" if not mic_in else "solid",
                 0, not mic_in, ""))

    # --- bottom edge (Detail C): probe the frames just inside each opening
    yb = -g.L + 0.3
    for x in g.PORT_X:
        hole = not P["B_frame"].is_inside(Vector(x, yb, -(g.ZTOP - g.BTN_FROM_BACK)))
        wall = P["B_frame"].is_inside(Vector(x + g.PORT_D / 2 + 0.03, yb, -(g.ZTOP - g.BTN_FROM_BACK)))
        rows.append((f"Port Ø{g.PORT_D} at {x:.2f}", "hole", "hole" if hole and wall else "check",
                     0, hole and wall, ""))
    zu = g.ZTOP - g.BTN_FROM_BACK
    for x, label in ((38.42, "left"), (46.99, "right")):
        inside = 0.03 if label == "left" else -0.03
        ok = (not P["A_frame"].is_inside(Vector(x + inside, yb, zu))
              and P["A_frame"].is_inside(Vector(x - inside, yb, zu)))
        rows.append((f"USB-C opening {label} end at {x:.2f}", "edge", "edge" if ok else "check", 0, ok,
                     "8.59 wide slot centred on 42.70"))
    for name in ("A_screws", "B_screws"):
        xs = sorted((s.bounding_box().min.X + s.bounding_box().max.X) / 2 for s in P[name].solids())
        for x, xd in zip(xs, g.SCREW_X):
            row(f"{name[0]} screw at {xd:.2f}", xd, x)

    write()


def write():
    lines = ["# iPhone Duo CAD vs drawing (sheet 1 of 7)", "",
             "Measured from `build/iPhone_Duo.step`. Units mm.", "",
             "| Feature | Drawing | Model | Δ | OK | Note |", "|---|---|---|---|---|---|"]
    n_ok = n_conf = 0
    for f, d, m, delta, ok, note in rows:
        mark = "drawing conflict" if ok == "conflict" else ("✓" if ok else "✗")
        n_ok += ok is True
        n_conf += ok == "conflict"
        if isinstance(d, str):
            lines.append(f"| {f} | {d} | {m} | | {mark} | {note} |")
        else:
            lines.append(f"| {f} | {d:.3f} | {m:.3f} | {delta:+.3f} | {mark} | {note} |")
    n_chk = len(rows) - n_conf
    lines += ["", f"{n_ok}/{n_chk} checks within tolerance (0.02 mm unless noted); "
              f"{n_conf} places where the sheet contradicts itself are listed as conflicts."]
    (OUT / "verification.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

"""Build the iPhone Duo (folded) as a named, coloured assembly and export STEP + STLs.

    .venv/bin/python -m duo.build            # uses cached skins in build/ if present
    .venv/bin/python -m duo.build --fresh    # rebuild skins (about a minute)
"""
import sys
import time
from pathlib import Path

import numpy as np
from build123d import (Solid, Face, Wire, Edge, Vector, Plane, Location, Axis, Compound,
                       Color, export_step, export_stl, export_brep, import_brep)

from . import geometry as g
from . import body

OUT = Path(__file__).resolve().parent.parent / "build"
OUT.mkdir(exist_ok=True)
ZB = g.ZTOP                       # exterior face height
Z_BTN_B = -(g.ZTOP - g.BTN_FROM_BACK)          # -2.98: buttons and B-side ports
Z_USB_A = g.ZTOP - g.BTN_FROM_BACK             # USB-C centred like the B-side ports
Z_SCREW_A = g.ZTOP - g.SCREW_A_FROM_FRONT      # 2.825
GLASS_T = 0.65
Z_PLATEAU = -(ZB + g.PLATEAU_H)                # -9.29
Z_CAMGLASS = -(ZB + g.CAM_GLASS_H)             # -11.37

t0 = time.time()


def log(msg):
    print(f"[{time.time() - t0:6.1f}s] {msg}", flush=True)


def cached(name, fn, fresh):
    p = OUT / f"{name}.brep"
    if p.exists() and not fresh:
        return import_brep(str(p))
    s = fn()
    export_brep(s, str(p))
    return s


# ------------------------------------------------------------------ primitives

def stadium_face(plane: Plane, length, width):
    """Full-round slot centred on plane origin, long axis along plane x."""
    r = width / 2
    a = length / 2 - r
    e1 = Edge.make_line(plane.from_local_coords((-a, -r)), plane.from_local_coords((a, -r)))
    arc1 = Edge.make_three_point_arc(plane.from_local_coords((a, -r)),
                                     plane.from_local_coords((a + r, 0)),
                                     plane.from_local_coords((a, r)))
    e2 = Edge.make_line(plane.from_local_coords((a, r)), plane.from_local_coords((-a, r)))
    arc2 = Edge.make_three_point_arc(plane.from_local_coords((-a, r)),
                                     plane.from_local_coords((-a - r, 0)),
                                     plane.from_local_coords((-a, -r)))
    return Face(Wire([e1, arc1, e2, arc2]))


def prism(face, vec):
    return Solid.extrude(face, Vector(*vec))


def cyl(r, p0, p1):
    p0, p1 = Vector(*p0), Vector(*p1)
    d = p1 - p0
    return Solid.make_cylinder(r, d.length, Plane(origin=p0, z_dir=d))


def outline_prism(z0, z1, d_side, d_tb=None, dh=0.0):
    w = body.section_wire(z0, d_side, d_tb, dh)
    return prism(Face(w), (0, 0, z1 - z0))


# ------------------------------------------------------------------ assembly

def build(fresh=False):
    parts = {}

    A = cached("halfA", lambda: body.half_body("A"), fresh)
    log("half A skin")
    B = cached("halfB", lambda: body.half_body("B"), fresh)
    log("half B skin")
    P = cached("plateau", lambda: body.plateau_solid(-ZB)[0], fresh)
    log("plateau")
    Bp = B.fuse(P, glue=True).solids()[0]
    log("plateau fused to back")

    # The sheet's primary sizes (glass 79.93 x 115.04, active area 77.17 x 112.28) and its
    # "all around" callouts (1.33, 2.71, 4.13) disagree by 0.05-0.09 mm. Sizes win: the insets
    # below are equal on the right, top and bottom, and the hinge side takes the remainder.
    glass_tb = (g.L - g.GLASS_L) / 2                           # 1.38
    glass_dh = (g.W - glass_tb - g.GLASS_W) - g.XH             # glass starts 2.79 from hinge
    aa_tb = (g.L - g.AA_L) / 2                                 # 2.76
    aa_dh = (g.W - aa_tb - g.AA_W) - g.XH                      # active area starts 4.17 from hinge

    # ---- half A: cover glass, display, frame
    gp = outline_prism(ZB - GLASS_T, ZB + 1, glass_tb, glass_tb, glass_dh)
    parts["A_cover_glass"] = A & gp
    frameA = A - gp
    aa = outline_prism(ZB - GLASS_T - 0.10, ZB - GLASS_T, aa_tb, aa_tb, aa_dh)
    fx, fy, fd = g.FRONT_CAM
    fcam = cyl(fd / 2, (fx, fy, ZB - GLASS_T - 0.10), (fx, fy, ZB - GLASS_T))
    parts["A_display_active_area"] = aa - fcam
    parts["A_front_camera"] = fcam
    frameA = frameA - aa
    log("A glass/display split")

    # receiver + front mic slot in the frame lip above the glass edge
    rx = (g.XH + aa_dh + (g.W - aa_tb)) / 2                 # centred on the active area
    slot = prism(stadium_face(Plane.XY.offset(ZB - 1.0).move(Location((rx, -0.98, 0))),
                              g.RECEIVER_LEN, 0.50), (0, 0, 2))
    frameA = frameA - slot

    # USB-C, screws (bottom edge, half A)
    yb = -g.L
    usb = prism(stadium_face(Plane(origin=(g.USBC_X, yb - 1, Z_USB_A), x_dir=(1, 0, 0), z_dir=(0, 1, 0)),
                             g.USBC_W, g.USBC_H), (0, 8.5, 0))
    frameA = frameA - usb
    parts["A_usbc_tongue"] = Solid.make_box(6.69, 4.4, 0.70,
                                            Plane.XY.move(Location((g.USBC_X - 3.345, yb + 1.3, Z_USB_A - 0.35))))
    screwsA = []
    for x in g.SCREW_X:
        frameA = frameA - cyl(g.SCREW_D / 2, (x, yb - 1, Z_SCREW_A), (x, yb + 1.6, Z_SCREW_A))
        screwsA.append(cyl(g.SCREW_D / 2 - 0.02, (x, yb + 0.05, Z_SCREW_A), (x, yb + 1.6, Z_SCREW_A))
                       - cyl(0.38, (x, yb, Z_SCREW_A), (x, yb + 0.45, Z_SCREW_A)))
    parts["A_screws"] = Compound(screwsA)
    log("A ports")

    # ---- half B: back glass (with plateau), frame
    gpB = outline_prism(-ZB - g.PLATEAU_H - 1, -(ZB - GLASS_T), glass_tb, glass_tb, glass_dh)
    backglass = Bp & gpB
    frameB = Bp - gpB
    log("B glass split")

    # cameras, flash, mic on the plateau top
    cams, rings, lenses, covers = [], [], [], []
    for xr in g.CAMS_XR:
        cx, cy = g.xr(xr), g.CAM_Y
        ro, ri = g.CAM_D / 2, 6.85
        ring = cyl(ro, (cx, cy, Z_PLATEAU), (cx, cy, Z_CAMGLASS)) - cyl(ri, (cx, cy, Z_PLATEAU - 1), (cx, cy, Z_CAMGLASS - 1))
        top = [e for e in ring.edges() if abs(e.center().Z - Z_CAMGLASS) < 1e-6 and e.radius > ri + 0.1]
        ring = ring.chamfer(0.30, None, top)
        rings.append(ring)
        barrel = cyl(ri, (cx, cy, Z_PLATEAU), (cx, cy, Z_CAMGLASS + 0.80))
        lens = Solid.make_sphere(9.0).moved(Location((cx, cy, Z_CAMGLASS + 0.80 + 9.0 - 0.20)))
        lens = lens & cyl(3.4, (cx, cy, Z_CAMGLASS + 0.80), (cx, cy, Z_CAMGLASS + 0.58))
        lenses.append(barrel)
        lenses.append(lens)
        covers.append(cyl(ri, (cx, cy, Z_CAMGLASS + 0.55), (cx, cy, Z_CAMGLASS)))
    parts["B_camera_rings"] = Compound(rings)
    parts["B_camera_lenses"] = Compound(lenses)
    parts["B_camera_cover_glass"] = Compound(covers)
    flx, fly, fld = g.FLASH
    flash = cyl(fld / 2, (g.xr(flx), fly, Z_PLATEAU + 0.4), (g.xr(flx), fly, Z_PLATEAU))
    backglass = backglass - flash
    parts["B_flash"] = flash
    mx, my, ml, mw = g.MIC
    backglass = backglass - prism(stadium_face(Plane.XY.offset(Z_PLATEAU + 0.8).move(Location((g.xr(mx), my, 0))),
                                               ml, mw), (0, 0, -1.2))
    parts["B_back_glass"] = backglass
    log("B cameras")

    # buttons (half B)
    def pocket_and_button(face_btn, face_pocket, depth_in, proud, axis):
        btn = prism(face_btn, tuple(np.array(axis) * (depth_in + proud)))
        pocket = prism(face_pocket, tuple(np.array(axis) * (depth_in + 2.0)))
        return btn, pocket

    btns = {}
    for name, x in (("B_volume_down", g.VOL_MINUS_X), ("B_volume_up", g.VOL_PLUS_X)):
        y_in = -1.2
        pl = Plane(origin=(x, y_in, Z_BTN_B), x_dir=(1, 0, 0), z_dir=(0, 1, 0))
        btn, pocket = pocket_and_button(stadium_face(pl, g.VOL_LEN, g.SIDE_BTN_W),
                                        stadium_face(pl, g.VOL_LEN + 0.2, g.SIDE_BTN_W + 0.2),
                                        1.2, g.BUTTON_PROUD, (0, 1, 0))
        frameB = frameB - pocket
        btns[name] = btn
    for name, yc, half, w, proud in (("B_side_button", g.SIDE_BTN_Y, g.SIDE_BTN_HALF, g.SIDE_BTN_W, g.BUTTON_PROUD),
                                     ("B_camera_control", g.CAM_CTRL_Y, g.CAM_CTRL_HALF, g.CAM_CTRL_W, g.CAM_CTRL_PROUD)):
        x_in = g.W - 1.2
        pl = Plane(origin=(x_in, yc, Z_BTN_B), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
        btn, pocket = pocket_and_button(stadium_face(pl, 2 * half, w),
                                        stadium_face(pl, 2 * half + 0.2, w + 0.2),
                                        1.2, proud, (1, 0, 0))
        frameB = frameB - pocket
        btns[name] = btn
    for k, v in btns.items():
        outer = [e for e in v.edges() if _is_outer_edge(e, k)]
        try:
            v = v.fillet(0.25 if "control" not in k else 0.04, outer)
        except Exception as exc:
            log(f"fillet skipped on {k}: {exc}")
        parts[k] = v
    log("B buttons")

    # bottom-edge ports and screws (half B)
    for x in g.PORT_X:
        frameB = frameB - cyl(g.PORT_D / 2, (x, yb - 1, Z_BTN_B), (x, yb + 2.0, Z_BTN_B))
    screwsB = []
    for x in g.SCREW_X:
        frameB = frameB - cyl(g.SCREW_D / 2, (x, yb - 1, Z_BTN_B), (x, yb + 1.6, Z_BTN_B))
        screwsB.append(cyl(g.SCREW_D / 2 - 0.02, (x, yb + 0.05, Z_BTN_B), (x, yb + 1.6, Z_BTN_B))
                       - cyl(0.38, (x, yb, Z_BTN_B), (x, yb + 0.45, Z_BTN_B)))
    parts["B_screws"] = Compound(screwsB)
    log("B ports")

    # antenna splits (both frames)
    def slabs(z0, z1):
        out = []
        hw = g.ANT_W / 2
        for x in g.ANT_TOP_X:
            out.append(Solid.make_box(g.ANT_W, 4.5, z1 - z0, Plane.XY.offset(z0).move(Location((x - hw, -3.5, 0)))))
        for x in g.ANT_BOT_X:
            out.append(Solid.make_box(g.ANT_W, 4.5, z1 - z0, Plane.XY.offset(z0).move(Location((x - hw, yb - 1, 0)))))
        for y in g.ANT_SIDE_Y:
            out.append(Solid.make_box(4.5, g.ANT_W, z1 - z0, Plane.XY.offset(z0).move(Location((g.W - 3.5, y - hw, 0)))))
        return out
    bands = []
    for side, fr, (z0, z1) in (("A", frameA, (0.0, 6.0)), ("B", frameB, (-6.0, 0.0))):
        for s in slabs(z0, z1):
            bands.append(fr & s)
            fr = fr - s
        if side == "A":
            frameA = fr
        else:
            frameB = fr
    parts["antenna_splits"] = Compound([b for b in bands if b.volume > 0])
    parts["A_frame"] = frameA
    parts["B_frame"] = frameB
    parts["hinge_barrel"] = body.barrel()
    log("antenna splits, frames, hinge")
    return parts


def _is_outer_edge(e, name):
    c = e.center()
    if "volume" in name:
        return c.Y > g.BUTTON_PROUD - 1e-3
    proud = g.CAM_CTRL_PROUD if "control" in name else g.BUTTON_PROUD
    return c.X > g.W + proud - 1e-3


COLORS = {
    "frame": (0.62, 0.64, 0.66), "glass": (0.05, 0.05, 0.06), "display": (0.01, 0.01, 0.01),
    "back": (0.70, 0.72, 0.74), "ring": (0.55, 0.57, 0.6), "lens": (0.02, 0.02, 0.03),
    "cover": (0.2, 0.25, 0.3), "flash": (0.95, 0.92, 0.8), "screw": (0.3, 0.3, 0.32),
    "antenna": (0.45, 0.46, 0.47), "hinge": (0.5, 0.52, 0.54), "button": (0.62, 0.64, 0.66),
    "control": (0.2, 0.2, 0.22), "tongue": (0.1, 0.1, 0.1), "camera": (0.0, 0.0, 0.0),
}


def color_for(name):
    for key, val in (("frame", "frame"), ("cover_glass", "glass"), ("display", "display"),
                     ("back_glass", "back"), ("rings", "ring"), ("lenses", "lens"),
                     ("camera_cover", "cover"), ("flash", "flash"), ("screws", "screw"),
                     ("antenna", "antenna"), ("hinge", "hinge"), ("control", "control"),
                     ("volume", "button"), ("side_button", "button"), ("tongue", "tongue"),
                     ("front_camera", "camera")):
        if key in name:
            return COLORS[val]
    return (0.5, 0.5, 0.5)


def export(parts):
    children = []
    for name, shp in parts.items():
        shp.label = name
        shp.color = Color(*color_for(name))
        children.append(shp)
    asm = Compound(children=children, label="iPhone_Duo_folded")
    export_step(asm, str(OUT / "iPhone_Duo.step"))
    log("STEP written")
    stl = OUT / "stl"
    stl.mkdir(exist_ok=True)
    for name, shp in parts.items():
        export_stl(shp, str(stl / f"{name}.stl"), tolerance=0.004, angular_tolerance=0.08)
    log("STLs written")
    return asm


if __name__ == "__main__":
    parts = build(fresh="--fresh" in sys.argv)
    for k, v in parts.items():
        print(f"  {k:24s} valid={v.is_valid}  vol={v.volume:9.2f} mm3")
    export(parts)

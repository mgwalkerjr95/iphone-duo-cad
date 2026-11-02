"""B-rep construction of the two halves, hinge barrel and plateau (build123d / OCCT)."""
import numpy as np
from build123d import (Edge, Wire, Face, Shell, Solid, Vector, Plane, Axis, Location,
                       Compound)
from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
from OCP.TopoDS import TopoDS
from OCP.ShapeFix import ShapeFix_Solid

from . import geometry as g
from . import plateau


def _v3(p, z):
    return Vector(float(p[0]), float(p[1]), float(z))


def section_wire(z, d_side, d_tb=None, dh=0.0):
    edges = []
    for kind, p in g.plan_pieces(d_side, d_tb, dh):
        if kind == "line":
            edges.append(Edge.make_line(_v3(p[0], z), _v3(p[1], z)))
        else:
            t0 = p[1] - p[0]
            t1 = p[-1] - p[-2]
            edges.append(Edge.make_spline([_v3(q, z) for q in p],
                                          tangents=[_v3(t0, 0), _v3(t1, 0)]))
    return Wire(edges)


def _loft_faces(wires, ruled=False):
    from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
    ts = BRepOffsetAPI_ThruSections(False, ruled, 1e-6)
    ts.SetSmoothing(False)
    ts.SetMaxDegree(5)
    for w in wires:
        ts.AddWire(w.wrapped)
    ts.Build()
    return Shell(ts.Shape()).faces()


def _sew_solid(faces, tol=1e-4):
    sew = BRepBuilderAPI_Sewing(tol)
    for f in faces:
        sew.Add(f.wrapped)
    sew.Perform()
    shell = TopoDS.Shell(sew.SewedShape())
    ms = BRepBuilderAPI_MakeSolid(shell)
    fix = ShapeFix_Solid(ms.Solid())
    fix.Perform()
    s = Solid(fix.Solid())
    if s.volume < 0:
        s = Solid(s.wrapped.Reversed())
    return s


def half_body(half="A"):
    """One half of the folded phone: exterior skin per Details A, AY, B, E."""
    sign = 1.0 if half == "A" else -1.0
    inner = g.inner_round_samples(14)
    outer = g.edge_round_samples(24)
    w_inner = [section_wire(sign * z, d, dh=0.0) for d, z in inner]
    w_wall = [section_wire(sign * inner[-1, 1], 0.0), section_wire(sign * outer[0, 1], 0.0)]
    w_outer = [section_wire(sign * z, d, dh=float(g.hinge_inset(half, z))) for d, z in outer]
    faces = []
    faces += _loft_faces(w_inner)
    faces += _loft_faces(w_wall, ruled=True)
    faces += _loft_faces(w_outer)
    faces.append(Face(w_inner[0]))
    faces.append(Face(w_outer[-1]))
    return _sew_solid(faces)


def barrel():
    """Hinge barrel: Detail E (XZ) and Detail AY (XY) share one R1.65 round."""
    y0, y1 = -g.L - g.BARREL_Y0, g.BARREL_Y0
    box = Solid.make_box(g.XH, y1 - y0, 2 * g.BARREL_Z,
                         Plane.XY.offset(-g.BARREL_Z).move(Location((0, y0, 0))))
    edges = [e for e in box.edges() if abs(e.center().X) < 1e-6]
    return box.fillet(g.BARREL_R, edges)


def plateau_solid(z_back):
    """Raised camera plateau on half B's back plate (grows toward -Z)."""
    loops, heights, _ = plateau.sections()
    wires = []
    for P, h in zip(loops, heights):
        z = z_back - h
        e = Edge.make_spline([_v3(p, z) for p in P], periodic=True)
        wires.append(Wire([e]))
    faces = _loft_faces(wires)
    faces.append(Face(wires[0]))
    faces.append(Face(wires[-1]))
    return _sew_solid(faces), wires

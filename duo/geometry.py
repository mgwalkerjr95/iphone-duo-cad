"""Numbers and curves read off Apple's iPhone Duo dimension drawing (sheet 1 of 7).

Frame of reference (matches the drawing's 0.00 datums):
  X  0 at the hinge exterior, +X toward the button side, 84.10 at the far edge
  Y  0 at the top edge (volume buttons), negative downward to -117.80
  Z  0 at the fold plane, +Z = half A (outer display), -Z = half B (cameras)
"""
import numpy as np
from scipy.interpolate import CubicSpline, PchipInterpolator
from scipy.integrate import quad
from scipy.optimize import fsolve, least_squares
from functools import lru_cache

W, L, T = 84.10, 117.80, 11.30          # product width, length, thickness
ZTOP = 5.65                              # exterior face of each half (T/2)
ZIN = 0.17                               # inner (fold-side) face: 5.65 - 5.48
XH = 1.80                                # hinge-side wall of each half (Detail E)

# Detail A, corner profile (all four corners), top-right corner
CORNER_TR = np.array([(66.80, 0.00), (71.66, -0.06), (76.42, -1.00), (80.48, -3.63),
                      (83.10, -7.68), (84.08, -12.44), (84.10, -17.31)])
# Detail AY, hinge corner profile, body corner (top-left)
CORNER_TL = np.array([(1.80, -0.67), (2.06, -0.23), (2.52, -0.02), (3.03, 0.00)])

# Detail B, side profile: (inset from exterior, z) for the exterior edge round
EDGE_ROUND = np.array([(0.00, 2.91), (0.02, 3.85), (0.23, 4.76), (0.89, 5.41),
                       (1.80, 5.63), (2.74, 5.65)])
# Detail B, fold-side edge round (not dimensioned; traced from the drawing)
INNER_ROUND = np.array([(1.24, 0.17), (0.91, 0.43), (0.62, 0.76), (0.33, 1.04),
                        (0.12, 1.38), (0.00, 1.92)])
# Detail E, hinge-side edge round: inset from XH vs z, per half
HINGE_ROUND = {
    "A": (np.array([4.60, 4.71, 5.09, 5.43, 5.62, 5.65]),
          np.array([0.00, 0.01, 0.16, 0.49, 0.87, 0.94])),
    "B": (np.array([4.60, 4.71, 5.09, 5.43, 5.62, 5.65]),
          np.array([0.00, 0.02, 0.19, 0.54, 0.94, 1.02])),
}

# Detail E / AY: hinge barrel
BARREL_Z = 4.09          # half height
BARREL_Y0 = -1.19        # end of barrel (top); bottom mirrors
BARREL_R = 1.65          # fits (0.26, 3.32), (0.92, 3.92), (0.01, 2.46) to 0.02 mm

# Front view
GLASS_W, GLASS_L = 79.93, 115.04
GLASS_EDGE = 1.33                        # exterior of housing to cover glass
AA_W, AA_L = 77.17, 112.28               # display active area
AA_EDGE = 2.71
AA_HINGE = 4.13
FRONT_CAM = (73.39, -10.62, 6.07)        # x, y, diameter
VOL_MINUS_X, VOL_PLUS_X, VOL_LEN = 44.35, 57.73, 10.88
BUTTON_PROUD = 0.45
SIDE_BTN_Y, SIDE_BTN_HALF = -42.87, 9.34
CAM_CTRL_Y, CAM_CTRL_HALF = -84.97, 8.55
CAM_CTRL_PROUD = 0.075
SIDE_BTN_W, CAM_CTRL_W = 3.06, 2.53
BTN_FROM_BACK = 2.670                    # button / port centerline from half B exterior
RECEIVER_LEN = 13.14

# Detail C, bottom edge
PORT_X = [17.78, 20.03, 22.29, 24.54, 60.85, 63.10, 65.36, 67.61]
PORT_D = 1.53
SCREW_X, SCREW_D = [35.35, 50.04], 1.50
SCREW_A_FROM_FRONT = 2.825
USBC_X, USBC_W, USBC_H = 42.70, 8.59, 2.60    # 38.42..46.99 in Detail C; height traced

# Detail D, rear (measured from the non-hinge edge, so x_model = W - x_rear)
PLATEAU_H = 3.64
CAM_GLASS_H = 5.72
PLATEAU_TOP, PLATEAU_BOT = -4.70, -25.80
PLATEAU_XR = (4.94, 60.56)
PLATEAU_FLAT_XR = (21.65, 43.85)          # tangent edges of the end caps (traced)
PLATEAU_BASE_GROW = 8.81                  # 69.37-60.56 and 34.62-25.80
CAMS_XR = [15.25, 32.98]
CAM_Y = -15.25
CAM_D = 16.20
FLASH = (49.58, -19.70, 3.75)
MIC = (49.58, -10.95, 3.32, 1.50)
FLAT_START = 2.74                         # exterior of housing to start of flat area

# Antenna splits (traced, not dimensioned)
ANT_W = 0.9
ANT_TOP_X = [17.2, 68.6]
ANT_BOT_X = [30.3, 55.0]
ANT_SIDE_Y = [-15.9, -101.9]


def xr(x_rear):
    return W - x_rear


# ---------------------------------------------------------------- 1D profiles

def _clamped(pts, t0, t1):
    """Cubic spline through pts with unit end tangents t0, t1 (None = natural)."""
    pts = np.asarray(pts, float)
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
    out = []
    for k in range(2):
        a = (1, t0[k]) if t0 is not None else (2, 0.0)
        b = (1, t1[k]) if t1 is not None else (2, 0.0)
        out.append(CubicSpline(s, pts[:, k], bc_type=(a, b)))
    return s[-1], out[0], out[1]


def edge_round_samples(n=15):
    """(d, z) along Detail B's exterior round, denser where it turns."""
    S, fx, fz = _clamped(EDGE_ROUND, (0, 1), (1, 0))
    u = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, n))
    s = u * S
    return np.c_[fx(s), fz(s)]


def inner_round_samples(n=8):
    S, fx, fz = _clamped(INNER_ROUND, None, (0, 1))
    s = S * np.sin(np.linspace(0, np.pi / 2, n))      # dense toward the flat wall
    return np.c_[fx(s), fz(s)]


def hinge_inset(half, z):
    zz, dd = HINGE_ROUND[half]
    z = np.asarray(z, float)
    return np.where(z <= zz[0], 0.0, PchipInterpolator(zz, dd)(np.clip(z, zz[0], zz[-1])))


# ---------------------------------------------------------------- plan curves

@lru_cache(None)
def _corner_tr_fit(K=9, m=2001):
    """Convex curve through Detail A's points: curvature >= 0 everywhere, zero at both
    tangent edges (continuous-curvature corner). Convexity keeps it inside the 84.10 x 117.80
    box, which a plain cubic spline through these points does not (it bulged 0.03 mm)."""
    P = CORNER_TR
    p0, p1 = P[0], P[-1]

    def curve(v):
        S = v[0]
        k = np.r_[0.0, np.logaddexp(0, v[1:]), 0.0]
        s = np.linspace(0, S, m)
        kap = PchipInterpolator(np.linspace(0, S, K), k)(s)
        th = np.r_[0, np.cumsum(0.5 * (kap[1:] + kap[:-1]) * np.diff(s))]
        th *= (np.pi / 2) / th[-1]
        ds = np.diff(s)
        x = p0[0] + np.r_[0, np.cumsum(0.5 * (np.cos(th[1:]) + np.cos(th[:-1])) * ds)]
        y = p0[1] - np.r_[0, np.cumsum(0.5 * (np.sin(th[1:]) + np.sin(th[:-1])) * ds)]
        return np.c_[x, y], th

    def res(v):
        c, _ = curve(v)
        r = [10 * (c[-1] - p1)]
        r += [[np.hypot(*(c - q).T).min()] for q in P[1:-1]]
        return np.concatenate(r)

    v0 = np.r_[27.0, np.zeros(K - 2)]
    sol = least_squares(res, v0)
    c, th = curve(sol.x)
    c[-1] = p1
    return c, th


def corner_tr_samples(n=48):
    c, th = _corner_tr_fit()
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(c, axis=0).T))]
    u = np.linspace(0, s[-1], n)
    p = np.c_[np.interp(u, s, c[:, 0]), np.interp(u, s, c[:, 1])]
    a = np.interp(u, s, th)
    t = np.c_[np.cos(a), -np.sin(a)]
    return p, t


def corner_tl_samples(n=12):
    S, fx, fy = _clamped(CORNER_TL, (0, 1), (1, 0))
    s = np.linspace(0, S, n)
    return np.c_[fx(s), fy(s)]


def offset_tr(d, n=48):
    """Top-right corner offset inward by d (right normal of a clockwise path)."""
    p, t = corner_tr_samples(n)
    # path runs along the top then down the right side (clockwise);
    # inward is to the right of travel
    nrm = np.c_[t[:, 1], -t[:, 0]]
    return p + d * nrm


def plan_pieces(d_side, d_tb=None, dh=0.0, n_corner=48):
    """Closed outline (clockwise from hinge side, top-left) as 8 point lists.

    d_side: inset of the right edge, d_tb: inset of top/bottom edges (defaults to d_side),
    dh: inset of the hinge wall from XH. Corners keep tangency with the inset lines.
    Returns list of ('line'|'curve', np.array of xy) in travel order.
    """
    if d_tb is None:
        d_tb = d_side
    tr = offset_tr(d_side, n_corner) + np.array([0.0, -(d_tb - d_side)])
    tl = corner_tl_samples() + np.array([dh, -d_tb])
    mid = -L / 2
    br = tr[::-1] * [1, -1] + [0, 2 * mid]          # mirror about y = -L/2, keep clockwise
    bl = tl[::-1] * [1, -1] + [0, 2 * mid]
    return [
        ("line", np.array([bl[-1], tl[0]])),          # hinge wall, going up
        ("curve", tl),                                # top-left corner
        ("line", np.array([tl[-1], tr[0]])),          # top edge
        ("curve", tr),                                # top-right corner
        ("line", np.array([tr[-1], br[0]])),          # right edge
        ("curve", br),                                # bottom-right corner
        ("line", np.array([br[-1], bl[0]])),          # bottom edge
        ("curve", bl),                                # bottom-left corner
    ]


def plan_polygon(d_side, d_tb=None, dh=0.0):
    pts = []
    for kind, p in plan_pieces(d_side, d_tb, dh):
        pts.append(p[:-1])
    return np.vstack(pts)


# ---------------------------------------------------------------- plateau cap

def _clothoid_cap(A, B):
    """Straight -> clothoid -> arc reaching a vertical tangent: run A, drop B."""
    def end(R, L1):
        th = lambda s: s * s / (2 * R * L1)
        xc = quad(lambda s: np.cos(th(s)), 0, L1)[0]
        yc = quad(lambda s: np.sin(th(s)), 0, L1)[0]
        t1 = L1 / (2 * R)
        return xc + R * (1 - np.sin(t1)), yc + R * np.cos(t1), t1

    def f(v):
        R, L1 = v
        x, y, t1 = end(R, L1)
        return [x - A, y - B]
    R, L1 = fsolve(f, [B * 0.9, B * 0.8])
    t1 = L1 / (2 * R)
    assert 0 < t1 < np.pi / 2, (R, L1)
    return R, L1


def capsule_rear(n=720):
    """Plateau top outline in rear coords (x_rear, y), counter-clockwise, dense."""
    x0, x1 = PLATEAU_XR
    f0, f1 = PLATEAU_FLAT_XR
    yc = CAM_Y
    B = (PLATEAU_TOP - PLATEAU_BOT) / 2
    A_r, A_l = x1 - f1, f0 - x0
    caps = {}
    for key, A in (("r", A_r), ("l", A_l)):
        R, L1 = _clothoid_cap(A, B)
        t1 = L1 / (2 * R)
        s1 = np.linspace(0, L1, 200)
        th = s1 ** 2 / (2 * R * L1)
        cx = np.r_[0, np.cumsum(0.5 * (np.cos(th[1:]) + np.cos(th[:-1])) * np.diff(s1))]
        cy = np.r_[0, np.cumsum(0.5 * (np.sin(th[1:]) + np.sin(th[:-1])) * np.diff(s1))]
        a = np.linspace(t1, np.pi / 2, 200)[1:]
        ax = cx[-1] + R * (np.sin(a) - np.sin(t1))
        ay = cy[-1] + R * (np.cos(t1) - np.cos(a))
        q = np.c_[np.r_[cx, ax], np.r_[cy, ay]]       # quarter: (run, drop)
        caps[key] = (q, R, L1)
    # assemble CCW in rear coords: start at top-right tangent edge going right
    qr = caps["r"][0]
    upper_r = np.c_[f1 + qr[:, 0], PLATEAU_TOP - qr[:, 1]]
    lower_r = np.c_[f1 + qr[::-1, 0], PLATEAU_BOT + qr[::-1, 1]]
    ql = caps["l"][0]
    lower_l = np.c_[f0 - ql[:, 0], PLATEAU_BOT + ql[:, 1]]
    upper_l = np.c_[f0 - ql[::-1, 0], PLATEAU_TOP - ql[::-1, 1]]
    # rear coords: going right along top then down = clockwise; build then fix orientation later
    loop = np.vstack([upper_r, lower_r, lower_l, upper_l])
    return loop, caps


def _resample_closed(p, n):
    p = np.vstack([p, p[:1]])
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]
    keep = np.r_[True, np.diff(s) > 1e-9]
    p, s = p[keep], s[keep]
    u = np.linspace(0, s[-1], n, endpoint=False)
    return np.c_[np.interp(u, s, p[:, 0]), np.interp(u, s, p[:, 1])]


def capsule_model(n=720):
    loop, caps = capsule_rear(4000)
    m = np.c_[W - loop[:, 0], loop[:, 1]]
    return _resample_closed(m, n), caps

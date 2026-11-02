"""Camera plateau slope: level sets of a blend between the plateau top (Detail D inner
capsule) and its base (capsule grown 8.81 mm, clipped where the back stops being flat).

Returns closed point loops in model XY with their heights above the back plate.
"""
import numpy as np
from matplotlib.path import Path
from scipy.spatial import cKDTree
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import gaussian_filter
from skimage.measure import find_contours

from . import geometry as g

STEP = 0.04


def _smin(a, b, k):
    m = np.minimum(a, b)
    return m - k * np.log(np.exp(-(a - m) / k) + np.exp(-(b - m) / k))


def field():
    cap, _ = g.capsule_model(3000)
    flat = g.plan_polygon(g.FLAT_START, dh=1.0)
    xs = np.arange(10.0, 84.0, STEP)
    ys = np.arange(-40.0, 0.0, STEP)
    X, Y = np.meshgrid(xs, ys)
    P = np.c_[X.ravel(), Y.ravel()]

    in_cap = Path(cap).contains_points(P)
    d_top = cKDTree(cap).query(P)[0]
    d_top[in_cap] = 0.0
    in_flat = Path(flat).contains_points(P)
    dense_flat = _dense(flat, 0.02)
    d_flat = cKDTree(dense_flat).query(P)[0]
    d_flat[~in_flat] *= -1
    d_grow = g.PLATEAU_BASE_GROW - d_top
    d_base = _smin(d_grow, d_flat, 0.5)
    d_base = gaussian_filter(d_base.reshape(X.shape), 0.6 / STEP).ravel()
    with np.errstate(divide="ignore", invalid="ignore"):
        phi = np.where(d_base > 0, d_base / (d_base + d_top), 0.0)
    phi[in_cap] = 1.0
    return xs, ys, phi.reshape(X.shape)


def _dense(poly, ds):
    p = np.vstack([poly, poly[:1]])
    out = []
    for a, b in zip(p[:-1], p[1:]):
        n = max(2, int(np.ceil(np.hypot(*(b - a)) / ds)))
        out.append(a + np.linspace(0, 1, n, endpoint=False)[:, None] * (b - a))
    return np.vstack(out)


def smoothstep(t):
    return t * t * (3 - 2 * t)


def sections(levels=None, n=360):
    if levels is None:
        levels = np.r_[0.0, np.linspace(0.06, 0.94, 12), 1.0]
    xs, ys, phi = field()
    gy, gx = np.gradient(phi, STEP)
    ip = RegularGridInterpolator((ys, xs), phi)
    igx = RegularGridInterpolator((ys, xs), gx)
    igy = RegularGridInterpolator((ys, xs), gy)

    # base loop: the outermost level set, resampled from the point above the capsule center
    c = find_contours(phi, 1e-3)
    c = max(c, key=len)
    base = np.c_[xs[0] + c[:, 1] * STEP, ys[0] + c[:, 0] * STEP]
    base = _orient_ccw(base)
    cx = g.W - np.mean(g.PLATEAU_XR)
    i0 = np.argmin(np.hypot(base[:, 0] - cx, base[:, 1] - 0.0))
    base = np.roll(base, -i0, axis=0)
    pts = g._resample_closed(base, n)

    loops = [pts.copy()]
    cur = levels[0]
    for lev in levels[1:]:
        lev_eff = min(lev, 0.9995)
        for _ in range(40):
            q = pts[:, ::-1]
            f = ip(q)
            gvec = np.c_[igx(q), igy(q)]
            g2 = np.maximum((gvec ** 2).sum(1), 1e-9)
            pts = pts + ((lev_eff - f) / g2)[:, None] * gvec * 0.5
        loops.append(pts.copy())
    # the top loop is the capsule itself: snap the last loop onto it
    cap, _ = g.capsule_model(6000)
    tree = cKDTree(cap)
    loops[-1] = cap[tree.query(loops[-1])[1]]
    heights = g.PLATEAU_H * smoothstep(np.asarray(levels))
    return loops, heights, (xs, ys, phi)


def _orient_ccw(p):
    a = 0.5 * np.sum(p[:-1, 0] * p[1:, 1] - p[1:, 0] * p[:-1, 1])
    return p if a > 0 else p[::-1]

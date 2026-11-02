"""Lay the orthographic CAD renders over Apple's drawing views.

Each render's silhouette is fitted to the drawing's line work (uniform scale + offset,
chamfer matching), then the drawing's lines are multiplied over the render.
    .venv/bin/python render/overlay.py
"""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, binary_erosion
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parent.parent
DRAW = Image.open(ROOT / "ref" / "drawing_sheet1.png").convert("L")
D = np.asarray(DRAW, float)
DIST = distance_transform_edt(D > 140)
RPX = 20.0           # render px per mm (2600 px over 130 mm)
RC = 1300.0          # render centre px

# view: render file, mm of render centre (h, v), drawing crop box, initial (scale, x0, y0)
# where x0, y0 = drawing px of the view's mm origin (h=0, v=0)
VIEWS = {
    "front":  ("ortho_front.png",  (42.05, -58.9), (880, 480, 1320, 1050), (4.29, 915, 518), +1),
    # the rear render is already mirrored, so its horizontal mm read as x_rear (from the far edge)
    "rear":   ("ortho_rear.png",   (42.05, -58.9), (1560, 480, 2000, 1050), (4.26, 1592, 518), +1),
    "side":   ("ortho_side.png",   (0.0, -58.9),   (590, 480, 720, 1050), (4.29, 647, 516), +1),
    "bottom": ("ortho_bottom.png", (42.05, 0.0),   (600, 1250, 1090, 1400), (4.32, 641, 1314), +1),
}


def silhouette_mm(path, centre, flip):
    im = Image.open(ROOT / "renders" / path)
    a = np.asarray(im)[:, :, 3] > 128
    edge = a & ~binary_erosion(a, iterations=2)
    v, u = np.nonzero(edge)
    keep = np.random.default_rng(0).choice(len(u), size=min(len(u), 6000), replace=False)
    u, v = u[keep], v[keep]
    h = (u - RC) / RPX * flip + centre[0] * 1.0
    w = -(v - RC) / RPX + centre[1]
    return im, h, w


def cost(p, h, w):
    s, x0, y0 = p
    X = np.clip((x0 + s * h).astype(int), 0, D.shape[1] - 1)
    Y = np.clip((y0 - s * w).astype(int), 0, D.shape[0] - 1)
    return np.minimum(DIST[Y, X], 8).mean()


def fit(h, w, p0):
    best = None
    for dx in (-6, 0, 6):
        for dy in (-6, 0, 6):
            r = minimize(cost, (p0[0], p0[1] + dx, p0[2] + dy), args=(h, w), method="Nelder-Mead",
                         options={"xatol": 1e-3, "fatol": 1e-4, "maxiter": 600})
            if best is None or r.fun < best.fun:
                best = r
    return best


def composite(name):
    path, centre, box, p0, flip = VIEWS[name]
    im, h, w = silhouette_mm(path, centre, flip)
    r = fit(h, w, p0)
    s, x0, y0 = r.x
    print(f"{name:7s} scale {s:.4f} px/mm  origin ({x0:.1f}, {y0:.1f})  mean edge miss {r.fun:.2f} px "
          f"= {r.fun / s:.3f} mm")
    # render px -> drawing px:  X = x0 + s*(flip*(u-RC)/RPX + ch),  Y = y0 - s*(-(v-RC)/RPX + cv)
    a = flip * s / RPX
    b = s / RPX
    c = x0 + s * (centre[0] - flip * RC / RPX)
    d = y0 - s * (centre[1] + RC / RPX)
    # PIL wants the inverse map: drawing px -> render px
    inv = (1 / a, 0, -c / a, 0, 1 / b, -d / b)
    warped = im.transform(DRAW.size, Image.AFFINE, inv, resample=Image.BICUBIC)
    base = Image.new("RGB", DRAW.size, (255, 255, 255))
    base.paste(warped, (0, 0), warped)
    lines = np.asarray(DRAW, float) / 255.0
    out = np.asarray(base, float) * lines[:, :, None] ** 1.5
    out = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    return out.crop(box), r


if __name__ == "__main__":
    out = ROOT / "renders"
    for name in VIEWS:
        img, r = composite(name)
        k = 1600 / max(img.size)
        img.resize((int(img.width * k), int(img.height * k)), Image.LANCZOS).save(out / f"overlay_{name}.png")

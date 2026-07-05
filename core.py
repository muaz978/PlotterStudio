"""
Plotter Studio -- core vectorize/export pipeline (no GUI, importable & testable).

image -> potrace outline trace -> polylines -> fit to bed -> SVG + G-code.
"""
import os
import re
import sys
import math
import shutil
import tempfile
import subprocess

__version__ = "0.1.1"

try:
    from PIL import Image, ImageFilter, ImageOps
except Exception:
    Image = None
try:
    from svgpathtools import svg2paths
except Exception:
    svg2paths = None


def deps_status():
    """Return dict of what's available, for the UI to report clearly."""
    return {"pillow": Image is not None,
            "svgpathtools": svg2paths is not None,
            "potrace": find_potrace()}


def find_potrace():
    # 1) bundled inside a frozen PyInstaller app (mac .app or Windows .exe)
    bases = []
    if getattr(sys, "frozen", False):
        bases.append(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)))
        bases.append(os.path.dirname(sys.executable))
    bases.append(os.path.dirname(os.path.abspath(__file__)))
    for base in bases:
        for cand in (os.path.join(base, "bin", "potrace"),
                     os.path.join(base, "bin", "potrace.exe"),
                     os.path.join(base, "potrace"),
                     os.path.join(base, "potrace.exe")):
            if os.path.exists(cand):
                return cand
    # 2) system PATH
    return shutil.which("potrace")


def vectorize(image_path, threshold=128, invert=False, despeckle=8,
              alphamax=1.2, potrace_path=None):
    """Trace an image to a list of polylines in image-pixel space (y-down)."""
    if Image is None:
        raise RuntimeError("Pillow is not installed (pip install pillow).")
    if svg2paths is None:
        raise RuntimeError("svgpathtools is not installed (pip install svgpathtools).")
    potrace_path = potrace_path or find_potrace()
    if not potrace_path:
        raise RuntimeError("potrace not found. Install it, then reopen the app.")

    im = Image.open(image_path).convert("L").filter(ImageFilter.MedianFilter(3))
    if invert:
        im = ImageOps.invert(im)
    bw = im.point(lambda p: 0 if p < threshold else 255, "1")   # black = ink

    tmp = tempfile.mkdtemp(prefix="plotterstudio_")
    bmp, svg = os.path.join(tmp, "in.bmp"), os.path.join(tmp, "out.svg")
    bw.save(bmp)
    try:
        subprocess.run([potrace_path, bmp, "-s", "-o", svg,
                        "-t", str(int(despeckle)), "-a", str(float(alphamax)),
                        "-O", "0.2"], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        raw = open(svg).read()
        m = re.search(r'transform="translate\(([-\d.]+),([-\d.]+)\)\s*'
                      r'scale\(([-\d.]+),([-\d.]+)\)"', raw)
        e, f, a, d = (float(m.group(1)), float(m.group(2)),
                      float(m.group(3)), float(m.group(4))) if m else (0., 0., 1., 1.)

        def xf(z):
            return (a * z.real + e, d * z.imag + f)

        paths, _ = svg2paths(svg)
        loops = []
        for p in paths:
            for sub in p.continuous_subpaths():
                L = sub.length()
                if L < 6:
                    continue
                n = max(16, min(800, int(L / 1.5)))
                loops.append([xf(sub.point(i / n)) for i in range(n + 1)])
        return loops
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def transform_loops(loops, rotate=0, flip_h=False, flip_v=False):
    """Rotate (deg) and flip about the art's bbox center."""
    if not loops or (rotate % 360 == 0 and not flip_h and not flip_v):
        return [list(lp) for lp in loops]
    xs = [q[0] for lp in loops for q in lp]; ys = [q[1] for lp in loops for q in lp]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    r = math.radians(rotate); ca, sa = math.cos(r), math.sin(r)
    out = []
    for lp in loops:
        nl = []
        for x, y in lp:
            x0, y0 = x - cx, y - cy
            if flip_h: x0 = -x0
            if flip_v: y0 = -y0
            nl.append((x0 * ca - y0 * sa + cx, x0 * sa + y0 * ca + cy))
        out.append(nl)
    return out


def compute_fit(loops, target_mm):
    xs = [q[0] for lp in loops for q in lp]; ys = [q[1] for lp in loops for q in lp]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    span = max(maxx - minx, maxy - miny) or 1.0
    s = target_mm / span
    return {"scale": s, "minx": minx, "maxx": maxx, "miny": miny, "maxy": maxy,
            "w": (maxx - minx) * s, "h": (maxy - miny) * s}


def to_bed(loops, fit, bed_w, bed_h, origin="center", margin=3.0):
    """Place art on the bed (machine Y up). origin: 'center' or 'corner'."""
    s = fit["scale"]
    minx, maxx = fit["minx"], fit["maxx"]
    miny, maxy = fit["miny"], fit["maxy"]
    if origin == "corner":                      # bottom-left, offset by margin
        def tb(q):
            return ((q[0] - minx) * s + margin, margin + (maxy - q[1]) * s)
    else:                                        # centered on the bed
        mx, my = (minx + maxx) / 2, (miny + maxy) / 2
        cx, cy = bed_w / 2.0, bed_h / 2.0

        def tb(q):
            return ((q[0] - mx) * s + cx, -(q[1] - my) * s + cy)
    return [[tb(q) for q in lp] for lp in loops]


def order_for_travel(loops, start=(0.0, 0.0)):
    """Greedy nearest-neighbour ordering (with endpoint reversal) to cut the
    pen-up travel between contours."""
    remaining = [list(lp) for lp in loops]
    ordered = []
    cur = start
    while remaining:
        best, best_d, rev = 0, float("inf"), False
        for idx, lp in enumerate(remaining):
            ds = math.dist(cur, lp[0])
            de = math.dist(cur, lp[-1])
            if ds < best_d:
                best, best_d, rev = idx, ds, False
            if de < best_d:
                best, best_d, rev = idx, de, True
        lp = remaining.pop(best)
        if rev:
            lp.reverse()
        ordered.append(lp)
        cur = lp[-1]
    return ordered


def out_of_bounds(loops_mm, bed_w, bed_h):
    return any(x < 0 or x > bed_w or y < 0 or y > bed_h
               for lp in loops_mm for x, y in lp)


def stats(loops_mm, start=(0.0, 0.0)):
    draw = sum(math.dist(lp[i], lp[i + 1]) for lp in loops_mm for i in range(len(lp) - 1))
    seg = sum(len(lp) - 1 for lp in loops_mm)
    travel, cur = 0.0, start
    for lp in loops_mm:
        travel += math.dist(cur, lp[0]); cur = lp[-1]
    return {"contours": len(loops_mm), "segments": seg, "draw_mm": draw, "travel_mm": travel}


def build_gcode(loops_mm, pen_up=5.0, pen_down=0.0, f_draw=150, f_travel=250):
    g = ["; Generated by Plotter Studio", "G21 G90", "G0 Z%.2f" % pen_up]
    for lp in loops_mm:
        g.append("G0 X%.3f Y%.3f F%d" % (lp[0][0], lp[0][1], f_travel))
        g.append("G1 Z%.2f F%d" % (pen_down, f_draw))
        for x, y in lp[1:]:
            g.append("G1 X%.3f Y%.3f F%d" % (x, y, f_draw))
        g.append("G0 Z%.2f" % pen_up)
    g += ["G0 X0 Y0", "; done"]
    return "\n".join(g) + "\n"


def build_svg(loops, fit):
    s, minx, miny = fit["scale"], fit["minx"], fit["miny"]
    w, h = fit["w"], fit["h"]
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" '
           'viewBox="0 0 %.2f %.2f">' % (w, h, w, h)]
    for lp in loops:
        pts = " ".join("%.3f,%.3f" % ((q[0] - minx) * s, (q[1] - miny) * s) for q in lp)
        out.append('<polyline points="%s" fill="none" stroke="#000" stroke-width="0.3"/>' % pts)
    out.append("</svg>")
    return "\n".join(out)

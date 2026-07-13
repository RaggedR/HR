#!/usr/bin/env python3
"""Overlay Penrose P2 tiling + Victorian wrought-iron border onto any PDF.

Usage:
    python pretty_pdf.py input.pdf                  # → input_pretty.pdf
    python pretty_pdf.py input.pdf -o output.pdf    # explicit output path
    python pretty_pdf.py input.pdf --border-only     # skip Penrose tiling
    python pretty_pdf.py input.pdf --tiling-only     # skip border
"""

from __future__ import annotations

import argparse
import io
import math
import random
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas

from pypdf import PdfReader, PdfWriter


# ── Penrose P2 tiling (Robinson triangle deflation) ────────────────

def _rot(px, py, ox, oy, deg):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    dx, dy = px - ox, py - oy
    return (ox + dx * c - dy * s, oy + dx * s + dy * c)


def _tri(shape, side, A, B):
    ang = 36 if shape == "A" else 108
    C = _rot(B[0], B[1], A[0], A[1], ang)
    return (shape, side, A, B, C)


def _deflate(triangles):
    result = []
    for shape, side, A, B, C in triangles:
        if shape == "A":
            if side == "F":
                P = _rot(B[0], B[1], C[0], C[1], -36)
                Q = _rot(B[0], B[1], C[0], C[1], -72)
                result.append(_tri("O", "F", Q, A))
                result.append(_tri("A", "B", C, Q))
                result.append(_tri("A", "F", C, P))
            else:
                P = _rot(C[0], C[1], B[0], B[1], 36)
                Q = _rot(C[0], C[1], B[0], B[1], 72)
                result.append(_tri("O", "B", Q, P))
                result.append(_tri("A", "F", B, P))
                result.append(_tri("A", "B", B, C))
        else:
            if side == "F":
                D = _rot(A[0], A[1], B[0], B[1], -36)
                result.append(_tri("A", "B", B, D))
                result.append(_tri("O", "F", D, C))
            else:
                D = _rot(A[0], A[1], C[0], C[1], 36)
                result.append(_tri("A", "F", C, A))
                result.append(_tri("O", "B", D, A))
    return result


def _make_sun_seed(cx, cy, radius):
    tris = []
    for i in range(5):
        deg = i * 72 - 90
        rad = math.radians(deg)
        Bf = (cx + radius * math.cos(rad), cy + radius * math.sin(rad))
        tris.append(_tri("A", "F", (cx, cy), Bf))
        Bb = _rot(Bf[0], Bf[1], cx, cy, -36)
        tris.append(_tri("A", "B", (cx, cy), Bb))
    return tris


def _generate_penrose_tiling(w, h):
    """Generate Penrose P2 triangles covering a w×h rectangle."""
    random.seed()
    spread = max(w, h) * 0.8
    ox = (random.random() - 0.5) * spread
    oy = (random.random() - 0.5) * spread
    cx, cy = w / 2 + ox, h / 2 + oy

    radius = max(
        math.hypot(cx, cy),
        math.hypot(w - cx, cy),
        math.hypot(cx, h - cy),
        math.hypot(w - cx, h - cy),
    ) * 1.05

    tris = _make_sun_seed(cx, cy, radius)
    for _ in range(7):
        tris = _deflate(tris)

    margin = 20
    return [
        t for t in tris
        if any(
            -margin < v[0] < w + margin and -margin < v[1] < h + margin
            for v in (t[2], t[3], t[4])
        )
    ]


def _ekey(a, b):
    ka = f"{round(a[0] * 100)},{round(a[1] * 100)}"
    kb = f"{round(b[0] * 100)},{round(b[1] * 100)}"
    return (ka + "|" + kb) if ka < kb else (kb + "|" + ka)


def draw_penrose(c, w, h):
    """Draw a subtle Penrose P2 tiling background on the canvas."""
    tris = _generate_penrose_tiling(w, h)

    c.saveState()

    kite_fill = colors.HexColor("#dce8f0")
    dart_fill = colors.HexColor("#f0dcd8")
    edge_color = colors.HexColor("#c0c8d0")

    # Fill triangles
    for shape, _side, A, B, C in tris:
        fill = kite_fill if shape == "A" else dart_fill
        p = c.beginPath()
        p.moveTo(A[0], A[1])
        p.lineTo(B[0], B[1])
        p.lineTo(C[0], C[1])
        p.close()
        c.setFillColor(fill)
        c.setStrokeColor(fill)
        c.drawPath(p, fill=1, stroke=0)

    # Classify edges — skip axis edges (internal to kite/dart pairs)
    edge_info = {}
    for shape, side, A, B, C in tris:
        axis_edge = (A, B) if side == "F" else (A, C)
        axis_key = _ekey(axis_edge[0], axis_edge[1])
        for p_pt, q_pt in [(A, B), (A, C), (B, C)]:
            k = _ekey(p_pt, q_pt)
            if k not in edge_info:
                edge_info[k] = {"axis": 0, "verts": (p_pt, q_pt)}
            if k == axis_key:
                edge_info[k]["axis"] += 1

    # Draw tile boundary edges only
    c.setStrokeColor(edge_color)
    c.setLineWidth(0.5)
    for info in edge_info.values():
        if info["axis"] >= 2:
            continue
        p_pt, q_pt = info["verts"]
        c.line(p_pt[0], p_pt[1], q_pt[0], q_pt[1])

    c.restoreState()


# ── Victorian wrought-iron border ──────────────────────────────────

def _draw_volute_pair_h(c, x1, x2, y_outer, y_inner, stroke_color):
    """Draw a facing volute pair between two bars on a horizontal edge."""
    c.setStrokeColor(stroke_color)
    c.setLineWidth(2.0)

    sw = x2 - x1
    dy = y_inner - y_outer

    # Left volute: 3-segment spiral
    p = c.beginPath()
    p.moveTo(x1 + sw * 0.04, y_outer + dy * 0.05)
    p.curveTo(x1 + sw * 0.04, y_outer + dy * 0.65,
              x1 + sw * 0.12, y_outer + dy * 0.95,
              x1 + sw * 0.30, y_outer + dy * 0.90)
    p.curveTo(x1 + sw * 0.45, y_outer + dy * 0.85,
              x1 + sw * 0.48, y_outer + dy * 0.45,
              x1 + sw * 0.40, y_outer + dy * 0.30)
    p.curveTo(x1 + sw * 0.35, y_outer + dy * 0.20,
              x1 + sw * 0.28, y_outer + dy * 0.35,
              x1 + sw * 0.33, y_outer + dy * 0.48)
    c.drawPath(p, fill=0, stroke=1)

    # Right volute (mirror)
    p = c.beginPath()
    p.moveTo(x2 - sw * 0.04, y_outer + dy * 0.05)
    p.curveTo(x2 - sw * 0.04, y_outer + dy * 0.65,
              x2 - sw * 0.12, y_outer + dy * 0.95,
              x2 - sw * 0.30, y_outer + dy * 0.90)
    p.curveTo(x2 - sw * 0.45, y_outer + dy * 0.85,
              x2 - sw * 0.48, y_outer + dy * 0.45,
              x2 - sw * 0.40, y_outer + dy * 0.30)
    p.curveTo(x2 - sw * 0.35, y_outer + dy * 0.20,
              x2 - sw * 0.28, y_outer + dy * 0.35,
              x2 - sw * 0.33, y_outer + dy * 0.48)
    c.drawPath(p, fill=0, stroke=1)


def _draw_volute_pair_v(c, y1, y2, x_inner, x_outer, stroke_color):
    """Draw a facing volute pair between two bars on a vertical edge."""
    c.setStrokeColor(stroke_color)
    c.setLineWidth(2.0)

    sh = y2 - y1
    dx = x_inner - x_outer

    # Bottom volute
    p = c.beginPath()
    p.moveTo(x_outer + dx * 0.05, y1 + sh * 0.04)
    p.curveTo(x_outer + dx * 0.65, y1 + sh * 0.04,
              x_outer + dx * 0.95, y1 + sh * 0.12,
              x_outer + dx * 0.90, y1 + sh * 0.30)
    p.curveTo(x_outer + dx * 0.85, y1 + sh * 0.45,
              x_outer + dx * 0.45, y1 + sh * 0.48,
              x_outer + dx * 0.30, y1 + sh * 0.40)
    p.curveTo(x_outer + dx * 0.20, y1 + sh * 0.35,
              x_outer + dx * 0.35, y1 + sh * 0.28,
              x_outer + dx * 0.48, y1 + sh * 0.33)
    c.drawPath(p, fill=0, stroke=1)

    # Top volute (mirror)
    p = c.beginPath()
    p.moveTo(x_outer + dx * 0.05, y2 - sh * 0.04)
    p.curveTo(x_outer + dx * 0.65, y2 - sh * 0.04,
              x_outer + dx * 0.95, y2 - sh * 0.12,
              x_outer + dx * 0.90, y2 - sh * 0.30)
    p.curveTo(x_outer + dx * 0.85, y2 - sh * 0.45,
              x_outer + dx * 0.45, y2 - sh * 0.48,
              x_outer + dx * 0.30, y2 - sh * 0.40)
    p.curveTo(x_outer + dx * 0.20, y2 - sh * 0.35,
              x_outer + dx * 0.35, y2 - sh * 0.28,
              x_outer + dx * 0.48, y2 - sh * 0.33)
    c.drawPath(p, fill=0, stroke=1)


def draw_border(c, w, h):
    """Draw a Victorian wrought-iron border with volute scrollwork."""
    c.saveState()

    iron = colors.HexColor("#1a1a1a")
    iron_fill = colors.HexColor("#222222")

    out = 11 * mm
    inn = 18 * mm
    band = inn - out

    # Rails (double frame)
    c.setStrokeColor(iron)
    c.setLineWidth(2.0)
    c.rect(out, out, w - 2 * out, h - 2 * out)
    c.setLineWidth(0.75)
    c.rect(inn, inn, w - 2 * inn, h - 2 * inn)

    # Corner rosettes
    for cx, cy in [(out, out), (w - out, out),
                   (out, h - out), (w - out, h - out)]:
        c.setFillColor(colors.white)
        c.setStrokeColor(iron)
        c.setLineWidth(1.5)
        c.circle(cx, cy, band * 0.45, fill=1, stroke=1)
        c.setFillColor(iron_fill)
        c.circle(cx, cy, band * 0.15, fill=1, stroke=0)

    # Bar positions
    pad = band * 0.5 + 2 * mm

    h_start = out + pad
    h_end = w - out - pad
    h_span = h_end - h_start
    n_h = max(3, round(h_span / (24 * mm)))
    n_h = n_h | 1
    h_step = h_span / (n_h - 1)

    v_start = out + pad
    v_end = h - out - pad
    v_span = v_end - v_start
    n_v = max(3, round(v_span / (24 * mm)))
    n_v = n_v | 1
    v_step = v_span / (n_v - 1)

    def _edge_h(y_out, y_inn):
        c.setStrokeColor(iron)
        for i in range(n_h):
            bx = h_start + i * h_step
            c.setLineWidth(1.5)
            c.line(bx, y_out, bx, y_inn)
        for i in range(n_h - 1):
            _draw_volute_pair_h(c,
                                h_start + i * h_step,
                                h_start + (i + 1) * h_step,
                                y_out, y_inn, iron)

    def _edge_v(x_out, x_inn):
        c.setStrokeColor(iron)
        for i in range(n_v):
            by = v_start + i * v_step
            c.setLineWidth(1.5)
            c.line(x_out, by, x_inn, by)
        for i in range(n_v - 1):
            _draw_volute_pair_v(c,
                                v_start + i * v_step,
                                v_start + (i + 1) * v_step,
                                x_inn, x_out, iron)

    _edge_h(h - out, h - inn)       # top
    _edge_h(out, inn)               # bottom
    _edge_v(out, inn)               # left
    _edge_v(w - out, w - inn)       # right

    c.restoreState()


# ── Public API ─────────────────────────────────────────────────────

def make_overlay(w, h, *, tiling=True, border=True):
    """Create an in-memory PDF page with Penrose tiling and/or border.

    Returns a PdfReader with a single page at dimensions (w, h).
    """
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(w, h))

    if tiling:
        draw_penrose(c, w, h)
    if border:
        draw_border(c, w, h)

    c.showPage()
    c.save()
    buf.seek(0)
    return PdfReader(buf)


def prettify(input_path, output_path=None, *, tiling=True, border=True):
    """Apply Penrose tiling + wrought-iron border to every page of a PDF.

    The overlay is drawn UNDER the existing content so text remains
    readable.  Returns the output Path.
    """
    input_path = Path(input_path)
    if output_path is None:
        output_path = input_path.with_stem(input_path.stem + "_pretty")
    output_path = Path(output_path)

    reader = PdfReader(str(input_path))
    writer = PdfWriter()

    for page in reader.pages:
        box = page.mediabox
        w = float(box.width)
        h = float(box.height)

        overlay_reader = make_overlay(w, h, tiling=tiling, border=border)
        overlay_page = overlay_reader.pages[0]

        # Merge overlay UNDER existing content
        overlay_page.merge_page(page)
        writer.add_page(overlay_page)

    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path


# ── CLI ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Add Penrose tiling + Victorian wrought-iron border to a PDF",
    )
    parser.add_argument("input", help="Input PDF path")
    parser.add_argument("-o", "--output", help="Output PDF path (default: <input>_pretty.pdf)")
    parser.add_argument("--border-only", action="store_true",
                        help="Skip Penrose tiling, add border only")
    parser.add_argument("--tiling-only", action="store_true",
                        help="Skip border, add Penrose tiling only")
    args = parser.parse_args()

    tiling = not args.border_only
    border = not args.tiling_only

    result = prettify(args.input, args.output, tiling=tiling, border=border)
    print(f"✓ {result}")


if __name__ == "__main__":
    main()

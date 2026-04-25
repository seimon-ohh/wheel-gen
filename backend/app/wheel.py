"""Cricut Print-Then-Cut SVG renderer for the wheel-of-fortune cover.

Produces a single SVG document with two visually-distinct logical layers
that the teacher will identify in Cricut Design Space:

- Print layer: black filled text and thin segment dividers (printed by the
  home printer). These get flattened into one Print-Then-Cut image.
- Cut layer: red hairline-stroked circles (outer wheel + center hub /
  Nabe). These remain as cut paths in Design Space.

Distances are in millimeters; the SVG ``viewBox`` is set in mm and the
document size uses explicit mm units so Cricut imports at the intended
real-world size.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from html import escape

from . import text_to_path
from .exercises.base import Exercise

WHEEL_DIAMETER_CRICUT_MM = 170.0
WHEEL_DIAMETER_FULL_MM = 188.0
HUB_DIAMETER_MM = 19.0
HUB_CLEARANCE_MM = 0.4
SEGMENTS = 12

CUT_STROKE = "#FF0000"
CUT_STROKE_WIDTH_MM = 0.1
PRINT_STROKE = "#111111"
PRINT_STROKE_WIDTH_MM = 0.4
TEXT_COLOR = "#111111"

PAGE_PADDING_MM = 5.0
# How far text sits from the *printed* outer ring (r ≈ R − 0.2). Keeps
# labels away from the cut edge and looks more refined than butting
# against the line.
OUTER_TEXT_MARGIN_MM = 1.0
# Radial position of the label centre, as a fraction of the way from
# the hub to the *outer text limit* (not the full R). 0.55 = mid annulus
# (old default); 0.82–0.90 = “outer” band, where the segment is wider in
# arc, giving the longest string more room and a more balanced layout.
TEXT_RADIAL_FRACTION = 0.88
# Slight insets for chord width so glyphs do not sit flush on the dividers.
CHORD_SAFETY = 0.9
# Upper bound for font “height” in mm (single line); can grow a bit
# when more radial depth is available because text is placed outward.
MAX_FONT_SIZE_MM = 14.0


@dataclass
class WheelOptions:
    diameter_mm: float = WHEEL_DIAMETER_CRICUT_MM
    hub_diameter_mm: float = HUB_DIAMETER_MM
    hub_clearance_mm: float = HUB_CLEARANCE_MM
    segments: int = SEGMENTS
    show_dividers: bool = True
    show_outline: bool = True
    title: str | None = None

    @property
    def hub_cut_diameter_mm(self) -> float:
        """Diameter of the cut hole = Nabe diameter + clearance."""
        return self.hub_diameter_mm + self.hub_clearance_mm


def _polar(cx: float, cy: float, r: float, angle_deg: float) -> tuple[float, float]:
    a = math.radians(angle_deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def _fmt(v: float) -> str:
    return f"{v:.3f}".rstrip("0").rstrip(".")


def _fit_font_size(text: str, max_width_mm: float, max_height_mm: float) -> float:
    """Find the largest font size at which ``text`` fits both constraints.

    Uses the bundled font metrics when available so the resulting size is
    accurate; otherwise approximates with an average-glyph-width heuristic.
    """
    if not text:
        return max_height_mm
    if text_to_path.is_available():
        probe = 10.0
        width_at_probe = text_to_path.measure_text(text, probe)
        if width_at_probe > 0:
            by_width = max_width_mm * (probe / width_at_probe)
            return max(2.0, min(by_width, max_height_mm, MAX_FONT_SIZE_MM))
    char_count = max(len(text), 1)
    by_width = max_width_mm / (char_count * 0.6)
    return max(2.0, min(by_width, max_height_mm, MAX_FONT_SIZE_MM))


def render_wheel_svg(
    exercises: list[Exercise],
    options: WheelOptions | None = None,
) -> str:
    opts = options or WheelOptions()
    if len(exercises) != opts.segments:
        raise ValueError(
            f"Expected {opts.segments} exercises, got {len(exercises)}"
        )

    R = opts.diameter_mm / 2.0
    r_hub = opts.hub_cut_diameter_mm / 2.0
    n = opts.segments
    seg_deg = 360.0 / n

    page = opts.diameter_mm + 2 * PAGE_PADDING_MM
    cx = cy = page / 2.0

    parts: list[str] = []
    parts.append(
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
    )
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
        f'width="{_fmt(page)}mm" height="{_fmt(page)}mm" '
        f'viewBox="0 0 {_fmt(page)} {_fmt(page)}" '
        f'shape-rendering="geometricPrecision" '
        f'text-rendering="geometricPrecision">'
    )

    if opts.title:
        parts.append(f"<title>{escape(opts.title)}</title>")

    style = (
        "<style>"
        ".cut{fill:none;stroke:" + CUT_STROKE + ";"
        "stroke-width:" + _fmt(CUT_STROKE_WIDTH_MM) + ";"
        "vector-effect:non-scaling-stroke}"
        ".print-stroke{fill:none;stroke:" + PRINT_STROKE + ";"
        "stroke-width:" + _fmt(PRINT_STROKE_WIDTH_MM) + ";stroke-linecap:butt}"
        ".print-text{fill:" + TEXT_COLOR + ";font-family:"
        '"Helvetica","Arial",sans-serif;font-weight:600;'
        "text-anchor:middle;dominant-baseline:middle}"
        "</style>"
    )
    parts.append(style)

    parts.append('<g id="print-layer" inkscape:label="Print" inkscape:groupmode="layer">')
    if opts.show_outline:
        parts.append(
            f'<circle class="print-stroke" cx="{_fmt(cx)}" cy="{_fmt(cy)}" '
            f'r="{_fmt(R - 0.2)}"/>'
        )
        parts.append(
            f'<circle class="print-stroke" cx="{_fmt(cx)}" cy="{_fmt(cy)}" '
            f'r="{_fmt(r_hub + 0.2)}"/>'
        )

    if opts.show_dividers:
        for i in range(n):
            angle = -90.0 + i * seg_deg
            x1, y1 = _polar(cx, cy, r_hub + 0.2, angle)
            x2, y2 = _polar(cx, cy, R - 0.2, angle)
            parts.append(
                f'<line class="print-stroke" '
                f'x1="{_fmt(x1)}" y1="{_fmt(y1)}" '
                f'x2="{_fmt(x2)}" y2="{_fmt(y2)}"/>'
            )

    # Text sits in the outer part of the annulus: at small radii a wedge
    # is too narrow; moving outward uses the longer arc and reads better.
    r_print = R - 0.2
    r_text_limit = r_print - OUTER_TEXT_MARGIN_MM
    annulus = r_text_limit - r_hub
    r_text = r_hub + annulus * TEXT_RADIAL_FRACTION
    r_text = min(r_text, r_text_limit - 0.15)

    # Arc half-chord at the text radius, reduced slightly so type does not
    # kiss the segment borders.
    arc_chord_at_text = (
        2 * r_text * math.sin(math.radians(seg_deg / 2)) * CHORD_SAFETY
    )
    r_in = r_text - (r_hub + 0.2)
    r_out = r_text_limit - r_text
    # Radial budget for a single line: more room on the “inside” of the
    # label (toward the hub) when the label is near the outer edge.
    radial_band = min(
        MAX_FONT_SIZE_MM,
        max(2.5, 0.38 * r_in + 0.5 * r_out + 0.6),
    )

    non_empty = [e.text for e in exercises if e.text]
    longest = max(non_empty, key=len, default="")
    font_size = _fit_font_size(
        longest,
        max_width_mm=arc_chord_at_text,
        max_height_mm=radial_band,
    )

    use_paths = text_to_path.is_available()
    for i, ex in enumerate(exercises):
        if not ex.text:
            continue
        mid = -90.0 + (i + 0.5) * seg_deg
        tx, ty = _polar(cx, cy, r_text, mid)
        rotate = mid + 90.0
        if use_paths:
            paths = text_to_path.render_text_paths(
                ex.text,
                cx=tx,
                cy=ty,
                font_size=font_size,
                rotation_deg=rotate,
                fill=TEXT_COLOR,
            )
            if paths:
                parts.append(paths)
                continue
        parts.append(
            f'<text class="print-text" x="{_fmt(tx)}" y="{_fmt(ty)}" '
            f'font-size="{_fmt(font_size)}" '
            f'transform="rotate({_fmt(rotate)} {_fmt(tx)} {_fmt(ty)})">'
            f'{escape(ex.text)}</text>'
        )

    parts.append("</g>")

    parts.append('<g id="cut-layer" inkscape:label="Cut" inkscape:groupmode="layer">')
    parts.append(
        f'<circle class="cut" cx="{_fmt(cx)}" cy="{_fmt(cy)}" r="{_fmt(R)}"/>'
    )
    parts.append(
        f'<circle class="cut" cx="{_fmt(cx)}" cy="{_fmt(cy)}" r="{_fmt(r_hub)}"/>'
    )
    parts.append("</g>")

    parts.append("</svg>")
    return "\n".join(parts)

"""Cricut Print-Then-Cut SVG renderer for the wheel-of-fortune cover.

Produces a single SVG document with two visually-distinct logical layers
that the teacher will identify in Cricut Design Space:

- Print layer: black filled text, thin segment dividers, two thin ring
  outlines (outer + around the hub), and — optionally — coloured
  segment fills behind everything else. These get flattened into one
  Print-Then-Cut image.
- Cut layer: red hairline-stroked circles (outer wheel + center hub /
  Nabe). These remain as cut paths in Design Space.

Coordinate system / scale
~~~~~~~~~~~~~~~~~~~~~~~~~
The geometry is computed in millimetres (the natural unit of the
physical wheel) and then converted to **inch user-units** at the moment
each attribute is written into the SVG. This is deliberate, because
real-world consumers disagree on how to interpret an SVG's units:

- Browsers, Inkscape and CairoSVG honour the ``width`` / ``height``
  attributes in physical units (we use ``mm``).
- Cricut Design Space (DS3) ignores the unit suffix on
  ``width`` / ``height`` and treats the viewBox as
  ``1 user unit = 1 inch``. It is also unreliable about respecting
  ``transform`` attributes on layer groups, so we cannot rely on a
  single outer ``scale()`` to bridge the unit gap.

The robust solution implemented here is therefore:

- ``viewBox`` is expressed in inches (``page_mm / 25.4``).
- ``width`` / ``height`` keep ``mm`` units so previews / PNG / PDF
  render at the correct physical size in every other tool.
- Every coordinate, radius, stroke width and font size is converted to
  inches *at write time* via :func:`_ifmt`. There are no transforms on
  layer groups, so Cricut imports the geometry at exactly the intended
  size without the teacher having to rescale.

Cricut also has a habit of ignoring ``fill="none"`` on imported
``<circle>`` elements (it shows them as solid black discs after
*Flatten*). The two thin printed rings are therefore drawn as
**filled annulus paths** instead of stroked circles: ``fill`` IS the
visible ring, so the outline survives any importer that strips
``fill="none"``.
"""
from __future__ import annotations

import base64
import colorsys
import math
from dataclasses import dataclass
from html import escape
from typing import Literal

from . import text_to_path, twemoji
from .exercises.base import Exercise

WHEEL_DIAMETER_CRICUT_MM = 170.0
WHEEL_DIAMETER_FULL_MM = 188.0
HUB_DIAMETER_MM = 19.0
HUB_CLEARANCE_MM = 0.4
SEGMENTS = 12

# Layout direction of each segment's label.
#   "horizontal": text runs along the chord (perpendicular to the radius),
#                 reading horizontally when the segment is at the top of
#                 the wheel. Best for short labels (e.g. single words,
#                 numbers).
#   "vertical":   text runs along the radius (from hub to outer edge),
#                 reading vertically when the segment is at the top.
#                 Useful when the label is long and needs the deeper
#                 radial dimension to fit at a readable size.
TextOrientation = Literal["horizontal", "vertical"]

# Colour scheme used to fill each segment.
#   "none":    no fill (white paper, current default).
#   "rainbow": evenly-spaced hues across the full colour wheel.
#   "blue" / "green" / "red": a family of related shades — hues drawn
#       from a narrow band so the result looks like a coordinated
#       palette rather than disco lights.
SegmentFillMode = Literal["none", "rainbow", "blue", "green", "red"]

# Hue band (start, end, in degrees on the HSL colour wheel) used by each
# colour-family fill mode. The band is walked linearly so the family
# flavour reads, while neighbouring slices alternate between a "light"
# and a "deep" lightness/saturation pair (see below) to keep them
# visually distinct rather than a near-imperceptible gradient.
_FAMILY_HUE_BANDS: dict[str, tuple[float, float]] = {
    "blue": (200.0, 245.0),
    "green": (95.0, 150.0),
    # The red band wraps around 0°: start past magenta, end in orange.
    "red": (340.0, 30.0),
}
# Rainbow already alternates hue strongly across the wheel, so it uses
# a single (sat, light) pair.
_FILL_SATURATION = 0.62
_FILL_LIGHTNESS = 0.78
# Family alternation: even-indexed segments get the light pastel, odd
# ones get a deeper, more saturated variant of the same hue. The deeper
# value still has L >= 0.60 so black text stays readable.
_FAMILY_LIGHT_S = 0.55
_FAMILY_LIGHT_L = 0.84
_FAMILY_DEEP_S = 0.66
_FAMILY_DEEP_L = 0.62

# Conversion used to bridge the mm-based coordinate space and the
# inch-based viewBox (see module docstring).
MM_PER_INCH = 25.4
MM_TO_IN = 1.0 / MM_PER_INCH

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
    text_orientation: TextOrientation = "horizontal"
    fill_mode: SegmentFillMode = "none"

    @property
    def hub_cut_diameter_mm(self) -> float:
        """Diameter of the cut hole = Nabe diameter + clearance."""
        return self.hub_diameter_mm + self.hub_clearance_mm


def _polar(cx: float, cy: float, r: float, angle_deg: float) -> tuple[float, float]:
    a = math.radians(angle_deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def _fmt(v: float) -> str:
    return f"{v:.4f}".rstrip("0").rstrip(".")


def _to_in(mm: float) -> float:
    """Convert a millimetre value to viewBox user-units (= inches)."""
    return mm * MM_TO_IN


def _ifmt(mm: float) -> str:
    """Format ``mm`` as a viewBox user-unit (inch) string for the SVG."""
    return _fmt(mm * MM_TO_IN)


def _hsl_hex(h_deg: float, s: float, l: float) -> str:
    h = (h_deg % 360.0) / 360.0
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (
        f"#{int(round(r * 255)):02X}"
        f"{int(round(g * 255)):02X}"
        f"{int(round(b * 255)):02X}"
    )


def _segment_fill_color(mode: SegmentFillMode, n: int, i: int) -> str | None:
    """Hex colour for segment ``i`` of ``n`` under fill mode ``mode``.

    Returns ``None`` when no fill should be drawn.
    """
    if mode == "none":
        return None
    if mode == "rainbow":
        # Evenly-spaced hues with a small offset so segment 0 (top) is a
        # warm tone rather than cold magenta against the divider.
        hue = (i * 360.0 / max(n, 1) + 15.0) % 360.0
        return _hsl_hex(hue, _FILL_SATURATION, _FILL_LIGHTNESS)
    band = _FAMILY_HUE_BANDS.get(mode)
    if band is None:
        return None
    start, end = band
    t = i / max(n - 1, 1)
    if end >= start:
        hue = start + (end - start) * t
    else:
        # Wrap-around band (e.g. red: 340° → 30° crosses 0°).
        span = (360.0 - start) + end
        hue = (start + span * t) % 360.0
    # Alternate light pastel / deeper tone so adjacent segments contrast
    # clearly even though they share the same family.
    if i % 2 == 0:
        return _hsl_hex(hue, _FAMILY_LIGHT_S, _FAMILY_LIGHT_L)
    return _hsl_hex(hue, _FAMILY_DEEP_S, _FAMILY_DEEP_L)


def _wedge_path_d(
    cx_mm: float,
    cy_mm: float,
    r_inner_mm: float,
    r_outer_mm: float,
    start_deg: float,
    end_deg: float,
) -> str:
    """SVG path ``d`` for an annular wedge (donut slice), in inch units.

    Coordinates and radii are converted to viewBox user-units (inches)
    on the way out, matching the convention used by every other path
    in this module.
    """
    p_in_start = _polar(cx_mm, cy_mm, r_inner_mm, start_deg)
    p_out_start = _polar(cx_mm, cy_mm, r_outer_mm, start_deg)
    p_out_end = _polar(cx_mm, cy_mm, r_outer_mm, end_deg)
    p_in_end = _polar(cx_mm, cy_mm, r_inner_mm, end_deg)
    ro = _ifmt(r_outer_mm)
    ri = _ifmt(r_inner_mm)
    large = 1 if (end_deg - start_deg) > 180 else 0
    return (
        f"M {_ifmt(p_in_start[0])} {_ifmt(p_in_start[1])} "
        f"L {_ifmt(p_out_start[0])} {_ifmt(p_out_start[1])} "
        f"A {ro} {ro} 0 {large} 1 "
        f"{_ifmt(p_out_end[0])} {_ifmt(p_out_end[1])} "
        f"L {_ifmt(p_in_end[0])} {_ifmt(p_in_end[1])} "
        f"A {ri} {ri} 0 {large} 0 "
        f"{_ifmt(p_in_start[0])} {_ifmt(p_in_start[1])} Z"
    )


def _ring_path_d(cx_mm: float, cy_mm: float, r_outer_mm: float, r_inner_mm: float) -> str:
    """Build a filled-ring (annulus) ``d`` attribute in inch user-units.

    The path is a single ``<path>`` whose two sub-paths describe the
    outer and inner circles. With ``fill-rule="evenodd"`` the area
    between them is filled, giving a thin ring whose appearance does
    not depend on the importer respecting ``fill="none"`` on a stroked
    circle.
    """
    cx = _to_in(cx_mm)
    cy = _to_in(cy_mm)
    ro = _to_in(r_outer_mm)
    ri = _to_in(r_inner_mm)
    return (
        f"M {_fmt(cx + ro)} {_fmt(cy)} "
        f"A {_fmt(ro)} {_fmt(ro)} 0 1 0 {_fmt(cx - ro)} {_fmt(cy)} "
        f"A {_fmt(ro)} {_fmt(ro)} 0 1 0 {_fmt(cx + ro)} {_fmt(cy)} Z "
        f"M {_fmt(cx + ri)} {_fmt(cy)} "
        f"A {_fmt(ri)} {_fmt(ri)} 0 1 0 {_fmt(cx - ri)} {_fmt(cy)} "
        f"A {_fmt(ri)} {_fmt(ri)} 0 1 0 {_fmt(cx + ri)} {_fmt(cy)} Z"
    )


# Rasterization DPI used when flattening the print layer for Cricut.
# 300 dpi matches typical home-printer output; raising it inflates the
# embedded base64 payload without any visible quality benefit.
FLATTEN_DPI = 300


def _rasterize_print_layer(
    print_inner_svg: str,
    page_mm: float,
    page_in: float,
) -> str:
    """Rasterize the print-layer body and return an ``<image>`` element.

    The returned tag covers the full page, in viewBox (inch) user-units,
    so it drops in as a 1:1 replacement for the inline print elements.
    """
    import cairosvg

    standalone = (
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{_fmt(page_mm)}mm" height="{_fmt(page_mm)}mm" '
        f'viewBox="0 0 {_fmt(page_in)} {_fmt(page_in)}" '
        'shape-rendering="geometricPrecision" '
        'text-rendering="geometricPrecision">'
        f"{print_inner_svg}"
        "</svg>"
    )
    output_size_px = max(1, int(round(page_mm / 25.4 * FLATTEN_DPI)))
    png_bytes = cairosvg.svg2png(
        bytestring=standalone.encode("utf-8"),
        output_width=output_size_px,
        output_height=output_size_px,
    )
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return (
        '<image x="0" y="0" '
        f'width="{_fmt(page_in)}" height="{_fmt(page_in)}" '
        'preserveAspectRatio="none" '
        f'href="data:image/png;base64,{b64}"/>'
    )


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
    flatten_print: bool = False,
) -> str:
    """Render the wheel SVG.

    When ``flatten_print`` is ``True`` the entire print layer (fills,
    rings, dividers, text) is rasterized to a single embedded PNG. The
    cut layer keeps its two vector circles. This is the right choice
    for Cricut Design Space, which would otherwise import every
    ``<path>`` as a separate cuttable layer; with the print layer
    flattened, only the two red circles end up cut.
    """
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
    page_in = page * MM_TO_IN

    parts: list[str] = []
    parts.append(
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
    )
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
        f'width="{_fmt(page)}mm" height="{_fmt(page)}mm" '
        f'viewBox="0 0 {_fmt(page_in)} {_fmt(page_in)}" '
        f'shape-rendering="geometricPrecision" '
        f'text-rendering="geometricPrecision">'
    )

    if opts.title:
        parts.append(f"<title>{escape(opts.title)}</title>")

    # No <style> block: Cricut Design Space ignores stylesheets at
    # import. Every visual attribute is therefore inlined directly on
    # the elements below.

    print_stroke_width_in = _ifmt(PRINT_STROKE_WIDTH_MM)
    divider_attrs = (
        f'fill="none" stroke="{PRINT_STROKE}" '
        f'stroke-width="{print_stroke_width_in}" '
        f'stroke-linecap="butt"'
    )

    # Print elements are accumulated here separately from the top-level
    # `parts` so we can either splice them in inline (vector preview
    # path) or rasterize the lot into a single <image> for Cricut.
    print_parts: list[str] = []

    if opts.fill_mode != "none":
        # Fills go in *first* so the printed rings, dividers and labels
        # all sit on top. Wedge boundaries match the printable annulus
        # (between the two thin rings) so the fills never poke past the
        # visible structure of the wheel.
        r_fill_inner = r_hub + 0.2
        r_fill_outer = R - 0.2
        for i in range(n):
            color = _segment_fill_color(opts.fill_mode, n, i)
            if not color:
                continue
            start_deg = -90.0 + i * seg_deg
            end_deg = -90.0 + (i + 1) * seg_deg
            d = _wedge_path_d(
                cx, cy, r_fill_inner, r_fill_outer, start_deg, end_deg,
            )
            print_parts.append(
                f'<path d="{d}" fill="{color}" stroke="none"/>'
            )

    if opts.show_outline:
        # The two visible printed rings. They were originally stroked
        # circles centred on r=R-0.2 / r=r_hub+0.2 with stroke-width
        # PRINT_STROKE_WIDTH_MM. We replicate the exact visible coverage
        # as a filled annulus path so the appearance survives importers
        # that strip ``fill="none"`` from <circle>.
        half = PRINT_STROKE_WIDTH_MM / 2.0
        outer_d = _ring_path_d(
            cx, cy,
            r_outer_mm=(R - 0.2) + half,
            r_inner_mm=(R - 0.2) - half,
        )
        hub_d = _ring_path_d(
            cx, cy,
            r_outer_mm=(r_hub + 0.2) + half,
            r_inner_mm=(r_hub + 0.2) - half,
        )
        ring_attrs = f'fill="{PRINT_STROKE}" fill-rule="evenodd" stroke="none"'
        print_parts.append(f'<path {ring_attrs} d="{outer_d}"/>')
        print_parts.append(f'<path {ring_attrs} d="{hub_d}"/>')

    if opts.show_dividers:
        for i in range(n):
            angle = -90.0 + i * seg_deg
            x1, y1 = _polar(cx, cy, r_hub + 0.2, angle)
            x2, y2 = _polar(cx, cy, R - 0.2, angle)
            print_parts.append(
                f'<line {divider_attrs} '
                f'x1="{_ifmt(x1)}" y1="{_ifmt(y1)}" '
                f'x2="{_ifmt(x2)}" y2="{_ifmt(y2)}"/>'
            )

    # The annulus (printable text band) runs from just outside the hub
    # to just inside the outer ring.
    r_print = R - 0.2
    r_text_limit = r_print - OUTER_TEXT_MARGIN_MM
    r_text_inner = r_hub + 0.2

    if opts.text_orientation == "vertical":
        # Radial layout: text runs along the radius, so its long axis is
        # the radial depth and its short axis is the local chord. Centre
        # the label in the middle of the annulus so it can extend evenly
        # toward both the hub and the outer ring.
        r_text = (r_text_inner + r_text_limit) / 2.0
        max_width_mm = (r_text_limit - r_text_inner) * CHORD_SAFETY
        max_height_mm = (
            2 * r_text * math.sin(math.radians(seg_deg / 2)) * CHORD_SAFETY
        )
        # rotate(mid) aligns the text baseline with the radial direction,
        # reading from hub outward in every segment.
        rotation_offset = 0.0
    else:
        # Horizontal (tangential) layout: text runs along the chord and
        # sits in the outer part of the annulus where the arc is widest.
        annulus = r_text_limit - r_hub
        r_text = r_hub + annulus * TEXT_RADIAL_FRACTION
        r_text = min(r_text, r_text_limit - 0.15)
        max_width_mm = (
            2 * r_text * math.sin(math.radians(seg_deg / 2)) * CHORD_SAFETY
        )
        r_in = r_text - r_text_inner
        r_out = r_text_limit - r_text
        # Asymmetric radial budget: more room toward the hub since labels
        # sit near the outer edge.
        max_height_mm = min(
            MAX_FONT_SIZE_MM,
            max(2.5, 0.38 * r_in + 0.5 * r_out + 0.6),
        )
        rotation_offset = 90.0

    # Place each emoji at the radius where the largest axis-aligned
    # square fits inside the wedge. For a sector of half-angle ``α``
    # the binding chord constraint at radius ``r`` is
    # ``s ≤ 2·r·tan(α) / (1 + tan(α))`` (the near-corners hit the
    # radial edge first). Setting that equal to the outer radial
    # budget ``s = 2·(r_out − r)`` and solving for r gives the sweet
    # spot:
    #
    #     r* = 2·r_out / (2 + chord_factor)
    #
    # where ``chord_factor = 2·tan(α)/(1+tan(α))``. Both constraints
    # bind there, so the inscribed square is as big as the geometry
    # allows. For 12 segments this lands at ~82 % of r_out — same
    # neighbourhood as TEXT_RADIAL_FRACTION, only it's derived from
    # geometry instead of being eyeballed.
    alpha_rad = math.radians(seg_deg / 2)
    tan_alpha = math.tan(alpha_rad)
    chord_factor = 2.0 * tan_alpha / (1.0 + tan_alpha)
    r_emoji_opt = 2.0 * r_text_limit / (2.0 + chord_factor)
    r_emoji = max(r_text_inner + 1.0, min(r_text_limit - 1.0, r_emoji_opt))
    emoji_box_mm = max(
        2.0,
        CHORD_SAFETY
        * min(
            chord_factor * r_emoji,
            2.0 * (r_text_limit - r_emoji),
            2.0 * (r_emoji - r_text_inner),
        ),
    )

    # Font size is chosen from text-only segments so emoji-bearing
    # entries don't pull the text size down for everyone else.
    non_empty = [e.text for e in exercises if e.text and not e.emoji]
    longest = max(non_empty, key=len, default="")
    font_size = _fit_font_size(
        longest,
        max_width_mm=max_width_mm,
        max_height_mm=max_height_mm,
    )

    use_paths = text_to_path.is_available()
    text_fallback_attrs = (
        f'fill="{TEXT_COLOR}" '
        'font-family="Helvetica, Arial, sans-serif" font-weight="600" '
        'text-anchor="middle" dominant-baseline="middle"'
    )
    for i, ex in enumerate(exercises):
        mid = -90.0 + (i + 0.5) * seg_deg
        rotate = mid + rotation_offset
        if ex.emoji:
            ex_cx, ex_cy = _polar(cx, cy, r_emoji, mid)
            group = twemoji.render_emoji_group(
                ex.emoji,
                cx=_to_in(ex_cx),
                cy=_to_in(ex_cy),
                box_size=_to_in(emoji_box_mm),
                rotation_deg=rotate,
            )
            if group:
                print_parts.append(group)
                continue
            # Fallback when Twemoji is unreachable: the browser preview
            # still shows the system-font emoji glyph, even if Cricut
            # would not pick it up.
            print_parts.append(
                f'<text {text_fallback_attrs} '
                f'x="{_ifmt(ex_cx)}" y="{_ifmt(ex_cy)}" '
                f'font-size="{_ifmt(emoji_box_mm * 0.9)}" '
                f'transform="rotate({_fmt(rotate)} '
                f'{_ifmt(ex_cx)} {_ifmt(ex_cy)})">'
                f"{escape(ex.emoji)}</text>"
            )
            continue
        if not ex.text:
            continue
        tx, ty = _polar(cx, cy, r_text, mid)
        if use_paths:
            # ``text_to_path`` works in whatever unit it is fed; pass
            # inches so its output matches the surrounding viewBox.
            paths = text_to_path.render_text_paths(
                ex.text,
                cx=_to_in(tx),
                cy=_to_in(ty),
                font_size=_to_in(font_size),
                rotation_deg=rotate,
                fill=TEXT_COLOR,
            )
            if paths:
                print_parts.append(paths)
                continue
        print_parts.append(
            f'<text {text_fallback_attrs} '
            f'x="{_ifmt(tx)}" y="{_ifmt(ty)}" '
            f'font-size="{_ifmt(font_size)}" '
            f'transform="rotate({_fmt(rotate)} {_ifmt(tx)} {_ifmt(ty)})">'
            f'{escape(ex.text)}</text>'
        )

    parts.append(
        '<g id="print-layer" inkscape:label="Print" inkscape:groupmode="layer">'
    )
    if flatten_print:
        # Cricut Design Space imports each <path> as its own cuttable
        # layer. By collapsing the entire print body into one embedded
        # PNG we leave Cricut nothing to mistake for a cut path — only
        # the two red circles below remain as actual cut geometry.
        parts.append(
            _rasterize_print_layer(
                "\n".join(print_parts),
                page_mm=page,
                page_in=page_in,
            )
        )
    else:
        parts.extend(print_parts)
    parts.append("</g>")

    cut_attrs = (
        f'fill="none" stroke="{CUT_STROKE}" '
        f'stroke-width="{_ifmt(CUT_STROKE_WIDTH_MM)}"'
    )
    parts.append(
        '<g id="cut-layer" inkscape:label="Cut" inkscape:groupmode="layer">'
    )
    parts.append(
        f'<circle {cut_attrs} cx="{_ifmt(cx)}" cy="{_ifmt(cy)}" r="{_ifmt(R)}"/>'
    )
    parts.append(
        f'<circle {cut_attrs} cx="{_ifmt(cx)}" cy="{_ifmt(cy)}" '
        f'r="{_ifmt(r_hub)}"/>'
    )
    parts.append("</g>")

    parts.append("</svg>")
    return "\n".join(parts)

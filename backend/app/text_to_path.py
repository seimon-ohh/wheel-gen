"""Convert short text strings to SVG ``<path>`` outlines.

We need this because:

1. Cricut Design Space silently ignores ``<text>`` elements when importing
   SVG files, so any aufgaben-text rendered as text would not appear on
   the print-then-cut output.
2. CairoSVG's raster (PNG) backend has shaky support for
   ``dominant-baseline`` and font metrics, which made the PNG look
   wrong while the PDF (which uses a different code path) looked fine.

Replacing ``<text>`` with vector paths drawn from glyph outlines makes
the SVG completely self-contained and renders identically across
browsers, Cricut, CairoSVG-PNG, and CairoSVG-PDF.

We bundle no font in the repo; instead we look for a sensible system
font on Linux/macOS/Windows. The Docker image installs
``fonts-dejavu-core`` so the production path is deterministic. The path
can be overridden with the ``WHEEL_FONT_PATH`` environment variable.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from html import escape

try:
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.ttLib import TTFont
except ImportError:  # pragma: no cover - dev fallback
    SVGPathPen = None  # type: ignore[assignment]
    TTFont = None  # type: ignore[assignment]


_CANDIDATE_FONTS: tuple[tuple[str, int], ...] = (
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 0),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 0),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 0),
    ("/Library/Fonts/Arial Bold.ttf", 0),
    ("/Library/Fonts/Arial.ttf", 0),
    ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 0),
    ("/System/Library/Fonts/Supplemental/Arial.ttf", 0),
    ("/System/Library/Fonts/Helvetica.ttc", 0),
    ("C:/Windows/Fonts/arialbd.ttf", 0),
    ("C:/Windows/Fonts/arial.ttf", 0),
)


@dataclass(frozen=True)
class LoadedFont:
    font: object
    cap_height: float
    ascender: float
    descender: float
    units_per_em: int


def _resolve_font_path() -> tuple[str, int] | None:
    env = os.environ.get("WHEEL_FONT_PATH")
    if env and os.path.isfile(env):
        return (env, 0)
    for path, idx in _CANDIDATE_FONTS:
        if os.path.isfile(path):
            return (path, idx)
    return None


@lru_cache(maxsize=1)
def _load() -> LoadedFont | None:
    if TTFont is None:
        return None
    resolved = _resolve_font_path()
    if not resolved:
        return None
    path, idx = resolved
    try:
        kwargs: dict = {"lazy": True}
        if path.lower().endswith(".ttc") or path.lower().endswith(".otc"):
            kwargs["fontNumber"] = idx
        font = TTFont(path, **kwargs)
    except Exception:
        return None

    upem = int(font["head"].unitsPerEm)
    os2 = font.get("OS/2")
    hhea = font.get("hhea")
    cap_height = float(getattr(os2, "sCapHeight", 0) or 0)
    ascender = float(
        getattr(os2, "sTypoAscender", None)
        or getattr(hhea, "ascent", None)
        or upem * 0.8
    )
    descender = float(
        getattr(os2, "sTypoDescender", None)
        or getattr(hhea, "descent", None)
        or -upem * 0.2
    )
    if cap_height <= 0:
        cap_height = ascender * 0.7
    return LoadedFont(
        font=font,
        cap_height=cap_height,
        ascender=ascender,
        descender=descender,
        units_per_em=upem,
    )


def is_available() -> bool:
    return _load() is not None


def measure_text(text: str, font_size: float) -> float:
    """Return the visual width of ``text`` in the same units as ``font_size``."""
    loaded = _load()
    if not loaded:
        return font_size * 0.55 * len(text)
    font = loaded.font
    cmap = font.getBestCmap()  # type: ignore[union-attr]
    hmtx = font["hmtx"]  # type: ignore[index]
    scale = font_size / loaded.units_per_em
    width = 0.0
    fallback = cmap.get(ord("?"))
    for ch in text:
        gname = cmap.get(ord(ch), fallback)
        if not gname:
            continue
        adv = hmtx[gname][0]
        width += adv * scale
    return width


def render_text_paths(
    text: str,
    cx: float,
    cy: float,
    font_size: float,
    rotation_deg: float = 0.0,
    fill: str = "#111111",
) -> str | None:
    """Render ``text`` as a group of SVG ``<path>`` elements centered on
    ``(cx, cy)`` and rotated by ``rotation_deg``.

    Returns ``None`` if no usable font was found, so the caller can fall
    back to a regular ``<text>`` element.
    """
    loaded = _load()
    if not loaded:
        return None
    font = loaded.font
    cmap = font.getBestCmap()  # type: ignore[union-attr]
    glyph_set = font.getGlyphSet()  # type: ignore[union-attr]
    hmtx = font["hmtx"]  # type: ignore[index]
    scale = font_size / loaded.units_per_em

    width = measure_text(text, font_size)
    cap_h = loaded.cap_height * scale

    glyph_paths: list[str] = []
    cur_x = -width / 2.0
    fallback = cmap.get(ord("?"))
    for ch in text:
        gname = cmap.get(ord(ch), fallback)
        if not gname:
            continue
        glyph = glyph_set[gname]
        pen = SVGPathPen(glyph_set)  # type: ignore[misc]
        glyph.draw(pen)
        d = pen.getCommands()
        if d:
            glyph_paths.append(
                f'<path d="{d}" '
                f'transform="translate({cur_x:.4f} 0) '
                f'scale({scale:.6f} {-scale:.6f})"/>'
            )
        adv = hmtx[gname][0]
        cur_x += adv * scale

    inner = "".join(glyph_paths)
    fill_attr = f' fill="{escape(fill)}"' if fill else ""
    return (
        f'<g transform="translate({cx:.4f} {cy:.4f}) '
        f'rotate({rotation_deg:.4f}) translate(0 {cap_h / 2:.4f})"'
        f'{fill_attr}>{inner}</g>'
    )

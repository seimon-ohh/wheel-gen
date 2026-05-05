from __future__ import annotations

import io
import random
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..exercises import bildwoerter as bildwoerter_mod
from ..exercises.base import Exercise
from ..exercises.registry import get_generator, list_generators
from ..wheel import (
    HUB_CLEARANCE_MM,
    HUB_DIAMETER_MM,
    PAGE_PADDING_MM,
    WHEEL_DIAMETER_CRICUT_MM,
    WHEEL_DIAMETER_FULL_MM,
    WheelOptions,
    render_wheel_svg,
)

# Cricut Design Space imports raster images at 6 px/mm = 152.4 DPI
# regardless of what the file's pHYs chunk says. (Empirically: a 180
# mm SVG rasterised by cairosvg at dpi=300 — 2126 px square — comes
# in at 35.42 cm = 354.2 mm in DS3, which is exactly 2126 / 354.2 =
# 6.00 px/mm.) Rendering the PNG download at this exact pixel density
# makes the imported image land at the physical size the teacher
# selected, even though Design Space ignores the embedded DPI. We
# also write a matching pHYs chunk so other tools (Inkscape, GIMP,
# Pillow) read the same physical size.
PNG_PIXELS_PER_MM = 6.0

router = APIRouter(prefix="/api", tags=["wheel"])

SizeMode = Literal["cricut", "full"]
TextOrientation = Literal["horizontal", "vertical"]
SegmentFillMode = Literal["none", "rainbow", "blue", "green", "red"]


# ---------- shared models ----------

class Item(BaseModel):
    text: str = ""
    answer: str = ""
    emoji: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)


# ---------- /api/items ----------

class ItemsRequest(BaseModel):
    generator_id: str
    params: dict[str, Any] = Field(default_factory=dict)
    count: int = Field(default=12, ge=1, le=24)
    seed: int | None = None


class ItemsResponse(BaseModel):
    seed: int
    items: list[Item]


# ---------- /api/render & download ----------

class RenderRequest(BaseModel):
    items: list[Item]
    segments: int = Field(default=12, ge=2, le=24)
    size: SizeMode = "cricut"
    hub_diameter_mm: float = Field(
        default=HUB_DIAMETER_MM,
        ge=5.0,
        le=60.0,
    )
    hub_clearance_mm: float = Field(
        default=HUB_CLEARANCE_MM,
        ge=0.0,
        le=5.0,
    )
    text_orientation: TextOrientation = "horizontal"
    fill_mode: SegmentFillMode = "none"
    title: str | None = None


class RenderResponse(BaseModel):
    segments: int
    size: SizeMode
    diameter_mm: float
    hub_diameter_mm: float
    hub_clearance_mm: float
    hub_cut_diameter_mm: float
    svg: str


# ---------- helpers ----------

def _diameter_for(size: SizeMode) -> float:
    return WHEEL_DIAMETER_CRICUT_MM if size == "cricut" else WHEEL_DIAMETER_FULL_MM


def _items_to_exercises(items: list[Item]) -> list[Exercise]:
    return [
        Exercise(
            text=i.text,
            answer=i.answer,
            emoji=i.emoji,
            meta=dict(i.meta),
        )
        for i in items
    ]


def _render(
    req: RenderRequest,
    *,
    flatten_print: bool = False,
) -> tuple[RenderResponse, str]:
    if len(req.items) != req.segments:
        raise HTTPException(
            status_code=400,
            detail=(
                f"items length ({len(req.items)}) must equal "
                f"segments ({req.segments})"
            ),
        )

    options = WheelOptions(
        diameter_mm=_diameter_for(req.size),
        hub_diameter_mm=req.hub_diameter_mm,
        hub_clearance_mm=req.hub_clearance_mm,
        segments=req.segments,
        text_orientation=req.text_orientation,
        fill_mode=req.fill_mode,
        title=req.title,
    )
    svg = render_wheel_svg(
        _items_to_exercises(req.items),
        options,
        flatten_print=flatten_print,
    )
    return (
        RenderResponse(
            segments=req.segments,
            size=req.size,
            diameter_mm=options.diameter_mm,
            hub_diameter_mm=options.hub_diameter_mm,
            hub_clearance_mm=options.hub_clearance_mm,
            hub_cut_diameter_mm=options.hub_cut_diameter_mm,
            svg=svg,
        ),
        svg,
    )


# ---------- routes ----------

@router.get("/exercise-types")
def exercise_types() -> list[dict[str, Any]]:
    return [g.schema() for g in list_generators()]


@router.get("/emoji-catalog")
def emoji_catalog() -> dict[str, Any]:
    """Catalog used by the manual emoji picker in the segment editor.

    Single source of truth: the same data drives the ``bildwoerter``
    generator (server-side random picks) and the per-row picker
    (client-side manual override). Shape is intentionally simple —
    one ``categories`` list with stable IDs so the frontend can use
    them as React keys without depending on label translations.
    """
    categories: list[dict[str, Any]] = []
    for cat_id, label in bildwoerter_mod.category_order():
        entries = bildwoerter_mod.CATEGORIES[label]
        categories.append(
            {
                "id": cat_id,
                "label": label,
                "emojis": [
                    {"emoji": emoji, "word": word}
                    for emoji, word in entries
                ],
            }
        )
    return {"categories": categories}


@router.post("/items", response_model=ItemsResponse)
def items(req: ItemsRequest) -> ItemsResponse:
    try:
        generator = get_generator(req.generator_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    seed = req.seed if req.seed is not None else random.randint(0, 2**31 - 1)
    rng = random.Random(seed)
    exercises = generator.generate(count=req.count, params=req.params, rng=rng)
    return ItemsResponse(
        seed=seed,
        items=[
            Item(text=e.text, answer=e.answer, emoji=e.emoji, meta=e.meta)
            for e in exercises
        ],
    )


@router.post("/render", response_model=RenderResponse)
def render(req: RenderRequest) -> RenderResponse:
    response, _ = _render(req)
    return response


@router.post("/download.svg")
def download_svg(req: RenderRequest) -> Response:
    # The SVG download is the Cricut workflow: flatten the entire print
    # layer into a single embedded raster image so Design Space cannot
    # mistake any divider, ring or glyph for a cut path. Only the two
    # red circles below remain as cuttable geometry.
    _, svg = _render(req, flatten_print=True)
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Content-Disposition": 'attachment; filename="gluecksrad.svg"'},
    )


def _png_with_phys(svg: str, page_mm: float, ppm: float) -> bytes:
    """Render ``svg`` to a square PNG of exactly ``page_mm * ppm`` px
    and rewrite the pHYs chunk so the file's metadata also reports
    ``ppm`` pixels-per-millimetre.

    Cricut Design Space ignores embedded DPI and applies its own
    fixed 6 px/mm scale to imported PNGs — so the *only* way to land
    at a given physical size is to control the pixel count directly.
    Other tools (Inkscape, GIMP, Pillow, browsers) DO honour pHYs, so
    we still write it consistently for those workflows.
    """
    import cairosvg

    px = max(1, int(round(page_mm * ppm)))
    buf = io.BytesIO()
    cairosvg.svg2png(
        bytestring=svg.encode("utf-8"),
        write_to=buf,
        output_width=px,
        output_height=px,
    )
    return _png_set_phys(buf.getvalue(), ppm)


def _png_set_phys(png: bytes, ppm: float) -> bytes:
    """Replace any pHYs chunk in ``png`` with one specifying
    ``ppm`` pixels-per-millimetre.

    The pHYs chunk goes immediately after IHDR, where every PNG
    decoder expects to find resolution metadata. We strip any
    previously-written pHYs (cairosvg writes its own with whatever
    DPI it inferred) so there is exactly one source of truth.
    """
    import struct
    import zlib

    if not png.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("not a PNG")

    # IHDR is always the first chunk after the 8-byte signature.
    ihdr_len = struct.unpack(">I", png[8:12])[0]
    ihdr_end = 12 + 4 + ihdr_len + 4  # length + 'IHDR' + data + crc

    # pHYs payload: pixels-per-meter (x, y) + unit byte (1 = metres).
    ppmeter = int(round(ppm * 1000.0))
    data = struct.pack(">IIB", ppmeter, ppmeter, 1)
    crc = zlib.crc32(b"pHYs" + data)
    new_phys = struct.pack(">I", 9) + b"pHYs" + data + struct.pack(">I", crc)

    rest = png[ihdr_end:]
    out = bytearray()
    pos = 0
    while pos < len(rest):
        if pos + 8 > len(rest):
            out += rest[pos:]
            break
        ln = struct.unpack(">I", rest[pos:pos + 4])[0]
        ty = bytes(rest[pos + 4:pos + 8])
        full = 4 + 4 + ln + 4
        if ty == b"pHYs":
            # Drop any existing pHYs; we re-add ours after IHDR.
            pos += full
            continue
        out += rest[pos:pos + full]
        pos += full

    return png[:ihdr_end] + new_phys + bytes(out)


@router.post("/download.png")
def download_png(req: RenderRequest) -> Response:
    _, svg = _render(req)
    page_mm = _diameter_for(req.size) + 2.0 * PAGE_PADDING_MM
    png_bytes = _png_with_phys(svg, page_mm=page_mm, ppm=PNG_PIXELS_PER_MM)
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Content-Disposition": 'attachment; filename="gluecksrad.png"'},
    )


@router.post("/download.pdf")
def download_pdf(req: RenderRequest) -> Response:
    import cairosvg

    _, svg = _render(req)
    buf = io.BytesIO()
    cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=buf)
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="gluecksrad.pdf"'},
    )

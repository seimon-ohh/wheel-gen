from __future__ import annotations

import io
import random
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..exercises.base import Exercise
from ..exercises.registry import get_generator, list_generators
from ..wheel import (
    HUB_CLEARANCE_MM,
    HUB_DIAMETER_MM,
    WHEEL_DIAMETER_CRICUT_MM,
    WHEEL_DIAMETER_FULL_MM,
    WheelOptions,
    render_wheel_svg,
)

router = APIRouter(prefix="/api", tags=["wheel"])

SizeMode = Literal["cricut", "full"]


# ---------- shared models ----------

class Item(BaseModel):
    text: str = ""
    answer: str = ""
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
    return [Exercise(text=i.text, answer=i.answer, meta=dict(i.meta)) for i in items]


def _render(req: RenderRequest) -> tuple[RenderResponse, str]:
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
        title=req.title,
    )
    svg = render_wheel_svg(_items_to_exercises(req.items), options)
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
            Item(text=e.text, answer=e.answer, meta=e.meta) for e in exercises
        ],
    )


@router.post("/render", response_model=RenderResponse)
def render(req: RenderRequest) -> RenderResponse:
    response, _ = _render(req)
    return response


@router.post("/download.svg")
def download_svg(req: RenderRequest) -> Response:
    _, svg = _render(req)
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Content-Disposition": 'attachment; filename="gluecksrad.svg"'},
    )


@router.post("/download.png")
def download_png(req: RenderRequest) -> Response:
    import cairosvg

    _, svg = _render(req)
    buf = io.BytesIO()
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=buf, dpi=300)
    return Response(
        content=buf.getvalue(),
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

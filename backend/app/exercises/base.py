from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Exercise:
    """A single exercise to display in one wheel segment.

    A segment shows either an ``emoji`` (rendered as a Twemoji vector
    image — see :mod:`app.twemoji`) or its ``text``. When an emoji is
    set it takes precedence and is the only content drawn in the
    segment; ``text`` and ``answer`` then exist purely for the answer
    key shown to the teacher.
    """

    text: str
    answer: str = ""
    emoji: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParamSpec:
    """Describes a generator parameter so the frontend can render a control."""

    key: str
    label: str
    type: str
    default: Any
    min: int | None = None
    max: int | None = None
    help: str | None = None


class ExerciseGenerator(ABC):
    """Base class for exercise generators.

    Subclasses provide an id, label, parameter schema, and a `generate`
    method that returns exactly `count` exercises using the given params.
    """

    id: str = ""
    label: str = ""
    description: str = ""
    params: list[ParamSpec] = []

    def schema(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "params": [p.__dict__ for p in self.params],
        }

    def _resolved_params(self, params: dict[str, Any] | None) -> dict[str, Any]:
        params = params or {}
        out: dict[str, Any] = {}
        for spec in self.params:
            value = params.get(spec.key, spec.default)
            if spec.type in ("int", "number") and value is not None:
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    value = spec.default
                if spec.min is not None and value < spec.min:
                    value = spec.min
                if spec.max is not None and value > spec.max:
                    value = spec.max
            out[spec.key] = value
        return out

    @abstractmethod
    def generate(
        self,
        count: int = 12,
        params: dict[str, Any] | None = None,
        rng: random.Random | None = None,
    ) -> list[Exercise]:
        ...

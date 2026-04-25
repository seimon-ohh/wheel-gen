from __future__ import annotations

import random
from typing import Any

from .base import Exercise, ExerciseGenerator, ParamSpec


class Kleines1x1Generator(ExerciseGenerator):
    id = "kleines_1x1"
    label = "Kleines 1x1"
    description = "Multiplikationsaufgaben mit Faktoren in einem wählbaren Bereich."
    params = [
        ParamSpec(
            key="min_factor",
            label="Kleinster Faktor",
            type="int",
            default=1,
            min=1,
            max=20,
        ),
        ParamSpec(
            key="max_factor",
            label="Größter Faktor",
            type="int",
            default=10,
            min=1,
            max=20,
        ),
        ParamSpec(
            key="exclude_trivial",
            label="Triviale Aufgaben (×1, ×0) ausschließen",
            type="bool",
            default=False,
        ),
    ]

    def generate(
        self,
        count: int = 12,
        params: dict[str, Any] | None = None,
        rng: random.Random | None = None,
    ) -> list[Exercise]:
        rng = rng or random.Random()
        p = self._resolved_params(params)
        lo, hi = p["min_factor"], p["max_factor"]
        if lo > hi:
            lo, hi = hi, lo

        pool: list[tuple[int, int]] = []
        for a in range(lo, hi + 1):
            for b in range(lo, hi + 1):
                if p.get("exclude_trivial") and (a <= 1 or b <= 1):
                    continue
                pool.append((a, b))

        if not pool:
            pool = [(a, b) for a in range(lo, hi + 1) for b in range(lo, hi + 1)]

        unique: list[tuple[int, int]] = []
        seen: set[frozenset[int]] = set()
        rng.shuffle(pool)
        for a, b in pool:
            key = frozenset({a, b}) if a != b else frozenset({a})
            if key in seen:
                continue
            seen.add(key)
            unique.append((a, b))
            if len(unique) == count:
                break

        if len(unique) < count:
            extra_needed = count - len(unique)
            extra = rng.choices(pool, k=extra_needed)
            unique.extend(extra)

        rng.shuffle(unique)
        return [
            Exercise(
                text=f"{a} \u00d7 {b}",
                answer=str(a * b),
                meta={"a": a, "b": b},
            )
            for a, b in unique[:count]
        ]

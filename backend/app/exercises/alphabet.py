from __future__ import annotations

import random
from typing import Any

from .base import Exercise, ExerciseGenerator, ParamSpec

LATIN_UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
UMLAUT_UPPER = "ÄÖÜ"
ESZETT = "ß"


class AlphabetGenerator(ExerciseGenerator):
    id = "alphabet"
    label = "Alphabet"
    description = (
        "Zufällige Buchstaben für Sprachübungen, z. B. "
        "„Nenne ein Wort, das mit diesem Buchstaben beginnt“."
    )
    params = [
        ParamSpec(
            key="case",
            label="Schreibweise",
            type="string",
            default="upper",
            help="upper | lower | mixed",
        ),
        ParamSpec(
            key="include_umlauts",
            label="Umlaute (Ä Ö Ü) einschließen",
            type="bool",
            default=False,
        ),
        ParamSpec(
            key="include_eszett",
            label="ß einschließen",
            type="bool",
            default=False,
        ),
        ParamSpec(
            key="unique",
            label="Nur unterschiedliche Buchstaben",
            type="bool",
            default=True,
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
        case = (p.get("case") or "upper").lower()
        if case not in {"upper", "lower", "mixed"}:
            case = "upper"

        pool = list(LATIN_UPPER)
        if p.get("include_umlauts"):
            pool += list(UMLAUT_UPPER)
        if p.get("include_eszett"):
            pool.append(ESZETT)

        if p.get("unique") and len(pool) >= count:
            chosen = rng.sample(pool, count)
        else:
            chosen = [rng.choice(pool) for _ in range(count)]

        out: list[Exercise] = []
        for ch in chosen:
            display = ch
            if case == "lower":
                display = ch.lower() if ch != ESZETT else ESZETT
            elif case == "mixed":
                low = ch.lower() if ch != ESZETT else ESZETT
                display = f"{ch} {low}"
            out.append(Exercise(text=display, answer="", meta={"letter": ch}))
        return out

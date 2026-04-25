from __future__ import annotations

import random
from typing import Any

from .base import Exercise, ExerciseGenerator, ParamSpec

NOMEN = [
    "Hund", "Katze", "Schule", "Buch", "Tisch", "Apfel", "Auto", "Baum",
    "Lehrer", "Freund", "Pferd", "Kuchen", "Garten", "Fenster", "Stuhl",
    "Brille", "Sonne", "Vogel", "Maus", "Ball", "Tasche", "Blume",
    "Kind", "Haus", "Brot", "Wasser",
]

VERBEN = [
    "laufen", "springen", "lesen", "schreiben", "essen", "trinken",
    "spielen", "malen", "singen", "lachen", "tanzen", "schwimmen",
    "fahren", "fliegen", "bauen", "kochen", "werfen", "lernen",
    "rennen", "schlafen", "klettern", "rufen",
]

ADJEKTIVE = [
    "groß", "klein", "schnell", "langsam", "rot", "blau", "schön",
    "hell", "dunkel", "warm", "kalt", "fröhlich", "traurig", "leise",
    "laut", "weich", "hart", "süß", "sauer", "neu", "alt", "stark",
]

ADVERBIEN = [
    "heute", "morgen", "gestern", "oft", "selten", "immer", "nie",
    "draußen", "drinnen", "schnell", "vorsichtig", "leise",
]

PRONOMEN = [
    "ich", "du", "er", "sie", "es", "wir", "ihr", "mein", "dein",
    "sein", "ihr",
]

ARTIKEL = ["der", "die", "das", "ein", "eine", "einen", "dem", "den"]


WORD_BANKS: dict[str, list[str]] = {
    "Nomen": NOMEN,
    "Verb": VERBEN,
    "Adjektiv": ADJEKTIVE,
    "Adverb": ADVERBIEN,
    "Pronomen": PRONOMEN,
    "Artikel": ARTIKEL,
}


class WortartenGenerator(ExerciseGenerator):
    id = "wortarten"
    label = "Deutsch: Wortarten"
    description = (
        "Auf jedem Segment steht ein Wort. Das Kind nennt die passende "
        "Wortart (Nomen, Verb, Adjektiv …)."
    )
    params = [
        ParamSpec(
            key="include_nomen",
            label="Nomen",
            type="bool",
            default=True,
        ),
        ParamSpec(
            key="include_verb",
            label="Verben",
            type="bool",
            default=True,
        ),
        ParamSpec(
            key="include_adjektiv",
            label="Adjektive",
            type="bool",
            default=True,
        ),
        ParamSpec(
            key="include_adverb",
            label="Adverbien",
            type="bool",
            default=False,
        ),
        ParamSpec(
            key="include_pronomen",
            label="Pronomen",
            type="bool",
            default=False,
        ),
        ParamSpec(
            key="include_artikel",
            label="Artikel",
            type="bool",
            default=False,
        ),
    ]

    def _enabled_categories(self, p: dict[str, Any]) -> list[str]:
        mapping = [
            ("include_nomen", "Nomen"),
            ("include_verb", "Verb"),
            ("include_adjektiv", "Adjektiv"),
            ("include_adverb", "Adverb"),
            ("include_pronomen", "Pronomen"),
            ("include_artikel", "Artikel"),
        ]
        enabled = [cat for key, cat in mapping if p.get(key)]
        if not enabled:
            enabled = ["Nomen", "Verb", "Adjektiv"]
        return enabled

    def generate(
        self,
        count: int = 12,
        params: dict[str, Any] | None = None,
        rng: random.Random | None = None,
    ) -> list[Exercise]:
        rng = rng or random.Random()
        p = self._resolved_params(params)
        cats = self._enabled_categories(p)

        pool: list[tuple[str, str]] = []
        for cat in cats:
            for word in WORD_BANKS[cat]:
                pool.append((word, cat))

        if len(pool) >= count:
            chosen = rng.sample(pool, count)
        else:
            chosen = list(pool)
            while len(chosen) < count:
                chosen.append(rng.choice(pool))
            rng.shuffle(chosen)

        return [
            Exercise(text=word, answer=cat, meta={"category": cat})
            for word, cat in chosen[:count]
        ]

"""Bildwörter (picture-words) exercise type.

Each segment shows a Twemoji glyph and the kid writes the German word
that goes with it (use-case: 🏠 → "Haus"). The catalog below is
curated for primary-school vocabulary — short, concrete, easily
recognisable nouns. Words are stored on ``Exercise.answer`` so they
appear in the teacher's answer key under the wheel; the visible
``Exercise.text`` is left blank because the wheel renderer only draws
either the emoji or the text, never both, and we want the picture to
stand alone.

Categories follow common Grundschule themes. Each is a plain list of
``(emoji, word)`` pairs so a teacher who needs e.g. "only animals" can
narrow the pool by unchecking the others.
"""
from __future__ import annotations

import random
from typing import Any

from .base import Exercise, ExerciseGenerator, ParamSpec


# (emoji, word) pairs grouped by topic. Words are spelled in the
# canonical singular form — they can still be edited per-segment in
# the UI after generation if a teacher wants a plural or alternate
# spelling. Exposed as ``CATEGORIES`` (without the leading underscore
# accessor) so the API layer can serve it to the frontend's manual
# emoji picker without duplicating the data.
CATEGORIES: dict[str, list[tuple[str, str]]] = {
    "Tiere": [
        ("🐶", "Hund"), ("🐱", "Katze"), ("🐰", "Hase"), ("🐭", "Maus"),
        ("🐹", "Hamster"), ("🐻", "Bär"), ("🐼", "Panda"), ("🦊", "Fuchs"),
        ("🦁", "Löwe"), ("🐯", "Tiger"), ("🐮", "Kuh"), ("🐷", "Schwein"),
        ("🐸", "Frosch"), ("🐔", "Huhn"), ("🐤", "Küken"), ("🦆", "Ente"),
        ("🦉", "Eule"), ("🐧", "Pinguin"), ("🐢", "Schildkröte"),
        ("🐟", "Fisch"), ("🐬", "Delfin"), ("🐳", "Wal"), ("🦈", "Hai"),
        ("🐝", "Biene"), ("🦋", "Schmetterling"), ("🐛", "Raupe"),
        ("🐞", "Marienkäfer"), ("🐌", "Schnecke"), ("🦔", "Igel"),
        ("🐺", "Wolf"), ("🐴", "Pferd"), ("🐑", "Schaf"), ("🐐", "Ziege"),
        ("🦌", "Hirsch"), ("🦒", "Giraffe"), ("🐘", "Elefant"),
        ("🦓", "Zebra"), ("🐊", "Krokodil"),
    ],
    "Essen": [
        ("🍎", "Apfel"), ("🍐", "Birne"), ("🍊", "Orange"),
        ("🍋", "Zitrone"), ("🍌", "Banane"), ("🍉", "Melone"),
        ("🍇", "Traube"), ("🍓", "Erdbeere"), ("🍒", "Kirsche"),
        ("🍑", "Pfirsich"), ("🥭", "Mango"), ("🥥", "Kokosnuss"),
        ("🍍", "Ananas"), ("🥕", "Karotte"), ("🥒", "Gurke"),
        ("🍅", "Tomate"), ("🥔", "Kartoffel"), ("🌽", "Mais"),
        ("🍄", "Pilz"), ("🥦", "Brokkoli"), ("🍞", "Brot"),
        ("🥐", "Croissant"), ("🥨", "Brezel"), ("🧀", "Käse"),
        ("🥚", "Ei"), ("🍕", "Pizza"), ("🍔", "Burger"),
        ("🌭", "Hotdog"), ("🍟", "Pommes"), ("🍝", "Spaghetti"),
        ("🍫", "Schokolade"), ("🍪", "Keks"), ("🍰", "Kuchen"),
        ("🎂", "Torte"), ("🍦", "Eis"), ("🍩", "Donut"),
        ("🍯", "Honig"),
    ],
    "Haus": [
        ("🏠", "Haus"), ("🏡", "Garten"), ("🚪", "Tür"),
        ("🪟", "Fenster"), ("🛏️", "Bett"), ("🪑", "Stuhl"),
        ("🛁", "Badewanne"), ("🚿", "Dusche"), ("🚽", "Toilette"),
        ("🧻", "Klopapier"), ("🧴", "Seife"), ("🪥", "Zahnbürste"),
        ("📺", "Fernseher"), ("📻", "Radio"), ("☎️", "Telefon"),
        ("💡", "Lampe"), ("🕰️", "Uhr"), ("🔑", "Schlüssel"),
        ("🧹", "Besen"), ("🧺", "Korb"), ("🪜", "Leiter"),
    ],
    "Verkehr": [
        ("🚗", "Auto"), ("🚕", "Taxi"), ("🚌", "Bus"),
        ("🚒", "Feuerwehr"), ("🚓", "Polizei"), ("🚑", "Krankenwagen"),
        ("🚜", "Traktor"), ("🛻", "Lastwagen"), ("🏍️", "Motorrad"),
        ("🛵", "Roller"), ("🚲", "Fahrrad"), ("🛴", "Tretroller"),
        ("🚂", "Zug"), ("🚇", "U-Bahn"), ("✈️", "Flugzeug"),
        ("🚁", "Hubschrauber"), ("🚀", "Rakete"), ("⛵", "Segelboot"),
        ("🚢", "Schiff"), ("⚓", "Anker"),
    ],
    "Natur": [
        ("🌳", "Baum"), ("🌲", "Tanne"), ("🌴", "Palme"),
        ("🌵", "Kaktus"), ("🌷", "Tulpe"), ("🌹", "Rose"),
        ("🌻", "Sonnenblume"), ("🌼", "Blume"), ("🍀", "Klee"),
        ("🍁", "Blatt"), ("🌊", "Welle"), ("🏔️", "Berg"),
        ("🌋", "Vulkan"), ("🏖️", "Strand"), ("🌍", "Erde"),
        ("🌙", "Mond"), ("☀️", "Sonne"), ("⭐", "Stern"),
        ("☁️", "Wolke"), ("🌧️", "Regen"), ("⛈️", "Gewitter"),
        ("❄️", "Schnee"), ("⛄", "Schneemann"), ("🌈", "Regenbogen"),
        ("💧", "Tropfen"), ("🔥", "Feuer"),
    ],
    "Körper": [
        ("👁️", "Auge"), ("👂", "Ohr"), ("👃", "Nase"),
        ("👄", "Mund"), ("👅", "Zunge"), ("🦷", "Zahn"),
        ("🧠", "Gehirn"), ("❤️", "Herz"), ("🦴", "Knochen"),
        ("🤚", "Hand"), ("👣", "Fuß"), ("💪", "Arm"),
    ],
    "Schule": [
        ("📚", "Bücher"), ("📖", "Buch"), ("📝", "Heft"),
        ("✏️", "Bleistift"), ("🖊️", "Kuli"), ("🖍️", "Wachsmaler"),
        ("🖌️", "Pinsel"), ("🎨", "Farben"), ("✂️", "Schere"),
        ("📐", "Lineal"), ("🎒", "Schulranzen"), ("📎", "Klammer"),
        ("🔍", "Lupe"), ("🌐", "Globus"), ("🧮", "Rechenrahmen"),
    ],
    "Spielzeug & Sport": [
        ("⚽", "Fußball"), ("🏀", "Basketball"), ("🏐", "Volleyball"),
        ("🎾", "Tennis"), ("🏓", "Tischtennis"), ("🎯", "Zielscheibe"),
        ("🎲", "Würfel"), ("🧩", "Puzzle"), ("🎮", "Spielkonsole"),
        ("🪁", "Drachen"), ("🧸", "Teddybär"), ("🎈", "Luftballon"),
        ("🎁", "Geschenk"), ("🥁", "Trommel"), ("🎸", "Gitarre"),
        ("🎹", "Klavier"), ("🎺", "Trompete"), ("🎻", "Geige"),
        ("🎤", "Mikrofon"), ("🎧", "Kopfhörer"),
    ],
}


# Order matters for the param list (and therefore the UI). Each entry
# is ``(param_key, catalog_label, default_enabled)``. The param key is
# what arrives in the generator's params dict; ``catalog_label`` is
# the human-readable name shown to the user *and* the key into
# :data:`CATEGORIES`. The leading ``include_`` prefix on the param
# key matches the convention used by the Wortarten generator, so the
# frontend's bool-checkbox renderer needs no special-casing.
_CATEGORY_PARAMS: list[tuple[str, str, bool]] = [
    ("include_tiere", "Tiere", True),
    ("include_essen", "Essen", True),
    ("include_haus", "Haus", True),
    ("include_verkehr", "Verkehr", True),
    ("include_natur", "Natur", True),
    ("include_koerper", "Körper", False),
    ("include_schule", "Schule", False),
    ("include_spiel", "Spielzeug & Sport", False),
]


def category_order() -> list[tuple[str, str]]:
    """Return ``(stable_id, label)`` tuples in display order.

    The stable ID is derived from the param key (without the
    ``include_`` prefix) so the frontend can use it as a dict key /
    React list key without seeing changes when the human-readable
    label is translated.
    """
    return [(key.removeprefix("include_"), label) for key, label, _ in _CATEGORY_PARAMS]


class BildwoerterGenerator(ExerciseGenerator):
    id = "bildwoerter"
    label = "Bildwörter (Schreibübung)"
    description = (
        "Auf jedem Segment steht ein Bild (Emoji). Das Kind schreibt "
        "das passende Wort auf, z. B. 🏠 → „Haus“. Die Lösungen siehst "
        "du als Lehrkraft unter dem Rad."
    )
    params = [
        ParamSpec(
            key=key,
            label=label,
            type="bool",
            default=default,
        )
        for key, label, default in _CATEGORY_PARAMS
    ]

    def _enabled_pool(self, p: dict[str, Any]) -> list[tuple[str, str, str]]:
        """Return the union of all enabled category pools, tagged with
        the category name so it lands in :attr:`Exercise.meta`.
        """
        pool: list[tuple[str, str, str]] = []
        for key, cat, _default in _CATEGORY_PARAMS:
            if not p.get(key):
                continue
            for emoji, word in CATEGORIES[cat]:
                pool.append((emoji, word, cat))
        if not pool:
            # If the teacher unchecks every category, fall back to the
            # defaults rather than serving an empty wheel.
            for key, cat, default in _CATEGORY_PARAMS:
                if not default:
                    continue
                for emoji, word in CATEGORIES[cat]:
                    pool.append((emoji, word, cat))
        return pool

    def generate(
        self,
        count: int = 12,
        params: dict[str, Any] | None = None,
        rng: random.Random | None = None,
    ) -> list[Exercise]:
        rng = rng or random.Random()
        p = self._resolved_params(params)
        pool = self._enabled_pool(p)

        # Prefer unique picks so the same word doesn't appear twice on
        # the same wheel; fall back to sampling-with-replacement only
        # if the pool is too small (very narrow category selection).
        if len(pool) >= count:
            chosen = rng.sample(pool, count)
        else:
            chosen = list(pool)
            rng.shuffle(chosen)
            while len(chosen) < count:
                chosen.append(rng.choice(pool))

        return [
            Exercise(
                text="",
                answer=word,
                emoji=emoji,
                meta={"category": cat},
            )
            for emoji, word, cat in chosen[:count]
        ]

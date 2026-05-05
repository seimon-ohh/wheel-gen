from __future__ import annotations

from .alphabet import AlphabetGenerator
from .base import ExerciseGenerator
from .bildwoerter import BildwoerterGenerator
from .kleines_1x1 import Kleines1x1Generator
from .wortarten import WortartenGenerator

_GENERATORS: dict[str, ExerciseGenerator] = {
    g.id: g
    for g in (
        Kleines1x1Generator(),
        WortartenGenerator(),
        AlphabetGenerator(),
        BildwoerterGenerator(),
    )
}


def get_generator(generator_id: str) -> ExerciseGenerator:
    if generator_id not in _GENERATORS:
        raise KeyError(f"Unknown exercise generator: {generator_id}")
    return _GENERATORS[generator_id]


def list_generators() -> list[ExerciseGenerator]:
    return list(_GENERATORS.values())

"""Widok tylko-do-odczytu przekazywany strategii AI (bez kart przeciwników)."""
from __future__ import annotations

from dataclasses import dataclass

from .cards import Card


@dataclass(frozen=True)
class OpponentInfo:
    id: int
    name: str
    stack: int
    current_bet: int
    in_hand: bool


@dataclass(frozen=True)
class PlayerView:
    own_hand: tuple[Card, ...]   # własne karty
    own_stack: int
    own_current_bet: int
    pot: int
    highest_bet: int             # najwyższy zakład w rundzie
    min_raise: int               # minimalna wysokość podbicia
    opponents: tuple[OpponentInfo, ...]

    @property
    def to_call(self) -> int:
        return max(0, self.highest_bet - self.own_current_bet)

"""Gracze przy stole oraz typy akcji."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .cards import Card


class PlayerStatus(Enum):
    ACTIVE = "active"          # bierze udział w rozdaniu
    FOLDED = "folded"          # spasował w tym rozdaniu
    SITTING_OUT = "sitting_out"  # brak żetonów, nie gra


class ActionType(Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"


@dataclass
class Action:
    type: ActionType
    amount: int = 0  # docelowa wysokość zakładu gracza (dla BET/RAISE)


# Kolory rewersów (wiersz backs w cards.png ma 4 kolory) — po jednym na gracza.
BACK_COLORS = ["red", "green", "blue", "purple"]


@dataclass
class Player:
    id: int
    name: str
    stack: int
    is_human: bool = False
    back_color: str = "red"
    hand: list[Card] = field(default_factory=list)
    status: PlayerStatus = PlayerStatus.ACTIVE
    current_bet: int = 0     # ile wstawił w bieżącej rundzie licytacji
    has_acted: bool = False  # czy działał od ostatniego podbicia

    def reset_for_hand(self) -> None:
        self.hand = []
        self.current_bet = 0
        self.has_acted = False
        if self.stack > 0:
            self.status = PlayerStatus.ACTIVE
        else:
            self.status = PlayerStatus.SITTING_OUT

    def is_in_hand(self) -> bool:
        return self.status == PlayerStatus.ACTIVE


@dataclass
class AIPlayer(Player):
    # Strategia ustawiana po utworzeniu (uniknięcie cyklicznego importu)
    strategy: object = None

"""Model kart: kolory, figury, pojedyncza karta i talia."""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import IntEnum


class Suit(IntEnum):
    # Kolejność wierszy w cards.png
    HEART = 0
    DIAMOND = 1
    CLUB = 2
    SPADE = 3


class Rank(IntEnum):
    # Wartości używane przy ocenie układów (As = 14)
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14


RANK_LABELS = {
    Rank.TWO: "2", Rank.THREE: "3", Rank.FOUR: "4", Rank.FIVE: "5",
    Rank.SIX: "6", Rank.SEVEN: "7", Rank.EIGHT: "8", Rank.NINE: "9",
    Rank.TEN: "10", Rank.JACK: "J", Rank.QUEEN: "Q", Rank.KING: "K",
    Rank.ACE: "A",
}

SUIT_LABELS = {
    Suit.HEART: "H", Suit.DIAMOND: "D", Suit.CLUB: "C", Suit.SPADE: "S",
}

# Kolumna w cards.png: As jest pierwszy (kolumna 0), potem 2..K
_RANK_COLUMN = {
    Rank.ACE: 0, Rank.TWO: 1, Rank.THREE: 2, Rank.FOUR: 3, Rank.FIVE: 4,
    Rank.SIX: 5, Rank.SEVEN: 6, Rank.EIGHT: 7, Rank.NINE: 8, Rank.TEN: 9,
    Rank.JACK: 10, Rank.QUEEN: 11, Rank.KING: 12,
}


@dataclass(frozen=True, order=True)
class Card:
    rank: Rank
    suit: Suit

    @property
    def sprite_col(self) -> int:
        return _RANK_COLUMN[self.rank]

    @property
    def sprite_row(self) -> int:
        return int(self.suit)

    @property
    def code(self) -> str:
        return f"{RANK_LABELS[self.rank]}{SUIT_LABELS[self.suit]}"

    def to_dict(self) -> dict:
        return {
            "rank": int(self.rank),
            "suit": int(self.suit),
            "col": self.sprite_col,
            "row": self.sprite_row,
            "code": self.code,
        }

    def __str__(self) -> str:
        return self.code


class Deck:
    def __init__(self) -> None:
        self._cards: list[Card] = [
            Card(rank, suit) for suit in Suit for rank in Rank
        ]

    def shuffle(self) -> None:
        random.shuffle(self._cards)

    def deal(self, n: int) -> list[Card]:
        if n > len(self._cards):
            raise ValueError("Za mało kart w talii")
        dealt, self._cards = self._cards[:n], self._cards[n:]
        return dealt

    def __len__(self) -> int:
        return len(self._cards)

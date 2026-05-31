"""Ocena 5-kartowego układu pokerowego."""
from __future__ import annotations

from collections import Counter
from enum import IntEnum

from .cards import Card, Rank


class Category(IntEnum):
    HIGH_CARD = 0
    PAIR = 1
    TWO_PAIR = 2
    TRIPS = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    QUADS = 7
    STRAIGHT_FLUSH = 8


CATEGORY_LABELS = {
    Category.HIGH_CARD: "Wysoka karta",
    Category.PAIR: "Para",
    Category.TWO_PAIR: "Dwie pary",
    Category.TRIPS: "Trójka",
    Category.STRAIGHT: "Strit",
    Category.FLUSH: "Kolor",
    Category.FULL_HOUSE: "Ful",
    Category.QUADS: "Kareta",
    Category.STRAIGHT_FLUSH: "Poker",
}


# Wynik porównywalny: (kategoria, *rozstrzygnięcia). Większy = lepszy.
HandRank = tuple


def _straight_high(sorted_ranks: list[int]) -> int | None:
    """Zwraca najwyższą kartę strita lub None. Obsługuje koło A-2-3-4-5."""
    unique = sorted(set(sorted_ranks), reverse=True)
    if len(unique) != 5:
        return None
    if unique[0] - unique[4] == 4:
        return unique[0]
    # Koło: As liczony jako 1
    if unique == [Rank.ACE, Rank.FIVE, Rank.FOUR, Rank.THREE, Rank.TWO]:
        return Rank.FIVE
    return None


class HandEvaluator:
    @staticmethod
    def evaluate(cards: list[Card]) -> HandRank:
        if len(cards) != 5:
            raise ValueError("Ocena wymaga dokładnie 5 kart")

        ranks = sorted((int(c.rank) for c in cards), reverse=True)
        is_flush = len({c.suit for c in cards}) == 1
        straight_high = _straight_high(ranks)

        counts = Counter(ranks)
        # Sortuj grupy: najpierw po liczności, potem po wartości
        groups = sorted(counts.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
        count_pattern = [c for _, c in groups]
        ordered_ranks = [r for r, _ in groups]

        if straight_high and is_flush:
            return (Category.STRAIGHT_FLUSH, straight_high)
        if count_pattern == [4, 1]:
            return (Category.QUADS, *ordered_ranks)
        if count_pattern == [3, 2]:
            return (Category.FULL_HOUSE, *ordered_ranks)
        if is_flush:
            return (Category.FLUSH, *ranks)
        if straight_high:
            return (Category.STRAIGHT, straight_high)
        if count_pattern == [3, 1, 1]:
            return (Category.TRIPS, *ordered_ranks)
        if count_pattern == [2, 2, 1]:
            return (Category.TWO_PAIR, *ordered_ranks)
        if count_pattern == [2, 1, 1, 1]:
            return (Category.PAIR, *ordered_ranks)
        return (Category.HIGH_CARD, *ranks)

    @staticmethod
    def category_of(rank: HandRank) -> Category:
        return Category(rank[0])

    @staticmethod
    def label(rank: HandRank) -> str:
        return CATEGORY_LABELS[Category(rank[0])]

    @staticmethod
    def combo_indices(cards: list[Card]) -> list[int]:
        """Indeksy kart tworzących układ (do podświetlenia w interfejsie)."""
        if len(cards) != 5:
            return []
        rank = HandEvaluator.evaluate(cards)
        category = Category(rank[0])

        # Strit, kolor, poker — liczy się całe 5 kart
        if category in (Category.STRAIGHT, Category.FLUSH, Category.STRAIGHT_FLUSH):
            return list(range(5))

        # Układy oparte na powtórzeniach figur — podświetl karty w grupach
        ranks = [int(c.rank) for c in cards]
        counts = Counter(ranks)
        if category in (
            Category.PAIR, Category.TWO_PAIR, Category.TRIPS,
            Category.QUADS, Category.FULL_HOUSE,
        ):
            return [i for i, r in enumerate(ranks) if counts[r] >= 2]

        # Wysoka karta — najwyższa pojedyncza karta
        best = max(range(5), key=lambda i: ranks[i])
        return [best]

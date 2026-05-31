"""Strategie AI"""
from __future__ import annotations

from collections import Counter
from typing import Protocol

from .cards import Card
from .evaluator import Category, HandEvaluator
from .player import Action, ActionType
from .view import PlayerView


class Strategy(Protocol):
    def decide_discards(self, hand: list[Card]) -> list[int]: ...
    def decide_action(self, view: PlayerView) -> Action: ...


class BasicStrategy:
    """Najprostsza logika: pary/trójki/kolor/strit. Trzyma układy, dobiera resztę."""

    def decide_discards(self, hand: list[Card]) -> list[int]:
        ranks = [int(c.rank) for c in hand]
        counts = Counter(ranks)
        suits = Counter(c.suit for c in hand)

        # Kolor lub blisko koloru — zachowaj wszystkie karty dominującego koloru
        dominant_suit, suit_count = suits.most_common(1)[0]
        if suit_count >= 4:
            return [i for i, c in enumerate(hand) if c.suit != dominant_suit]

        # Zachowaj karty tworzące pary/trójki/karety; wymień singletony
        keep_ranks = {r for r, n in counts.items() if n >= 2}
        if keep_ranks:
            discards = [i for i, c in enumerate(hand) if int(c.rank) not in keep_ranks]
            # Nie wymieniaj więcej niż 3 kart (zasada draw pokera)
            return discards[:3]

        # Brak układu: zatrzymaj 2 najwyższe karty, wymień 3 najniższe
        order = sorted(range(len(hand)), key=lambda i: ranks[i])
        return order[:3]

    def decide_action(self, view: PlayerView) -> Action:
        rank = HandEvaluator.evaluate(list(view.own_hand))
        category = HandEvaluator.category_of(rank)
        to_call = view.to_call

        # Słaby układ (wysoka karta): czek jeśli za darmo, inaczej pas
        if category == Category.HIGH_CARD:
            if to_call == 0:
                return Action(ActionType.CHECK)
            return Action(ActionType.FOLD)

        # Para: ostrożnie sprawdzaj małe zakłady
        if category == Category.PAIR:
            if to_call == 0:
                return Action(ActionType.CHECK)
            if to_call <= view.own_stack // 4:
                return Action(ActionType.CALL)
            return Action(ActionType.FOLD)

        # Dwie pary lub lepiej: stawiaj / podbijaj
        if to_call == 0:
            bet = min(view.min_raise, view.own_stack)
            return Action(ActionType.BET, amount=view.own_current_bet + bet)
        # Mocny układ — podbij raz, potem sprawdzaj
        if category >= Category.TRIPS and view.own_stack > to_call + view.min_raise:
            target = view.highest_bet + view.min_raise
            return Action(ActionType.RAISE, amount=min(target, view.own_current_bet + view.own_stack))
        return Action(ActionType.CALL)

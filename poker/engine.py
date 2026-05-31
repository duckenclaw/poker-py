"""Silnik gry: maszyna stanów dla pokera dobieranego (5-card draw)."""
from __future__ import annotations

from enum import Enum

from .cards import Deck
from .evaluator import HandEvaluator
from .player import (
    Action,
    ActionType,
    AIPlayer,
    BACK_COLORS,
    Player,
    PlayerStatus,
)
from .strategy import BasicStrategy
from .view import OpponentInfo, PlayerView

STARTING_STACK = 200
ANTE = 5
MIN_BET = 10


class Phase(Enum):
    DRAW = "draw"                  # faza dobierania kart
    BETTING = "betting"            # pojedyncza runda licytacji
    WAITING_HUMAN = "waiting_human"  # silnik czeka na akcję człowieka
    HAND_COMPLETE = "hand_complete"
    GAME_OVER = "game_over"


class GameEngine:
    def __init__(self) -> None:
        self.players: list[Player] = self._make_players()
        self.deck = Deck()
        self.pot = 0
        self.phase = Phase.DRAW
        self.button = 0
        self.current_idx = 0
        self.highest_bet = 0
        self.last_aggressor: int | None = None
        self.hand_number = 0
        self.message = ""
        self.waiting_for = "draw"  # czego silnik oczekuje od człowieka: "draw" lub "betting"
        self.showdown: list[dict] = []
        # Historia wyników do eksportu JSON
        self.results: dict = {
            "hands_played": 0,
            "human_wins": 0,
            "chip_history": [STARTING_STACK],
            "events": [],
        }
        self.start_hand()

    # ----- inicjalizacja -----

    def _make_players(self) -> list[Player]:
        strategy = BasicStrategy()
        players: list[Player] = [
            Player(0, "Ty", STARTING_STACK, is_human=True, back_color=BACK_COLORS[0])
        ]
        for i in range(1, 4):
            ai = AIPlayer(
                id=i, name=f"Bot {i}", stack=STARTING_STACK,
                back_color=BACK_COLORS[i], strategy=strategy,
            )
            players.append(ai)
        return players

    @property
    def human(self) -> Player:
        return self.players[0]

    def _solvent_players(self) -> list[Player]:
        return [p for p in self.players if p.stack > 0 or p.is_in_hand()]

    # ----- rozpoczęcie rozdania -----

    def start_hand(self) -> None:
        if sum(1 for p in self.players if p.stack > 0) <= 1:
            self.phase = Phase.GAME_OVER
            winner = max(self.players, key=lambda p: p.stack)
            self.message = f"Koniec gry. Zwycięża: {winner.name}"
            return

        self.hand_number += 1
        self.deck = Deck()
        self.deck.shuffle()
        self.pot = 0
        self.highest_bet = 0
        self.last_aggressor = None
        self.showdown = []
        self.message = f"Rozdanie #{self.hand_number}"

        for p in self.players:
            p.reset_for_hand()

        # Wpłata ante i rozdanie 5 kart każdemu grającemu
        for p in self.players:
            if p.is_in_hand():
                ante = min(ANTE, p.stack)
                p.stack -= ante
                self.pot += ante
                p.hand = self.deck.deal(5)

        self.phase = Phase.DRAW
        # Pierwszy gra człowiek (uproszczenie)
        self.current_idx = 0
        self.advance()

    # ----- główna pętla (pauza przez return) -----

    def advance(self) -> None:
        """Posuwa grę do przodu aż napotka człowieka lub zakończy rozdanie."""
        if self.phase == Phase.DRAW:
            self._run_draw_phase()
            if self.phase == Phase.WAITING_HUMAN:
                return
        if self.phase == Phase.BETTING:
            self._run_betting_phase()

    def _run_draw_phase(self) -> None:
        # Każdy grający dobiera; człowiek przerywa pętlę.
        for p in self.players:
            if not p.is_in_hand() or getattr(p, "_drawn", False):
                continue
            if p.is_human:
                self.phase = Phase.WAITING_HUMAN
                self.waiting_for = "draw"
                self.current_idx = p.id
                self.message = "Wybierz karty do wymiany"
                return
            discards = p.strategy.decide_discards(p.hand)
            self._replace_cards(p, discards)
            p._drawn = True

        # Wszyscy dobrali — start licytacji
        for p in self.players:
            if hasattr(p, "_drawn"):
                delattr(p, "_drawn")
        self._begin_betting()

    def _replace_cards(self, player: Player, discard_indices: list[int]) -> None:
        keep = [c for i, c in enumerate(player.hand) if i not in set(discard_indices)]
        new_cards = self.deck.deal(len(discard_indices)) if discard_indices else []
        player.hand = keep + new_cards

    def _begin_betting(self) -> None:
        self.phase = Phase.BETTING
        self.highest_bet = 0
        self.last_aggressor = None
        for p in self.players:
            p.current_bet = 0
            p.has_acted = False
        # Pierwszy gra człowiek, jeśli wciąż w rozdaniu, inaczej kolejny
        self.current_idx = self._first_active_from(0)

    def _run_betting_phase(self) -> None:
        while True:
            if self._only_one_left():
                self._finish_hand()
                return
            if self._betting_closed():
                self._finish_hand()
                return

            player = self.players[self.current_idx]
            if not player.is_in_hand():
                self._advance_player()
                continue

            if player.is_human:
                self.phase = Phase.WAITING_HUMAN
                self.waiting_for = "betting"
                self.message = "Twoja kolej"
                return

            action = player.strategy.decide_action(self._build_view(player))
            self.apply_action(player, action)
            self._advance_player()

    # ----- akcje człowieka (punkty wejścia z warstwy web) -----

    def submit_human_discards(self, indices: list[int]) -> None:
        if self.phase != Phase.WAITING_HUMAN:
            return
        human = self.human
        self._replace_cards(human, indices)
        human._drawn = True
        self.phase = Phase.DRAW
        self.advance()

    def submit_human_action(self, action: Action) -> None:
        if self.phase != Phase.WAITING_HUMAN:
            return
        human = self.human
        self.apply_action(human, action)
        self._advance_player()
        self.phase = Phase.BETTING
        self.advance()

    # ----- mutacja stołu -----

    def apply_action(self, player: Player, action: Action) -> None:
        if action.type == ActionType.FOLD:
            player.status = PlayerStatus.FOLDED
            self.message = f"{player.name}: pas"
        elif action.type == ActionType.CHECK:
            self.message = f"{player.name}: czek"
        elif action.type == ActionType.CALL:
            self._put_in(player, self.highest_bet)
            self.message = f"{player.name}: sprawdza"
        elif action.type in (ActionType.BET, ActionType.RAISE):
            target = max(action.amount, self.highest_bet + MIN_BET)
            target = min(target, player.current_bet + player.stack)
            self._put_in(player, target)
            self.highest_bet = player.current_bet
            self.last_aggressor = player.id
            # Po podbiciu reszta musi znów działać
            for other in self.players:
                if other.id != player.id and other.is_in_hand():
                    other.has_acted = False
            self.message = f"{player.name}: stawia {self.highest_bet}"
        player.has_acted = True

    def _put_in(self, player: Player, target_bet: int) -> None:
        need = target_bet - player.current_bet
        need = min(need, player.stack)  # all-in jeśli za mało żetonów
        player.stack -= need
        player.current_bet += need
        self.pot += need

    # ----- warunki zamknięcia rundy -----

    def _active_players(self) -> list[Player]:
        return [p for p in self.players if p.is_in_hand()]

    def _only_one_left(self) -> bool:
        return len(self._active_players()) <= 1

    def _betting_closed(self) -> bool:
        actives = self._active_players()
        if not all(p.has_acted for p in actives):
            return False
        # Wszyscy wyrównali najwyższy zakład (lub są all-in)
        return all(
            p.current_bet == self.highest_bet or p.stack == 0 for p in actives
        )

    def _first_active_from(self, start: int) -> int:
        for offset in range(len(self.players)):
            idx = (start + offset) % len(self.players)
            if self.players[idx].is_in_hand():
                return idx
        return start

    def _advance_player(self) -> None:
        self.current_idx = self._first_active_from(self.current_idx + 1)

    # ----- zakończenie rozdania -----

    def _finish_hand(self) -> None:
        actives = self._active_players()
        if len(actives) == 1:
            winner = actives[0]
            winner.stack += self.pot
            self.message = f"{winner.name} wygrywa {self.pot} (reszta spasowała)"
            self.showdown = [{"id": winner.name, "hand": None, "label": None}]
        else:
            scored = [(p, HandEvaluator.evaluate(p.hand)) for p in actives]
            best = max(score for _, score in scored)
            winners = [p for p, score in scored if score == best]
            share = self.pot // len(winners)
            for w in winners:
                w.stack += share
            # Reszta z dzielenia trafia do pierwszego zwycięzcy
            winners[0].stack += self.pot - share * len(winners)
            names = ", ".join(w.name for w in winners)
            self.message = f"{names} wygrywa {self.pot} ({HandEvaluator.label(best)})"
            self.showdown = [
                {
                    "id": p.name,
                    "hand": [c.to_dict() for c in p.hand],
                    "label": HandEvaluator.label(score),
                    "winner": p in winners,
                }
                for p, score in scored
            ]

        # Statystyki
        self.results["hands_played"] += 1
        if self.human.is_in_hand() and any(
            s.get("winner") and s["id"] == self.human.name for s in self.showdown
        ):
            self.results["human_wins"] += 1
        elif len(actives) == 1 and actives[0] == self.human:
            self.results["human_wins"] += 1
        self.results["chip_history"].append(self.human.stack)
        self.results["events"].append({
            "hand": self.hand_number,
            "human_stack": self.human.stack,
            "pot": self.pot,
            "message": self.message,
        })

        # Wyzeruj graczy bez żetonów
        for p in self.players:
            if p.stack <= 0:
                p.status = PlayerStatus.SITTING_OUT

        self.pot = 0
        self.phase = Phase.HAND_COMPLETE

    def next_hand(self) -> None:
        if self.phase != Phase.HAND_COMPLETE:
            return
        self.button = (self.button + 1) % len(self.players)
        self.start_hand()

    # ----- budowanie widoku -----

    def _build_view(self, player: Player) -> PlayerView:
        opponents = tuple(
            OpponentInfo(p.id, p.name, p.stack, p.current_bet, p.is_in_hand())
            for p in self.players if p.id != player.id
        )
        return PlayerView(
            own_hand=tuple(player.hand),
            own_stack=player.stack,
            own_current_bet=player.current_bet,
            pot=self.pot,
            highest_bet=self.highest_bet,
            min_raise=MIN_BET,
            opponents=opponents,
        )

    def legal_actions(self) -> list[dict]:
        if self.phase != Phase.WAITING_HUMAN:
            return []
        human = self.human
        to_call = self.highest_bet - human.current_bet
        actions: list[dict] = [{"type": "fold"}]
        if to_call <= 0:
            actions.append({"type": "check"})
            actions.append({"type": "bet", "min": MIN_BET, "max": human.stack})
        else:
            actions.append({"type": "call", "amount": min(to_call, human.stack)})
            if human.stack > to_call:
                actions.append({
                    "type": "raise",
                    "min": min(to_call + MIN_BET, human.stack),
                    "max": human.stack,
                })
        return actions

    def to_public_dict(self) -> dict:
        reveal = self.phase in (Phase.HAND_COMPLETE,)
        players = []
        for p in self.players:
            show_cards = p.is_human or reveal
            # Podświetlenie układu: tylko gdy karty są widoczne i są pełne 4 (5 kart)
            combo = (
                HandEvaluator.combo_indices(p.hand)
                if show_cards and len(p.hand) == 5 and p.is_in_hand()
                else []
            )
            players.append({
                "id": p.id,
                "name": p.name,
                "stack": p.stack,
                "current_bet": p.current_bet,
                "status": p.status.value,
                "is_human": p.is_human,
                "back_color": p.back_color,
                "card_count": len(p.hand),
                "hand": [c.to_dict() for c in p.hand] if show_cards else None,
                "combo": combo,
            })
        return {
            "phase": self.phase.value,
            "sub_phase": self.waiting_for,
            "pot": self.pot,
            "highest_bet": self.highest_bet,
            "current_idx": self.current_idx,
            "hand_number": self.hand_number,
            "message": self.message,
            "players": players,
            "showdown": self.showdown,
            "legal_actions": self.legal_actions(),
            "game_over": self.phase == Phase.GAME_OVER,
        }

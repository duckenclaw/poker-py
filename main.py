"""Interfejs gry w pokera dobieranego — w całości w Pythonie (NiceGUI)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from nicegui import app, ui

from poker.engine import GameEngine, Phase
from poker.player import Action, ActionType

ASSETS = Path(__file__).parent / "assets"
app.add_static_files("/assets", str(ASSETS))

# Wymiary sprite'ów w cards.png.
CARD_W, CARD_H = 48, 64
BACK_ROW_Y = 256
BACK_COL = {"red": 0, "green": 2, "blue": 4, "purple": 6}

# Skala wyświetlania kart: ręka człowieka większa, karty botów mniejsze.
SCALE = 2.0
BOT_SCALE = 1.25

# Żetony w tokens.png (368x192): 8 kolorów po 4 warianty stosu (1-4 sztuki).
TOKEN_W, TOKEN_H = 46, 48
# Kolor gracza w siatce tokens.png.
TOKEN_BLOCK = {
    "red": (0, 0),
    "blue": (0, 4),
    "purple": (1, 4),
    "green": (2, 0),
}

engine = GameEngine()

# Indeksy kart zaznaczonych do wymiany w fazie dobierania.
discard_selection: set[int] = set()


def _sprite_style(x_px: int, y_px: int, scale: float = SCALE) -> str:
    w, h = round(CARD_W * scale), round(CARD_H * scale)
    return (
        f"width:{w}px;height:{h}px;flex:none;"
        f"background-image:url('/assets/cards.png');"
        f"background-position:-{round(x_px * scale)}px -{round(y_px * scale)}px;"
        f"background-size:{round(944 * scale)}px {round(385 * scale)}px;"
        f"background-repeat:no-repeat;border-radius:4px;"
    )


def card_face_style(col: int, row: int, scale: float = SCALE) -> str:
    return _sprite_style(col * CARD_W, row * CARD_H, scale)


def card_back_style(color: str, scale: float = SCALE) -> str:
    return _sprite_style(BACK_COL.get(color, 0) * CARD_W, BACK_ROW_Y, scale)


def token_style(color: str, count: int, scale: float = 0.8) -> str:
    """Styl stosu żetonów dla danego koloru gracza. Liczba 1-4 wybiera wariant stosu."""
    row, base_col = TOKEN_BLOCK.get(color, (0, 0))
    variant = max(0, min(3, count - 1))  # 0..3 = stos 1..4 sztuk
    col = base_col + variant
    w, h = round(TOKEN_W * scale), round(TOKEN_H * scale)
    return (
        f"width:{w}px;height:{h}px;flex:none;"
        f"background-image:url('/assets/tokens.png');"
        f"background-position:-{round(col * TOKEN_W * scale)}px -{round(row * TOKEN_H * scale)}px;"
        f"background-size:{round(368 * scale)}px {round(192 * scale)}px;"
        f"background-repeat:no-repeat;"
    )


def _stack_variant(amount: int) -> int:
    """Mapuje wysokość puli żetonów na wariant stosu 1-4 (więcej = wyższy stos)."""
    if amount <= 0:
        return 1
    if amount < 50:
        return 1
    if amount < 150:
        return 2
    if amount < 300:
        return 3
    return 4


def _chip_stack(color: str, stack: int, bet: int) -> None:
    """Rysuje żetony gracza: stos puli oraz aktualny zakład."""
    with ui.row().classes("items-center gap-1 no-wrap"):
        ui.element("div").style(token_style(color, _stack_variant(stack)))
        ui.label(f"{stack}").classes("token-amt")
        if bet > 0:
            ui.label("|").classes("token-sep")
            ui.element("div").style(token_style(color, _stack_variant(bet), scale=0.6))
            ui.label(f"{bet}").classes("token-bet")


# ----- akcje sterujące grą -----

def _ai_pending() -> bool:
    """Czy silnik czeka, aż AI wykona ruch (faza nie-ludzka)?"""
    return engine.phase in (Phase.DRAW, Phase.BETTING)


def new_game() -> None:
    global engine
    engine = GameEngine()
    discard_selection.clear()
    table.refresh()


def toggle_discard(i: int) -> None:
    if i in discard_selection:
        discard_selection.discard(i)
    elif len(discard_selection) < 3:
        discard_selection.add(i)
    table.refresh()


def submit_draw() -> None:
    indices = sorted(discard_selection)
    discard_selection.clear()
    engine.submit_human_discards(indices)
    table.refresh()


def do_action(atype: ActionType, amount: int = 0) -> None:
    engine.submit_human_action(Action(atype, amount))
    table.refresh()


def next_hand() -> None:
    engine.next_hand()
    discard_selection.clear()
    table.refresh()


def download_results() -> None:
    payload = json.dumps(engine.results, indent=2, ensure_ascii=False)
    ui.download(payload.encode("utf-8"), "poker-wyniki.json")


# ----- renderowanie -----

def _render_card(c: dict, glow: bool, scale: float = SCALE) -> "ui.element":
    style = card_face_style(c["col"], c["row"], scale)
    el = ui.element("div").style(style)
    if glow:
        el.classes("combo-glow")
    return el


@ui.refreshable
def table() -> None:
    state = engine.to_public_dict()

    with ui.column().classes("table-root no-wrap"):
        # Nagłówek: numer rozdania, pula, komunikat
        with ui.row().classes("items-center gap-4 header-row no-wrap"):
            ui.label(f"Rozdanie #{state['hand_number']}").classes("title-sm")
            with ui.row().classes("items-center gap-1 no-wrap"):
                ui.element("div").style(token_style("red", _stack_variant(state["pot"]), scale=0.7))
                ui.label(f"Pula: {state['pot']}").classes("pot-label")
        ui.label(state["message"]).classes("msg-label")

        # Przeciwnicy (boty)
        with ui.row().classes("gap-3 justify-center no-wrap seats-row"):
            for p in state["players"]:
                if not p["is_human"]:
                    _render_seat(p, state)

        # Ręka człowieka
        _render_human(state)

        # Sterowanie
        _render_controls(state)

    # AI gra automatycznie z lekkim opóźnieniem
    if _ai_pending():
        ui.timer(0.7, table.refresh, once=True)


def _render_seat(p: dict, state: dict) -> None:
    classes = "seat-card items-center gap-1"
    if p["status"] == "folded":
        classes += " opacity-40"
    if state["current_idx"] == p["id"] and state["phase"] != "hand_complete":
        classes += " active-seat"
    combo = set(p.get("combo") or [])
    reveal = p["hand"] and state["phase"] == "hand_complete"
    with ui.card().classes(classes):
        ui.label(p["name"]).classes("seat-name")
        _chip_stack(p["back_color"], p["stack"], p["current_bet"])
        with ui.row().classes("gap-1 no-wrap"):
            for i in range(p["card_count"]):
                if reveal:
                    _render_card(p["hand"][i], glow=i in combo, scale=BOT_SCALE)
                else:
                    ui.element("div").style(card_back_style(p["back_color"], BOT_SCALE))
        if reveal:
            _seat_combo_label(state, p)


def _seat_combo_label(state: dict, p: dict) -> None:
    entry = next((s for s in state.get("showdown", []) if s.get("id") == p["name"]), None)
    if entry and entry.get("label"):
        cls = "combo-label win" if entry.get("winner") else "combo-label"
        text = entry["label"] + (" ★" if entry.get("winner") else "")
        ui.label(text).classes(cls)


def _render_human(state: dict) -> None:
    human = next(p for p in state["players"] if p["is_human"])
    is_draw = state["phase"] == "waiting_human" and state["sub_phase"] == "draw"
    combo = set(human.get("combo") or [])
    # Podczas dobierania nie podświetlamy układu (gracz właśnie go zmienia).
    show_glow = not is_draw

    with ui.column().classes("items-center gap-1 human-area no-wrap"):
        with ui.row().classes("items-center gap-3 no-wrap"):
            ui.label("Ty").classes("seat-name").style("font-size:16px")
            _chip_stack(human["back_color"], human["stack"], human["current_bet"])
        if is_draw:
            ui.label("Kliknij karty do wymiany (maks. 3)").classes("hint-label")
        with ui.row().classes("gap-2 no-wrap"):
            for i, c in enumerate(human["hand"] or []):
                style = card_face_style(c["col"], c["row"])
                if is_draw and i in discard_selection:
                    style += "outline:3px solid #ef4444;transform:translateY(8px);"
                el = ui.element("div").style(style)
                if show_glow and i in combo:
                    el.classes("combo-glow")
                if is_draw:
                    el.classes("cursor-pointer transition-transform")
                    el.on("click", lambda i=i: toggle_discard(i))


def _render_controls(state: dict) -> None:
    phase, sub = state["phase"], state["sub_phase"]

    if state["game_over"]:
        with ui.row().classes("gap-2 ctrl-row no-wrap"):
            ui.button("Nowa gra", on_click=new_game, color="primary")
            ui.button("Pobierz wyniki", icon="download", on_click=download_results)
        return

    with ui.row().classes("gap-2 ctrl-row no-wrap"):
        if phase == "waiting_human" and sub == "draw":
            n = len(discard_selection)
            label = f"Dobierz ({n})" if n else "Zostaję (pas)"
            ui.button(label, on_click=submit_draw, color="primary")
        elif phase == "waiting_human" and sub == "betting":
            _render_bet_buttons(state)
        elif phase == "hand_complete":
            ui.button("Następne rozdanie", on_click=next_hand, color="primary")
        ui.button("Nowa gra", on_click=new_game).props("flat dense")
        ui.button("Pobierz wyniki", icon="download", on_click=download_results).props("flat dense")


def _render_bet_buttons(state: dict) -> None:
    human = next(p for p in state["players"] if p["is_human"])
    for a in state["legal_actions"]:
        if a["type"] == "fold":
            ui.button("Pas", on_click=lambda: do_action(ActionType.FOLD), color="red")
        elif a["type"] == "check":
            ui.button("Czek", on_click=lambda: do_action(ActionType.CHECK))
        elif a["type"] == "call":
            amt = a["amount"]
            ui.button(f"Sprawdź ({amt})", on_click=lambda: do_action(ActionType.CALL), color="primary")
        elif a["type"] in ("bet", "raise"):
            target = human["current_bet"] + a["min"]
            label = "Stawiaj" if a["type"] == "bet" else "Podbij"
            atype = ActionType.BET if a["type"] == "bet" else ActionType.RAISE
            ui.button(f"{label} ({a['min']})",
                      on_click=lambda atype=atype, target=target: do_action(atype, target),
                      color="green")


# CSS globalny
PAGE_CSS = """
@font-face {
    font-family: 'Pixeloid Mono';
    src: url('/assets/PixeloidMono.ttf') format('truetype');
}
html, body, .nicegui-content {
    font-family: 'Pixeloid Mono', monospace !important;
    height: 100%;
    overflow: hidden;
    background: #15803d;
}
.nicegui-content { padding: 0 !important; }
.table-root {
    height: 100vh;
    width: 100%;
    max-width: 1100px;
    margin: 0 auto;
    padding: 16px;
    gap: 14px;
    align-items: center;
    justify-content: center;
    background: #15803d;
}
.no-wrap { flex-wrap: nowrap !important; }
.header-row .title-sm { font-size: 18px; font-weight: bold; color: #fff; }
.pot-label { font-size: 16px; font-weight: bold; color: #fde68a; }
.msg-label { font-size: 13px; color: #d1fae5; min-height: 18px; }
.seats-row { width: 100%; }
.seat-card {
    padding: 6px 8px;
    background: #166534;
    border: 1px solid #14532d;
    flex: 1 1 0;
    min-width: 0;
}
.seat-name { font-weight: bold; color: #fff; font-size: 13px; }
.active-seat { outline: 3px solid #fbbf24; }
.combo-label { font-size: 12px; color: #d1fae5; }
.combo-label.win { color: #fde047; font-weight: bold; }
.token-amt { font-size: 13px; color: #fff; }
.token-bet { font-size: 12px; color: #fde68a; }
.token-sep { color: #4ade80; font-size: 12px; }
.hint-label { font-size: 11px; color: #bbf7d0; }
.human-area { background: #166534; border-radius: 10px; padding: 8px 14px; }
.ctrl-row { min-height: 38px; align-items: center; }
.combo-glow {
    outline: 3px solid #fde047;
    box-shadow: 0 0 12px 3px rgba(253, 224, 71, 0.9);
    z-index: 1;
}
"""


@ui.page("/")
def index() -> None:
    ui.add_head_html(f"<style>{PAGE_CSS}</style>")
    ui.query("body").classes("bg-green-900")
    table()


ui.run(
    title="Poker dobierany",
    port=int(os.environ.get("PORT", "8080")),
    reload=False,
    show=False,
)

Create a single-player poker web game using Python. The game will be against 3 AI players with the simplest logic (cards in a row, pairs, flush). The game must have a simple web interface with drag and drop controls. All the comments must be in polish language and only when absolutely necessary.

The project shouldn't be too complex and have a backend, no server-side logic.

The assets are located in `assets/` folder, it contains:
1. cards.png - 52 poker cards 48x64 

- 0x0 - 624x64: heart cards
- 0x64 - 624x128: diamond cards
- 0x128 - 624x192: club cards
- 0x192 - 624x256: spade cards
- 0x256 - 384x320: back of cards (has 4 colors with 2 variants per color. use only one variant for every player to differentiate them with color)
- 624x0 - 720x64: two jokers

2. decks.png - 4 colors with 2 variant each, also has dealer's deck and discard pile

3. tokens.png - 8 colors with 4 variants for 1, 2, 3 and 4 tokens in a stack


## Game State Machine

The engine advances itself as far as it can, only stopping when it needs input. One loop:

```
1. Start hand
   - rotate button, post blinds, deal hole cards
   - set street = PREFLOP, phase = WAITING_FOR_ACTION
   - current_player = first to act (left of big blind preflop)

2. While betting round not closed:
   - if current player is AI:
       action = ai.strategy.decide(public_state, private_view)
       apply_action(action)            # validate -> mutate table
   - else (human):
       set phase = WAITING_FOR_ACTION and RETURN to web layer
       (resume here when the human submits an action)
   - advance current_player to next ACTIVE seat

3. Betting round closes when:
   - all ACTIVE players have matched the highest bet, AND
   - everyone has had a chance to act since the last aggressor
   (or only one ACTIVE player remains -> hand ends early)

4. Advance street: deal community cards, reset current_bets,
   first-to-act = left of button. Repeat from 2.

5. After RIVER betting (or early-out):
   - phase = HAND_COMPLETE
   - evaluate hands, build pots, award chips
   - mark busted players SITTING_OUT
   - if <=1 player with chips -> GAME_OVER, else loop to 1
```

The key trick: the loop **pauses by returning** when it hits the human, and the web layer re-enters by calling `engine.submit_human_action(action)`. AI turns resolve synchronously inside the loop (optionally with an artificial delay on the frontend so it feels human-paced).

---

## AI Players — Basic Strategy

Use the **Strategy pattern**: `AIPlayer` holds a `Strategy`.

```python
class Strategy(Protocol):
    def decide(self, view: PlayerView) -> Action: ...
```

`PlayerView` is a restricted, read-only snapshot — the bot sees its own hole cards + all public info (community cards, pot, bets, positions, stacks) but **not** opponents' hole cards. This isolation prevents accidental cheating and keeps bots honest.

Strategies should currently only have the simplest logic (cards in a row, pairs, flush). All players share one strategy.

### `HandEvaluator`
- `evaluate(seven_cards) -> HandRank` where `HandRank` is a comparable tuple like `(category, kicker_tiebreakers...)`.
- Categories: high card → pair → two pair → trips → straight → flush → full house → quads → straight flush.
- Standard approach: enumerate the best 5 of 7, or use a precomputed lookup (e.g. the `treys` library) if you want speed. For a 4-handed casual game, brute force is plenty fast.

---
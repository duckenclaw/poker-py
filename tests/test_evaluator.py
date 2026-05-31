"""Testy oceny układów pokerowych."""
from poker.cards import Card, Rank, Suit
from poker.evaluator import Category, HandEvaluator


def hand(*specs: tuple[Rank, Suit]) -> list[Card]:
    return [Card(r, s) for r, s in specs]


H, D, C, S = Suit.HEART, Suit.DIAMOND, Suit.CLUB, Suit.SPADE


def test_categories_detected():
    straight_flush = hand((Rank.TEN, H), (Rank.JACK, H), (Rank.QUEEN, H), (Rank.KING, H), (Rank.ACE, H))
    quads = hand((Rank.NINE, H), (Rank.NINE, D), (Rank.NINE, C), (Rank.NINE, S), (Rank.TWO, H))
    full = hand((Rank.KING, H), (Rank.KING, D), (Rank.KING, C), (Rank.TWO, S), (Rank.TWO, H))
    flush = hand((Rank.TWO, S), (Rank.FIVE, S), (Rank.NINE, S), (Rank.JACK, S), (Rank.KING, S))
    straight = hand((Rank.FIVE, H), (Rank.SIX, D), (Rank.SEVEN, C), (Rank.EIGHT, S), (Rank.NINE, H))
    trips = hand((Rank.SEVEN, H), (Rank.SEVEN, D), (Rank.SEVEN, C), (Rank.TWO, S), (Rank.KING, H))
    two_pair = hand((Rank.SEVEN, H), (Rank.SEVEN, D), (Rank.TWO, C), (Rank.TWO, S), (Rank.KING, H))
    pair = hand((Rank.SEVEN, H), (Rank.SEVEN, D), (Rank.FOUR, C), (Rank.TWO, S), (Rank.KING, H))
    high = hand((Rank.SEVEN, H), (Rank.NINE, D), (Rank.FOUR, C), (Rank.TWO, S), (Rank.KING, H))

    ev = HandEvaluator.evaluate
    assert HandEvaluator.category_of(ev(straight_flush)) == Category.STRAIGHT_FLUSH
    assert HandEvaluator.category_of(ev(quads)) == Category.QUADS
    assert HandEvaluator.category_of(ev(full)) == Category.FULL_HOUSE
    assert HandEvaluator.category_of(ev(flush)) == Category.FLUSH
    assert HandEvaluator.category_of(ev(straight)) == Category.STRAIGHT
    assert HandEvaluator.category_of(ev(trips)) == Category.TRIPS
    assert HandEvaluator.category_of(ev(two_pair)) == Category.TWO_PAIR
    assert HandEvaluator.category_of(ev(pair)) == Category.PAIR
    assert HandEvaluator.category_of(ev(high)) == Category.HIGH_CARD


def test_ranking_order():
    ev = HandEvaluator.evaluate
    flush = hand((Rank.TWO, S), (Rank.FIVE, S), (Rank.NINE, S), (Rank.JACK, S), (Rank.KING, S))
    straight = hand((Rank.FIVE, H), (Rank.SIX, D), (Rank.SEVEN, C), (Rank.EIGHT, S), (Rank.NINE, H))
    trips = hand((Rank.SEVEN, H), (Rank.SEVEN, D), (Rank.SEVEN, C), (Rank.TWO, S), (Rank.KING, H))
    full = hand((Rank.KING, H), (Rank.KING, D), (Rank.KING, C), (Rank.TWO, S), (Rank.TWO, H))

    assert ev(straight) > ev(trips)
    assert ev(flush) > ev(straight)
    assert ev(full) > ev(flush)


def test_wheel_straight():
    # Koło A-2-3-4-5: As liczony nisko, najwyższa karta to 5
    wheel = hand((Rank.ACE, H), (Rank.TWO, D), (Rank.THREE, C), (Rank.FOUR, S), (Rank.FIVE, H))
    rank = HandEvaluator.evaluate(wheel)
    assert HandEvaluator.category_of(rank) == Category.STRAIGHT
    assert rank[1] == Rank.FIVE


def test_tie_detection():
    a = hand((Rank.KING, H), (Rank.KING, D), (Rank.TWO, C), (Rank.FIVE, S), (Rank.NINE, H))
    b = hand((Rank.KING, C), (Rank.KING, S), (Rank.TWO, H), (Rank.FIVE, D), (Rank.NINE, C))
    assert HandEvaluator.evaluate(a) == HandEvaluator.evaluate(b)


def test_higher_pair_wins():
    aces = hand((Rank.ACE, H), (Rank.ACE, D), (Rank.TWO, C), (Rank.FIVE, S), (Rank.NINE, H))
    kings = hand((Rank.KING, H), (Rank.KING, D), (Rank.TWO, C), (Rank.FIVE, S), (Rank.NINE, H))
    assert HandEvaluator.evaluate(aces) > HandEvaluator.evaluate(kings)

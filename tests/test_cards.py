"""Юнит-тесты доменной модели карт."""

from __future__ import annotations

import pytest

from app.domain.cards import Card, Deck, Rank, Suit


def test_deck_has_36_unique_cards() -> None:
    deck = Deck()

    assert len(deck) == Deck.CARDS_IN_DECK == 36
    assert len(set(deck.cards)) == 36


def test_deck_contains_all_suit_rank_combinations() -> None:
    deck = Deck()

    expected = {Card(suit=suit, rank=rank) for suit in Suit for rank in Rank}
    assert set(deck.cards) == expected


def test_draw_reduces_deck_size() -> None:
    deck = Deck()
    initial_size = len(deck)

    drawn = deck.draw(6)

    assert len(drawn) == 6
    assert len(deck) == initial_size - 6


def test_draw_returns_cards_from_top_of_deck() -> None:
    deck = Deck()
    top_cards = deck.cards[:3]

    drawn = deck.draw(3)

    assert drawn == list(top_cards)


def test_draw_more_than_available_raises() -> None:
    deck = Deck()

    with pytest.raises(ValueError):
        deck.draw(37)


def test_draw_non_positive_count_raises() -> None:
    deck = Deck()

    with pytest.raises(ValueError):
        deck.draw(0)
    with pytest.raises(ValueError):
        deck.draw(-1)


def test_shuffle_keeps_all_cards() -> None:
    deck = Deck()
    before = set(deck.cards)

    deck.shuffle()

    assert set(deck.cards) == before
    assert len(deck) == 36


def test_card_str_and_repr() -> None:
    card = Card(suit=Suit.HEARTS, rank=Rank.ACE)

    assert str(card) == "A♥"
    assert repr(card) == "Card(suit=HEARTS, rank=ACE)"


def test_card_is_immutable() -> None:
    card = Card(suit=Suit.SPADES, rank=Rank.SIX)

    with pytest.raises(Exception):
        card.rank = Rank.ACE  # type: ignore[misc]

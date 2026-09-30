"""Юнит-тесты доменной модели игрока."""

from __future__ import annotations

import pytest

from app.domain.cards import Card, Rank, Suit
from app.domain.player import Player


def test_player_starts_with_empty_hand() -> None:
    player = Player(name="alice")

    assert player.name == "alice"
    assert player.hand == []
    assert player.is_empty() is True
    assert player.is_active is True


def test_player_empty_name_raises() -> None:
    with pytest.raises(ValueError):
        Player(name="")


def test_add_card_appends_to_hand() -> None:
    player = Player(name="alice")
    card = Card(suit=Suit.HEARTS, rank=Rank.ACE)

    player.add_card(card)

    assert player.hand == [card]
    assert player.is_empty() is False


def test_remove_card_removes_from_hand() -> None:
    player = Player(name="alice")
    card = Card(suit=Suit.SPADES, rank=Rank.SIX)
    player.add_card(card)

    player.remove_card(card)

    assert player.hand == []
    assert player.is_empty() is True


def test_remove_missing_card_raises() -> None:
    player = Player(name="alice")
    card = Card(suit=Suit.CLUBS, rank=Rank.KING)

    with pytest.raises(ValueError):
        player.remove_card(card)


def test_repr_shows_name_and_hand_size() -> None:
    player = Player(name="bob")
    player.add_card(Card(suit=Suit.DIAMONDS, rank=Rank.TEN))

    assert repr(player) == "Player(name='bob', hand=1, is_active=True)"


def test_deactivate_sets_is_active_false() -> None:
    player = Player(name="alice")

    player.deactivate()

    assert player.is_active is False
    assert repr(player) == "Player(name='alice', hand=0, is_active=False)"

"""Доменная модель игральных карт для игры «Подкидной Дурак».

Модуль полностью изолирован от веб-фреймворков и сторонних библиотек
и содержит только чистую бизнес-логику.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import IntEnum, StrEnum

__all__ = ["Suit", "Rank", "Card", "Deck"]


class Suit(StrEnum):
    """Масти игральных карт с символьными обозначениями."""

    HEARTS = "♥"
    DIAMONDS = "♦"
    CLUBS = "♣"
    SPADES = "♠"

    @property
    def symbol(self) -> str:
        """Символьное обозначение масти."""
        return self.value


class Rank(IntEnum):
    """Ранги карт с весами от 6 до 14 (A — старшая)."""

    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14

    @property
    def label(self) -> str:
        """Строковое обозначение ранга ('6'..'10', 'J', 'Q', 'K', 'A')."""
        return _RANK_LABELS[self]


_RANK_LABELS: dict[Rank, str] = {
    Rank.SIX: "6",
    Rank.SEVEN: "7",
    Rank.EIGHT: "8",
    Rank.NINE: "9",
    Rank.TEN: "10",
    Rank.JACK: "J",
    Rank.QUEEN: "Q",
    Rank.KING: "K",
    Rank.ACE: "A",
}


@dataclass(frozen=True, slots=True)
class Card:
    """Неизменяемая игральная карта."""

    suit: Suit
    rank: Rank

    def __str__(self) -> str:
        return f"{self.rank.label}{self.suit.symbol}"

    def __repr__(self) -> str:
        return f"Card(suit={self.suit.name}, rank={self.rank.name})"


class Deck:
    """Колода из 36 карт (от шестёрки до туза во всех мастях)."""

    CARDS_IN_DECK: int = 36

    def __init__(self) -> None:
        self._cards: list[Card] = [
            Card(suit=suit, rank=rank)
            for suit in Suit
            for rank in Rank
        ]

    def __len__(self) -> int:
        return len(self._cards)

    def __repr__(self) -> str:
        return f"Deck(cards={len(self._cards)})"

    @property
    def cards(self) -> tuple[Card, ...]:
        """Текущее содержимое колоды (только для чтения)."""
        return tuple(self._cards)

    def shuffle(self) -> None:
        """Случайным образом перемешивает колоду."""
        random.shuffle(self._cards)

    def draw(self, count: int) -> list[Card]:
        """Берёт `count` карт с вершины колоды.

        :param count: количество карт для взятия (должно быть > 0)
        :return: список взятых карт
        :raises ValueError: если count <= 0 или в колоде недостаточно карт
        """
        if count <= 0:
            raise ValueError("Количество карт для взятия должно быть больше нуля")
        if count > len(self._cards):
            raise ValueError(
                f"В колоде недостаточно карт: запрошено {count}, доступно {len(self._cards)}"
            )
        drawn = self._cards[:count]
        del self._cards[:count]
        return drawn

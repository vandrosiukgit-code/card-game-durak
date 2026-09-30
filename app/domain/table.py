"""Доменная модель стола для игры «Подкидной Дурак».

Стол хранит карты, выложенные в текущем раунде: карты атаки и карты
защиты. Каждая карта защиты привязана к конкретной карте атаки по
индексу (см. PODKIDNOY_DURAK_RULES.md §14).
"""

from __future__ import annotations

from app.domain.cards import Card

__all__ = ["Table"]


class Table:
    """Стол текущего раунда: карты атаки и соответствующие им карты защиты.

    Карты атаки и защиты хранятся в параллельных списках: элемент
    ``defense_cards[i]`` — это карта, которой отбита ``attack_cards[i]``,
    либо ``None``, если карта ещё не отбита.
    """

    def __init__(self) -> None:
        self._attack_cards: list[Card] = []
        self._defense_cards: list[Card | None] = []

    def __len__(self) -> int:
        return len(self._attack_cards)

    def __repr__(self) -> str:
        return (
            f"Table(attack={len(self._attack_cards)}, "
            f"defense={sum(1 for c in self._defense_cards if c is not None)})"
        )

    @property
    def attack_cards(self) -> tuple[Card, ...]:
        """Карты, выложенные в атаку (только для чтения)."""
        return tuple(self._attack_cards)

    @property
    def defense_cards(self) -> tuple[Card | None, ...]:
        """Карты защиты по индексу атаки (``None`` — карта не отбита)."""
        return tuple(self._defense_cards)

    def is_empty(self) -> bool:
        """Пуст ли стол (нет ни одной карты атаки)."""
        return not self._attack_cards

    def add_attack(self, card: Card) -> None:
        """Кладёт карту в атаку.

        :param card: карта для атаки
        """
        self._attack_cards.append(card)
        self._defense_cards.append(None)

    def add_defense(self, card: Card) -> None:
        """Кладёт карту в защиту — отбивает последнюю неотбитую атаку.

        :param card: карта для защиты
        :raises ValueError: если на столе нет неотбитой карты атаки
        """
        for index, defense in enumerate(self._defense_cards):
            if defense is None:
                self._defense_cards[index] = card
                return
        raise ValueError("Нет карты атаки, которую можно отбить")

    def clear(self) -> None:
        """Очищает стол (после отбоя или взятия карт защитником)."""
        self._attack_cards.clear()
        self._defense_cards.clear()

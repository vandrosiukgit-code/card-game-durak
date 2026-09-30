"""Доменная модель игрока для игры «Подкидной Дурак».

Модуль изолирован от веб-фреймворков и сторонних библиотек.
Содержит только чистую бизнес-логику: имя игрока, его руку и статус.
"""

from __future__ import annotations

from app.domain.cards import Card

__all__ = ["Player"]


class Player:
    """Участник партии: имя, рука с картами и статус активности.

    Класс изменяемый: рука и статус меняются по ходу партии
    (взятие карт, сброс карт на стол, выход из игры).
    """

    def __init__(self, name: str) -> None:
        """Создаёт игрока с пустой рукой.

        :param name: никнейм игрока (непустой)
        :raises ValueError: если имя пустое
        """
        if not name:
            raise ValueError("Имя игрока не может быть пустым")
        self.name: str = name
        self.hand: list[Card] = []
        self.is_active: bool = True

    def __repr__(self) -> str:
        return (
            f"Player(name={self.name!r}, "
            f"hand={len(self.hand)}, is_active={self.is_active})"
        )

    def add_card(self, card: Card) -> None:
        """Добавляет карту в руку игрока.

        :param card: карта для добавления
        """
        self.hand.append(card)

    def remove_card(self, card: Card) -> None:
        """Убирает карту из руки игрока.

        :param card: карта для удаления
        :raises ValueError: если карты нет в руке
        """
        try:
            self.hand.remove(card)
        except ValueError as exc:
            raise ValueError(f"Карты {card} нет в руке игрока {self.name}") from exc

    def is_empty(self) -> bool:
        """Проверяет, пуста ли рука игрока."""
        return not self.hand

    def deactivate(self) -> None:
        """Помечает игрока как выбывшего из активной игры.

        Вызывается, когда рука игрока пуста и колода исчерпана
        (см. PODKIDNOY_DURAK_RULES.md §22).
        """
        self.is_active = False

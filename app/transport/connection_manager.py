"""Менеджер WebSocket-соединений и тестовой авторизации."""

from __future__ import annotations

from fastapi import WebSocket

__all__ = ["ConnectionManager", "manager"]


class ConnectionManager:
    """Управляет активными WebSocket-подключениями и их авторизацией."""

    USERS: dict[str, str] = {"player1": "123", "player2": "123"}

    def __init__(self) -> None:
        # Хранит активные сокеты и имя авторизованного пользователя (None если не авторизован)
        self.active_connections: dict[WebSocket, str | None] = {}

    async def connect(self, websocket: WebSocket) -> None:
        """Принимает соединение и регистрирует сокет как неавторизованный."""
        await websocket.accept()
        self.active_connections[websocket] = None

    def disconnect(self, websocket: WebSocket) -> None:
        """Удаляет сокет из списка активных подключений."""
        self.active_connections.pop(websocket, None)

    def authenticate(self, websocket: WebSocket, username: str, password: str) -> bool:
        """Проверяет пару логин/пароль и привязывает username к сокету."""
        if self.USERS.get(username) == password:
            self.active_connections[websocket] = username
            return True
        return False

    def get_username(self, websocket: WebSocket) -> str | None:
        """Возвращает логин авторизованного пользователя или None."""
        return self.active_connections.get(websocket)

    async def broadcast(self, message: dict) -> None:
        """Рассылает сообщение всем активным клиентам."""
        for connection in list(self.active_connections.keys()):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()

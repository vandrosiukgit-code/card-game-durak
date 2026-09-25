"""Точка входа FastAPI: WebSocket-эндпоинт и раздача статики."""

from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from app.transport.connection_manager import manager

app = FastAPI(title="Durak Walking Skeleton")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "AUTH":
                username = data.get("username", "")
                password = data.get("password", "")
                if manager.authenticate(websocket, username, password):
                    await websocket.send_json({"type": "AUTH_SUCCESS", "username": username})
                else:
                    await websocket.send_json(
                        {"type": "AUTH_FAIL", "message": "Неверный логин или пароль"}
                    )

            elif msg_type == "ACTION_MOVE":
                username = manager.get_username(websocket)
                if not username:
                    await websocket.send_json(
                        {"type": "ERROR", "message": "Требуется авторизация"}
                    )
                    continue

                timestamp = datetime.now().strftime("%H:%M:%S")
                await manager.broadcast(
                    {
                        "type": "SYSTEM_LOG",
                        "text": (
                            f"[{timestamp}] Сервер подтверждает: "
                            f"Игрок '{username}' успешно выполнил 'Ход'!"
                        ),
                    }
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Монтируем статику последней, чтобы не перехватывать роуты
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

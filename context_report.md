# Context Report: card-game-durak

> Отчёт о состоянии проекта «Подкидной Дурак» (Walking Skeleton).
> Сформирован для быстрого погружения в контекст.

## 1. Общее описание

Проект представляет собой **walking skeleton** (минимальный сквозной каркас) сетевой
карточной игры «Подкидной Дурак». Реализован полный вертикальный срез:

- доменная модель карт (чистая бизнес-логика);
- транспортный слой на WebSocket (FastAPI);
- тестовая авторизация;
- простой веб-клиент (HTML + JS) для ручной проверки.

Игровая логика (правила ходов, взятие карт, определение победителя) **пока не реализована** —
эндпоинт `ACTION_MOVE` лишь подтверждает получение команды и рассылает системный лог.

## 2. Файловая структура

```
card-game-durak/
├── .gitignore
├── .pre-commit-config.yaml
├── README.md
├── main.py                          # Точка входа (uvicorn.run)
├── pyproject.toml                   # Конфигурация ruff + mypy
├── requirements.txt                 # Зависимости
├── .idea/                           # Настройки PyCharm (не код)
│   ├── .gitignore
│   ├── PythonProjects.iml
│   ├── inspectionProfiles/
│   │   ├── Project_Default.xml
│   │   └── profiles_settings.xml
│   ├── misc.xml
│   ├── modules.xml
│   └── vcs.xml
├── app/
│   ├── __init__.py                  # Пакет приложения
│   ├── main.py                      # FastAPI: WebSocket-эндпоинт + статика
│   ├── domain/
│   │   ├── __init__.py
│   │   └── cards.py                 # Suit, Rank, Card, Deck
│   ├── transport/
│   │   ├── __init__.py
│   │   └── connection_manager.py    # ConnectionManager, manager
│   └── static/
│       ├── index.html               # Тестовый UI
│       └── app.js                   # WebSocket-клиент
└── tests/
    ├── __init__.py
    └── test_cards.py                # Юнит-тесты доменной модели
```

## 3. Слои и зависимости

```
┌─────────────────────────────────────────────┐
│  app/static (index.html, app.js)            │  ← браузер
└───────────────────┬─────────────────────────┘
                    │ WebSocket /ws (JSON)
┌───────────────────▼─────────────────────────┐
│  app/main.py (FastAPI)                      │  ← транспорт
│    • websocket_endpoint                     │
│    • StaticFiles mount("/")                 │
└───────────────────┬─────────────────────────┘
                    │
┌───────────────────▼─────────────────────────┐
│  app/transport/connection_manager.py        │  ← управление соединениями
│    • ConnectionManager, manager             │
└───────────────────┬─────────────────────────┘
                    │ (пока не используется)
┌───────────────────▼─────────────────────────┐
│  app/domain/cards.py                        │  ← чистая доменная логика
│    • Suit, Rank, Card, Deck                 │
└─────────────────────────────────────────────┘
```

**Ключевой принцип:** `app/domain` не зависит от FastAPI и сторонних библиотек
(кроме стандартной). Транспорт зависит от домена, но не наоборот.

## 4. Содержание модулей

### 4.1. `app/domain/cards.py`

Чистая доменная модель, изолированная от веб-фреймворков.

| Сущность | Тип | Описание |
|---|---|---|
| `Suit` | `StrEnum` | Масти: `HEARTS="♥"`, `DIAMONDS="♦"`, `CLUBS="♣"`, `SPADES="♠"`. Свойство `symbol`. |
| `Rank` | `IntEnum` | Ранги 6..14 (`SIX=6` … `ACE=14`). Свойство `label` → `"6".."A"`. |
| `Card` | `@dataclass(frozen=True, slots=True)` | Неизменяемая карта (`suit`, `rank`). `__str__` → `"A♥"`, `__repr__` → `Card(suit=HEARTS, rank=ACE)`. |
| `Deck` | класс | Колода из 36 карт. |

**API `Deck`:**

- `CARDS_IN_DECK: int = 36` — константа.
- `__len__()` — текущее число карт.
- `cards` (property) → `tuple[Card, ...]` — содержимое только для чтения.
- `shuffle()` — перемешивание (`random.shuffle`).
- `draw(count: int) -> list[Card]` — взять `count` карт сверху.
  - `ValueError`, если `count <= 0`.
  - `ValueError`, если `count > len(self._cards)`.

### 4.2. `app/transport/connection_manager.py`

Управление активными WebSocket-подключениями и тестовой авторизацией.

| Элемент | Описание |
|---|---|
| `ConnectionManager.USERS` | `{"player1": "123", "player2": "123"}` — тестовые учётки (в коде, не в БД). |
| `active_connections` | `dict[WebSocket, str \| None]` — сокет → логин (или `None`). |
| `connect(ws)` | `accept()` + регистрация как неавторизованного. |
| `disconnect(ws)` | Удаление сокета. |
| `authenticate(ws, username, password) -> bool` | Проверка пары и привязка `username` к сокету. |
| `get_username(ws) -> str \| None` | Логин авторизованного пользователя. |
| `broadcast(message: dict)` | Рассылка всем; при ошибке — `disconnect`. |
| `manager` | Глобальный синглтон `ConnectionManager()`. |

### 4.3. `app/main.py`

FastAPI-приложение `Durak Walking Skeleton`.

- **`@app.websocket("/ws")`** — `websocket_endpoint`:
  - `connect` → цикл `receive_json`;
  - `AUTH` → `authenticate` → `AUTH_SUCCESS` / `AUTH_FAIL`;
  - `ACTION_MOVE` → проверка авторизации → `broadcast` `SYSTEM_LOG`
    с временной меткой `HH:MM:SS`;
  - `WebSocketDisconnect` → `disconnect`.
- **`app.mount("/", StaticFiles(directory="app/static", html=True))`** —
  монтируется **последним**, чтобы не перехватывать `/ws`.

### 4.4. `app/static/index.html` + `app/static/app.js`

Тестовый стенд (тёмная тема, monospace):

- экран авторизации (`#auth-screen`) — логин/пароль, кнопка «Войти»;
- игровой экран (`#game-screen`) — кнопка «Сделать ход»;
- сетевой лог (`#log`) — вывод `SYSTEM_LOG`.

`app.js`:
- открывает `ws(s)://<host>/ws`;
- обрабатывает `AUTH_SUCCESS`, `AUTH_FAIL`, `SYSTEM_LOG`, `ERROR`;
- отправляет `{type:"AUTH", username, password}` и `{type:"ACTION_MOVE"}`.

### 4.5. `main.py` (корень)

```python
uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
```

### 4.6. `tests/test_cards.py`

Юнит-тесты `Deck` и `Card` (pytest):

- 36 уникальных карт, все комбинации масть×ранг;
- `draw` уменьшает колоду, берёт сверху, ошибки при `count<=0` и `count>len`;
- `shuffle` сохраняет состав;
- `str`/`repr` карты;
- иммутабельность `Card` (frozen).

## 5. Протокол WebSocket (JSON)

| Направление | `type` | Поля | Ответ сервера |
|---|---|---|---|
| C→S | `AUTH` | `username`, `password` | `AUTH_SUCCESS` / `AUTH_FAIL` |
| C→S | `ACTION_MOVE` | — | `SYSTEM_LOG` (broadcast) или `ERROR` |
| S→C | `AUTH_SUCCESS` | `username` | — |
| S→C | `AUTH_FAIL` | `message` | — |
| S→C | `SYSTEM_LOG` | `text` | — |
| S→C | `ERROR` | `message` | — |

## 6. Конфигурация и зависимости

### `requirements.txt`

```
fastapi>=0.110.0
uvicorn[standard]>=0.28.0
websockets>=12.0
pytest>=8.0.0
```

### `pyproject.toml`

- **ruff**: `line-length=88`, `target-version="py311"`,
  `select=["E","W","F","I","B"]`, `quote-style="double"`.
- **mypy**: `python_version="3.11"`, `disallow_untyped_defs=true`,
  `warn_return_any=true`, `ignore_missing_imports=true`.

### `.pre-commit-config.yaml`

- `ruff` (`--fix`) + `ruff-format`;
- `mypy`.

## 7. Запуск

```bash
python -m pip install -r requirements.txt
python main.py
# или
python -m uvicorn app.main:app --reload --port 8000
```

Открыть: http://127.0.0.1:8000/

Тестовые учётки: `player1 / 123`, `player2 / 123`.

## 8. Текущее состояние и точки расширения

**Реализовано:**
- доменная модель карт + тесты;
- WebSocket-транспорт, авторизация, broadcast;
- тестовый веб-клиент.

**Не реализовано (кандидаты на развитие):**
- игровая логика: раздача, ходы, отбой, взятие, козырь, конец игры;
- доменные сущности `Player`, `Game`, `Table`, `GameState`;
- комнаты/лобби (сейчас один общий broadcast);
- персистентность (БД) и реальная аутентификация (JWT/сессии);
- типизированные схемы сообщений (Pydantic-модели вместо `dict`);
- расширение тестов: транспорт, интеграционные WebSocket-тесты.

**Замечания по коду:**
- `ConnectionManager.USERS` — тестовые данные в коде, вынести в конфиг/БД.
- `broadcast` использует `except Exception` — стоит сузить.
- `app/domain/__init__.py` и `app/transport/__init__.py` пусты — можно
  реэкспортировать публичный API.

## 9. История коммитов (последние 5)

| Хеш | Сообщение |
|---|---|
| `f5e3bf9` | feat: добавь requirements.txt и запуск сервера через uvicorn |
| `61fd802` | feat: добавить WebSocket-авторизацию и обработку хода |
| `6b6a57c` | feat: добавь доменную модель карт и тесты колоды |
| `c645fcf` | feat: добавить функцию вычисления среднего значения |
| `947aa22` | build: setup environment, ruff, mypy and pre-commit hooks |

**Последний коммит `f5e3bf9`** затронул: `README.md`, `main.py`, `requirements.txt`.

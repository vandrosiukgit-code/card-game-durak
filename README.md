# card-game-durak

Сетевая карточная игра «Подкидной Дурак» в браузере.

## Документация

- `VISION.md` — концепция проекта (единственный источник истины по продукту).
- `CONVENTIONS.md` — правила работы над проектом и роль ассистента.
- `PODKIDNOY_DURAK_RULES.md` — спецификация правил игры.
- `docs/design.md` — дизайн-документ (функционал, визуал, стек).

## Стек

- Python 3.11+, FastAPI, uvicorn, WebSocket
- Vanilla JS + HTML (клиент)
- SQLite (позже)
- pytest, ruff, mypy, pre-commit

## Установка

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pre-commit install
```

## Запуск тестов и линтеров

```bash
pytest
ruff check .
mypy .
```

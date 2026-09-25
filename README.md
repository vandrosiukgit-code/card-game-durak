# card-game-durak

## Быстрый старт

Установите зависимости проекта:

```bash
python -m pip install -r requirements.txt
```

Запустить сервер можно двумя альтернативными способами.

### Способ А: Запуск скрипта напрямую

```bash
python main.py
```

### Способ Б: Запуск через модуль

```bash
python -m uvicorn app.main:app --reload --port 8000
```

После запуска откройте в браузере: http://127.0.0.1:8000/

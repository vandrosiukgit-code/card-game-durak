import logging

import uvicorn

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
    except KeyboardInterrupt:
        logger.info("Сервер остановлен пользователем")
    except OSError as exc:
        logger.error("Не удалось запустить сервер: %s", exc)
        raise SystemExit(1) from exc
    except Exception as exc:
        logger.exception("Непредвиденная ошибка при запуске сервера: %s", exc)
        raise SystemExit(1) from exc

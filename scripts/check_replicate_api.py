"""Проверка доступности Replicate API и валидности токена.

Минимальный CLI-скрипт для диагностики: убедиться, что токен задан,
SDK установлен, модель доступна. Опционально — сделать реальный
запрос на генерацию (``--full``).

Использование::

    export REPLICATE_API_TOKEN=r8_...   # Windows: set REPLICATE_API_TOKEN=r8_...
    python scripts/check_replicate_api.py
    python scripts/check_replicate_api.py --model black-forest-labs/flux-schnell
    python scripts/check_replicate_api.py --full

Требования: Python 3.11+ и пакет ``replicate`` (см. ``requirements.txt``).
"""

from __future__ import annotations

import argparse
import os
import sys
import time

DEFAULT_MODEL = "black-forest-labs/flux-schnell"
TOKEN_ENV = "REPLICATE_API_TOKEN"
TIMEOUT_ENV = "REPLICATE_TIMEOUT"
DEFAULT_TIMEOUT = 300.0


def _check_token() -> str | None:
    """Проверяет наличие токена в переменной окружения.

    :return: токен или ``None``, если не задан
    """
    token = os.environ.get(TOKEN_ENV)
    if not token:
        print(
            f"[FAIL] Переменная окружения {TOKEN_ENV} не задана.\n"
            f"       Установи её: export {TOKEN_ENV}=r8_... "
            f"(Windows: set {TOKEN_ENV}=r8_...)",
            file=sys.stderr,
        )
        return None
    if not token.isascii():
        print(
            f"[FAIL] Токен {TOKEN_ENV} содержит не-ASCII символы. "
            f"Скопируй его заново из Replicate.",
            file=sys.stderr,
        )
        return None
    print(f"[ OK ] Токен {TOKEN_ENV} задан (длина {len(token)}, ASCII).")
    return token


def _check_sdk() -> bool:
    """Проверяет, что пакет ``replicate`` установлен.

    :return: ``True``, если SDK доступен
    """
    try:
        import replicate  # noqa: F401
    except ImportError:
        print(
            "[FAIL] Пакет 'replicate' не установлен.\n"
            "       Установи: python -m pip install replicate",
            file=sys.stderr,
        )
        return False
    print("[ OK ] Пакет 'replicate' установлен.")
    return True


def _check_model(model: str) -> bool:
    """Проверяет доступность модели через API.

    :param model: идентификатор модели (``owner/name``)
    :return: ``True``, если модель доступна
    """
    import replicate

    try:
        info = replicate.models.get(model)
    except Exception as exc:  # noqa: BLE001 — SDK бросает разные типы
        print(f"[FAIL] Не удалось получить модель {model!r}: {exc}", file=sys.stderr)
        return False

    owner = getattr(info, "owner", "?")
    name = getattr(info, "name", "?")
    print(f"[ OK ] Модель доступна: {owner}/{name}")

    # Пробуем получить цену из API (может отсутствовать).
    latest = getattr(info, "latest_version", None)
    if latest is not None:
        price = getattr(latest, "cost_per_second", None)
        if price is not None:
            print(f"       Цена: ${price:.4f}/сек predict_time")

    return True


def _create_prediction(model: str) -> object:
    """Создаёт prediction через ``predictions.create(version=...)``.

    Использует ``latest_version.id`` модели — это единственный рабочий
    путь в текущем SDK (``predictions.create(model=...)`` падает с
    ``version: none is not an allowed value``).

    :param model: идентификатор модели (``owner/name``)
    :return: объект prediction
    :raises RuntimeError: если не удалось получить версию или создать prediction
    """
    import replicate

    payload = {
        "prompt": "a red apple on a white background",
        "aspect_ratio": "1:1",
        "output_format": "png",
        "num_outputs": 1,
    }

    try:
        info = replicate.models.get(model)
        version_id = info.latest_version.id
    except Exception as exc_info:  # noqa: BLE001
        raise RuntimeError(
            f"Не удалось получить latest_version для {model!r}: {exc_info}"
        ) from exc_info

    print(f"       [info] latest_version.id={version_id}")
    try:
        return replicate.predictions.create(version=version_id, input=payload)
    except Exception as exc_version:  # noqa: BLE001
        raise RuntimeError(
            f"predictions.create(version=...) не сработал: {exc_version}"
        ) from exc_version


def _check_full(model: str) -> bool:
    """Создаёт prediction через асинхронный API и ждёт завершения.

    Использует ``predictions.create`` + polling через ``predictions.get``.
    Это даёт полный контроль над таймаутом и доступ к метрикам.

    :param model: идентификатор модели
    :return: ``True``, если prediction успешно завершился и PNG скачан
    """
    import urllib.error
    import urllib.request

    import replicate

    timeout = float(os.environ.get(TIMEOUT_ENV, DEFAULT_TIMEOUT))
    print(f"[ .. ] Создаю prediction на {model}...")
    print("       Промпт: 'a red apple on a white background'")
    print(f"       Таймаут polling: {timeout:.0f}s (env {TIMEOUT_ENV})")

    started = time.monotonic()
    try:
        prediction = _create_prediction(model)
    except RuntimeError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return False

    prediction_id = getattr(prediction, "id", None)
    if not prediction_id:
        print(f"[FAIL] Replicate не вернул id: {prediction!r}", file=sys.stderr)
        return False
    print(f"       Prediction id={prediction_id}")
    print(f"       Начальный статус: {getattr(prediction, 'status', '?')!r}")

    last_status = None
    while True:
        elapsed = time.monotonic() - started
        if elapsed > timeout:
            print(
                f"[FAIL] Prediction {prediction_id} не завершился за "
                f"{timeout:.0f} сек.",
                file=sys.stderr,
            )
            return False

        status = getattr(prediction, "status", None)
        if status != last_status:
            print(f"       [{elapsed:5.1f}s] статус: {status!r}")
            last_status = status

        if status == "succeeded":
            break
        if status in ("failed", "canceled"):
            error = getattr(prediction, "error", None)
            print(
                f"[FAIL] Prediction {prediction_id} статус={status!r}, error={error!r}",
                file=sys.stderr,
            )
            return False

        time.sleep(2.0)
        try:
            prediction = replicate.predictions.get(prediction_id)
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] Ошибка опроса: {exc}", file=sys.stderr)
            return False

    elapsed = time.monotonic() - started
    output = getattr(prediction, "output", None)
    metrics = getattr(prediction, "metrics", {}) or {}
    print(f"[ OK ] Prediction завершён за {elapsed:.1f}s")
    print(f"       metrics: {metrics}")
    print(f"       output type: {type(output).__name__}")
    print(f"       output: {output!r}")

    if not output:
        print("[FAIL] output пустой", file=sys.stderr)
        return False

    image_url = output[0] if isinstance(output, list) else output
    print(f"       image_url: {image_url}")

    print("[ .. ] Скачиваю PNG...")
    try:
        request = urllib.request.Request(
            str(image_url),
            headers={"User-Agent": "card-game-durak/0.1 (check)"},
        )
        with urllib.request.urlopen(request, timeout=30.0) as response:
            content_type = response.headers.get("Content-Type", "?")
            data = response.read()
    except urllib.error.URLError as exc:
        print(f"[FAIL] Ошибка скачивания: {exc.reason}", file=sys.stderr)
        return False

    print(f"       Content-Type: {content_type}")
    print(f"       Размер: {len(data)} байт")
    print(f"       Первые 8 байт: {data[:8]!r}")

    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        print(
            "[FAIL] Данные не являются PNG (нет сигнатуры)",
            file=sys.stderr,
        )
        return False

    print("[ OK ] PNG скачан успешно.")
    return True


def _build_parser() -> argparse.ArgumentParser:
    """Собирает парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(
        prog="check_replicate_api",
        description=(
            "Проверка доступности Replicate API: токен, SDK, модель. "
            "С флагом --full делает реальный запрос на генерацию."
        ),
        epilog=(
            "Примеры:\n"
            "  python scripts/check_replicate_api.py\n"
            "  python scripts/check_replicate_api.py "
            "--model black-forest-labs/flux-schnell\n"
            "  python scripts/check_replicate_api.py --full\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Идентификатор модели (по умолчанию: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Сделать реальный запрос на генерацию (тратит кредиты).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Точка входа CLI. Возвращает код выхода (0 — успех, 1 — ошибка)."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    print(f"Проверка Replicate API (модель: {args.model})")
    print("-" * 60)

    if _check_token() is None:
        return 1
    if not _check_sdk():
        return 1
    if not _check_model(args.model):
        return 1

    if args.full:
        if not _check_full(args.model):
            return 1
    else:
        print("[skip] Реальный запрос не выполнялся (используй --full).")

    print("-" * 60)
    print("Итог: API доступен, токен валиден.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

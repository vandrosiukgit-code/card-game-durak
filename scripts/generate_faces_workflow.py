"""Пакетная генерация растровых портретов фигурных карт через Replicate FLUX.

Самостоятельный CLI-скрипт. Не импортирует ``app/`` и ``tools/``.
Генерирует 12 изображений (J/Q/K × 4 масти) в ``assets/art/`` и собирает
HTML-превью ``assets/art/preview.html`` для визуальной оценки единства стиля.

Использование::

    export REPLICATE_API_TOKEN=r8_...   # Windows: set REPLICATE_API_TOKEN=r8_...
    python scripts/generate_faces_workflow.py
    python scripts/generate_faces_workflow.py --force
    python scripts/generate_faces_workflow.py --only J_spades Q_hearts
    python scripts/generate_faces_workflow.py --output-dir ./out

Требования: Python 3.11+ и пакет ``replicate`` (см. ``requirements.txt``).
Токен Replicate читается из переменной окружения ``REPLICATE_API_TOKEN``.
Таймаут ожидания prediction — переменная окружения ``REPLICATE_TIMEOUT``
(по умолчанию 300 сек).
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import replicate

# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "assets" / "art"

REPLICATE_MODEL = "black-forest-labs/flux-schnell"
REPLICATE_BG_REMOVAL_MODEL = "bria/remove-background"
REPLICATE_TOKEN_ENV = "REPLICATE_API_TOKEN"
REPLICATE_TIMEOUT_ENV = "REPLICATE_TIMEOUT"
FACE_SEED_SALT_ENV = "FACE_SEED_SALT"

API_TIMEOUT = 30.0
DEFAULT_PREDICTION_TIMEOUT = 300.0
# Replicate ограничивает 6 запросов/мин при балансе < $5 (burst 1).
# Значит, между любыми запросами нужна пауза >= 10 сек. Берём 12 с запасом.
API_PAUSE_SECONDS = 12.0
POLL_INTERVAL_SECONDS = 2.0
USER_AGENT = "card-game-durak/0.1 (face-generator)"


RANKS: tuple[str, ...] = ("J", "Q", "K")
SUITS: tuple[str, ...] = ("spades", "hearts", "clubs", "diamonds")

# ---------------------------------------------------------------------------
# Матрица промптов
# ---------------------------------------------------------------------------

CORE_STYLE = (
    "2D playing card character bust portrait, cut off strictly at the waist, "
    "perfectly centered facing forward. Traditional Russian imperial playing "
    "card style, Russian lubok aesthetic, flat vector art, clean bold black "
    "line art, rich saturated colors (deep red, gold, royal blue, forest "
    "green), decorative ornamental border around the character. "
    "Isolated character on a pure solid chroma-key green background "
    "(#00ff00), no shadows on the background, no gradients on the background. "
    "Plain solid green background only, character fills the frame, "
    "no decorative elements around the character, no symbols in the corners. "
    "STRICTLY NO letters, NO numbers, NO digits, NO rank labels, "
    "NO corner indices, NO playing card suit symbols (no hearts, no diamonds, "
    "no clubs, no spades), NO card frames, NO borders, NO margins, "
    "NO text, NO typography, NO watermarks, NO signatures."
)

SUIT_MODIFIERS: dict[str, str] = {
    "spades": (
        "Northern Russian warrior theme, cold steel accents, dark iron armor "
        "and wolf fur collar, sharp angular silhouettes, serious expression."
    ),
    "hearts": (
        "Russian royal court theme, rich scarlet red #c8102e velvet garments, "
        "flowing curved drapery, warm gold embroidery, graceful regal "
        "expression."
    ),
    "clubs": (
        "Russian boyar nobility, heavy dark robes, bronze filigree, "
        "dignified ornate collars, stoic expression."
    ),
    "diamonds": (
        "Russian merchant aristocracy, rich gold and amber jewelry, crisp "
        "geometric brocade patterns, luxurious elegant attire."
    ),
}

RANK_ROLES: dict[str, str] = {
    "J": (
        "Young Russian bogatyr squire, pointed helmet with fur trim, "
        "short red kaftan with gold embroidery, holding a sword, "
        "determined expression"
    ),
    "Q": (
        "Russian tsarina, tall kokoshnik headdress with pearls and gold, "
        "long flowing sarafan gown with rich embroidery, holding a flower, "
        "graceful regal expression"
    ),
    "K": (
        "Russian tsar, Monomakh cap with fur trim and gold cross, "
        "heavy brocade kaftan with fur collar, holding a scepter, "
        "long beard, majestic stern expression"
    ),
}


# ---------------------------------------------------------------------------
# Промпты и seed
# ---------------------------------------------------------------------------


def build_prompt(rank: str, suit: str) -> str:
    """Собирает полный промпт для пары (rank, suit).

    :param rank: номинал (``J``, ``Q``, ``K``)
    :param suit: масть (``spades``, ``hearts``, ``clubs``, ``diamonds``)
    :return: строка промпта
    """
    return " ".join(
        [
            RANK_ROLES[rank],
            SUIT_MODIFIERS[suit],
            CORE_STYLE,
        ]
    )


def deterministic_seed(rank: str, suit: str) -> int:
    """Возвращает детерминированный seed на основе пары (rank, suit).

    Использует SHA-256 — стабильно между запусками и платформами
    (в отличие от встроенного ``hash()``, который рандомизирован).

    Соль читается из переменной окружения ``FACE_SEED_SALT``. Это
    позволяет перегенерировать конкретную карту с другим seed, не
    меняя код: ``FACE_SEED_SALT=v2 python scripts/generate_faces_workflow.py
    --only K_hearts --force``.

    :param rank: номинал
    :param suit: масть
    :return: целое число в диапазоне [0, 2**31)
    """
    salt = os.environ.get(FACE_SEED_SALT_ENV, "")
    digest = hashlib.sha256(f"{rank}_{suit}_{salt}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % (2**31)


def build_prediction_input(rank: str, suit: str) -> dict:
    """Собирает входные параметры модели для пары (rank, suit).

    :param rank: номинал
    :param suit: масть
    :return: словарь с параметрами для ``replicate.run``
    """
    return {
        "prompt": build_prompt(rank, suit),
        "aspect_ratio": "2:3",
        "output_format": "png",
        "seed": deterministic_seed(rank, suit),
        "num_outputs": 1,
    }


# ---------------------------------------------------------------------------
# Загрузка
# ---------------------------------------------------------------------------


def _is_rate_limit_error(exc: Exception) -> bool:
    """Проверяет, является ли исключение ошибкой rate-limit (429).

    :param exc: исключение от SDK Replicate
    :return: ``True``, если это похоже на rate-limit
    """
    text = str(exc).lower()
    return "429" in text or "rate limit" in text or "throttled" in text


def _create_prediction(rank: str, suit: str) -> object:
    """Создаёт prediction через ``predictions.create(version=...)``.

    Использует ``latest_version.id`` модели — это единственный рабочий
    путь в текущем SDK (``predictions.create(model=...)`` падает с
    ``version: none is not an allowed value``).

    :param rank: номинал
    :param suit: масть
    :return: объект prediction
    :raises RuntimeError: если не удалось получить версию или создать prediction
    """
    payload = build_prediction_input(rank, suit)

    try:
        info = replicate.models.get(REPLICATE_MODEL)
        version_id = info.latest_version.id
    except Exception as exc_info:  # noqa: BLE001
        raise RuntimeError(
            f"Не удалось получить latest_version для {REPLICATE_MODEL!r}: {exc_info}"
        ) from exc_info

    for attempt in range(3):
        try:
            return replicate.predictions.create(version=version_id, input=payload)
        except Exception as exc_version:  # noqa: BLE001
            if _is_rate_limit_error(exc_version) and attempt < 2:
                print(
                    f"[warn] rate-limit, жду {API_PAUSE_SECONDS:.0f} сек "
                    f"(попытка {attempt + 1}/3)",
                    file=sys.stderr,
                )
                time.sleep(API_PAUSE_SECONDS)
                continue
            raise RuntimeError(
                f"predictions.create(version=...) не сработал: {exc_version}"
            ) from exc_version
    raise RuntimeError("predictions.create: исчерпаны попытки retry")


def _run_prediction(rank: str, suit: str) -> dict:
    """Запускает prediction и ждёт завершения через polling.

    Использует ``predictions.create`` + ``predictions.get`` — это даёт
    полный контроль над таймаутом (``replicate.run`` игнорирует параметр
    ``timeout`` и использует внутренний дефолт ~60 сек).

    Таймаут контролируется через env-переменную ``REPLICATE_TIMEOUT``
    (по умолчанию 300 сек).

    :param rank: номинал
    :param suit: масть
    :return: словарь с ключами ``output``, ``metrics``, ``elapsed``
    :raises RuntimeError: при ошибке API, таймауте или пустом ответе
    """
    timeout = float(os.environ.get(REPLICATE_TIMEOUT_ENV, DEFAULT_PREDICTION_TIMEOUT))
    started = time.monotonic()

    try:
        prediction = _create_prediction(rank, suit)
    except RuntimeError:
        raise

    prediction_id = getattr(prediction, "id", None)
    if not prediction_id:
        raise RuntimeError(f"Replicate не вернул id: {prediction!r}")

    while True:
        elapsed = time.monotonic() - started
        if elapsed > timeout:
            raise RuntimeError(
                f"Prediction {prediction_id} не завершился за {timeout:.0f} сек."
            )

        status = getattr(prediction, "status", None)
        if status == "succeeded":
            break
        if status in ("failed", "canceled"):
            error = getattr(prediction, "error", None)
            raise RuntimeError(
                f"Prediction {prediction_id} статус={status!r}, error={error!r}"
            )

        time.sleep(POLL_INTERVAL_SECONDS)
        try:
            prediction = replicate.predictions.get(prediction_id)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Ошибка опроса prediction: {exc}") from exc

    elapsed = time.monotonic() - started
    output = getattr(prediction, "output", None)
    if not output:
        raise RuntimeError(f"Replicate вернул пустой output: {output!r}")

    metrics = getattr(prediction, "metrics", {}) or {}
    return {
        "output": output,
        "metrics": metrics,
        "elapsed": elapsed,
    }


def _remove_background(image_url: str) -> str:
    """Удаляет фон с изображения через ``briaai/remove-background``.

    Возвращает URL PNG с альфа-каналом.

    :param image_url: URL исходного PNG
    :return: URL PNG с прозрачным фоном
    :raises RuntimeError: при ошибке API
    """
    timeout = float(os.environ.get(REPLICATE_TIMEOUT_ENV, DEFAULT_PREDICTION_TIMEOUT))
    started = time.monotonic()

    try:
        info = replicate.models.get(REPLICATE_BG_REMOVAL_MODEL)
        version_id = info.latest_version.id
    except Exception as exc_info:  # noqa: BLE001
        raise RuntimeError(
            f"Не удалось получить latest_version для "
            f"{REPLICATE_BG_REMOVAL_MODEL!r}: {exc_info}"
        ) from exc_info

    prediction = None
    for attempt in range(3):
        try:
            prediction = replicate.predictions.create(
                version=version_id,
                input={"image": image_url},
            )
            break
        except Exception as exc_create:  # noqa: BLE001
            if _is_rate_limit_error(exc_create) and attempt < 2:
                print(
                    f"[warn] rate-limit (remove-background), "
                    f"жду {API_PAUSE_SECONDS:.0f} сек "
                    f"(попытка {attempt + 1}/3)",
                    file=sys.stderr,
                )
                time.sleep(API_PAUSE_SECONDS)
                continue
            raise RuntimeError(
                f"predictions.create для remove-background не сработал: {exc_create}"
            ) from exc_create
    if prediction is None:
        raise RuntimeError("remove-background: исчерпаны попытки retry")

    prediction_id = getattr(prediction, "id", None)
    if not prediction_id:
        raise RuntimeError(f"Replicate не вернул id: {prediction!r}")

    while True:
        elapsed = time.monotonic() - started
        if elapsed > timeout:
            raise RuntimeError(
                f"remove-background {prediction_id} не завершился за {timeout:.0f} сек."
            )

        status = getattr(prediction, "status", None)
        if status == "succeeded":
            break
        if status in ("failed", "canceled"):
            error = getattr(prediction, "error", None)
            raise RuntimeError(
                f"remove-background {prediction_id} статус={status!r}, error={error!r}"
            )

        time.sleep(POLL_INTERVAL_SECONDS)
        try:
            prediction = replicate.predictions.get(prediction_id)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Ошибка опроса remove-background: {exc}") from exc

    output = getattr(prediction, "output", None)
    if not output:
        raise RuntimeError(f"remove-background вернул пустой output: {output!r}")
    url = output if isinstance(output, str) else output[0]
    return str(url)


def _fetch_model_price() -> tuple[float, str]:
    """Получает цену модели, парся HTML страницы Replicate.

    ⚠️ Хрупкий подход: зависит от вёрстки страницы. Если Replicate
    изменит HTML — функция упадёт с RuntimeError.

    :return: кортеж ``(цена_за_секунду, источник)``
    :raises RuntimeError: если не удалось получить или распарсить страницу
    """
    url = f"https://replicate.com/{REPLICATE_MODEL}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=API_TIMEOUT) as response:
            html = response.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Не удалось получить страницу модели {url}: {exc.reason}"
        ) from exc

    # Ищем паттерн вида "$0.003 per second" или "$3 per 1000 seconds".
    # Пробуем сначала "per second", потом "per 1000 seconds".
    match = re.search(
        r"\$([0-9.]+)\s*(?:USD\s*)?per\s+second",
        html,
        re.IGNORECASE,
    )
    if match:
        price = float(match.group(1))
        return price, "html (per second)"

    match = re.search(
        r"\$([0-9.]+)\s*(?:USD\s*)?per\s+1000\s+seconds",
        html,
        re.IGNORECASE,
    )
    if match:
        price = float(match.group(1)) / 1000.0
        return price, "html (per 1000 seconds)"

    raise RuntimeError(
        f"Не удалось найти цену на странице {url}. "
        f"Возможно, изменилась вёрстка. Проверь вручную."
    )


def generate_image(
    rank: str,
    suit: str,
    dest: Path,
    price_per_second: float,
) -> dict:
    """Генерирует изображение через Replicate, удаляет фон, сохраняет PNG.

    Двухшаговый процесс:

    1. ``flux-schnell`` генерирует портрет на chroma-key зелёном фоне.
    2. ``briaai/remove-background`` удаляет фон, возвращает PNG с альфой.

    Токен берётся из переменной окружения ``REPLICATE_API_TOKEN``
    (SDK ``replicate`` читает её автоматически).

    :param rank: номинал
    :param suit: масть
    :param dest: путь для сохранения PNG
    :param price_per_second: цена модели за секунду predict_time
    :return: словарь с метриками (``elapsed``, ``predict_time``, ``cost``,
        ``size_bytes``)
    :raises RuntimeError: при ошибке API или загрузки
    """
    result = _run_prediction(rank, suit)
    output = result["output"]
    image_url = output[0] if isinstance(output, list) else output

    # Пауза перед вторым запросом — иначе поймаем 429 rate-limit.
    time.sleep(API_PAUSE_SECONDS)

    # Шаг 2: удаляем фон через briaai/remove-background.
    transparent_url = _remove_background(image_url)

    # Скачиваем PNG с альфа-каналом.
    request = urllib.request.Request(
        transparent_url, headers={"User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(request, timeout=API_TIMEOUT) as response:
            data = response.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ошибка загрузки PNG: {exc.reason}") from exc

    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("Полученные данные не являются PNG (нет сигнатуры).")

    dest.write_bytes(data)

    metrics = result["metrics"]
    predict_time = metrics.get("predict_time")
    # Replicate не возвращает стоимость в metrics — считаем сами
    # по predict_time × цена модели.
    cost = predict_time * price_per_second if predict_time is not None else None
    return {
        "elapsed": result["elapsed"],
        "predict_time": predict_time,
        "cost": cost,
        "size_bytes": len(data),
    }


# ---------------------------------------------------------------------------
# HTML-превью
# ---------------------------------------------------------------------------

_PREVIEW_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Face cards preview</title>
<style>
  body {{
    margin: 0;
    padding: 24px;
    background: #0e0e0e;
    color: #e0e0e0;
    font-family: system-ui, sans-serif;
  }}
  h1 {{ font-size: 18px; font-weight: 500; margin: 0 0 16px; }}
  .grid {{
    display: grid;
    grid-template-columns: 60px repeat(4, 1fr);
    gap: 12px;
    max-width: 1200px;
  }}
  .cell {{
    background: #1a1a1a;
    border-radius: 8px;
    overflow: hidden;
    aspect-ratio: 1 / 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  .cell img {{ width: 100%; height: 100%; object-fit: contain; display: block; }}
  .label {{
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    font-weight: 600;
    color: #888;
  }}
  .header {{ font-size: 14px; color: #888; text-align: center; }}
</style>
</head>
<body>
<h1>Face cards — {count} изображений</h1>
<div class="grid">
  <div></div>
{headers}
{rows}
</div>
</body>
</html>
"""


def build_preview_html(output_dir: Path) -> str:
    """Собирает HTML-превью всех сгенерированных портретов.

    :param output_dir: каталог с PNG-файлами
    :return: строка HTML
    """
    headers = "\n".join(f'  <div class="header">{suit}</div>' for suit in SUITS)
    rows: list[str] = []
    count = 0
    for rank in RANKS:
        cells = [f'  <div class="label">{rank}</div>']
        for suit in SUITS:
            filename = f"{rank}_{suit}.png"
            if (output_dir / filename).exists():
                cells.append(
                    f'  <div class="cell">'
                    f'<img src="{filename}" alt="{rank} {suit}">'
                    f"</div>"
                )
                count += 1
            else:
                cells.append('  <div class="cell"></div>')
        rows.append("\n".join(cells))
    return _PREVIEW_TEMPLATE.format(
        count=count,
        headers=headers,
        rows="\n".join(rows),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_target(value: str) -> tuple[str, str]:
    """Разбирает строку вида ``J_spades`` в пару (rank, suit)."""
    parts = value.strip().split("_", 1)
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(
            f"Ожидается формат RANK_SUIT (например, J_spades), получено: {value!r}"
        )
    rank, suit = parts[0].upper(), parts[1].lower()
    if rank not in RANKS:
        raise argparse.ArgumentTypeError(
            f"Неизвестный номинал: {rank!r}. Допустимо: {', '.join(RANKS)}"
        )
    if suit not in SUITS:
        raise argparse.ArgumentTypeError(
            f"Неизвестная масть: {suit!r}. Допустимо: {', '.join(SUITS)}"
        )
    return rank, suit


def _build_parser() -> argparse.ArgumentParser:
    """Собирает парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(
        prog="generate_faces_workflow",
        description=(
            "Пакетная генерация портретов фигурных карт (J/Q/K × 4 масти) "
            "через Replicate FLUX. Собирает HTML-превью."
        ),
        epilog=(
            "Примеры:\n"
            "  python scripts/generate_faces_workflow.py\n"
            "  python scripts/generate_faces_workflow.py --force\n"
            "  python scripts/generate_faces_workflow.py --only J_spades Q_hearts\n"
            "  python scripts/generate_faces_workflow.py -o ./out\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--only",
        nargs="+",
        type=_parse_target,
        default=None,
        metavar="RANK_SUIT",
        help="Сгенерировать только указанные пары (например, J_spades Q_hearts).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Перезаписать существующие файлы.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Каталог для сохранения PNG (по умолчанию: {DEFAULT_OUTPUT_DIR}).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Точка входа CLI. Возвращает код выхода (0 — успех, 1 — были ошибки)."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not os.environ.get(REPLICATE_TOKEN_ENV):
        print(
            f"Ошибка: переменная окружения {REPLICATE_TOKEN_ENV} не задана.\n"
            f"Установи её: export {REPLICATE_TOKEN_ENV}=r8_... "
            f"(Windows: set {REPLICATE_TOKEN_ENV}=r8_...)",
            file=sys.stderr,
        )
        return 1

    try:
        price_per_second, price_source = _fetch_model_price()
        print(
            f"[info] Цена модели: ${price_per_second:.4f}/сек "
            f"(источник: {price_source})"
        )
    except RuntimeError as exc:
        price_per_second = 0.0
        print(
            f"[warn] Не удалось получить цену модели: {exc}\n"
            f"[warn] Продолжаю без оценки стоимости (cost будет n/a).",
            file=sys.stderr,
        )

    targets: list[tuple[str, str]] = (
        list(args.only)
        if args.only is not None
        else [(rank, suit) for rank in RANKS for suit in SUITS]
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)

    generated = 0
    skipped = 0
    failed = 0
    total_cost = 0.0

    for index, (rank, suit) in enumerate(targets):
        dest = args.output_dir / f"{rank}_{suit}.png"

        if dest.exists() and not args.force:
            mtime = time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(dest.stat().st_mtime),
            )
            print(
                f"[skip] {dest.name} уже существует "
                f"(создан {mtime}, {dest.stat().st_size} байт). "
                f"Используй --force для перезаписи."
            )
            skipped += 1
            continue

        if dest.exists() and args.force:
            mtime = time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(dest.stat().st_mtime),
            )
            print(f"[over] {dest.name} будет перезаписан (старый файл от {mtime})")

        print(f"[gen ] {dest.name} (seed={deterministic_seed(rank, suit)})")
        try:
            stats = generate_image(rank, suit, dest, price_per_second)
            generated += 1
            if stats["cost"] is not None:
                total_cost += stats["cost"]
            cost_str = f"${stats['cost']:.4f}" if stats["cost"] is not None else "n/a"
            predict_str = (
                f"{stats['predict_time']:.2f}s"
                if stats["predict_time"] is not None
                else "n/a"
            )
            mtime = time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(dest.stat().st_mtime),
            )
            print(
                f"[ ok ] {dest.name}: "
                f"predict={predict_str}, "
                f"cost={cost_str}, "
                f"total={stats['elapsed']:.1f}s, "
                f"size={stats['size_bytes'] / 1024:.0f} KB, "
                f"записан {mtime}"
            )
        except RuntimeError as exc:
            print(f"[fail] {dest.name}: {exc}", file=sys.stderr)
            failed += 1

        # Пауза между запросами, кроме последнего.
        if index < len(targets) - 1:
            time.sleep(API_PAUSE_SECONDS)

    # HTML-превью собираем только если есть хоть один PNG.
    if generated > 0:
        preview_path = args.output_dir / "preview.html"
        preview_path.write_text(build_preview_html(args.output_dir), encoding="utf-8")
        print(f"[html] {preview_path.resolve()}")

    print(f"Готово: сгенерировано {generated}, пропущено {skipped}, ошибок {failed}.")
    if total_cost > 0:
        print(
            f"Cost: ${total_cost / max(generated, 1):.4f} per image, "
            f"${total_cost:.4f} total"
        )
    if failed:
        print(
            "Подробности ошибок — выше в stderr (строки [fail]).",
            file=sys.stderr,
        )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

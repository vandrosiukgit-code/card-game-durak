"""Процедурный генератор SVG-карт для «Подкидного Дурака».

Разовый инструмент для Langflow (Custom Component).
Не является частью основного проекта.

Область применения
------------------

Скрипт генерирует SVG-карты для всех 36 карт колоды.

Числовые ранги (2–10) и туз (A) рисуются **пипсами** (символами масти).

Фигурные карты (J, Q, K) используют растровые портреты из
``assets/art/<RANK>_<suit>.png``, сгенерированные скриптом
``scripts/generate_faces_workflow.py``. Перед встраиванием PNG
обрезается по bounding box непрозрачных пикселей (``_trim_png_alpha``)
— это убирает прозрачные поля, из-за которых персонаж казался
смещённым относительно центра карты. В стиле русской колоды портрет
рисуется **дважды**: верхний — нормальный, нижний — повёрнутый на
180° вокруг центра карты. Портреты встраиваются в SVG как
base64-encoded ``<image>`` — это делает SVG самодостаточным
(не зависит от внешних файлов при рендере), но увеличивает размер
файла примерно на 66% от размера PNG (два портрета).

Раскладка пипсов (русская колода)
---------------------------------

Русская игральная колода — 36 карт: ранги 6–10, J, Q, K, A в четырёх
мастях (♥ ♦ ♣ ♠). Раскладка пипсов (символов масти) в русской колоде
совпадает со стандартной французской колодой и подчиняется правилу
**симметрии относительно центра карты**.

Пипсы располагаются в области ``pip_area`` — прямоугольнике с отступами
``pip_margin_x`` / ``pip_margin_y`` от краёв карты. Координаты задаются
в **нормированных долях** (0.0 — верх/лево, 1.0 — низ/право) и умножаются
на ширину/высоту области.

Стандартные раскладки для 2–10:

* **2** — две точки по вертикали (верх, низ).
* **3** — три точки по вертикали (верх, центр, низ).
* **4** — четыре точки по углам (2×2).
* **5** — четыре по углам + одна в центре.
* **6** — две колонки по три точки (2×3).
* **7** — шесть как у «6» + одна в центре между верхней парой.
* **8** — шесть как у «6» + две в центре (между верхней и нижней парами).
* **9** — две колонки по четыре точки (2×4) + одна в центре.
* **10** — две колонки по четыре точки (2×4) + две в центре (верх/низ).

Пипсы в нижней половине карты (``fy > 0.5``) **зеркалятся** поворотом
на 180° — это классический приём, чтобы символы масти «смотрели» вниз
и карта читалась одинаково с любой стороны.

Угловой индекс (якорь дизайна)
------------------------------

Угловой индекс — это **ранг + мелкая масть** в верхнем-левом и
(повёрнутый на 180°) в нижнем-правом углу карты. Его положение и размер
**фиксированы** для всех карт и не зависят от номинала. Это «якорь»
дизайна: при смене номинала меняется только внутренняя раскладка пипсов,
углы остаются на месте.

Параметры якоря задаются в ``CardStyle``:

* ``corner_padding_x`` / ``corner_padding_y`` — отступы от края карты;
* ``corner_rank_size`` — размер цифры ранга;
* ``corner_suit_size`` — размер мелкой масти под цифрой.

⚠️ **Не менять эти параметры без пересчёта коллизий** — есть тест
``test_corner_index_does_not_overlap_pip_area``, который проверяет, что
угловой индекс не пересекается с областью пипсов.

Запуск
------

Модуль запускается **из корня проекта** (там, где лежит ``tools/``)::

    cd /d/PythonProjects
    python -m tools.deck_design_system J --suit spades

⚠️ **Не запускать из папки ``tools/``** — тогда Python ищет
``tools/tools/deck_design_system.py`` и падает с ``No module named tools``.
Если очень нужно из ``tools/`` — используй ``python -m deck_design_system``
(без префикса ``tools.``).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Пути вывода
# ---------------------------------------------------------------------------

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "card_deck" / "cards"

# Каталог с растровыми портретами фигурных карт (J/Q/K × 4 масти).
# Генерируется скриптом scripts/generate_faces_workflow.py.
ART_DIR = Path(__file__).resolve().parent.parent / "assets" / "art"

# ---------------------------------------------------------------------------
# Параметры стиля
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CardStyle:
    """Параметры визуального стиля карты."""

    width: int = 825
    height: int = 1125
    border_color: str = "#1a1a1a"
    border_width: int = 2
    corner_radius: int = 40
    bg_color: str = "#ffffff"

    # Цвета мастей
    red_color: str = "#c8102e"
    black_color: str = "#1a1a1a"

    # Шрифты
    font_family: str = "'Times New Roman', 'Georgia', serif"
    corner_rank_size: int = 130
    corner_suit_size: int = 72
    pip_size: int = 170

    # Отступы
    corner_padding_x: int = 35
    corner_padding_y: int = 30
    pip_margin_x: int = 260
    pip_margin_y: int = 250

    # Зеркальность пипсов в нижней половине карты
    mirror_pips: bool = True


# ---------------------------------------------------------------------------
# Векторные пути мастей из assets/card_deck/cards/svg_samples/*.svg
# Формат: suit -> (viewBox_width, viewBox_height, path_d)
# ---------------------------------------------------------------------------

SUIT_PATHS: dict[str, tuple[float, float, str]] = {
    "hearts": (
        168,
        176,
        (
            "M68.8486 8.42593C74.4418 12.8289 77.728 18.1029 80.8486 24.4259"
            "C81.2237 25.113 81.5988 25.8001 81.9853 26.508C82.8486 28.4259"
            " 82.8486 28.4259 82.8486 31.4259C83.5086 31.4259 84.1686 31.4259"
            " 84.8486 31.4259C84.984 30.8923 85.1193 30.3586 85.2588 29.8087"
            "C88.3189 19.2174 94.5414 11.2878 103.849 5.42593C113.989 -0.0716867"
            " 125.897 -1.48457 137.099 1.61343C148.283 5.48065 157.207 11.878"
            " 162.849 22.4259C164.125 25.71 165.056 28.9956 165.849 32.4259"
            "C166.075 33.3953 166.302 34.3647 166.536 35.3634C166.639 36.3741"
            " 166.742 37.3847 166.849 38.4259C166.925 39.1323 167.001 39.8387"
            " 167.079 40.5666C168.579 66.9937 150.937 91.5199 134.458 110.422"
            "C132.069 113.172 129.761 115.967 127.474 118.801C124.42 122.56"
            " 121.288 126.234 118.097 129.876C105.655 144.08 94.2841 159.034"
            " 84.8486 175.426C81.192 172.089 78.6923 168.366 76.0361 164.238"
            "C72.2183 158.412 68.2394 152.839 63.8486 147.426C63.2479 146.664"
            " 62.6472 145.902 62.0283 145.117C56.0303 137.529 49.7587 130.173"
            " 43.4765 122.82C-1.34419 70.3568 -1.34419 70.3568 0.62205 36.3981"
            "C1.95338 24.8092 9.01118 15.226 17.7158 7.96108C33.0993 -3.11167"
            " 53.5594 -1.76685 68.8486 8.42593Z"
        ),
    ),
    "diamonds": (
        141,
        180,
        (
            "M70 0C74.2931 3.69573 76.7095 8.34622 79.5 13.1875C89.8587 30.7814"
            " 101.867 47.5091 115.734 62.5234C117.609 64.573 119.426 66.6532"
            " 121.238 68.7578C125.115 73.2016 129.244 77.3568 133.438 81.5"
            "C134.169 82.227 134.901 82.9541 135.654 83.7031C137.434 85.4711"
            " 139.216 87.2367 141 89C139.261 92.7669 137.097 95.2123 134 98"
            "C133.34 98 132.68 98 132 98C132 98.66 132 99.32 132 100"
            "C131.319 100.536 130.639 101.072 129.938 101.625C126.865 104.109"
            " 124.492 106.754 121.938 109.75C119.923 112.089 117.841 114.354"
            " 115.75 116.625C110.163 122.822 105.06 129.371 100 136"
            "C99.0003 137.305 99.0003 137.305 97.9805 138.637C88.1552 151.813"
            " 79.4936 165.938 71 180C68.4704 177.677 66.7784 175.222 65.0039 172.289"
            "C64.4451 171.374 63.8863 170.459 63.3105 169.516C62.7337 168.562"
            " 62.1568 167.608 61.5625 166.625C58.2621 161.175 55.0179 155.956"
            " 51 151C51 150.34 51 149.68 51 149C50.34 149 49.68 149 49 149"
            "C48.7319 148.466 48.4638 147.933 48.1875 147.383C44.8056 140.953"
            " 40.6392 135.567 36 130C35.2743 129.1 34.5485 128.2 33.8008 127.273"
            "C29.4548 121.888 24.9849 116.654 20.3203 111.543C18.6983 109.765"
            " 17.09 107.975 15.4922 106.176C10.6196 100.715 5.66716 95.6382 0 91"
            "C1.56717 87.0083 4.17809 84.8437 7.375 82.0625C10.2658 79.5418"
            " 12.8457 77.1952 15.2266 74.1836C15.8118 73.463 16.397 72.7424 17 72"
            "C17.66 72 18.32 72 19 72C19.223 71.4573 19.446 70.9146 19.6758 70.3555"
            "C21.4164 67.2594 23.7542 64.8648 26.1875 62.3125C30.7639 57.4021"
            " 35.0191 52.4122 39 47C39.4507 46.3948 39.9014 45.7896 40.3657 45.166"
            "C51.1383 30.6742 60.8709 15.5755 70 0Z"
        ),
    ),
    "clubs": (
        172,
        174,
        (
            "M106.16 5.45321C115.093 10.9959 121.18 18.322 124.461 28.3438"
            "C126.954 39.434 125.598 50.4647 120.16 60.4532C116.905 64.842"
            " 113.101 68.6842 109.16 72.4532C110.086 71.9466 110.086 71.9466"
            " 111.031 71.4298C121.369 65.9855 131.614 63.5247 143.16 66.5782"
            "C153.917 70.1923 162.84 76.5211 168.035 86.7032C172.425 96.0644"
            " 172.656 107.001 170.324 117.059C166.298 127.501 159.727 134.189"
            " 149.871 139.262C140.075 143.567 128.752 144.183 118.562 140.555"
            "C108.289 135.844 99.4994 129.175 95.1597 118.453C95.1597 117.793"
            " 95.1597 117.133 95.1597 116.453C94.4997 116.453 93.8397 116.453"
            " 93.1597 116.453C94.8918 129.763 97.8075 142.429 102.597 154.953"
            "C102.873 155.682 103.149 156.412 103.434 157.163C105.244 161.724"
            " 107.453 165.733 110.191 169.807C111.16 171.453 111.16 171.453"
            " 111.16 173.453C94.6597 173.453 78.1597 173.453 61.1597 173.453"
            "C63.7997 168.173 66.4397 162.893 69.1597 157.453C74.7637 144.579"
            " 77.3883 132.5 77.1597 118.453C76.7099 119.227 76.26 120 75.7965 120.797"
            "C69.4596 131.058 61.9153 137.947 50.1597 141.453C49.5629 141.635"
            " 48.9661 141.817 48.3512 142.004C37.6149 144.205 26.8171 142.521"
            " 17.5347 136.828C8.19306 130.115 2.46283 121.751 0.159746 110.453"
            "C-0.703861 97.6999 1.84534 88.2039 9.98006 78.2188C17.7673 69.8326"
            " 27.259 66.1986 38.4722 65.1407C46.8337 65.8493 54.0796 67.9897"
            " 61.1597 72.4532C61.8197 72.4532 62.4797 72.4532 63.1597 72.4532"
            "C62.6519 72.0639 62.144 71.6746 61.6207 71.2735C53.7776 64.8992"
            " 48.1154 56.4922 46.1597 46.4532C45.0341 35.0719 47.349 23.7858"
            " 54.1597 14.4532C67.6563 -1.20161 88.3264 -4.03873 106.16 5.45321Z"
        ),
    ),
    "spades": (
        164,
        178,
        (
            "M81.2701 0C84.2421 2.00404 85.8077 3.58367 87.3326 6.8125"
            "C93.5453 18.5667 103.712 31.0097 114.27 39C115.947 40.6561"
            " 117.612 42.3247 119.27 44C120.703 45.4083 122.135 46.8165"
            " 123.57 48.2228C125.806 50.4182 128.034 52.6222 130.261 54.8264"
            "C131.424 55.974 132.589 57.119 133.757 58.261C143.624 67.9137"
            " 152.783 77.7601 158.77 90.375C159.103 91.0337 159.435 91.6924"
            " 159.778 92.3711C162.922 98.8005 163.422 104.42 163.458 111.5"
            "C163.472 112.768 163.486 114.037 163.501 115.344C163.273 118.961"
            " 162.588 121.643 161.27 125C161.01 125.69 160.749 126.379 160.481 127.09"
            "C156.697 135.454 149.697 140.699 141.27 144C130.052 147.739"
            " 118.243 146.858 107.606 141.711C100.448 137.667 95.1027 132.607"
            " 90.2701 126C90.5955 143.275 96.6636 162.274 107.27 176"
            "C107.27 176.66 107.27 177.32 107.27 178C90.4401 178 73.6101 178"
            " 56.2701 178C57.7837 174.216 58.7236 172.199 61.0201 169.125"
            "C69.7763 156.237 73.3782 140.347 74.2701 125C73.6101 125 72.9501 125"
            " 72.2701 125C72.011 125.744 71.7519 126.488 71.485 127.254"
            "C67.5039 136.253 57.9939 141.252 49.2818 144.812C39.0912 147.955"
            " 27.6713 146.82 18.2701 142C9.88409 136.888 3.08989 129.378"
            " 0.695913 119.672C-1.68953 104.703 2.15965 92.7688 10.6764 80.3555"
            "C13.0507 77.1001 15.6263 74.0408 18.2701 71C18.7281 70.4667"
            " 19.186 69.9333 19.6578 69.3838C25.2358 62.9118 25.2358 62.9118"
            " 28.2701 60C28.9301 60 29.5901 60 30.2701 60C30.5281 59.4115"
            " 30.7861 58.8231 31.0519 58.2168C32.3709 55.8167 33.7481 54.3768"
            " 35.7623 52.5312C36.4616 51.8839 37.1608 51.2365 37.8812 50.5696"
            "C38.6283 49.8866 39.3754 49.2037 40.1451 48.5C41.697 47.0572"
            " 43.2478 45.6132 44.7975 44.168C45.5604 43.4582 46.3234 42.7484"
            " 47.1095 42.0171C60.6953 29.3339 71.1631 15.5477 81.2701 0Z"
        ),
    ),
}

SUIT_COLORS: dict[str, str] = {
    "hearts": "red",
    "diamonds": "red",
    "clubs": "black",
    "spades": "black",
}


# ---------------------------------------------------------------------------
# Раскладка пипсов для рангов 2–10
# ---------------------------------------------------------------------------

# ⚠️ В «Подкидном Дураке» используются только ранги 6–10, J, Q, K, A.
# Раскладки для 2–5 оставлены для совместимости с французской колодой
# (52 карты) и не участвуют в генерации колоды Дурака.
PIP_LAYOUTS: dict[int, list[tuple[float, float]]] = {
    1: [(0.5, 0.5)],
    2: [(0.5, 0.0), (0.5, 1.0)],
    3: [(0.5, 0.0), (0.5, 0.5), (0.5, 1.0)],
    4: [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)],
    5: [
        (0.0, 0.0),
        (1.0, 0.0),
        (0.5, 0.5),
        (0.0, 1.0),
        (1.0, 1.0),
    ],
    6: [
        (0.0, 0.0),
        (1.0, 0.0),
        (0.0, 0.5),
        (1.0, 0.5),
        (0.0, 1.0),
        (1.0, 1.0),
    ],
    7: [
        (0.0, 0.0),
        (1.0, 0.0),
        (0.5, 0.25),
        (0.0, 0.5),
        (1.0, 0.5),
        (0.0, 1.0),
        (1.0, 1.0),
    ],
    8: [
        (0.0, 0.0),
        (1.0, 0.0),
        (0.5, 0.25),
        (0.0, 0.5),
        (1.0, 0.5),
        (0.5, 0.75),
        (0.0, 1.0),
        (1.0, 1.0),
    ],
    9: [
        (0.0, 0.0),
        (1.0, 0.0),
        (0.0, 0.33),
        (1.0, 0.33),
        (0.5, 0.5),
        (0.0, 0.67),
        (1.0, 0.67),
        (0.0, 1.0),
        (1.0, 1.0),
    ],
    10: [
        (0.0, 0.0),
        (1.0, 0.0),
        (0.5, 0.17),
        (0.0, 0.33),
        (1.0, 0.33),
        (0.0, 0.67),
        (1.0, 0.67),
        (0.5, 0.83),
        (0.0, 1.0),
        (1.0, 1.0),
    ],
    14: [(0.5, 0.5)],  # A — один крупный пипс в центре
}

# Ранги, у которых пипсы рисуются крупнее (туз — один большой символ).
LARGE_PIP_RANKS: frozenset[int] = frozenset({14})

# Фигурные карты: рисуются растровым портретом, а не пипсами.
FACE_RANKS: frozenset[int] = frozenset({11, 12, 13})  # J, Q, K


# ---------------------------------------------------------------------------
# Генерация SVG
# ---------------------------------------------------------------------------


def _corner_index_bbox(style: CardStyle) -> tuple[float, float, float, float]:
    """Возвращает bounding box углового индекса (x_min, y_min, x_max, y_max).

    Учитывает ранг (текст) и мелкую масть под ним. Используется для
    проверки коллизий с областью пипсов.
    """
    pad_x = style.corner_padding_x
    pad_y = style.corner_padding_y
    rank_size = style.corner_rank_size
    suit_size = style.corner_suit_size

    # Ранг: текст с text-anchor="middle" в точке (pad_x + rank_size/2, ...)
    # Приблизительно: ширина текста ~ rank_size * 0.7, высота ~ rank_size
    rank_x_min = pad_x
    rank_x_max = pad_x + rank_size
    rank_y_min = pad_y
    rank_y_max = pad_y + rank_size

    # Масть: квадрат suit_size, центр в (rank_x_center, rank_y_max + suit_size*0.6)
    suit_cx = pad_x + rank_size / 2
    suit_cy = rank_y_max + suit_size * 0.6
    suit_x_min = suit_cx - suit_size / 2
    suit_x_max = suit_cx + suit_size / 2
    suit_y_min = suit_cy - suit_size / 2
    suit_y_max = suit_cy + suit_size / 2

    return (
        min(rank_x_min, suit_x_min),
        min(rank_y_min, suit_y_min),
        max(rank_x_max, suit_x_max),
        max(rank_y_max, suit_y_max),
    )


def _pip_area_bbox(style: CardStyle) -> tuple[float, float, float, float]:
    """Возвращает bounding box области пипсов (x_min, y_min, x_max, y_max)."""
    return (
        style.pip_margin_x,
        style.pip_margin_y,
        style.width - style.pip_margin_x,
        style.height - style.pip_margin_y,
    )


def _suit_color(suit: str, style: CardStyle) -> str:
    """Возвращает цвет масти (красный или чёрный)."""
    return style.red_color if SUIT_COLORS[suit] == "red" else style.black_color


def _suit_symbol(
    suit: str,
    x: float,
    y: float,
    size: float,
    color: str,
) -> str:
    """Возвращает SVG-элемент символа масти, вписанного в квадрат size×size."""
    vb_w, vb_h, path = SUIT_PATHS[suit]
    scale = size / max(vb_w, vb_h)
    # Центрируем символ внутри квадрата size×size
    offset_x = (size - vb_w * scale) / 2
    offset_y = (size - vb_h * scale) / 2
    tx = x - size / 2 + offset_x
    ty = y - size / 2 + offset_y
    return (
        f'<g transform="translate({tx:.2f},{ty:.2f}) scale({scale:.4f})">'
        f'<path d="{path}" fill="{color}"/>'
        f"</g>"
    )


def _trim_png_alpha(png_bytes: bytes) -> bytes:
    """Обрезает прозрачные поля PNG по bounding box непрозрачных пикселей.

    Использует только stdlib (``struct`` + ``zlib``). Поддерживает
    только 8-битные RGBA PNG без интерлейса — этого достаточно для
    вывода ``bria/remove-background``. Если формат не поддержан —
    возвращает исходные байты (безопасный fallback).

    :param png_bytes: исходные байты PNG
    :return: обрезанные байты PNG
    """
    import struct
    import zlib

    if not png_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return png_bytes

    pos = 8
    width = height = None
    idat = bytearray()
    while pos < len(png_bytes):
        length = struct.unpack(">I", png_bytes[pos : pos + 4])[0]
        chunk_type = png_bytes[pos + 4 : pos + 8]
        chunk_data = png_bytes[pos + 8 : pos + 8 + length]
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack(
                ">IIBBBBB", chunk_data
            )
            if bit_depth != 8 or color_type != 6 or interlace != 0:
                return png_bytes
        elif chunk_type == b"IDAT":
            idat.extend(chunk_data)
        elif chunk_type == b"IEND":
            break
        pos += 12 + length

    if width is None or height is None or not idat:
        return png_bytes

    try:
        raw = zlib.decompress(bytes(idat))
    except zlib.error:
        # Битый IDAT (например, тестовый «минимальный» PNG) — не падаем,
        # возвращаем исходные байты. Это безопасный fallback.
        return png_bytes
    stride = width * 4
    pixels = bytearray(width * height * 4)
    prev = bytearray(stride)
    for y in range(height):
        filter_type = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1 : (y + 1) * (stride + 1)])
        if filter_type == 1:  # Sub
            for i in range(4, stride):
                line[i] = (line[i] + line[i - 4]) & 0xFF
        elif filter_type == 2:  # Up
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif filter_type == 3:  # Average
            for i in range(stride):
                left = line[i - 4] if i >= 4 else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif filter_type == 4:  # Paeth
            for i in range(stride):
                a = line[i - 4] if i >= 4 else 0
                b = prev[i]
                c = prev[i - 4] if i >= 4 else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                if pa <= pb and pa <= pc:
                    pred = a
                elif pb <= pc:
                    pred = b
                else:
                    pred = c
                line[i] = (line[i] + pred) & 0xFF
        pixels[y * stride : (y + 1) * stride] = line
        prev = line

    x_min, y_min, x_max, y_max = width, height, -1, -1
    for y in range(height):
        row = y * stride
        for x in range(width):
            if pixels[row + x * 4 + 3] > 0:
                if x < x_min:
                    x_min = x
                if x > x_max:
                    x_max = x
                if y < y_min:
                    y_min = y
                if y > y_max:
                    y_max = y

    if x_max < 0:
        return png_bytes

    new_w = x_max - x_min + 1
    new_h = y_max - y_min + 1
    if new_w == width and new_h == height:
        return png_bytes

    cropped = bytearray()
    for y in range(y_min, y_max + 1):
        row = y * stride
        cropped.extend(b"\x00")
        cropped.extend(pixels[row + x_min * 4 : row + (x_max + 1) * 4])

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", new_w, new_h, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(cropped), 9))
        + _chunk(b"IEND", b"")
    )


def _face_portrait_image(
    rank: int,
    suit: str,
    style: CardStyle,
    *,
    flip: bool = False,
) -> str:
    """Возвращает SVG-элемент с PNG-портретом фигурной карты.

    Портрет берётся из ``assets/art/<RANK>_<suit>.png`` и встраивается
    как base64-encoded ``<image>``. Это делает SVG самодостаточным
    (не зависит от внешних файлов при рендере).

    :param rank: числовой ранг (11=J, 12=Q, 13=K)
    :param suit: масть
    :param style: параметры стиля
    :param flip: если ``True`` — портрет повёрнут на 180° вокруг центра
        карты (нижняя половина в стиле русской колоды)
    :return: строка с SVG-элементом ``<image>``
    :raises FileNotFoundError: если PNG-портрет не найден
    """
    import base64

    rank_label = RANK_LABELS[rank]
    png_path = ART_DIR / f"{rank_label}_{suit}.png"
    if not png_path.exists():
        raise FileNotFoundError(
            f"Портрет не найден: {png_path}. "
            f"Сгенерируй его через scripts/generate_faces_workflow.py."
        )

    png_bytes = _trim_png_alpha(png_path.read_bytes())
    data = base64.b64encode(png_bytes).decode("ascii")

    # Портрет занимает верхнюю половину карты с отступом под угловой
    # индекс. Коэффициенты подобраны так, чтобы портрет был крупным
    # (~20% больше прежнего), но не залезал на угловой индекс.
    portrait_margin_x = style.corner_padding_x + style.corner_rank_size * 0.3
    portrait_margin_y = style.corner_padding_y + style.corner_rank_size * 0.5
    area_x = portrait_margin_x
    area_y = portrait_margin_y
    area_w = style.width - 2 * area_x
    area_h = (style.height - 2 * area_y) / 2

    image = (
        f'<image x="{area_x}" y="{area_y}" '
        f'width="{area_w}" height="{area_h}" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'href="data:image/png;base64,{data}"/>'
    )

    if not flip:
        return image

    cx, cy = style.width / 2, style.height / 2
    return f'<g transform="rotate(180 {cx} {cy})">{image}</g>'


def _face_portraits(rank: int, suit: str, style: CardStyle) -> list[str]:
    """Возвращает пару портретов фигурной карты: верхний и нижний (зеркало).

    В стиле русской колоды фигурная карта содержит два одинаковых
    портрета: верхний — нормальный, нижний — повёрнутый на 180° вокруг
    центра карты. Это делает карту читаемой с любой стороны.

    :param rank: числовой ранг (11=J, 12=Q, 13=K)
    :param suit: масть
    :param style: параметры стиля
    :return: список из двух SVG-элементов ``<image>``
    """
    return [
        _face_portrait_image(rank, suit, style, flip=False),
        _face_portrait_image(rank, suit, style, flip=True),
    ]


def get_base_frame(style: CardStyle) -> str:
    """Генерирует каркас карты: фон, скругление, рамку."""
    w, h = style.width, style.height
    r = style.corner_radius
    bw = style.border_width
    return (
        f'<rect x="{bw / 2}" y="{bw / 2}" '
        f'width="{w - bw}" height="{h - bw}" '
        f'rx="{r}" ry="{r}" '
        f'fill="{style.bg_color}" stroke="{style.border_color}" '
        f'stroke-width="{bw}"/>'
    )


def get_pip_layout(rank: int, suit: str) -> list[tuple[float, float]]:
    """Возвращает список координат (x, y) для пипсов карты."""
    return PIP_LAYOUTS.get(rank, [])


def _corner_index(
    rank_label: str,
    suit: str,
    style: CardStyle,
    color: str,
    flip: bool = False,
) -> str:
    """Генерирует угловой индекс (ранг + мелкая масть)."""
    pad_x = style.corner_padding_x
    pad_y = style.corner_padding_y
    rank_size = style.corner_rank_size
    suit_size = style.corner_suit_size

    rank_x = pad_x + rank_size / 2
    rank_y = pad_y + rank_size * 0.9
    suit_x = rank_x
    suit_y = rank_y + suit_size * 0.6

    inner = (
        f'<text x="{rank_x:.2f}" y="{rank_y:.2f}" '
        f'font-family="{style.font_family}" '
        f'font-size="{rank_size}" font-weight="bold" '
        f'letter-spacing="-2px" dominant-baseline="auto" '
        f'fill="{color}" text-anchor="middle">{rank_label}</text>'
        + _suit_symbol(suit, suit_x, suit_y, suit_size, color)
    )

    if not flip:
        return inner

    cx, cy = style.width / 2, style.height / 2
    return f'<g transform="rotate(180 {cx} {cy})">{inner}</g>'


# Соответствие числового ранга буквенному обозначению для углового индекса.
RANK_LABELS: dict[int, str] = {
    2: "2",
    3: "3",
    4: "4",
    5: "5",
    6: "6",
    7: "7",
    8: "8",
    9: "9",
    10: "10",
    11: "J",
    12: "Q",
    13: "K",
    14: "A",
}


def generate_card(rank: int, suit: str, style: CardStyle | None = None) -> str:
    """Генерирует standalone SVG-код карты.

    :param rank: числовой ранг карты (2–10, 11=J, 12=Q, 13=K, 14=A)
    :param suit: масть (``hearts``, ``diamonds``, ``clubs``, ``spades``)
    :param style: параметры стиля; если ``None`` — используется ``CardStyle()``
    :return: строка с SVG-кодом карты
    :raises ValueError: если масть или ранг неизвестны
    """
    if style is None:
        style = CardStyle()
    if suit not in SUIT_PATHS:
        raise ValueError(f"Неизвестная масть: {suit}")
    if rank not in RANK_LABELS:
        raise ValueError(
            f"Ранг должен быть 2–14 (J=11, Q=12, K=13, A=14), получено: {rank}"
        )

    color = _suit_color(suit, style)
    rank_label = RANK_LABELS[rank]

    area_x = style.pip_margin_x
    area_y = style.pip_margin_y
    area_w = style.width - 2 * area_x
    area_h = style.height - 2 * area_y

    pip_size = style.pip_size * 2 if rank in LARGE_PIP_RANKS else style.pip_size

    pips: list[str] = []
    if rank in FACE_RANKS:
        # Фигурные карты: два портрета (верхний + нижний зеркальный).
        pips.extend(_face_portraits(rank, suit, style))
    else:
        for fx, fy in get_pip_layout(rank, suit):
            px = area_x + fx * area_w
            py = area_y + fy * area_h
            symbol = _suit_symbol(suit, px, py, pip_size, color)
            if style.mirror_pips and fy > 0.5:
                symbol = f'<g transform="rotate(180 {px:.2f} {py:.2f})">{symbol}</g>'
            pips.append(symbol)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {style.width} {style.height}" '
        f'width="{style.width}" height="{style.height}">',
        get_base_frame(style),
        _corner_index(rank_label, suit, style, color, flip=False),
        _corner_index(rank_label, suit, style, color, flip=True),
        *pips,
        "</svg>",
    ]
    return "\n".join(parts)


def _card_filename(rank: int, suit: str) -> str:
    """Возвращает имя файла карты, удобное для использования в коде.

    Формат: ``<rank>_of_<suit>.svg``, например ``10_of_spades.svg``.
    Для фигурных карт используется буквенное обозначение:
    ``J_of_spades.svg``, ``Q_of_hearts.svg``, ``K_of_clubs.svg``,
    ``A_of_diamonds.svg``.
    """
    return f"{RANK_LABELS[rank]}_of_{suit}.svg"


# ---------------------------------------------------------------------------
# HTML-превью
# ---------------------------------------------------------------------------

_PREVIEW_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Deck preview — 36 cards</title>
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
    grid-template-columns: repeat(9, 1fr);
    gap: 12px;
    max-width: 1600px;
  }}
  .cell {{
    background: #1a1a1a;
    border-radius: 8px;
    overflow: hidden;
    aspect-ratio: 825 / 1125;
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  .cell img {{ width: 100%; height: 100%; object-fit: contain; display: block; }}
  .cell.missing {{ background: #2a1010; }}
  .cell.missing::after {{
    content: "missing";
    color: #a04040;
    font-size: 12px;
  }}
</style>
</head>
<body>
<h1>Deck preview — {count} / 36 карт</h1>
<div class="grid">
{rows}
</div>
</body>
</html>
"""


def build_preview_html(output_dir: Path) -> str:
    """Собирает HTML-превью всех 36 карт колоды в виде сетки 9×4.

    Порядок: строки — масти (spades, hearts, clubs, diamonds),
    столбцы — ранги (6..10, J, Q, K, A). Отсутствующие файлы
    помечаются классом ``missing``.

    :param output_dir: каталог с SVG-файлами карт
    :return: строка HTML
    """
    # Порядок рангов в колоде: 6..10, J, Q, K, A.
    rank_order = [6, 7, 8, 9, 10, 11, 12, 13, 14]
    suit_order = ["spades", "hearts", "clubs", "diamonds"]

    rows: list[str] = []
    count = 0
    for suit in suit_order:
        cells: list[str] = []
        for rank in rank_order:
            filename = _card_filename(rank, suit)
            if (output_dir / filename).exists():
                cells.append(
                    f'  <div class="cell"><img src="{filename}" alt="{filename}"></div>'
                )
                count += 1
            else:
                cells.append('  <div class="cell missing"></div>')
        rows.append("\n".join(cells))
    return _PREVIEW_TEMPLATE.format(
        count=count,
        rows="\n".join(rows),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

# Алиасы мастей: латиница, символы, русские названия.
SUIT_ALIASES: dict[str, str] = {
    "hearts": "hearts",
    "h": "hearts",
    "♥": "hearts",
    "черви": "hearts",
    "diamonds": "diamonds",
    "d": "diamonds",
    "♦": "diamonds",
    "бубны": "diamonds",
    "clubs": "clubs",
    "c": "clubs",
    "♣": "clubs",
    "трефы": "clubs",
    "spades": "spades",
    "s": "spades",
    "♠": "spades",
    "пики": "spades",
}

# Алиасы рангов: цифры и буквы фигурных карт.
RANK_ALIASES: dict[str, int] = {
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "j": 11,
    "jack": 11,
    "валет": 11,
    "q": 12,
    "queen": 12,
    "дама": 12,
    "k": 13,
    "king": 13,
    "король": 13,
    "a": 14,
    "ace": 14,
    "туз": 14,
}


def _parse_rank(value: str) -> int:
    """Преобразует строку ранга в число (2–14)."""
    key = value.strip().lower()
    if key not in RANK_ALIASES:
        raise argparse.ArgumentTypeError(
            f"Неизвестный ранг: {value!r}. "
            f"Допустимо: 2–10, J, Q, K, A (или jack/queen/king/ace)."
        )
    return RANK_ALIASES[key]


def _parse_suit(value: str) -> str:
    """Преобразует строку масти в каноническое имя (hearts/diamonds/clubs/spades)."""
    key = value.strip().lower()
    if key not in SUIT_ALIASES:
        raise argparse.ArgumentTypeError(
            f"Неизвестная масть: {value!r}. "
            f"Допустимо: hearts, diamonds, clubs, spades (или ♥ ♦ ♣ ♠, h/d/c/s)."
        )
    return SUIT_ALIASES[key]


def _parse_rank_range(value: str) -> list[int]:
    """Преобразует строку диапазона рангов в список чисел.

    Формат: ``START-END`` (например, ``2-10``). Оба конца включительно.

    :param value: строка диапазона
    :return: список рангов по возрастанию
    :raises argparse.ArgumentTypeError: если формат неверен или start > end
    """
    parts = value.strip().split("-")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(
            f"Диапазон должен быть в формате START-END, получено: {value!r}"
        )
    start = _parse_rank(parts[0])
    end = _parse_rank(parts[1])
    if start > end:
        raise argparse.ArgumentTypeError(
            f"Начало диапазона больше конца: {start} > {end}"
        )
    return list(range(start, end + 1))


def _build_parser() -> argparse.ArgumentParser:
    """Собирает парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(
        prog="deck_design_system",
        description=(
            "Генератор SVG-карт для «Подкидного Дурака». "
            "Создаёт одну карту или пакет карт в assets/card_deck/cards/."
        ),
        epilog=(
            "Примеры:\n"
            "  python -m tools.deck_design_system 9 --suit spades\n"
            "  python -m tools.deck_design_system 10 --suit ♥\n"
            "  python -m tools.deck_design_system --rank-range 2-10 --all-suits\n"
            "  python -m tools.deck_design_system --rank-range 2-10 --suit spades\n"
            "  python -m tools.deck_design_system J --suit clubs -o ./out\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "rank",
        nargs="?",
        type=_parse_rank,
        default=None,
        help="Ранг карты: 2–10, J, Q, K, A (или jack/queen/king/ace).",
    )
    parser.add_argument(
        "--suit",
        type=_parse_suit,
        default=None,
        metavar="SUIT",
        help="Масть: hearts, diamonds, clubs, spades (или ♥ ♦ ♣ ♠, h/d/c/s).",
    )
    parser.add_argument(
        "--rank-range",
        type=_parse_rank_range,
        default=None,
        metavar="START-END",
        help="Диапазон рангов для пакетной генерации (например, 2-10).",
    )
    parser.add_argument(
        "--all-suits",
        action="store_true",
        help="Генерировать все четыре масти (только с --rank-range).",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Каталог для сохранения SVG (по умолчанию: {OUTPUT_DIR}).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Точка входа CLI. Возвращает код выхода (0 — успех)."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Пакетный режим: --rank-range задан.
    if args.rank_range is not None:
        if args.rank is not None:
            parser.error("Нельзя указывать позиционный rank вместе с --rank-range")
        if args.all_suits:
            suits = list(SUIT_PATHS.keys())
        elif args.suit is not None:
            suits = [args.suit]
        else:
            parser.error("С --rank-range укажи --suit или --all-suits")

        args.output_dir.mkdir(parents=True, exist_ok=True)
        count = 0
        for rank in args.rank_range:
            for suit in suits:
                svg = generate_card(rank=rank, suit=suit)
                out = args.output_dir / _card_filename(rank, suit)
                out.write_text(svg, encoding="utf-8")
                count += 1
        preview_path = args.output_dir / "preview.html"
        preview_path.write_text(build_preview_html(args.output_dir), encoding="utf-8")
        print(f"Готово: {count} карт(ы) в {args.output_dir.resolve()}")
        print(f"[html] {preview_path.resolve()}")
        return 0

    # Одиночный режим: нужны rank и --suit.
    if args.rank is None or args.suit is None:
        parser.error("Укажи rank и --suit, либо используй --rank-range")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    svg = generate_card(rank=args.rank, suit=args.suit)
    out = args.output_dir / _card_filename(args.rank, args.suit)
    out.write_text(svg, encoding="utf-8")
    print(f"Готово: {out.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Тесты генератора SVG-карт: проверка коллизий углового индекса и пипсов."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from tools.deck_design_system import (
    FACE_RANKS,
    LARGE_PIP_RANKS,
    CardStyle,
    _corner_index_bbox,
    _parse_rank,
    _parse_rank_range,
    _parse_suit,
    _pip_area_bbox,
    generate_card,
    main,
)


def _bboxes_overlap(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> bool:
    """Проверяет пересечение двух прямоугольников (x_min, y_min, x_max, y_max)."""
    ax_min, ay_min, ax_max, ay_max = a
    bx_min, by_min, bx_max, by_max = b
    return not (
        ax_max <= bx_min or bx_max <= ax_min or ay_max <= by_min or by_max <= ay_min
    )


def test_corner_index_does_not_overlap_pip_area() -> None:
    """Угловой индекс (ранг + масть) не должен пересекаться с областью пипсов."""
    style = CardStyle()
    corner = _corner_index_bbox(style)
    pips = _pip_area_bbox(style)

    assert not _bboxes_overlap(corner, pips), (
        f"Угловой индекс {corner} пересекается с областью пипсов {pips}"
    )


@pytest.mark.parametrize("rank", [2, 3, 4, 5, 6, 7, 8, 9, 10])
def test_pips_do_not_overlap_corner_index(rank: int) -> None:
    """Ни один пипс числовой карты не пересекается с угловым индексом.

    Угловой индекс — «якорь дизайна»: его размер и положение одинаковы
    для всех рангов. Но раскладка пипсов у каждого ранга своя, поэтому
    проверяем каждый ранг отдельно.

    Пипс — квадрат ``pip_size × pip_size`` с центром в точке раскладки.
    Угловой индекс — bbox из ``_corner_index_bbox``.
    """
    from tools.deck_design_system import PIP_LAYOUTS

    style = CardStyle()
    corner = _corner_index_bbox(style)

    area_x, area_y, area_x_max, area_y_max = _pip_area_bbox(style)
    area_w = area_x_max - area_x
    area_h = area_y_max - area_y

    pip_size = style.pip_size * 2 if rank in LARGE_PIP_RANKS else style.pip_size
    half = pip_size / 2

    for fx, fy in PIP_LAYOUTS[rank]:
        px = area_x + fx * area_w
        py = area_y + fy * area_h
        pip_bbox = (px - half, py - half, px + half, py + half)
        assert not _bboxes_overlap(corner, pip_bbox), (
            f"Ранг {rank}: пипс в ({px:.1f}, {py:.1f}) "
            f"пересекается с угловым индексом {corner}"
        )


def test_corner_index_fits_inside_card() -> None:
    """Угловой индекс должен целиком помещаться в границы карты."""
    style = CardStyle()
    x_min, y_min, x_max, y_max = _corner_index_bbox(style)

    assert x_min >= 0
    assert y_min >= 0
    assert x_max <= style.width
    assert y_max <= style.height


def test_pip_area_fits_inside_card() -> None:
    """Область пипсов должна целиком помещаться в границы карты."""
    style = CardStyle()
    x_min, y_min, x_max, y_max = _pip_area_bbox(style)

    assert x_min >= 0
    assert y_min >= 0
    assert x_max <= style.width
    assert y_max <= style.height


@pytest.mark.parametrize("suit", ["hearts", "diamonds", "clubs", "spades"])
@pytest.mark.parametrize("rank", [2, 5, 10, 14])
def test_generate_card_produces_valid_svg(rank: int, suit: str) -> None:
    """Генератор возвращает корректный SVG для числовых рангов и туза."""
    svg = generate_card(rank=rank, suit=suit)

    assert svg.startswith("<svg")
    assert svg.endswith("</svg>")
    assert f'viewBox="0 0 {CardStyle().width} {CardStyle().height}"' in svg


@pytest.fixture
def fake_face_portraits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Создаёт временный каталог с фиктивными PNG-портретами J/Q/K × 4 масти.

    Подменяет ``ART_DIR`` в модуле, чтобы тесты не зависели от реальных
    файлов в ``assets/art/``.
    """
    import tools.deck_design_system as dds

    # Минимальный валидный PNG (1×1, прозрачный).
    png_bytes = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000d49444154789c6300010000000500010d0a2db40000000049454e44"
        "ae426082"
    )
    for rank_label in ("J", "Q", "K"):
        for suit in ("hearts", "diamonds", "clubs", "spades"):
            (tmp_path / f"{rank_label}_{suit}.png").write_bytes(png_bytes)

    monkeypatch.setattr(dds, "ART_DIR", tmp_path)
    return tmp_path


@pytest.mark.parametrize("suit", ["hearts", "diamonds", "clubs", "spades"])
@pytest.mark.parametrize("rank", [11, 12, 13])
def test_face_card_embeds_portrait(
    rank: int,
    suit: str,
    fake_face_portraits: Path,
) -> None:
    """Фигурные карты встраивают PNG-портрет как base64 data-URI."""
    svg = generate_card(rank=rank, suit=suit)

    assert svg.startswith("<svg")
    assert svg.endswith("</svg>")
    assert "data:image/png;base64," in svg
    # В стиле русской колоды — два портрета (верхний + нижний зеркальный).
    assert svg.count("<image ") == 2
    # Нижний портрет обёрнут в rotate(180 ...).
    assert "rotate(180" in svg


def test_face_card_missing_portrait_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Если PNG-портрет отсутствует — FileNotFoundError."""
    import tools.deck_design_system as dds

    monkeypatch.setattr(dds, "ART_DIR", tmp_path)  # пустой каталог

    with pytest.raises(FileNotFoundError):
        generate_card(rank=11, suit="spades")


def test_trim_png_alpha_removes_transparent_borders() -> None:
    """_trim_png_alpha обрезает прозрачные поля PNG."""
    import struct
    import zlib

    from tools.deck_design_system import _trim_png_alpha

    # Собираем PNG 4×4: непрозрачный квадрат 2×2 в центре.
    width = height = 4
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type 0
        for x in range(width):
            if 1 <= x <= 2 and 1 <= y <= 2:
                raw.extend(b"\xff\x00\x00\xff")  # красный, непрозрачный
            else:
                raw.extend(b"\x00\x00\x00\x00")  # прозрачный

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )

    trimmed = _trim_png_alpha(png)

    # Размер обрезанного PNG должен быть 2×2.
    new_w, new_h = struct.unpack(">II", trimmed[16:24])
    assert (new_w, new_h) == (2, 2)


def test_trim_png_alpha_passthrough_on_bad_format() -> None:
    """_trim_png_alpha возвращает исходные байты, если формат не поддержан."""
    from tools.deck_design_system import _trim_png_alpha

    garbage = b"not a png at all"
    assert _trim_png_alpha(garbage) == garbage


def test_face_ranks_constant() -> None:
    """FACE_RANKS содержит ровно J, Q, K."""
    assert FACE_RANKS == frozenset({11, 12, 13})


@pytest.mark.parametrize(
    ("rank", "label"),
    [(11, "J"), (12, "Q"), (13, "K"), (14, "A")],
)
def test_face_card_uses_letter_label(
    rank: int,
    label: str,
    fake_face_portraits: Path,
) -> None:
    """Фигурные карты используют буквенное обозначение в угловом индексе."""
    svg = generate_card(rank=rank, suit="spades")

    assert f">{label}</text>" in svg


def test_unknown_rank_raises() -> None:
    """Неизвестный ранг вызывает ValueError."""
    with pytest.raises(ValueError):
        generate_card(rank=15, suit="spades")
    with pytest.raises(ValueError):
        generate_card(rank=1, suit="spades")


def test_unknown_suit_raises() -> None:
    """Неизвестная масть вызывает ValueError."""
    with pytest.raises(ValueError):
        generate_card(rank=5, suit="stars")


def test_mirror_pips_rotates_bottom_half() -> None:
    """При mirror_pips=True пипсы в нижней половине повёрнуты на 180°."""
    svg = generate_card(rank=2, suit="spades", style=CardStyle(mirror_pips=True))

    # У «2» один пипс сверху (fy=0.0) и один снизу (fy=1.0).
    # Нижний должен быть обёрнут в rotate(180 ...).
    assert "rotate(180" in svg


def test_mirror_pips_disabled_has_no_rotation() -> None:
    """При mirror_pips=False поворотов пипсов нет.

    Угловой индекс в нижнем-правом углу всегда повёрнут на 180° —
    это часть дизайна карты, а не зеркальность пипсов. Поэтому
    проверяем, что поворот ровно один (нижний угловой индекс),
    а не больше.
    """
    svg = generate_card(rank=2, suit="spades", style=CardStyle(mirror_pips=False))

    # Один угловой индекс (нижний-правый) — ровно 1 поворот.
    assert svg.count("rotate(180") == 1


def test_ace_uses_large_pip() -> None:
    """Туз рисуется крупным пипсом (LARGE_PIP_RANKS)."""
    assert 14 in LARGE_PIP_RANKS

    style = CardStyle()
    svg_ace = generate_card(rank=14, suit="spades", style=style)
    svg_two = generate_card(rank=2, suit="spades", style=style)

    # Угловой индекс тоже использует scale(...), поэтому берём
    # последний scale(...) — это пипс (пипсы идут после угловых индексов).
    import re

    def _last_scale(svg: str) -> float:
        matches = re.findall(r"scale\(([0-9.]+)\)", svg)
        assert matches, "scale не найден в SVG"
        return float(matches[-1])

    assert _last_scale(svg_ace) > _last_scale(svg_two)


# ---------------------------------------------------------------------------
# Парсеры алиасов
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2", 2),
        ("10", 10),
        ("J", 11),
        ("j", 11),
        ("jack", 11),
        ("валет", 11),
        ("Q", 12),
        ("queen", 12),
        ("дама", 12),
        ("K", 13),
        ("king", 13),
        ("король", 13),
        ("A", 14),
        ("ace", 14),
        ("туз", 14),
    ],
)
def test_parse_rank_aliases(value: str, expected: int) -> None:
    """Парсер ранга понимает цифры, латиницу и русские названия."""
    assert _parse_rank(value) == expected


def test_parse_rank_unknown_raises() -> None:
    """Неизвестный ранг — argparse.ArgumentTypeError."""
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_rank("joker")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("hearts", "hearts"),
        ("h", "hearts"),
        ("♥", "hearts"),
        ("черви", "hearts"),
        ("diamonds", "diamonds"),
        ("d", "diamonds"),
        ("♦", "diamonds"),
        ("бубны", "diamonds"),
        ("clubs", "clubs"),
        ("c", "clubs"),
        ("♣", "clubs"),
        ("трефы", "clubs"),
        ("spades", "spades"),
        ("s", "spades"),
        ("♠", "spades"),
        ("пики", "spades"),
    ],
)
def test_parse_suit_aliases(value: str, expected: str) -> None:
    """Парсер масти понимает латиницу, символы и русские названия."""
    assert _parse_suit(value) == expected


def test_parse_suit_unknown_raises() -> None:
    """Неизвестная масть — argparse.ArgumentTypeError."""
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_suit("stars")


def test_parse_rank_range_ok() -> None:
    """Диапазон 2-10 разворачивается в список рангов."""
    assert _parse_rank_range("2-10") == list(range(2, 11))
    assert _parse_rank_range("J-A") == [11, 12, 13, 14]


def test_parse_rank_range_bad_format_raises() -> None:
    """Неверный формат диапазона — argparse.ArgumentTypeError."""
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_rank_range("2..10")
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_rank_range("10-2")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_single_card(tmp_path: Path) -> None:
    """CLI в одиночном режиме создаёт один SVG-файл."""
    exit_code = main(["9", "--suit", "spades", "-o", str(tmp_path)])

    assert exit_code == 0
    out = tmp_path / "9_of_spades.svg"
    assert out.exists()
    assert out.read_text(encoding="utf-8").startswith("<svg")


def test_cli_rank_range_single_suit(tmp_path: Path) -> None:
    """CLI с --rank-range и одной мастью создаёт N файлов."""
    exit_code = main(["--rank-range", "2-4", "--suit", "hearts", "-o", str(tmp_path)])

    assert exit_code == 0
    for rank in (2, 3, 4):
        assert (tmp_path / f"{rank}_of_hearts.svg").exists()


def test_cli_rank_range_all_suits(tmp_path: Path) -> None:
    """CLI с --rank-range и --all-suits создаёт N×4 файлов."""
    exit_code = main(["--rank-range", "2-3", "--all-suits", "-o", str(tmp_path)])

    assert exit_code == 0
    for rank in (2, 3):
        for suit in ("hearts", "diamonds", "clubs", "spades"):
            assert (tmp_path / f"{rank}_of_{suit}.svg").exists()


def test_cli_face_card_filename(
    tmp_path: Path,
    fake_face_portraits: Path,
) -> None:
    """CLI для фигурной карты использует буквенное имя файла."""
    exit_code = main(["J", "--suit", "clubs", "-o", str(tmp_path)])

    assert exit_code == 0
    assert (tmp_path / "J_of_clubs.svg").exists()


def test_cli_rank_range_builds_preview_html(tmp_path: Path) -> None:
    """CLI в пакетном режиме собирает preview.html рядом с картами.

    Превью показывает сетку 9×4 (ранги 6..A × 4 масти) — это колода
    «Подкидного Дурака». Поэтому в тесте берём ранги из колоды (6, 7),
    а не 2, 3.
    """
    exit_code = main(["--rank-range", "6-7", "--all-suits", "-o", str(tmp_path)])

    assert exit_code == 0
    preview = tmp_path / "preview.html"
    assert preview.exists()
    html = preview.read_text(encoding="utf-8")
    # 2 ранга × 4 масти = 8 карт.
    assert "8 / 36" in html
    # Ссылки на сгенерированные файлы.
    assert "6_of_spades.svg" in html
    assert "7_of_hearts.svg" in html

"""Тесты генератора SVG-карт: проверка коллизий углового индекса и пипсов."""

from __future__ import annotations

import pytest

from tools.deck_design_system import (
    CardStyle,
    _corner_index_bbox,
    _pip_area_bbox,
    generate_card,
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
@pytest.mark.parametrize("rank", [2, 5, 10])
def test_generate_card_produces_valid_svg(rank: int, suit: str) -> None:
    """Генератор возвращает корректный SVG для всех мастей и рангов."""
    svg = generate_card(rank=rank, suit=suit)

    assert svg.startswith("<svg")
    assert svg.endswith("</svg>")
    assert f'viewBox="0 0 {CardStyle().width} {CardStyle().height}"' in svg

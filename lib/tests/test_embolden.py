"""The contour order `path_to_glyph` imposes on skia-pathops' output.

This is the fix for half of KIT-297. `OpBuilder.resolve` does not promise the
order in which it emits contours, and on the repo's own pins it does not
deliver one either: `x86_64-linux` and `aarch64-darwin` produced the same 30
contours for `uni2FF3` of `LXGWWenKai-Medium` at strength 5, numbers 12 and 13
swapped, every coordinate equal as a set. One glyph in 3265 was enough to move
the outline digest and turn `just verify` red on a Mac.

Skia is not reachable from a unit test — it is compiled, and the divergence
takes a real CJK master to provoke. What *is* reachable, and what actually
carries the fix, is the pen-level contract: given contours in any order, emit
them in one order; and never reorder within a contour, because that would
rotate its start point and reverse its direction.
"""

from __future__ import annotations

import pytest

from fontkit import embolden


class FakePath:
    """Stands in for `pathops.Path`: all `draw` has to do is replay commands."""

    def __init__(self, commands):
        self._commands = commands

    def draw(self, pen):
        for operator, operands in self._commands:
            getattr(pen, operator)(*operands)


SQUARE = [
    ("moveTo", ((0, 0),)),
    ("lineTo", ((100, 0),)),
    ("lineTo", ((100, 100),)),
    ("closePath", ()),
]

TRIANGLE = [
    ("moveTo", ((500, 500),)),
    ("lineTo", ((600, 500),)),
    ("lineTo", ((550, 620),)),
    ("closePath", ()),
]

CURVE = [
    ("moveTo", ((0, 300),)),
    ("qCurveTo", ((40, 380), (90, 300))),
    ("closePath", ()),
]


def _glyph_points(commands):
    glyph = embolden.path_to_glyph(FakePath(commands))
    glyph.expand(None) if hasattr(glyph, "expand") else None
    return [tuple(c) for c in glyph.coordinates], list(glyph.endPtsOfContours)


def test_contour_order_does_not_depend_on_emission_order():
    """The whole point: two permutations of one path give one glyph."""
    a = _glyph_points(SQUARE + TRIANGLE + CURVE)
    b = _glyph_points(CURVE + SQUARE + TRIANGLE)
    c = _glyph_points(TRIANGLE + CURVE + SQUARE)
    assert a == b == c


def test_every_contour_survives():
    """Sorting must not drop or merge one — three in, three out."""
    _, ends = _glyph_points(SQUARE + TRIANGLE + CURVE)
    assert len(ends) == 3


def test_points_within_a_contour_keep_their_order():
    """Direction and start point are meaning; only the sequence of whole
    contours is free. A sort that reached inside a contour would reverse its
    winding, which flips whether it is a counter or a shape."""
    points, ends = _glyph_points(TRIANGLE)
    assert points == [(500, 500), (600, 500), (550, 620)]
    assert ends == [2]


def test_identical_contours_are_not_deduplicated():
    """Two coincident contours are legal (and meaningful under the non-zero
    winding rule). A `set` here instead of a `sort` would silently drop one."""
    _, ends = _glyph_points(SQUARE + SQUARE)
    assert len(ends) == 2


@pytest.mark.parametrize("order", [
    SQUARE + TRIANGLE,
    TRIANGLE + SQUARE,
])
def test_order_is_the_same_one_every_time(order):
    """Not merely stable within a process — pinned, so a baseline taken on one
    machine still matches a build on another."""
    points, _ = _glyph_points(order)
    # The square sorts before the triangle on its own commands.
    assert points[0] == (0, 0)

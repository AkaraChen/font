"""The fixtures' codepoints must keep the width class the tests assume.

Every narrow/widen decision in this package reads
`unicodedata.east_asian_width`, and unicodedata ships with the interpreter — a
nixpkgs bump moves the Unicode version under the build. That is a real product
risk, not just a test one: U+2630 ☰ is EAW=N through Unicode 15.1 and W from
16.0, so the same source font gains or loses a full-cell glyph depending on
which Python built it. The devShell pins the interpreter for exactly this
reason; this test makes the assumption visible when the pin moves.
"""
from __future__ import annotations

import unicodedata

import pytest

from conftest import EXPECTED_EAW


@pytest.mark.parametrize("cp,expected", sorted(EXPECTED_EAW.items()))
def test_fixture_codepoints_still_have_the_expected_eaw_class(cp, expected):
    got = unicodedata.east_asian_width(chr(cp))
    assert got == expected, (
        f"U+{cp:04X} is EAW={got} under Unicode {unicodedata.unidata_version}, "
        f"but the fixtures assume {expected}. Pick a stabler codepoint rather "
        f"than relaxing this."
    )

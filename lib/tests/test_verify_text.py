"""The text gate, pinned to the cases that make it a *different* gate.

`verify-2to1` and `verify-text` are not two settings of one check: a correct
text product fails every assertion the coding gate makes, and a correct coding
product fails most of these. The tests below are the pairs where the two gates
say the opposite thing, because that is what a future "let's unify them" would
break.
"""

from __future__ import annotations

import pytest
from fontTools.ttLib import TTFont

from fontkit import verify_text

from conftest import CP_A, CP_PUA, FULL, HALF

CP_CODICON = 0xEA60  # a codepoint only the Nerd patcher fills

# The everyday Han the gate requires, plus the punctuation it makes claims about.
CJK_SAMPLE = "中文测试字体阅读排版汉字标点正文"
CJK_PUNCT = "、。「」，：；？！" + "　"


def _text_font(make_font, *, name="text.ttf", extra=None, **overrides):
    """A minimal but *passing* text product, so each test breaks exactly one thing."""
    glyphs = {"A": (HALF, (10, 0, 240, 700)), "a": (HALF, (10, 0, 240, 500)),
              "zero": (HALF, (10, 0, 240, 700))}
    cmap = {CP_A: "A", ord("a"): "a", ord("0"): "zero"}
    for i, ch in enumerate(CJK_SAMPLE + CJK_PUNCT + "…—"):
        gname = f"cjk{i}"
        glyphs[gname] = (FULL, (10, 0, 900, 800))
        cmap[ord(ch)] = gname
    if extra:
        for cp, (gname, adv) in extra.items():
            glyphs[gname] = (adv, (10, 0, adv - 10, 700))
            cmap[cp] = gname

    defaults = dict(is_fixed_pitch=0, panose_proportion=0)
    defaults.update(overrides)
    path = make_font(name, glyphs=glyphs, cmap=cmap, **defaults)

    # The line box and the layout evidence the gate looks for. FontBuilder does
    # not give us a GSUB, so the layout checks are exercised via --no-layout
    # here and by the real build in CI.
    font = TTFont(path)
    os2 = font["OS/2"]
    # USE_TYPO_METRICS is only defined from OS/2 v4; the real donors are v4+.
    os2.version = max(os2.version, 4)
    os2.fsSelection |= 0x80
    os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap = 880, -220, 200
    font.save(path)
    font.close()
    return path


def _verify(path, **kwargs):
    kwargs.setdefault("require_layout", False)
    return verify_text.verify_font(path, **kwargs)


def test_a_well_formed_text_face_passes(make_font):
    rc, report = _verify(_text_font(make_font), expect_full=FULL)
    assert rc == 0, "\n".join(report)


def test_a_face_that_still_claims_the_terminal_grid_fails(make_font):
    """The single most important check: the coding gate *requires* this flag.

    Both donors are monospaced, so `post.isFixedPitch` arrives set and the merge
    has to clear it. A text face that kept it turns up in every "monospace only"
    picker.
    """
    rc, report = _verify(_text_font(make_font, is_fixed_pitch=1))
    assert rc == 1
    assert any("isFixedPitch" in line for line in report)


def test_panose_monospaced_fails(make_font):
    rc, report = _verify(_text_font(make_font, panose_proportion=9))
    assert rc == 1
    assert any("PANOSE" in line for line in report)


def test_nerd_icons_are_a_wrong_donor_not_a_bonus(make_font):
    """`--check-nerd` is a *requirement* of the coding gate and a failure here.

    The two profiles take different upstream Latin files; a Codicon in a text
    product means a derivation reached for the pre-patched one.
    """
    rc, report = _verify(
        _text_font(make_font, extra={CP_CODICON: ("codicon", HALF)})
    )
    assert rc == 1
    assert any("Nerd Font icon" in line for line in report)


def test_powerline_is_not_a_nerd_patch(make_font):
    """The plain Monaspace Radon ships 55 PUA codepoints of its own — Powerline
    plus a few Monaspace-native ones. Failing on those would fail the *correct*
    donor, which is why the check is the icon ranges and not all of PUA."""
    rc, report = _verify(_text_font(make_font, extra={CP_PUA: ("powerline", HALF)}))
    assert rc == 0, "\n".join(report)


def test_a_half_width_ellipsis_fails(make_font):
    """Where the two gates contradict each other outright.

    U+2026 is East_Asian_Width=Ambiguous. A terminal gives it one cell, so the
    coding gate is happy with the Latin donor's narrow ellipsis. Prose set by a
    CJK face wants the full-width 省略号, so here that same advance is the bug.
    """
    rc, report = _verify(_text_font(make_font, extra={0x2026: ("ell", HALF)}))
    assert rc == 1
    assert any("U+2026" in line for line in report)


def test_a_donors_own_proportional_punctuation_is_caught(make_font):
    """350/1000 is neither cell — it is LXGW WenKai's Latin quote leaking in."""
    rc, report = _verify(_text_font(make_font, extra={0x201C: ("qdl", 350)}))
    assert rc == 1
    assert any("neither the half cell" in line for line in report)


def test_the_latin_donors_quotes_are_fine(make_font):
    """…and the half cell is not, because the merge declined WenKai's."""
    rc, report = _verify(_text_font(make_font, extra={0x201C: ("qdl", HALF)}))
    assert rc == 0, "\n".join(report)


def test_a_terminal_tight_line_box_fails(make_font):
    """`sTypoLineGap == 0` is what a terminal-tuned metric set looks like."""
    path = _text_font(make_font)
    font = TTFont(path)
    font["OS/2"].sTypoLineGap = 0
    font.save(path)
    font.close()

    rc, report = _verify(path)
    assert rc == 1
    assert any("sTypoLineGap" in line for line in report)


def test_use_typo_metrics_must_be_set(make_font):
    path = _text_font(make_font)
    font = TTFont(path)
    font["OS/2"].fsSelection &= ~0x80
    font.save(path)
    font.close()

    rc, report = _verify(path)
    assert rc == 1
    assert any("USE_TYPO_METRICS" in line for line in report)


def test_a_wrong_cell_is_a_hard_pin_not_a_warning(make_font):
    rc, _ = _verify(_text_font(make_font), expect_full=999)
    assert rc == 1


def test_a_font_with_no_cjk_is_a_usage_error_not_a_failure(make_font):
    """Exit 2, like the coding gate: pointing the gate at the wrong file is not
    the same as the file being wrong."""
    path = make_font(
        "latin.ttf",
        glyphs={"A": (HALF, (10, 0, 240, 700))},
        cmap={CP_A: "A"},
        is_fixed_pitch=0,
    )
    rc, _ = _verify(path)
    assert rc == 2


# Not 中: that is the gate's reference glyph, so narrowing it moves the cell the
# whole check is measured against rather than failing against it.
@pytest.mark.parametrize("cp", (ord("文"), ord("。")))
def test_cjk_on_a_half_cell_fails(make_font, cp):
    rc, report = _verify(_text_font(make_font, extra={cp: ("narrow", HALF)}))
    assert rc == 1
    assert any(f"U+{cp:04X}" in line for line in report)

"""The order and the composition of the Nerd passes, which five families share.

`nerd_patch` is the one module where a family's difference is a *missing* pass
rather than a different argument: pixel skips the EAW fit, serif skips the PUA
half-cell pass and adds a donor plus the ligature fold. The fingerprint net
catches a wrong order eventually — after a multi-hour build, on CI, for whichever
family drew the short straw. This catches it in milliseconds.

font-patcher itself is not exercised here: it needs fontforge and a real icon
set. What is exercised is everything this module decides.
"""

from __future__ import annotations

import pytest

from fontkit import (
    expand_ligatures,
    fix_nerd_widths,
    fix_terminal_metrics,
    narrow_symbol_widths,
    nerd_patch,
    rename_nerd_family,
)


@pytest.fixture()
def calls(monkeypatch, tmp_path):
    """Record every pass `main` runs, in order, with its arguments."""
    recorded: list[tuple[str, list[str]]] = []
    font = tmp_path / "out" / "Product-Regular.ttf"
    font.parent.mkdir()
    font.touch()

    def record(name, returns=0):
        def _call(argv, *_, **__):
            recorded.append((name, list(argv)))
            return returns

        return _call

    monkeypatch.setattr(nerd_patch, "run_patcher", lambda *a, **k: recorded.append(("patch", [])))
    monkeypatch.setattr(nerd_patch, "patched_fonts", lambda _out: [font])
    monkeypatch.setattr(rename_nerd_family, "main", record("rename"))
    monkeypatch.setattr(fix_nerd_widths, "main", record("nerd-widths"))
    monkeypatch.setattr(narrow_symbol_widths, "main", record("narrow"))
    monkeypatch.setattr(fix_terminal_metrics, "main", record("terminal-metrics"))
    monkeypatch.setattr(expand_ligatures, "main", record("expand-ligatures"))
    return recorded, font


def _run(tmp_path, font, *flags):
    return nerd_patch.main(
        [
            str(font),
            "--patcher",
            str(tmp_path),
            "--out",
            str(font.parent),
            "--family",
            "Test NFM",
            "--family-ps",
            "TestNFM",
            *flags,
        ]
    )


def test_the_merged_families_run_every_pass_in_order(calls, tmp_path):
    recorded, font = calls
    assert _run(tmp_path, font, "--narrow-symbols") == 0
    assert [name for name, _ in recorded] == [
        "patch",
        "rename",
        "nerd-widths",
        "narrow",
        "terminal-metrics",
    ]
    # No donor on their grid: the outlines are fitted geometrically.
    narrow_argv = dict(recorded)["narrow"]
    assert "--no-donor" in narrow_argv
    assert "--widen-shared" in narrow_argv and "fork" in narrow_argv


def test_pixel_has_no_eaw_fit(calls, tmp_path):
    recorded, font = calls
    assert _run(tmp_path, font) == 0
    assert "narrow" not in [name for name, _ in recorded]


def test_serif_skips_the_pua_pass_and_folds_dlig(calls, tmp_path):
    recorded, font = calls
    donor = tmp_path / "SarasaTermSlabSC-Regular.ttf"
    donor.touch()
    rc = _run(
        tmp_path,
        font,
        "--no-nerd-widths",
        "--narrow-symbols",
        "--donor",
        str(donor),
        "--protect-ambiguous",
        "--widen-shared",
        "skip",
        "--expand-ligatures",
    )
    assert rc == 0
    assert [name for name, _ in recorded] == [
        "patch",
        "rename",
        "narrow",
        "terminal-metrics",
        "expand-ligatures",
    ]
    narrow_argv = dict(recorded)["narrow"]
    assert narrow_argv[:2] == ["--donor", str(donor)]
    assert "--protect-ambiguous" in narrow_argv
    assert narrow_argv[narrow_argv.index("--widen-shared") + 1] == "skip"


def test_a_donor_without_the_narrow_pass_is_rejected(calls, tmp_path):
    _recorded, font = calls
    with pytest.raises(SystemExit) as excinfo:
        _run(tmp_path, font, "--donor", str(tmp_path / "donor.ttf"))
    assert excinfo.value.code == 2


def test_a_failing_pass_is_not_swallowed(calls, tmp_path, monkeypatch):
    """A narrow pass that reports failure used to be discarded, so a font with
    wrong advances went on to be packaged as if it had passed."""
    _recorded, font = calls
    monkeypatch.setattr(narrow_symbol_widths, "main", lambda argv, *a, **k: 1)
    with pytest.raises(SystemExit):
        _run(tmp_path, font, "--narrow-symbols")

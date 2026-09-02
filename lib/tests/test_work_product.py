"""Consumer checks for the work family — the real script the Nix gate runs.

`work/scripts/verify-product.py` is what `work-verify` invokes on built TTFs.
These tests drive that function, not a reimplementation, so a broken RIBBI or
2:1 assertion cannot go green here and red only after a three-hour font build.

Skipped inside the `fontkit` derivation, which packages `lib/` plus font.toml
and not family scripts.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont

from fontkit import merge, naming

from conftest import CP_A, CP_ZHONG

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "work" / "scripts" / "verify-product.py"


def _load():
    spec = importlib.util.spec_from_file_location("work_verify_product", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


pytestmark = pytest.mark.skipif(not SCRIPT.is_file(), reason="work/scripts not in fontkit src")


def _spec():
    return merge.MergeSpec(
        family="AKR Work SC NFM",
        family_ps="AKRWorkSCNFM",
        version="1.000",
        sources_note="test",
        en_adv=500,
        cjk_adv=1000,
        metrics={},
        profile="coding",
        slope="upright",
        slant_deg=0.0,
        latin="none",
        cjk="as-is",
        import_policy="cjk-side",
        placement="center",
        declares_fixed_grid=True,
        glyph_prefix="ph.",
        required_sample="",
        latin_subset="none",
        latin_src_adv=None,
        latin_target_upm=None,
        drop_hinting_on_upem_change=False,
        set_weight_class=False,
        recalc_bounds=False,
        widen_wide_base_glyphs=False,
        drop_vertical_metrics=False,
        check_glyph_budget=False,
    )


def _product(make_font, tmp_path, subfamily: str, *, nerd=0xE0A0, han_adv=1000):
    path = make_font(
        name=f"AKRWorkSCNFM-{subfamily}.ttf",
        glyphs={
            "A": (500, (50, 0, 450, 700)),
            "zhong": (han_adv, (50, 0, 950, 800)),
            "nerd": (500, (50, 0, 450, 700)),
        },
        cmap={CP_A: "A", CP_ZHONG: "zhong", nerd: "nerd"},
    )
    font = TTFont(path)
    merge.rename_family(font, subfamily, _spec())
    font.save(path)
    font.close()
    return path


def test_consumer_accepts_a_well_formed_three_weight_face(make_font, tmp_path):
    mod = _load()
    for subfamily in ("Light", "Regular", "Bold"):
        path = _product(make_font, tmp_path, subfamily)
        assert mod.check_one(path, 500) == []


def test_consumer_rejects_light_stuffed_into_name_id_2(make_font, tmp_path):
    mod = _load()
    path = _product(make_font, tmp_path, "Light")
    font = TTFont(path)
    font["name"].setName("Light", 2, 3, 1, 0x409)
    font.save(path)
    font.close()
    errors = mod.check_one(path, 500)
    assert any("name ID 2" in e or "stuffed" in e for e in errors)


def test_consumer_rejects_cjk_advance_that_is_not_double_latin(make_font, tmp_path):
    mod = _load()
    path = _product(make_font, tmp_path, "Regular", han_adv=800)
    errors = mod.check_one(path, 500)
    assert any("中" in e and "2" in e for e in errors)


def test_consumer_requires_han_and_nerd_from_the_cascadia_zip(make_font, tmp_path):
    mod = _load()
    path = make_font(
        name="AKRWorkSCNFM-Regular.ttf",
        glyphs={"A": (500, (50, 0, 450, 700))},
        cmap={CP_A: "A"},
    )
    font = TTFont(path)
    merge.rename_family(font, "Regular", _spec())
    font.save(path)
    font.close()
    errors = mod.check_one(path, 500)
    assert any("中" in e for e in errors)
    assert any("Nerd" in e for e in errors)


def test_legacy_family_for_work_light_stays_inside_the_windows_budget():
    assert naming.legacy_family("AKR Work SC NFM", "Light") == "AKR Work SC NFM Light"
    assert len("AKR Work SC NFM Light") <= naming.WINDOWS_FAMILY_LIMIT

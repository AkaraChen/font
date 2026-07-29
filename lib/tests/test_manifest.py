from __future__ import annotations

import copy
import tomllib
from pathlib import Path

import pytest
from pydantic import ValidationError

from fontkit.manifest import Manifest, legacy_environment, load_manifest

ROOT = Path(__file__).parents[2]
FAMILIES = ("casual", "handwriting", "pixel", "rounded", "sans", "serif", "typewriter")
FETCHED_FILES = {
    "casual": {"ArrowType-Recursive.zip", "Yozai-Regular.ttf", "Yozai-Medium.ttf"},
    "handwriting": {
        # coding: the pre-patched Nerd build …
        "MonaspaceRadonNF-Regular.otf",
        "MonaspaceRadonNF-Bold.otf",
        # … text: the plain build from the same release, because "no Nerd patch"
        # is a different donor rather than an un-patch step.
        "MonaspaceRadon-Light.otf",
        "MonaspaceRadon-Regular.otf",
        "MonaspaceRadon-Bold.otf",
        "LXGWWenKai-Regular.ttf",
        "LXGWWenKai-Medium.ttf",
    },
    "pixel": {"fusion-pixel-12px-monospaced-ttf.zip"},
    "rounded": {"PkgTTF-IosevkaCurly.zip", "RHR-CN.7z"},
    "sans": {"Lilex.zip", "IBMPlexSansSC-Regular.ttf", "IBMPlexSansSC-Bold.ttf"},
    "serif": {"LXGWNeoZhiSongPlus.ttf", "SarasaTermSlabSC-TTF-Unhinted.7z"},
    "typewriter": {
        "CourierPrime-Regular.ttf",
        "CourierPrime-Bold.ttf",
        "ZhuqueFangsong.zip",
    },
}


def raw(family: str = "sans") -> dict:
    with (ROOT / family / "font.toml").open("rb") as handle:
        return tomllib.load(handle)


@pytest.mark.parametrize("family", FAMILIES)
def test_every_family_manifest_validates(family: str) -> None:
    manifest = load_manifest(ROOT / family / "font.toml")
    assert manifest.family == family
    assert "upright" in manifest.build.slopes


@pytest.mark.parametrize("family", FAMILIES)
def test_manifest_declares_exact_source_cache_files(family: str) -> None:
    manifest = load_manifest(ROOT / family / "font.toml")
    fetched = {
        artifact.file
        for source in manifest.sources.values()
        for artifact in source.artifacts.values()
        if artifact.fetch != "embedded"
    }
    assert fetched == FETCHED_FILES[family]


def test_missing_artifact_sha256_fails_at_parse_time() -> None:
    data = raw()
    del data["sources"]["lilex"]["artifacts"]["archive"]["sha256"]
    with pytest.raises(ValidationError, match="sha256"):
        Manifest.model_validate(data)


@pytest.mark.parametrize(
    ("axis", "value"),
    (("regions", "tc"), ("weights", "light"), ("formats", "woff2")),
)
def test_matrix_cannot_reference_undeclared_axis(axis: str, value: str) -> None:
    data = raw()
    data["build"]["matrix"][0][axis].append(value)
    with pytest.raises(ValidationError, match=f"undeclared {axis}"):
        Manifest.model_validate(data)


def test_region_needs_a_corresponding_cjk_source() -> None:
    data = raw()
    data["build"]["regions"].append("tc")
    data["build"]["matrix"][0]["regions"].append("tc")
    with pytest.raises(ValidationError, match="no corresponding CJK source"):
        Manifest.model_validate(data)


def test_italic_schema_slot_is_accepted() -> None:
    data = raw()
    data["build"]["slopes"].append("italic")
    data["build"]["matrix"][0]["slopes"].append("italic")
    assert "italic" in Manifest.model_validate(data).build.slopes


def test_windows_typographic_family_is_limited_to_31_characters() -> None:
    data = raw()
    data["naming"]["id16"] = "x" * 32
    with pytest.raises(ValidationError, match="at most 31 characters"):
        Manifest.model_validate(data)


def test_shell_export_preserves_serif_runtime_contract() -> None:
    env = legacy_environment(load_manifest(ROOT / "serif" / "font.toml"))
    assert env["SARASA_COMMIT"] == "4b908c71116a3192f7a9889bd67b1939a891e527"
    assert env["LXGW_SHA256"] == "279c973effc2811a827713ffa12706d556cab10b5067c0728400bf9e464f7008"
    assert env["SARASA_TERM_REGULAR"] == "SarasaTermSlabSC-Regular.ttf"


def test_manifest_rejects_unknown_fields() -> None:
    data = copy.deepcopy(raw())
    data["mystery"] = True
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Manifest.model_validate(data)


# --------------------------------------------------------------------------- #
# Phase 6 — profiles, and the weights a family cannot have
# --------------------------------------------------------------------------- #


def test_a_built_profile_needs_its_own_line_box() -> None:
    """Declaring `text` without `[metrics.text]` must fail at validation.

    The alternative is a merge step that dies an hour into a font build with a
    message about a missing dict key.
    """
    data = raw()
    data["build"]["profiles"].append("text")
    with pytest.raises(ValidationError, match=r"no \[metrics.<profile>\]"):
        Manifest.model_validate(data)


def test_a_second_profile_must_rename_the_family() -> None:
    data = raw()
    data["build"]["profiles"].append("text")
    data["metrics"]["text"] = copy.deepcopy(data["metrics"]["coding"])
    with pytest.raises(ValidationError, match="collide with the coding face"):
        Manifest.model_validate(data)


def test_naming_override_layers_over_the_base() -> None:
    from fontkit.manifest import naming_for

    manifest = load_manifest(ROOT / "handwriting" / "font.toml")
    coding = naming_for(manifest, "coding")
    text = naming_for(manifest, "text")

    assert coding.family == "RadonWenKai NFM"
    assert text.family == "RadonWenKai Text"
    # Stated once, inherited by both: an override says what differs.
    assert text.rfn_note == coding.rfn_note
    assert text.version == coding.version
    assert text.house == coding.house


def test_unsupported_cannot_disown_a_value_the_family_also_builds() -> None:
    data = raw()
    data["build"]["unsupported"] = [
        {"axis": "weights", "values": ["bold"], "reason": "nonsense"}
    ]
    with pytest.raises(ValidationError, match="both declares and disowns"):
        Manifest.model_validate(data)


def test_unsupported_needs_a_reason() -> None:
    data = raw()
    data["build"]["unsupported"] = [
        {"axis": "weights", "values": ["light"], "reason": ""}
    ]
    with pytest.raises(ValidationError, match="reason"):
        Manifest.model_validate(data)


@pytest.mark.parametrize("family", ("serif", "typewriter", "pixel"))
def test_families_that_cannot_take_a_light_say_so(family: str) -> None:
    """"不支持的显式声明，不是静默缺失" — the Phase 6 completion criterion.

    serif and typewriter derive their Bold by thickening a single CJK master
    with pathops, and pixel is a 12px bitmap. None of the three can produce a
    Light from these pins, and an empty slot in `weights` reads as an oversight.
    """
    manifest = load_manifest(ROOT / family / "font.toml")
    disowned = [
        entry
        for entry in manifest.build.unsupported
        if entry.axis == "weights" and "light" in entry.values
    ]
    assert disowned, f"{family} omits Light without saying why"
    assert len(disowned[0].reason) > 40, "the reason has to be a reason"

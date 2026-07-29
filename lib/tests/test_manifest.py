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
    "sans": {
        "Lilex.zip",
        # One Plex master per region (KIT-282). The Latin side stays a single
        # archive, which is the region axis paying for itself.
        "IBMPlexSansSC-Regular.ttf",
        "IBMPlexSansSC-Bold.ttf",
        "IBMPlexSansTC-Regular.ttf",
        "IBMPlexSansTC-Bold.ttf",
        "IBMPlexSansJP-Regular.ttf",
        "IBMPlexSansJP-Bold.ttf",
        "IBMPlexSansKR-Regular.ttf",
        "IBMPlexSansKR-Bold.ttf",
    },
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
    # `hk`, not `tc`: sans builds Simplified, Traditional, Japanese and Korean
    # since KIT-282, and Plex has no Hong Kong master to build a fifth from.
    ("axis", "value"),
    (("regions", "hk"), ("weights", "light"), ("formats", "woff2")),
)
def test_matrix_cannot_reference_undeclared_axis(axis: str, value: str) -> None:
    data = raw()
    data["build"]["matrix"][0][axis].append(value)
    with pytest.raises(ValidationError, match=f"undeclared {axis}"):
        Manifest.model_validate(data)


def test_region_needs_a_corresponding_cjk_source() -> None:
    data = raw()
    # `hk` has no [sources.plex] master and is declared unsupported; asking the
    # matrix for it anyway is the mistake this catches.
    data["build"]["unsupported"] = []
    data["build"]["regions"].append("hk")
    data["build"]["matrix"][0]["regions"].append("hk")
    with pytest.raises(ValidationError, match="no corresponding CJK source"):
        Manifest.model_validate(data)


def test_italic_schema_slot_is_accepted() -> None:
    data = raw()
    data["build"]["slopes"].append("italic")
    data["build"]["matrix"][0]["slopes"].append("italic")
    assert "italic" in Manifest.model_validate(data).build.slopes


def test_windows_family_budget_is_checked_on_the_composed_name() -> None:
    """The budget belongs to a *product*, not to a literal in the TOML.

    Nothing writes `AKR Sans SC NFM` down any more — it is four segments and an
    axis — so the check has to run on what the matrix composes.
    """
    data = raw()
    data["naming"]["style"] = "x" * 32
    with pytest.raises(ValidationError, match="at most 31"):
        Manifest.model_validate(data)


def test_the_budget_is_measured_against_the_weighted_name_id_1() -> None:
    """`Light` moves into name ID 1, so it is ID 1 that can overflow.

    24 characters of family plus ` Light` is 30 and fits; one more character of
    family fits as a *family* and does not fit as a product, which is exactly
    the failure the old family-only check could not see.
    """
    data = raw()
    data["build"]["weights"].append("light")
    data["build"]["matrix"][0]["weights"].append("light")
    data["calibration"]["light"] = dict(data["calibration"]["regular"])
    # "AKR " + style + " SC NFM" = 11 + len(style)
    data["naming"]["style"] = "x" * 14  # family 25, "… Light" 31 — fits
    Manifest.model_validate(data)

    data["naming"]["style"] = "x" * 15  # family 26, "… Light" 32 — does not
    with pytest.raises(ValidationError, match="Light"):
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
    with pytest.raises(ValidationError, match="both compose to"):
        Manifest.model_validate(data)


def test_naming_override_layers_over_the_base() -> None:
    from fontkit.manifest import naming_for

    manifest = load_manifest(ROOT / "handwriting" / "font.toml")
    coding = naming_for(manifest, "coding", "sc")
    text = naming_for(manifest, "text", "sc")

    assert coding.family == "AKR Hand SC NFM"
    assert text.family == "AKR Hand SC Text"
    # One segment differs and one segment is written down; everything else —
    # the house, the style token, the RFN note, the version — is inherited.
    assert text.rfn_note == coding.rfn_note
    assert text.version == coding.version
    assert text.house == coding.house
    assert text.style == coding.style


def test_the_region_is_an_axis_rather_than_a_string_in_the_file() -> None:
    """Four regions, one `[naming]` table (KIT-282)."""
    from fontkit.manifest import naming_for

    manifest = load_manifest(ROOT / "sans" / "font.toml")
    families = {
        region: naming_for(manifest, "coding", region).family
        for region in manifest.build.regions
    }
    assert families == {
        "sc": "AKR Sans SC NFM",
        "tc": "AKR Sans TC NFM",
        "jp": "AKR Sans JP NFM",
        "kr": "AKR Sans KR NFM",
    }
    # The PostScript name and the file stem are the same derived string, so a
    # product's file name and its name ID 6 cannot drift apart.
    names = naming_for(manifest, "coding", "jp")
    assert names.ps == names.stem == "AKRSansJPNFM"
    assert names.base_family == "AKR Sans JP Dual"


@pytest.mark.parametrize("family", FAMILIES)
def test_no_upstream_reserved_name_survives_in_a_family_name(family: str) -> None:
    """The rename's actual point (KIT-282).

    `pins.env` warned in five places that these names had to go before public
    OFL redistribution, and the old `rfn_note` fields said the same thing. This
    is the assertion that keeps it true.
    """
    from fontkit.manifest import naming_for

    reserved = (
        "iosevka", "monaspace", "radon", "lilex", "plex", "lxgw", "wenkai",
        "sarasa", "recursive", "yozai", "courier", "zhuque", "fusion",
        "resourcehan", "neozhisong",
    )
    manifest = load_manifest(ROOT / family / "font.toml")
    for profile in manifest.build.profiles:
        for region in manifest.build.regions:
            names = naming_for(manifest, profile, region)
            for candidate in filter(None, (names.family, names.base_family)):
                flat = candidate.replace(" ", "").lower()
                assert not [word for word in reserved if word in flat], candidate


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

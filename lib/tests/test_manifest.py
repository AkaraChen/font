from __future__ import annotations

import copy
import tomllib
from pathlib import Path

import pytest
from pydantic import ValidationError

from fontkit.manifest import Manifest, legacy_environment, load_manifest

ROOT = Path(__file__).parents[2]
FAMILIES = ("casual", "handwriting", "pixel", "rounded", "sans", "serif", "typewriter")


def raw(family: str = "sans") -> dict:
    with (ROOT / family / "font.toml").open("rb") as handle:
        return tomllib.load(handle)


@pytest.mark.parametrize("family", FAMILIES)
def test_every_family_manifest_validates(family: str) -> None:
    manifest = load_manifest(ROOT / family / "font.toml")
    assert manifest.family == family
    assert "upright" in manifest.build.slopes


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

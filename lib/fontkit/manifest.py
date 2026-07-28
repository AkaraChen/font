"""Validated reader for a family's ``font.toml`` build manifest.

TOML is the source of truth for both Nix and Python.  This module owns the
human-facing validation errors and the temporary shell export needed by serif's
last non-Nix pipeline and the calibration diagnostics.
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
import tomllib
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

Weight = Literal["light", "regular", "medium", "bold"]
Format = Literal["ttf", "otf", "woff2"]
Slope = Literal["upright", "italic"]
Profile = Literal["coding", "text"]
Region = Literal["sc", "tc", "hk", "jp", "kr"]
Scalar = str | int | float | bool


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Artifact(StrictModel):
    file: str | None = None
    fetch: Literal["plain", "zip-member", "embedded"] = "plain"
    url: HttpUrl
    sha256: str
    member: str | None = None

    @field_validator("sha256")
    @classmethod
    def sha256_is_hex(cls, value: str) -> str:
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("sha256 must be 64 lowercase hexadecimal characters")
        return value

    @model_validator(mode="after")
    def fetch_contract_is_complete(self) -> Self:
        if self.fetch != "embedded" and not self.file:
            raise ValueError("fetched artifacts must declare their canonical file name")
        if self.fetch == "zip-member" and not self.member:
            raise ValueError("zip-member artifacts must declare member")
        return self


class Source(StrictModel):
    role: Literal["latin", "cjk", "donor", "tool"]
    repository: HttpUrl
    version: str | None = None
    ref: str | None = None
    commit: str | None = None
    hash: str | None = None
    regions: list[Region] = Field(default_factory=list)
    artifacts: dict[str, Artifact] = Field(default_factory=dict)

    @model_validator(mode="after")
    def source_is_pinned(self) -> Self:
        if not (self.version or self.ref or self.commit):
            raise ValueError("source needs one of version, ref, or commit")
        if not self.artifacts and not (self.commit and self.hash):
            raise ValueError("source needs artifacts, or commit + hash for a source tree")
        if self.role == "cjk" and not self.regions:
            raise ValueError("CJK source must declare at least one region")
        return self


class Grid(StrictModel):
    en_adv: int = Field(gt=0)
    cjk_adv: int = Field(gt=0)
    upm: int = Field(gt=0)
    latin_src_adv: int | None = Field(default=None, gt=0)
    latin_src_upm: int | None = Field(default=None, gt=0)
    latin_target_upm: int | None = Field(default=None, gt=0)
    latin_narrow_adv: int | None = Field(default=None, gt=0)
    latin_uniform_scale: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def dual_width_grid(self) -> Self:
        if self.cjk_adv != self.en_adv * 2:
            raise ValueError("cjk_adv must be exactly twice en_adv")
        return self


class Naming(StrictModel):
    family: str
    ps: str
    stem: str
    house: str
    style: str
    region: str
    variant: str
    id16: str
    id17: str
    rfn_note: str
    base_family: str | None = None
    base_ps: str | None = None
    suffix: str = ""
    version: str = "0.1.0"
    product_name_zh: str | None = None

    @field_validator("family", "base_family", "id16")
    @classmethod
    def windows_family_name_limit(cls, value: str | None) -> str | None:
        if value is not None and len(value) > 31:
            raise ValueError("Windows family names must be at most 31 characters")
        return value


class VerticalMetrics(StrictModel):
    hhea_ascent: int
    hhea_descent: int
    hhea_line_gap: int = 0
    os2_typo_ascender: int | None = None
    os2_typo_descender: int | None = None
    os2_typo_line_gap: int | None = None
    os2_win_ascent: int | None = None
    os2_win_descent: int | None = None


class Calibration(StrictModel):
    source_weight: Weight | None = None
    embolden: float = Field(ge=0)
    slant_deg: float = 0
    slant_pivot_y: int = 375


class Merge(StrictModel):
    """Every knob `fontkit.merge` needs to build this family's face.

    A family that merges a Latin donor with a CJK donor declares *what is
    different about it* here, and nothing else. The engine has no per-family
    branches: adding a family means adding this table, not a `merge_*.py`.
    """

    # name ID 5 — "<version>;KIT;<family> merge (<sources_note>; EN … / CJK …)".
    # `{slant}` in sources_note is filled from [calibration.<weight>].slant_deg,
    # per weight, so a family whose shear differs by weight says so honestly.
    version: str
    sources_note: str

    # What the donors need before they are on the product grid.
    latin: Literal["none", "scale", "normalize"]
    cjk: Literal["as-is", "normalize", "require-same-upm"]
    latin_subset: Literal["none", "coding"] = "none"
    drop_hinting: bool = False

    # Which codepoints come from the CJK donor, and how they land on a cell.
    import_policy: Literal["cjk-side", "cjk-side-or-missing", "east-asian-width"]
    placement: Literal["center", "fit"] = "center"
    glyph_prefix: str
    required_sample: str

    # Finishing touches a family needs and the others do not.
    set_weight_class: bool = False
    recalc_bounds: bool = False
    widen_wide_base_glyphs: bool = False
    drop_vertical_metrics: bool = False
    check_glyph_budget: bool = False

    @field_validator("glyph_prefix")
    @classmethod
    def prefix_cannot_collide_with_a_real_glyph_name(cls, value: str) -> str:
        if not value.endswith("."):
            raise ValueError("glyph_prefix must end with '.' so it cannot shadow a donor name")
        return value

    @model_validator(mode="after")
    def fit_placement_needs_a_per_cell_policy(self) -> Self:
        if self.placement == "fit" and self.import_policy != "east-asian-width":
            raise ValueError(
                "placement = \"fit\" only means something when the cell is decided "
                "per codepoint (import_policy = \"east-asian-width\")"
            )
        if self.latin_subset != "none" and self.latin != "normalize":
            raise ValueError("latin_subset applies to latin = \"normalize\" only")
        return self


class Nerd(StrictModel):
    version: str
    commit: str = Field(min_length=40, max_length=40)
    hash: str


class MatrixEntry(StrictModel):
    profile: Profile
    regions: list[Region]
    weights: list[Weight]
    formats: list[Format]
    slopes: list[Slope]


class Build(StrictModel):
    profiles: list[Profile]
    regions: list[Region]
    weights: list[Weight]
    formats: list[Format]
    slopes: list[Slope]
    matrix: list[MatrixEntry]


class Manifest(StrictModel):
    schema_version: Literal[1]
    family: str
    build: Build
    sources: dict[str, Source]
    grid: Grid
    naming: Naming
    metrics: dict[Profile, VerticalMetrics] = Field(default_factory=dict)
    calibration: dict[Weight, Calibration] = Field(default_factory=dict)
    merge: Merge | None = None
    nerd: Nerd | None = None
    options: dict[str, Scalar | list[str]] = Field(default_factory=dict)

    @field_validator("options")
    @classmethod
    def calibration_is_not_hidden_in_options(
        cls, value: dict[str, Scalar | list[str]]
    ) -> dict[str, Scalar | list[str]]:
        forbidden = ("embolden", "slant", "calibration")
        misplaced = [key for key in value if any(word in key for word in forbidden)]
        if misplaced:
            raise ValueError(
                f"calibration values belong under [calibration.<weight>], not options: {misplaced}"
            )
        return value

    @model_validator(mode="after")
    def matrix_references_declared_axes_and_sources(self) -> Self:
        declared = self.build
        for i, entry in enumerate(declared.matrix):
            for axis in ("regions", "weights", "formats", "slopes"):
                missing = set(getattr(entry, axis)) - set(getattr(declared, axis))
                if missing:
                    raise ValueError(f"matrix[{i}] references undeclared {axis}: {sorted(missing)}")
            if entry.profile not in declared.profiles:
                raise ValueError(f"matrix[{i}] references undeclared profile: {entry.profile}")

        matrix_regions = {r for entry in declared.matrix for r in entry.regions}
        source_regions = {
            region
            for source in self.sources.values()
            if source.role == "cjk"
            for region in source.regions
        }
        missing_sources = matrix_regions - source_regions
        if missing_sources:
            raise ValueError(
                f"matrix regions have no corresponding CJK source: {sorted(missing_sources)}"
            )

        matrix_weights = {w for entry in declared.matrix for w in entry.weights}
        missing_calibration = matrix_weights - set(self.calibration)
        if missing_calibration and self.family != "pixel":
            raise ValueError(
                f"matrix weights have no calibration entry: {sorted(missing_calibration)}"
            )
        return self


def load_manifest(path: str | Path) -> Manifest:
    path = Path(path)
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    return Manifest.model_validate(data)


def _artifact(manifest: Manifest, source: str, artifact: str) -> Artifact:
    return manifest.sources[source].artifacts[artifact]


def legacy_environment(manifest: Manifest) -> dict[str, str]:
    """Translate semantic fields to names still used by shell diagnostics.

    The compatibility names are code, not duplicated manifest data.  What reads
    them is ``tools/diagnostic.sh`` — the hand-run calibration and preview
    scripts, not the build, which takes its values from ``font.toml`` through
    Nix.  They can disappear whenever those scripts stop wanting shell
    variables, without changing ``font.toml``.
    """

    def text(value: object) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    env: dict[str, object] = {
        "EN_ADV": manifest.grid.en_adv,
        "CJK_ADV": manifest.grid.cjk_adv,
        "UPM": manifest.grid.upm,
        "FAMILY_NAME": manifest.naming.family,
        "FAMILY_PS": manifest.naming.ps,
        "PRODUCT_STEM": manifest.naming.stem,
        "FAMILY_SUFFIX": manifest.naming.suffix,
        "PRODUCT_VERSION": manifest.naming.version,
    }
    if manifest.naming.base_family is not None:
        env["BASE_FAMILY_NAME"] = manifest.naming.base_family
    if manifest.naming.base_ps is not None:
        env["BASE_FAMILY_PS"] = manifest.naming.base_ps
    if manifest.naming.product_name_zh is not None:
        env["PRODUCT_NAME_ZH"] = manifest.naming.product_name_zh

    grid_names = {
        "latin_src_adv": "LATIN_SRC_ADV",
        "latin_src_upm": "LATIN_SRC_UPM",
        "latin_target_upm": "LATIN_TARGET_UPM",
        "latin_narrow_adv": "LATIN_NARROW_ADV",
        "latin_uniform_scale": "LATIN_UNIFORM_SCALE",
    }
    for field, name in grid_names.items():
        value = getattr(manifest.grid, field)
        if value is not None:
            env[name] = value

    metrics = manifest.metrics.get("coding")
    if metrics:
        for field, value in metrics:
            if value is not None:
                env[field.upper()] = value
    for weight, calibration in manifest.calibration.items():
        upper = weight.upper()
        env[f"CJK_EMBOLDEN_{upper}"] = calibration.embolden
        if calibration.source_weight:
            env[f"CJK_SOURCE_WEIGHT_{upper}"] = calibration.source_weight.capitalize()
        env[f"CJK_SLANT_DEG_{upper}"] = calibration.slant_deg
        env[f"CJK_SLANT_PIVOT_Y_{upper}"] = calibration.slant_pivot_y
    if manifest.calibration:
        first = next(iter(manifest.calibration.values()))
        env["CJK_SLANT_DEG"] = first.slant_deg
        env["CJK_SLANT_PIVOT_Y"] = first.slant_pivot_y

    if manifest.nerd:
        env.update(
            NERD_FONTS_PATCHER_VERSION=manifest.nerd.version,
            NERD_FONTS_PATCHER_COMMIT=manifest.nerd.commit,
            NERD_FONTS_PATCHER_HASH=manifest.nerd.hash,
        )

    # Family-specific shell names. Every value still comes from a typed field.
    family = manifest.family
    source = manifest.sources
    options = manifest.options
    if family == "serif":
        sarasa, lxgw, donor = source["sarasa"], source["lxgw"], source["sarasa_term"]
        env.update(
            SARASA_REPO=sarasa.repository,
            SARASA_REF=sarasa.ref,
            SARASA_COMMIT=sarasa.commit,
            SARASA_SRC_HASH=sarasa.hash,
            LXGW_REPO=lxgw.repository,
            LXGW_TAG=lxgw.version,
            LXGW_ASSET=options["lxgw_asset"],
            LXGW_URL=_artifact(manifest, "lxgw", "regular").url,
            LXGW_SHA256=_artifact(manifest, "lxgw", "regular").sha256,
            CJK_TARGET_UPM=manifest.grid.upm,
            BUILD_TARGET=options["build_target"],
            SARASA_TERM_ARCHIVE_URL=_artifact(manifest, "sarasa_term", "archive").url,
            SARASA_TERM_ARCHIVE_SHA256=_artifact(
                manifest, "sarasa_term", "archive"
            ).sha256,
            SARASA_TERM_REGULAR=options["sarasa_term_regular"],
            SARASA_TERM_BOLD=options["sarasa_term_bold"],
        )
    elif family == "casual":
        env.update(
            YOZAI_FOR_REGULAR=manifest.calibration["regular"].source_weight.capitalize(),
            YOZAI_FOR_BOLD=manifest.calibration["bold"].source_weight.capitalize(),
        )
    elif family == "handwriting":
        env.update(
            WENKAI_REPO=source["wenkai"].repository,
            WENKAI_RELEASE_TAG=source["wenkai"].version,
            WENKAI_FOR_REGULAR=manifest.calibration["regular"].source_weight.capitalize(),
            WENKAI_FOR_BOLD=manifest.calibration["bold"].source_weight.capitalize(),
        )

    env.update(
        {
            key.upper(): ",".join(value) if isinstance(value, list) else value
            for key, value in options.items()
        }
    )
    return {key: text(value) for key, value in env.items() if value is not None}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "shell", "json"))
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)

    try:
        manifest = load_manifest(args.manifest)
    except Exception as error:
        print(f"{args.manifest}: {error}", file=sys.stderr)
        return 2

    if args.command == "validate":
        print(f"{args.manifest}: valid")
    elif args.command == "json":
        print(json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True))
    else:
        for key, value in sorted(legacy_environment(manifest).items()):
            print(f"export {key}={shlex.quote(value)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

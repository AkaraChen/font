"""Release notes are generated, so the things they must not get wrong are tests.

The old serif workflow wrote its notes by hand and they drifted: they advertised
pins the products were not built from and a "Changes" section about a fix three
releases old. Every fact below comes out of the same `font.toml` the build
reads, and these tests pin the four that would be actively harmful if wrong —
the family name, the pins, the format descriptions, and whether the reader is
told their editor config is about to break.

Run against the real manifests rather than a fixture: a synthetic font.toml
would let the notes stay correct about a family that does not exist.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fontkit import release_notes
from fontkit.manifest import load_manifest, naming_for

REPO_ROOT = Path(__file__).resolve().parents[2]
FAMILIES = [
    "casual",
    "handwriting",
    "pixel",
    "rounded",
    "sans",
    "serif",
    "typewriter",
]


def _cells():
    for family in FAMILIES:
        manifest = load_manifest(REPO_ROOT / family / "font.toml")
        for entry in manifest.build.matrix:
            for region in entry.regions:
                yield manifest, entry, region


def _render(manifest, entry, region, version="9.9.9"):
    return release_notes.render(
        manifest, entry.profile, region, version, list(entry.weights), list(entry.formats)
    )


@pytest.mark.parametrize(
    "manifest,entry,region",
    [pytest.param(m, e, r, id=f"{m.family}-{e.profile}-{r}") for m, e, r in _cells()],
)
def test_every_cell_renders_its_own_product(manifest, entry, region):
    text = _render(manifest, entry, region)
    names = naming_for(manifest, entry.profile, region)
    assert names.family in text
    assert names.stem in text
    assert "v9.9.9" in text
    # The pins the build read, not a hand-typed list.
    for source in manifest.sources.values():
        assert str(source.repository).rstrip("/") in text


@pytest.mark.parametrize(
    "manifest,entry,region",
    [pytest.param(m, e, r, id=f"{m.family}-{e.profile}-{r}") for m, e, r in _cells()],
)
def test_every_shipped_format_is_described(manifest, entry, region):
    """A reader choosing between a .ttf and an .otf has to be told they are not
    the same file. Silence would read as "pick either"."""
    text = _render(manifest, entry, region)
    for fmt in entry.formats:
        assert f"**`.{fmt}`**" in text
    assert "hinting" in text  # every format list says something about hinting


def test_a_renamed_product_says_so_and_a_new_one_does_not():
    """The rename broke every editor config that named an old family (KIT-282).

    SC shipped before the rename and must carry the migration note; TC never
    existed, so telling its users to change a config they never wrote would be
    inventing history.
    """
    sans = load_manifest(REPO_ROOT / "sans" / "font.toml")
    entry = sans.build.matrix[0]

    sc = _render(sans, entry, "sc")
    assert "LilexSansSC NFM" in sc
    assert "breaking change" in sc
    assert "Uninstall the old family" in sc

    tc = _render(sans, entry, "tc")
    assert "LilexSansSC NFM" not in tc
    assert "has never shipped under another name" in tc


def test_the_two_handwriting_profiles_migrate_separately():
    """They were renamed as two products because they are two products."""
    hand = load_manifest(REPO_ROOT / "handwriting" / "font.toml")
    by_profile = {entry.profile: entry for entry in hand.build.matrix}

    coding = _render(hand, by_profile["coding"], "sc")
    text = _render(hand, by_profile["text"], "sc")
    assert "RadonWenKai NFM" in coding
    assert "RadonWenKai Text" in text
    # …and the reading face is the one cell in the repo that ships an OTF.
    assert "**`.otf`**" in text
    assert "**`.otf`**" not in coding


def test_unbuildable_axis_values_are_reported_with_their_reason():
    """`[[build.unsupported]]` exists so a gap reads as a decision. It only does
    that if the decision reaches the reader."""
    serif = load_manifest(REPO_ROOT / "serif" / "font.toml")
    text = _render(serif, serif.build.matrix[0], "sc")
    assert "Not in this release, on purpose" in text
    assert "stroke embolden has no negative strength" in text


def test_the_migration_doc_and_the_manifests_agree():
    """Two places now state the old→new mapping: docs/naming-migration.md, which
    a human reads, and `[naming.former]`, which the notes are generated from.

    They are allowed to coexist — the doc carries the long explanation — but not
    to disagree, and a table nobody checks is exactly how a release ends up
    telling users to migrate from a name that was never used.

    Skipped inside the `fontkit` derivation, which is deliberately built from
    `lib/` plus the seven `font.toml` files and nothing else (nix/fontkit.nix):
    putting `docs/` in that fileset would make editing a paragraph rebuild every
    build step in the repo. It runs in the devShell — `just test`, and CI's
    fontkit job, both of which have the working copy.
    """
    path = REPO_ROOT / "docs" / "naming-migration.md"
    if not path.is_file():
        pytest.skip("docs/ is not part of the fontkit derivation's source")
    doc = path.read_text(encoding="utf-8")
    documented = {}
    for line in doc.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 2 or not all(c.startswith("`") and c.endswith("`") for c in cells):
            continue
        documented[cells[0].strip("`")] = cells[1].strip("`")

    declared = {}
    for family in FAMILIES:
        manifest = load_manifest(REPO_ROOT / family / "font.toml")
        for entry in manifest.build.matrix:
            for region in entry.regions:
                names = naming_for(manifest, entry.profile, region)
                if names.former_family:
                    declared[names.former_family] = names.family

    assert declared == documented


def test_a_cell_that_does_not_exist_is_an_error(tmp_path, capsys):
    rc = release_notes.main(
        [
            "--manifest",
            str(REPO_ROOT / "serif" / "font.toml"),
            "--profile",
            "text",
            "--region",
            "sc",
            "--version",
            "1.0.0",
        ]
    )
    assert rc == 2
    assert "declares no (text, sc) cell" in capsys.readouterr().err


def test_a_format_the_cell_does_not_ship_is_an_error(capsys):
    """The notes list what the archive holds. Letting the caller name a format
    the build never produced would put a file in the notes and not in the zip."""
    rc = release_notes.main(
        [
            "--manifest",
            str(REPO_ROOT / "sans" / "font.toml"),
            "--profile",
            "coding",
            "--region",
            "sc",
            "--version",
            "1.0.0",
            "--formats",
            "otf",
        ]
    )
    assert rc == 2
    assert "not declared for this cell" in capsys.readouterr().err

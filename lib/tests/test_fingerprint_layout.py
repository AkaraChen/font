"""The GSUB/GPOS dump has to be a function of the font, not of table order.

The other half of KIT-297. A Nerd diff used to show two `feature locl` lines
swapping places between an `x86_64-linux` build and an `aarch64-darwin` one.
That was never FontForge miswriting the font: a font carries one `locl` per
script, `fingerprint.py` sorted FeatureRecords by tag, and a tag is not a
unique key — so ties fell through to the record's index in the FeatureList,
which FontForge is free to permute as long as it remaps the LangSys
FeatureIndex to match. Which it does.

Permuting the FeatureList must therefore produce an identical dump; pointing a
LangSys at a *different* feature must not. Both are checked here, because a
normalisation that only satisfies the first is indistinguishable from deleting
the information.

`tools/` is not a package, so the module is loaded by path.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from fontTools.ttLib import newTable
from fontTools.ttLib.tables import otTables

REPO_ROOT = Path(__file__).resolve().parents[2]
FINGERPRINT_PY = REPO_ROOT / "tools" / "fingerprint.py"

# The fontkit derivation packages `lib/` and the seven `font.toml` fixtures and
# deliberately nothing else, so that a change to a tool or a README does not
# invalidate it (nix/fontkit.nix). `tools/fingerprint.py` is therefore absent
# when pytest runs inside that build — but present for `just test` and for the
# workflow's own "Unit tests" step, which run against the working copy. Skipping
# is the honest answer for the one context that cannot see the file; adding
# `tools/` to the fileset to satisfy it would put every fingerprint edit on
# fontkit's cache key.
pytestmark = pytest.mark.skipif(
    not FINGERPRINT_PY.is_file(),
    reason="tools/fingerprint.py is outside the packaged source (nix/fontkit.nix)",
)


def _load_fingerprint():
    spec = importlib.util.spec_from_file_location("fingerprint", FINGERPRINT_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fingerprint = _load_fingerprint() if FINGERPRINT_PY.is_file() else None


def _lookup(lookup_type: int):
    lookup = otTables.Lookup()
    lookup.LookupType = lookup_type
    lookup.LookupFlag = 0
    lookup.SubTable = []
    lookup.SubTableCount = 0
    return lookup


def _feature(tag: str, indices: list[int]):
    record = otTables.FeatureRecord()
    record.FeatureTag = tag
    record.Feature = otTables.Feature()
    record.Feature.LookupListIndex = list(indices)
    record.Feature.LookupCount = len(indices)
    record.Feature.FeatureParams = None
    return record


def _langsys(indices: list[int]):
    lang = otTables.LangSys()
    lang.FeatureIndex = list(indices)
    lang.FeatureCount = len(indices)
    lang.LookupOrder = None
    lang.ReqFeatureIndex = 0xFFFF
    return lang


def _gsub(feature_records, script_langsys):
    """A GSUB carrying three lookups, the given features, and one script per
    entry of `script_langsys` ({script tag: [feature indices]})."""
    table = otTables.GSUB()
    table.Version = 0x00010000

    table.LookupList = otTables.LookupList()
    table.LookupList.Lookup = [_lookup(1), _lookup(6), _lookup(2)]
    table.LookupList.LookupCount = 3

    table.FeatureList = otTables.FeatureList()
    table.FeatureList.FeatureRecord = list(feature_records)
    table.FeatureList.FeatureCount = len(feature_records)

    table.ScriptList = otTables.ScriptList()
    table.ScriptList.ScriptRecord = []
    for tag, indices in sorted(script_langsys.items()):
        record = otTables.ScriptRecord()
        record.ScriptTag = tag
        record.Script = otTables.Script()
        record.Script.DefaultLangSys = _langsys(indices)
        record.Script.LangSysRecord = []
        record.Script.LangSysCount = 0
        table.ScriptList.ScriptRecord.append(record)
    table.ScriptList.ScriptCount = len(table.ScriptList.ScriptRecord)
    return table


class FakeFont(dict):
    """`_dump_layout` only ever does `tag in font` and `font[tag].table`."""

    def __init__(self, table):
        super().__init__()
        holder = newTable("GSUB")
        holder.table = table
        self["GSUB"] = holder


def _dump(table) -> list[str]:
    lines: list[str] = []
    fingerprint._dump_layout(FakeFont(table), "GSUB", lines)
    return lines


# `locl` twice with different lookups — the shape that actually drifted — plus
# a `calt` so the common single-instance case is covered in the same font.
LOCL_A = lambda: _feature("locl", [0])       # noqa: E731 - lookup type 1
LOCL_B = lambda: _feature("locl", [1])       # noqa: E731 - lookup type 6
CALT = lambda: _feature("calt", [1, 2])      # noqa: E731


def test_permuting_the_featurelist_changes_nothing():
    """The bug, directly: same font, FeatureList written the other way round."""
    straight = _gsub(
        [LOCL_A(), LOCL_B(), CALT()],
        {"latn": [0, 2], "cyrl": [1, 2]},
    )
    # locl A and locl B swap places; every FeatureIndex is remapped to match,
    # which is exactly what FontForge does.
    swapped = _gsub(
        [LOCL_B(), LOCL_A(), CALT()],
        {"latn": [1, 2], "cyrl": [0, 2]},
    )
    assert _dump(straight) == _dump(swapped)


def test_repointing_a_langsys_still_shows():
    """The normalisation must not have achieved agreement by discarding the
    thing that differs: give `latn` the *other* locl and the dump must move."""
    before = _gsub([LOCL_A(), LOCL_B(), CALT()], {"latn": [0, 2], "cyrl": [1, 2]})
    after = _gsub([LOCL_A(), LOCL_B(), CALT()], {"latn": [1, 2], "cyrl": [1, 2]})
    assert _dump(before) != _dump(after)


def test_same_tag_instances_are_distinguished_on_script_lines():
    table = _gsub([LOCL_A(), LOCL_B(), CALT()], {"latn": [0, 2], "cyrl": [1, 2]})
    script_lines = [ln for ln in _dump(table) if ln.startswith("script")]
    latn = next(ln for ln in script_lines if "latn" in ln)
    cyrl = next(ln for ln in script_lines if "cyrl" in ln)
    assert "locl#1" in latn or "locl#2" in latn
    assert "locl#1" in cyrl or "locl#2" in cyrl
    assert latn.split("\t")[-1] != cyrl.split("\t")[-1]


def test_a_tag_with_one_instance_keeps_its_bare_name():
    """No churn where there was no ambiguity — `calt` stays `calt`, so the
    committed baselines only move on the lines that needed disambiguating."""
    table = _gsub([LOCL_A(), LOCL_B(), CALT()], {"latn": [0, 2]})
    line = next(ln for ln in _dump(table) if ln.startswith("script"))
    assert "calt" in line.split("\t")[-1].split(",")
    assert "calt#" not in line


def test_feature_lines_are_sorted_by_tag_then_signature():
    table = _gsub([LOCL_B(), LOCL_A(), CALT()], {"latn": [0, 1, 2]})
    features = [ln for ln in _dump(table) if ln.startswith("feature")]
    assert features == sorted(features)


@pytest.mark.parametrize("tag", ["GSUB", "GPOS"])
def test_absent_table_is_recorded_not_skipped(tag):
    lines: list[str] = []
    fingerprint._dump_layout({}, tag, lines)
    assert lines == [f"[{tag}]", "absent\t1"]

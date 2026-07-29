"""Cache-key projections must ignore pure metadata bumps (KIT-304)."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"


def _load(name: str):
    path = TOOLS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sources_key = _load("sources-cache-key")
intermediates_key = _load("intermediates-cache-key")


def _digest(body: str) -> str:
    return hashlib.sha256(body.encode()).hexdigest()


def test_sources_key_stable_on_version_bump(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Minimal repo: one family + the fetcher files the projection hashes.
    fam = tmp_path / "demo"
    fam.mkdir()
    (fam / "font.toml").write_text(
        """
schema_version = 1
family = "demo"

[sources.latin.artifacts.regular]
file = "Latin.ttf"
url = "https://example.invalid/Latin.ttf"
sha256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

[naming]
version = "1.0.0"
""".lstrip()
    )
    for rel in sources_key.FETCHER_PATHS:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# stub {rel}\n")

    before = sources_key.projection(tmp_path)

    text = (fam / "font.toml").read_text().replace('version = "1.0.0"', 'version = "9.9.9"')
    (fam / "font.toml").write_text(text)
    after = sources_key.projection(tmp_path)

    assert _digest(before) == _digest(after)
    assert "naming" not in before
    assert "1.0.0" not in before


def test_sources_key_moves_when_source_hash_changes(tmp_path: Path):
    fam = tmp_path / "demo"
    fam.mkdir()
    manifest = """
schema_version = 1
family = "demo"

[sources.latin.artifacts.regular]
file = "Latin.ttf"
url = "https://example.invalid/Latin.ttf"
sha256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
"""
    (fam / "font.toml").write_text(manifest.lstrip())
    for rel in sources_key.FETCHER_PATHS:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# stub {rel}\n")

    before = _digest(sources_key.projection(tmp_path))
    (fam / "font.toml").write_text(
        manifest.replace("aaaaaaaa", "bbbbbbbb").lstrip()
    )
    after = _digest(sources_key.projection(tmp_path))
    assert before != after


def test_intermediates_key_stable_on_version_bump():
    # Against the real repo: renaming version in a copy would be heavy; instead
    # assert the live projection omits naming and includes the sarasa pin.
    body = intermediates_key.projection(ROOT)
    assert "naming.version" not in body
    assert "naming.house" not in body
    assert "sources.sarasa" in body or "sources.sarasa.commit" in body
    assert "file flake.lock" in body
    assert "file nix/families/serif.nix" in body

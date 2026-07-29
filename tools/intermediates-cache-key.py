#!/usr/bin/env python3
"""Project the inputs that decide the CI *intermediates* cache layer.

The intermediates warmer (KIT-304) keeps:

  * every `latin-prepared-*` step (casual, handwriting) — region-independent
  * `serif-sarasa` — the upstream Sarasa npm build

Its key must follow those steps' real inputs, not a whole-family hash: a
`[naming] version` bump must not evict a multi-minute Sarasa build.

Printed projection covers:

  * for casual / handwriting / serif manifests: `sources`, `grid`,
    `calibration`, `options`, `nerd`, `build` (not `naming` / `merge`)
  * the nix graph and scripts those steps import
  * `flake.lock` + `flake.nix` (toolchain pins change the build)

Usage:
  tools/intermediates-cache-key.py
  tools/intermediates-cache-key.py --digest
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

FAMILIES = ("casual", "handwriting", "serif")

# Manifest tables that feed latin-prepared / serif-sarasa. naming + merge are
# deliberately absent: version stamps do not change those outputs.
MANIFEST_SECTIONS = (
    "sources",
    "grid",
    "calibration",
    "options",
    "nerd",
    "build",
)

# Files whose bytes are inputs to the intermediate derivations.
PATH_GLOBS = [
    "flake.lock",
    "flake.nix",
    "nix/intermediates.nix",
    "nix/granularity.nix",
    "nix/fontkit.nix",
    "nix/matrix.nix",
    "nix/lib/manifest.nix",
    "nix/sources/default.nix",
    "nix/families/default.nix",
    "nix/families/support.nix",
    "nix/families/casual.nix",
    "nix/families/handwriting.nix",
    "nix/families/serif.nix",
    "casual/scripts/prepare_latin.py",
    "handwriting/scripts/prepare_latin.py",
    "serif/patches/series",
    "serif/patches/0001-verdafile-unhinted-and-direct-ttf.patch",
    "serif/patches/0002-config-monoslab-neozhisong-opt.patch",
    "lib/fontkit/__init__.py",
    "lib/fontkit/prepare_cjk.py",
    "lib/fontkit/embolden.py",
    "lib/fontkit/scale_upem.py",
    "lib/pyproject.toml",
]


def dump_table(prefix: str, value: object, out: list[str]) -> None:
    if not isinstance(value, dict):
        out.append(f"{prefix} = {value!r}")
        return
    for key in sorted(value):
        child = value[key]
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(child, dict):
            dump_table(path, child, out)
        elif isinstance(child, list):
            out.append(f"{path} = {child!r}")
        else:
            out.append(f"{path} = {child!r}")


def project_manifest(family: str, data: dict) -> list[str]:
    lines = [f"# family={family}"]
    for section in MANIFEST_SECTIONS:
        if section in data:
            dump_table(section, data[section], lines)
    return lines


def projection(root: Path) -> str:
    chunks: list[str] = ["# intermediates-cache-key v1"]
    for family in FAMILIES:
        text = (root / family / "font.toml").read_bytes()
        data = tomllib.loads(text.decode())
        chunks.extend(project_manifest(family, data))
        chunks.append("")
    for rel in PATH_GLOBS:
        path = root / rel
        if not path.is_file():
            raise SystemExit(f"intermediates-cache-key: missing {rel}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        chunks.append(f"file {rel} = {digest}")
    chunks.append("")
    return "\n".join(chunks)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--digest", action="store_true")
    ap.add_argument("--root", type=Path, default=REPO)
    args = ap.parse_args()
    body = projection(args.root)
    if args.digest:
        print(hashlib.sha256(body.encode()).hexdigest())
    else:
        sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

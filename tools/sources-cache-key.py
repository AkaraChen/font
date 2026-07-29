#!/usr/bin/env python3
"""Project the inputs that decide the CI *sources* cache layer.

The sources warmer realises every pinned upstream artifact (`.#source-cache`,
`.#sarasa-src`, `.#font-patcher`). Its GHA key used to be
`hashFiles('*/font.toml')`, which invalidates the whole ~700 MiB layer when
anything in any manifest changes — including a pure metadata bump of
`[naming] version` that does not touch a single fetched byte.

This script prints a stable, canonical projection of only the sections that
affect fetches:

  * every `[sources.*]` table (urls, hashes, members, commits)
  * every `[nerd]` table (font-patcher pin)
  * the fetchers themselves (`nix/sources/`, `nix/lib/manifest.nix`,
    `nix/source-cache.nix`, `tools/fetch_zip_member.py`)

CI hashes this projection (sha256 of stdout) into the `nix-src-…` primary key.
A version-only bump leaves the projection — and the layer — untouched.

Usage:
  tools/sources-cache-key.py              # print projection
  tools/sources-cache-key.py --digest     # print sha256 of projection only
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Files whose bytes are inputs to the source layer, independent of any family.
FETCHER_PATHS = [
    "nix/sources/default.nix",
    "nix/lib/manifest.nix",
    "nix/source-cache.nix",
    "tools/fetch_zip_member.py",
]


def family_dirs(root: Path) -> list[Path]:
    return sorted(
        p for p in root.iterdir() if p.is_dir() and (p / "font.toml").is_file()
    )


def dump_table(prefix: str, value: object, out: list[str]) -> None:
    """Flatten a TOML table into sorted `key = repr(value)` lines."""
    if not isinstance(value, dict):
        out.append(f"{prefix} = {value!r}")
        return
    for key in sorted(value):
        child = value[key]
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(child, dict):
            dump_table(path, child, out)
        else:
            out.append(f"{path} = {child!r}")


def project_manifest(family: str, data: dict) -> list[str]:
    lines = [f"# family={family}"]
    sources = data.get("sources")
    if sources is not None:
        dump_table("sources", sources, lines)
    nerd = data.get("nerd")
    if nerd is not None:
        dump_table("nerd", nerd, lines)
    return lines


def projection(root: Path) -> str:
    chunks: list[str] = ["# sources-cache-key v1"]
    for fam in family_dirs(root):
        text = (fam / "font.toml").read_bytes()
        data = tomllib.loads(text.decode())
        chunks.extend(project_manifest(fam.name, data))
        chunks.append("")
    for rel in FETCHER_PATHS:
        path = root / rel
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        chunks.append(f"file {rel} = {digest}")
    chunks.append("")
    return "\n".join(chunks)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--digest",
        action="store_true",
        help="print only the sha256 of the projection",
    )
    ap.add_argument(
        "--root",
        type=Path,
        default=REPO,
        help="repository root (default: parent of tools/)",
    )
    args = ap.parse_args()
    body = projection(args.root)
    if args.digest:
        print(hashlib.sha256(body.encode()).hexdigest())
    else:
        sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

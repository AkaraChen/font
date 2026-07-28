"""Release packaging — one implementation, six families.

Replaces `<family>/scripts/package-release.sh` ×6 (56-80 lines each). Those
scripts were three things glued together: a re-run of the family's verify gate,
a `cat > README.txt <<EOF` heredoc interpolating pins.env, and `zip -9 -r`.

Only the third is packaging.

  * The gate moved into the build graph. A product derivation that failed its
    own gate does not exist, so there is nothing left to re-check here — the
    old re-run guarded against `out/` having been edited by hand between build
    and package, which a store path cannot be.
  * The README body is now rendered by Nix from the same pins the build read,
    and arrives as `--readme`. A heredoc that interpolates shell variables is a
    second copy of every pin, and it drifted: casual's said "no Nerd patch in
    v0.1" for a family that never had one, pixel's hardcoded a grid.

The zip is written deterministically: sorted member order, and every timestamp
forced to the DOS epoch floor (1980-01-01) so the same products always produce
the same archive bytes. `zip -9 -r` did neither, so two identical builds
produced two different zips and nothing downstream could compare them.
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

# The zip format cannot represent a timestamp before 1980; fontTools and the
# rest of the toolchain honour SOURCE_DATE_EPOCH=0 (1970), so clamping here is
# the closest deterministic equivalent.
DOS_EPOCH = (1980, 1, 1, 0, 0, 0)


def write_zip(dest: Path, members: list[tuple[str, Path]]) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for arcname, source in sorted(members):
            info = zipfile.ZipInfo(arcname, date_time=DOS_EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, source.read_bytes())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fonts", nargs="+", type=Path, help="product fonts to ship")
    ap.add_argument("--stem", required=True, help="archive stem, e.g. 'LilexSansSCNFM'")
    ap.add_argument("--version", required=True, help="release version, e.g. '0.1.0'")
    ap.add_argument("--out", required=True, type=Path, help="directory to write the zip into")
    ap.add_argument("--readme", type=Path, help="rendered README.txt to include")
    ap.add_argument(
        "--license",
        dest="licenses",
        action="append",
        default=[],
        type=Path,
        help="licence file to include (repeatable)",
    )
    args = ap.parse_args(argv)

    version = args.version.lstrip("v")
    members: list[tuple[str, Path]] = [(f.name, f) for f in args.fonts]
    members += [(f.name, f) for f in args.licenses]
    if args.readme:
        members.append(("README.txt", args.readme))

    dest = args.out / f"{args.stem}-{version}.zip"
    write_zip(dest, members)
    print(dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

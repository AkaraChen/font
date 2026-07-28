"""Nerd Font patch step — one implementation, four families.

Replaces `<family>/scripts/0N-nerd-patch.sh` ×4 (pixel, sans, rounded,
typewriter), which were 130-141 lines each and differed only in the glob used to
find the input fonts.

The docker path is gone. It existed because fontforge was "whatever the
maintainer had installed", so a container was the only way to get a predictable
patcher — but the toolchain is pinned now, `nixpkgs` provides fontforge, and the
derivation this runs inside cannot reach a docker socket anyway. What the old
`NERD_PATCH_METHOD=auto` ladder actually bought was two builds that could differ
silently depending on which runner had docker; that is the failure mode the
fingerprint net exists to catch, so it should not be reachable in the first
place.

Order matters and is the same order the shells used, because the fingerprint
baselines were taken with it:

    font-patcher            icons in, at --single-width-glyphs
    rename_nerd_family      short Windows-safe family, and rename the file
    fix_nerd_widths         PUA icons forced to the half cell
    narrow_symbol_widths    EAW-correct advances     (--narrow-symbols only)
    fix_terminal_metrics    isFixedPitch / PANOSE / xAvgCharWidth

`narrow_symbol_widths` runs for sans / rounded / typewriter and not for pixel,
which is the one real difference between the four scripts.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from fontkit import fix_nerd_widths, fix_terminal_metrics, narrow_symbol_widths, rename_nerd_family

FONT_SUFFIXES = (".ttf", ".otf")

# --complete   the whole icon set
# --single-width-glyphs   icons occupy one half cell
# --careful    never overwrite a glyph the base font already has
# --makegroups 1   patcher's own name-mangling ruleset, pinned so a patcher
#                  upgrade shows up as a fingerprint diff rather than silently
#
# Never --mono / -s: those force *every* glyph to one cell, which would collapse
# the CJK half of a dual-width font.
PATCH_ARGS = [
    "--complete",
    "--single-width-glyphs",
    "--careful",
    "--makegroups",
    "1",
    "--quiet",
]


def patched_fonts(out_dir: Path) -> list[Path]:
    return sorted(p for p in out_dir.iterdir() if p.suffix in FONT_SUFFIXES)


def run_patcher(patcher_dir: Path, font: Path, out_dir: Path) -> None:
    script = patcher_dir / "font-patcher"
    if not script.is_file():
        raise SystemExit(f"error: {script} does not exist")
    fontforge = shutil.which("fontforge")
    if fontforge is None:
        raise SystemExit(
            "error: fontforge is not on PATH. It is a build input of this step; "
            "there is no docker fallback any more."
        )

    # The input is staged into a writable directory first. font-patcher reopens
    # the *source* file read-write near the end of its run to copy head.flags,
    # head.lowestRecPPEM and OS/2.xAvgCharWidth across to the patched output; a
    # read-only path makes that raise, and the patcher swallows it as
    # `ERROR: Can not handle font flags (PermissionError…)` and carries on with
    # those three fields unset. Two of them are in the fingerprint, so a build
    # that patched straight out of the store would look like a real regression.
    with tempfile.TemporaryDirectory(dir=out_dir.parent) as tmp:
        staged = Path(tmp) / font.name
        shutil.copyfile(font, staged)
        staged.chmod(0o644)
        subprocess.run(
            [
                fontforge,
                "-script",
                str(script),
                str(staged),
                "--glyphdir",
                f"{patcher_dir / 'src' / 'glyphs'}/",
                "--outputdir",
                str(out_dir),
                *PATCH_ARGS,
            ],
            check=True,
        )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fonts", nargs="+", type=Path, help="base fonts to patch")
    ap.add_argument("--patcher", required=True, type=Path, help="unpacked FontPatcher directory")
    ap.add_argument("--out", required=True, type=Path, help="directory to write patched fonts to")
    ap.add_argument("--family", required=True, help="short family name, e.g. 'LilexSansSC NFM'")
    ap.add_argument("--family-ps", required=True, help="PostScript family, e.g. 'LilexSansSCNFM'")
    ap.add_argument(
        "--narrow-symbols",
        action="store_true",
        help="run narrow_symbol_widths (EAW fit) after the PUA pass — sans / rounded / typewriter",
    )
    args = ap.parse_args(argv)

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    for font in sorted(args.fonts):
        print(f"==> patching {font.name}", file=sys.stderr)
        run_patcher(args.patcher, font, out_dir)

    fonts = patched_fonts(out_dir)
    if not fonts:
        raise SystemExit(f"error: font-patcher produced nothing under {out_dir}")

    print(f"==> shorten Nerd family names → {args.family}", file=sys.stderr)
    rename_nerd_family.main(
        ["--family", args.family, "--family-ps", args.family_ps, "--rename-file", *map(str, fonts)]
    )

    # rename_nerd_family --rename-file moves the files, so re-read the directory.
    fonts = patched_fonts(out_dir)

    print("==> fix Nerd/PUA icon advances → half-cell", file=sys.stderr)
    fix_nerd_widths.main(list(map(str, fonts)))

    if args.narrow_symbols:
        print("==> narrow/widen symbols to match East_Asian_Width", file=sys.stderr)
        narrow_symbol_widths.main(["--no-donor", *map(str, fonts)])

    # Last, always: every pass above saves the font again, and FontForge (plus
    # our own narrow pass) clears the mono flags on the way out.
    print("==> fix terminal metrics", file=sys.stderr)
    fix_terminal_metrics.main(list(map(str, fonts)))

    for font in patched_fonts(out_dir):
        print(f"    {font.name}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

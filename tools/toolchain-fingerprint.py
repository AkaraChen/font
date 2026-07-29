#!/usr/bin/env python3
"""Print the one table both platforms have to agree on (KIT-297).

`fingerprints/` says the baselines belong to CI because a darwin build does not
reproduce a `x86_64-linux` one. That was true and unexplained for a long time,
and the reason it stayed unexplained is that nobody could put the two
toolchains side by side: the build logs printed `fontTools 4.60.1` on both and
stopped there.

This prints everything that could plausibly make two runs of the *same pinned
code* disagree, in a form that diffs:

  identity     platform, machine, libc, python, package versions
  accelerators whether fontTools' Cython modules are compiled (.so) or pure
               Python — two different implementations of cu2qu would explain
               everything, so it has to be ruled in or out first
  libm         the arithmetic the build actually performs. Pure-Python float
               ops are IEEE-754 and bit-identical everywhere; libm functions
               are *not* required to be correctly rounded and are the only way
               a pure-Python step can differ across platforms.
  steps        the two build steps that consume libm, run on synthetic input:
               the CJK shear (`math.tan`) and a skia-pathops stroke.

Run it on both sides and diff:

    just toolchain-fingerprint > darwin.txt
    # CI prints the same table in the "Toolchain fingerprint" step

Every line is `key<TAB>value`, sorted within its section, so `diff` output
names the thing that differs rather than reflowing.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import platform
import struct
import sys
from decimal import Decimal, getcontext

# The fontTools modules that ship a Cython twin. If a platform compiled these
# and the other did not, the two are running different implementations of the
# same algorithm and no amount of pinning makes their output agree.
ACCELERATED = [
    "fontTools.cu2qu.cu2qu",
    "fontTools.qu2cu.qu2cu",
    "fontTools.pens.momentsPen",
    "fontTools.varLib.iup",
    "fontTools.misc.bezierTools",
]

# Angles the repo actually shears at, plus neighbours so a table stays useful
# when a calibration changes. handwriting is the only family with a non-zero
# slant, and it is also the only family whose `embolden = 0` weights drift.
SLANT_DEGREES = [0.0, 6.0, 7.5, 9.0, 12.0]


def _hex(value: float) -> str:
    """Exact double, no decimal rounding in the way."""
    return struct.pack(">d", value).hex()


def _digest(lines: list[str]) -> str:
    h = hashlib.sha256()
    for line in lines:
        h.update(line.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _correctly_rounded_hypot(x: float, y: float) -> float:
    """hypot computed at 60 significant digits, then rounded once."""
    return float((Decimal(x) ** 2 + Decimal(y) ** 2).sqrt())


# --------------------------------------------------------------------------- #
# sections
# --------------------------------------------------------------------------- #

def section_identity(out: list[str]) -> None:
    out.append("[identity]")
    out.append(f"platform.system\t{platform.system()}")
    out.append(f"platform.machine\t{platform.machine()}")
    out.append(f"platform.libc\t{'-'.join(p for p in platform.libc_ver() if p) or 'none'}")
    out.append(f"sys.platform\t{sys.platform}")
    out.append(f"python.version\t{platform.python_version()}")
    out.append(f"python.implementation\t{platform.python_implementation()}")
    out.append(f"float.repr_style\t{sys.float_repr_style}")

    for module, attr in (
        ("fontTools", "version"),
        ("pathops", "__version__"),
    ):
        try:
            mod = __import__(module)
            out.append(f"{module}.version\t{getattr(mod, attr, 'unknown')}")
        except ImportError:
            out.append(f"{module}.version\tMISSING")


def section_accelerators(out: list[str]) -> None:
    """Compiled or interpreted, per module.

    Read this first when a digest goes red. nixpkgs builds fontTools without
    Cython on every platform (no `cython` in nativeBuildInputs, no
    FONTTOOLS_WITH_CYTHON), so the expected answer is `py` on both sides and a
    `so` anywhere is a finding, not a detail.
    """
    out.append("[accelerators]")
    for name in ACCELERATED:
        try:
            module = __import__(name, fromlist=["__file__"])
        except ImportError:
            out.append(f"{name}\tMISSING")
            continue
        path = getattr(module, "__file__", "") or ""
        kind = "so" if path.endswith((".so", ".pyd", ".dylib")) else "py"
        compiled = getattr(module, "COMPILED", None)
        out.append(f"{name}\t{kind}\tCOMPILED={compiled}")


def section_libm(out: list[str]) -> None:
    """Where a pure-Python build step can still disagree with itself.

    `tan` and `radians` are what `fontkit.prepare_cjk.shear_font` calls once
    per font; `abs(complex)` is `hypot`, which is what cu2qu calls on every
    curve it considers splitting. Neither is required by IEEE-754 to be
    correctly rounded, and implementations differ by design.
    """
    out.append("[libm]")

    for deg in SLANT_DEGREES:
        rad = math.radians(deg)
        tan = math.tan(rad)
        out.append(f"radians({deg:g})\t{_hex(rad)}")
        out.append(f"tan(radians({deg:g}))\t{_hex(tan)}")
        # What the shear actually writes: the caret slope run is the one
        # scalar in the product that is a bare function of tan.
        out.append(f"caretSlopeRun({deg:g})\t{int(round(tan * 1000))}")

    for fn in ("sin", "cos", "sqrt", "atan", "log", "exp"):
        value = getattr(math, fn)(0.7)
        out.append(f"{fn}(0.7)\t{_hex(value)}")

    out.append(f"hypot(3.7,4.9)\t{_hex(math.hypot(3.7, 4.9))}")
    out.append(f"abs(complex(3.7,4.9))\t{_hex(abs(complex(3.7, 4.9)))}")


def section_libm_quality(out: list[str], samples: int) -> None:
    """How far this platform's hypot is from correctly rounded.

    A deterministic LCG walks the same inputs everywhere, so the counts are
    comparable. `abs(complex)` is CPython's `_Py_c_abs`, i.e. the platform
    `hypot`; cu2qu compares its result against a tolerance, so a 1-ULP
    disagreement is a branch that can flip.
    """
    out.append("[libm-quality]")
    state = 0x2545F4914F6CDD1D
    off = 0
    worst = 0.0
    checked = 0
    for _ in range(samples):
        state = (state * 6364136223846793005 + 1442695040888963407) & ((1 << 64) - 1)
        x = ((state >> 11) / float(1 << 53)) * 4000.0 - 2000.0
        state = (state * 6364136223846793005 + 1442695040888963407) & ((1 << 64) - 1)
        y = ((state >> 11) / float(1 << 53)) * 4000.0 - 2000.0
        if x == 0.0 and y == 0.0:
            continue
        checked += 1
        got = abs(complex(x, y))
        want = _correctly_rounded_hypot(x, y)
        if got != want:
            off += 1
            ulp = math.ulp(want)
            if ulp:
                worst = max(worst, abs(got - want) / ulp)
    out.append(f"hypot.samples\t{checked}")
    out.append(f"hypot.not_correctly_rounded\t{off}")
    out.append(f"hypot.not_correctly_rounded_pct\t{100.0 * off / checked:.4f}")
    out.append(f"hypot.worst_ulp\t{worst:.2f}")


def section_shear(out: list[str]) -> None:
    """The CJK shear, on synthetic coordinates.

    `shear_font` is `int(round(x + tan·(y − pivot)))` per point. It is pure
    Python apart from `tan`, so this reproduces the *entire* arithmetic of the
    step: if this digest differs across two platforms, so does every
    handwriting product, and no font is needed to prove it.
    """
    out.append("[shear]")
    pivot = 375.0
    for deg in SLANT_DEGREES:
        if deg == 0.0:
            continue
        tan = math.tan(math.radians(deg))
        moved = 0
        rows = []
        # A dense lattice over a 1000-UPM em, which is the coordinate range the
        # imported Han glyphs actually occupy.
        for y in range(-250, 1001, 1):
            for x in range(0, 1001, 7):
                exact = x + tan * (y - pivot)
                rows.append(f"{x},{y},{int(round(exact))}")
                # How many points land close enough to a .5 boundary that one
                # ULP of `tan` decides which way they round.
                frac = abs(exact - math.floor(exact) - 0.5)
                if frac < 1e-9:
                    moved += 1
        out.append(f"shear({deg:g}).digest\t{_digest(rows)}")
        out.append(f"shear({deg:g}).points\t{len(rows)}")
        out.append(f"shear({deg:g}).on_rounding_boundary\t{moved}")


def section_pathops(out: list[str]) -> None:
    """skia-pathops, on a synthetic contour.

    Unlike the shear this is compiled C++: Skia is built for the host
    architecture, so its float behaviour is a property of the *build*, not of
    the Python above it. `fontkit.embolden` strokes and unions exactly like
    this, at the strengths the four emboldening families calibrate.
    """
    out.append("[pathops]")
    try:
        import pathops
        from pathops import OpBuilder, PathOp
    except ImportError:
        out.append("pathops\tMISSING")
        return

    def build() -> "pathops.Path":
        path = pathops.Path()
        pen = path.getPen()
        # A closed shape with both straight and curved segments, at CJK scale.
        pen.moveTo((100, 100))
        pen.lineTo((900, 120))
        pen.curveTo((940, 400), (700, 700), (500, 880))
        pen.qCurveTo((220, 760), (120, 420))
        pen.closePath()
        return path

    for strength in (4.0, 5.0, 8.0, 10.0, 15.0, 20.0, 32.0):
        path = build()
        path.convertConicsToQuads()
        stroked = pathops.Path(path)
        stroked.stroke(strength * 2.0, pathops.LineCap.ROUND_CAP,
                       pathops.LineJoin.ROUND_JOIN, 4.0)
        stroked.convertConicsToQuads()
        builder = OpBuilder(fix_winding=True)
        builder.add(path, PathOp.UNION)
        builder.add(stroked, PathOp.UNION)
        result = builder.resolve()
        result.convertConicsToQuads()

        points: list[str] = []
        for verb, pts in result:
            points.append(str(verb) + ":" + ";".join(
                f"{_hex(float(px))},{_hex(float(py))}" for px, py in pts
            ))
        out.append(f"embolden({strength:g}).digest\t{_digest(points)}")
        out.append(f"embolden({strength:g}).segments\t{len(points)}")


def section_cu2qu(out: list[str]) -> None:
    """cu2qu on synthetic cubics.

    Pure Python under nixpkgs (see [accelerators]), and pure-Python float
    arithmetic is bit-identical across platforms — except that cu2qu decides
    how many times to split a curve by comparing `abs(complex)` against a
    tolerance, and `abs(complex)` is the platform `hypot`.
    """
    out.append("[cu2qu]")
    try:
        from fontTools.cu2qu import curve_to_quadratic
    except ImportError:
        out.append("cu2qu\tMISSING")
        return

    state = 0x9E3779B97F4A7C15
    rows: list[str] = []
    splits = 0
    for _ in range(4000):
        pts = []
        for _ in range(4):
            state = (state * 6364136223846793005 + 1442695040888963407) & ((1 << 64) - 1)
            px = ((state >> 11) / float(1 << 53)) * 1000.0
            state = (state * 6364136223846793005 + 1442695040888963407) & ((1 << 64) - 1)
            py = ((state >> 11) / float(1 << 53)) * 1000.0
            pts.append((px, py))
        quads = curve_to_quadratic(pts, 0.5)
        splits += len(quads) - 2
        rows.append(";".join(f"{_hex(qx)},{_hex(qy)}" for qx, qy in quads))
    out.append(f"curve_to_quadratic.digest\t{_digest(rows)}")
    out.append(f"curve_to_quadratic.curves\t{len(rows)}")
    out.append(f"curve_to_quadratic.total_splits\t{splits}")


SECTIONS = {
    "identity": lambda out, args: section_identity(out),
    "accelerators": lambda out, args: section_accelerators(out),
    "libm": lambda out, args: section_libm(out),
    "libm-quality": lambda out, args: section_libm_quality(out, args.hypot_samples),
    "shear": lambda out, args: section_shear(out),
    "cu2qu": lambda out, args: section_cu2qu(out),
    "pathops": lambda out, args: section_pathops(out),
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "--only", action="append", choices=sorted(SECTIONS),
        help="run one section (repeatable); default is all of them",
    )
    ap.add_argument(
        "--hypot-samples", type=int, default=50000,
        help="how many random pairs the libm-quality section checks",
    )
    args = ap.parse_args(argv)

    wanted = args.only or list(SECTIONS)
    out: list[str] = ["akr-fonts toolchain fingerprint v1"]
    for name in SECTIONS:
        if name in wanted:
            SECTIONS[name](out, args)
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# The derivation-granularity contract.
#
# Caching in this repo is decided here and nowhere else. Nix caches per
# derivation, so what a derivation is *allowed to see* is exactly what makes it
# rebuild. One derivation per family would make every sharing opportunity
# vanish; one per step, with the axes each step actually depends on, is what
# lets sc/tc/hk/jp/kr share a single Latin build.
#
# The two claims worth the whole phase:
#
#   latin-prepared has no `region` axis    → prepared once for all five regions
#   cjk-prepared   has no `profile` axis   → optical embolden is scene-agnostic,
#                                            so coding and text share it
#
# A comment saying that would rot. `mkStep` enforces it: passing `region` to a
# latin-prepared step is an eval error, not a silently wider cache key. Phase 3
# (KIT-277) builds the real derivations on top of this; Phase 1 fixes the shape
# and the tests so Phase 3 cannot quietly widen a key.
{ lib }:

let
  # Declaration order is name order, so a name is stable and greppable.
  axisOrder = [
    "family"
    "profile"
    "region"
    "weight"
    "format"
  ];

  steps = {
    # Raw upstream bytes. Identical in every region — sc/tc/hk/jp/kr ask for the
    # same Latin file — but NOT in every scene, which the note here used to
    # claim. Phase 6 (KIT-281) is where that stopped being true: "no Nerd Font
    # patch in the text profile" is not an un-patch step, it is a different
    # upstream file. handwriting's coding faces come from Monaspace's
    # pre-patched `MonaspaceRadonNF-*` and its text faces from the plain
    # `MonaspaceRadon-*` in the same release.
    #
    # Modelling that as an axis rather than letting the two share a derivation
    # name is the point of this file: two different upstream files under one
    # name is a graph nobody can bisect.
    src-latin = {
      axes = [
        "family"
        "profile"
        "weight"
      ];
      note = "upstream Latin face for one scene; shared across every region";
    };

    # CJK source does vary by region: sc/tc/hk/jp/kr are different masters or
    # different subsets, so region is a real input here.
    src-cjk = {
      axes = [
        "family"
        "region"
        "weight"
      ];
      note = "upstream CJK master for one region";
    };

    # ★ No region axis. Latin scaling / narrowing / feature work depends on the
    # product grid, which is a profile property — a Simplified build and a
    # Japanese build ask for byte-identical Latin.
    latin-prepared = {
      axes = [
        "family"
        "profile"
        "weight"
      ];
      note = "scaled + gridded Latin; shared across all regions";
    };

    # ★ No profile axis. Optical stroke matching is about ink weight, which does
    # not change because the font is used for prose instead of code.
    cjk-prepared = {
      axes = [
        "family"
        "region"
        "weight"
      ];
      note = "embolden / UPM-normalised CJK; shared across profiles";
    };

    # The first step that genuinely needs the full cross product.
    merged = {
      axes = [
        "family"
        "profile"
        "region"
        "weight"
      ];
      note = "latin-prepared x cjk-prepared";
    };

    # Nerd patching only exists in the coding profile, so `profile` is not an
    # axis: a text-profile nerd derivation is a bug, not a cache miss.
    nerd = {
      axes = [
        "family"
        "region"
        "weight"
      ];
      note = "Nerd Fonts patch; coding profile only";
    };

    packaged = {
      axes = [
        "family"
        "profile"
        "region"
        "weight"
        "format"
      ];
      note = "TTF / WOFF2 / OTF product";
    };
  };

  known = lib.attrNames steps;

  orderedAxes =
    step:
    let
      declared = steps.${step}.axes;
      unknown = lib.subtractLists axisOrder declared;
    in
    assert lib.assertMsg (unknown == [ ]) "granularity: ${step} declares unknown axes: ${
      lib.concatStringsSep ", " unknown
    }";
    lib.filter (a: lib.elem a declared) axisOrder;

  # Restrict an argument set to a step's declared axes, refusing anything else.
  #
  # This is the enforcement point. `filterAttrs` would have been the convenient
  # choice and would have been wrong: silently dropping `region` from a
  # latin-prepared call gives the right cache key by accident while the caller
  # goes on believing it built a per-region Latin. Erroring makes the caller fix
  # the graph.
  scope =
    step: args:
    let
      declared = steps.${step}.axes or (throw "granularity: unknown step ${step}, expected one of ${
        lib.concatStringsSep ", " known
      }");
      extra = lib.subtractLists declared (lib.attrNames args);
      missing = lib.subtractLists (lib.attrNames args) declared;
    in
    assert lib.assertMsg (extra == [ ])
      (
        "granularity: ${step} may not depend on ${lib.concatStringsSep ", " extra} "
        + "— widening its cache key would ${
        if lib.elem "region" extra then
          "rebuild it once per region"
        else if lib.elem "profile" extra then
          "rebuild it once per profile"
        else
          "cost sharing"
      }. Declared axes: ${lib.concatStringsSep ", " declared}."
      );
    assert lib.assertMsg (missing == [ ]) "granularity: ${step} needs ${
      lib.concatStringsSep ", " missing
    }";
    args;

  # `src-cjk-sans-tc-Bold`, `latin-prepared-sans-coding-Bold`, …
  mkName =
    step: args:
    let
      scoped = scope step args;
    in
    lib.concatStringsSep "-" ([ step ] ++ map (a: scoped.${a}) (orderedAxes step));

in
{
  inherit
    axisOrder
    steps
    known
    mkName
    scope
    ;

  # Phase 3 entry point: build a derivation whose name and whose visible
  # parameters both come from the contract.
  #
  #   mkStep pkgs "latin-prepared" { family = "sans"; profile = "coding";
  #                                  weight = "Bold"; } { … drvArgs … }
  mkStep =
    pkgs: step: axes: drvArgs:
    pkgs.stdenvNoCC.mkDerivation (
      drvArgs
      // {
        name = mkName step axes;
        passthru = (drvArgs.passthru or { }) // {
          fontkitStep = step;
          fontkitAxes = scope step axes;
        };
      }
    );
}

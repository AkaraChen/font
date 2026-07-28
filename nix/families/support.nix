# Shared scaffolding for the per-step family derivations.
#
# Phase 1 fixed the granularity contract (nix/granularity.nix) and the pinned
# sources (nix/sources). This is the layer that turns them into actual build
# steps, replacing the ~2900 lines of shell orchestration the six families
# carried between them.
#
# Three things live here because every family needs them identically:
#
#   pythonEnv   the interpreter the steps run on. `common.sh`'s `ensure_python`
#               — 30 lines of "uv, or venv, or pip, or die" per family — is
#               exactly this attribute now.
#   patcher     FontPatcher.zip unpacked once. Five families patched with it and
#               each unzipped its own copy into <family>/work/.
#   step        granularity.mkStep with the defaults every step wants.
{ pkgs
, lib
, granularity
, sources
, fontkit
, root
,
}:

let
  # fontTools + skia-pathops + fontkit, and nothing else. The devShell carries
  # more (Pillow, uharfbuzz, numpy) because the diagnostics under tools/ need
  # them; a build step that imported one of those would be reaching outside the
  # build vocabulary, so it is not in scope here and fails loudly if it tries.
  pythonEnv = pkgs.python3.withPackages (ps: [
    ps.fonttools
    ps.skia-pathops
    fontkit
  ]);

  # verify-features.py shapes text to prove the ligatures actually fire. It used
  # to print "uharfbuzz not installed — ligature shaping gate skipped" and pass,
  # which is a gate that reports green for the one thing it exists to check.
  verifyEnv = pkgs.python3.withPackages (ps: [
    ps.fonttools
    ps.skia-pathops
    ps.uharfbuzz
    fontkit
  ]);

  patcher = pkgs.runCommand "font-patcher-unpacked"
    {
      nativeBuildInputs = [ pkgs.unzip ];
    }
    ''
      mkdir -p $out
      unzip -q ${sources.fontPatcher} -d $out
      test -f $out/font-patcher
    '';

  # Every family builds the coding profile of the Simplified master. Phase 6
  # adds `text`, Phase 7 adds the other regions; both arrive as more values for
  # these two names rather than as more steps.
  profile = "coding";
  region = "sc";

  # granularity.mkStep, plus the defaults a font build step always wants.
  #
  # SOURCE_DATE_EPOCH is set to 0 rather than left at the stdenv default
  # (315532800). fontTools writes head.modified from it, and the devShell — the
  # side the fingerprint baselines were taken on — sets 0. The fingerprint
  # deliberately drops head.modified, so this changes no baseline; it is here so
  # that products built inside and outside the sandbox stay byte-comparable when
  # someone reaches for sha256 anyway.
  step =
    name: axes: args:
    granularity.mkStep pkgs name axes (
      {
        dontUnpack = true;
        SOURCE_DATE_EPOCH = "0";
      }
      // args
      // {
        nativeBuildInputs = [ pythonEnv ] ++ (args.nativeBuildInputs or [ ]);
      }
    );

  # `fontkit embolden --strength 0` is not a no-op: the pathops round-trip
  # rewrites every outline whatever the strength, so a family that pins 0
  # (rounded — Resource Han Rounded ships a real Bold) must copy the master
  # instead. The shells branched on this with `awk "BEGIN{exit !(s > 0)}"`;
  # the answer is fixed at pin time, so it belongs in eval.
  emboldenOrCopy =
    { strength, src, dst }:
    if strength == "0" || strength == "0.0" then
      "cp ${src} ${dst}"
    else
      "fontkit embolden ${src} ${dst} --strength ${strength}";

  # A file from the working tree as a build input. Single files, never the whole
  # checkout: a step that took `root` would rebuild when any family's README
  # changed, which is the cache key mistake nix/granularity.nix exists to stop.
  file = path: root + "/${path}";

in
{
  inherit
    pythonEnv
    verifyEnv
    patcher
    profile
    region
    step
    file
    emboldenOrCopy
    ;

  inherit (pkgs) fontforge;
}

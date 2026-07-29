# fontkit — lib/ packaged for the Nix python environment.
#
# The devShell gets this so `fontkit <step>` works from a bare shell, and the
# per-step derivations depend on it rather than on a repo checkout.
#
# It also installs the `fontkit` console script (lib/pyproject.toml), which is
# how every build step is invoked. The `python3 -m fontkit.<module>` form still
# works and is what the unit tests call, but nothing in the build uses it any
# more — serif was the last caller and its shell pipeline is gone (KIT-280).
{ lib
, buildPythonPackage
, setuptools
, fonttools
, pydantic
, skia-pathops
, brotli
, cffsubr
, pytestCheckHook
}:

let
  families = [ "casual" "handwriting" "pixel" "rounded" "sans" "serif" "typewriter" ];
in
buildPythonPackage {
  pname = "fontkit";
  version = "0.1.0";
  pyproject = true;

  # Unit tests live under lib/, while manifest integration tests intentionally
  # read the seven repo-level font.toml files. Include exactly those fixtures;
  # sourceRoot keeps packaging rooted at lib/ and avoids making README changes
  # invalidate the fontkit derivation.
  src = lib.fileset.toSource {
    root = ../.;
    fileset = lib.fileset.unions (
      [ ../lib ]
      ++ map (family: ../. + "/${family}/font.toml") families
    );
  };
  sourceRoot = "source/lib";

  build-system = [ setuptools ];

  dependencies = [
    fonttools
    pydantic
    skia-pathops
    # fontTools writes a WOFF2 through brotli, and `fontkit convert` is a build
    # step: the narrow build interpreter (nix/families/support.nix) has to be
    # able to run it without reaching for the devShell's wider set.
    brotli
    # …and the OTF conversion subroutinizes the CFF through AFDKO's `tx`, which
    # is what cffsubr wraps. A hard dependency rather than a soft import: an
    # un-subroutinized CFF is a different file with a different fingerprint, so
    # "whether tx was on PATH" must not be an input to the build (KIT-283).
    cffsubr
  ];

  nativeCheckInputs = [ pytestCheckHook ];
  # tests/ lives next to the package; font.toml fixtures are one directory up.
  pytestFlagsArray = [ "tests" ];
  # test_cache_keys.py loads repo-level tools/sources-cache-key.py etc., which
  # are not in this package's fileset (only lib/ + font.toml). Full-checkout
  # `pytest lib/tests` still runs them; package checkPhase must not.
  disabledTestPaths = [ "tests/test_cache_keys.py" ];

  pythonImportsCheck = [
    "fontkit"
    "fontkit.cli"
    "fontkit.nerd_patch"
    "fontkit.package"
    "fontkit.prepare_cjk"
    "fontkit.scale_upem"
    "fontkit.merge"
    "fontkit.expand_ligatures"
    "fontkit.fix_nerd_widths"
    "fontkit.fix_terminal_metrics"
    "fontkit.narrow_symbol_widths"
    "fontkit.rename_nerd_family"
    "fontkit.verify2to1"
    "fontkit.verify_text"
    "fontkit.verify_formats"
    "fontkit.convert"
    "fontkit.release_notes"
    "fontkit.embolden"
    "fontkit.measure"
    "fontkit.manifest"
  ];

  meta = {
    description = "Shared build steps for the AKR font families";
    license = lib.licenses.mit;
  };
}

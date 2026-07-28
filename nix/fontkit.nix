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
  ];

  nativeCheckInputs = [ pytestCheckHook ];
  # tests/ lives next to the package; font.toml fixtures are one directory up.
  pytestFlagsArray = [ "tests" ];

  pythonImportsCheck = [
    "fontkit"
    "fontkit.cli"
    "fontkit.nerd_patch"
    "fontkit.package"
    "fontkit.prepare_cjk"
    "fontkit.scale_upem"
    "fontkit.merge_radon_wenkai"
    "fontkit.expand_ligatures"
    "fontkit.fix_nerd_widths"
    "fontkit.fix_terminal_metrics"
    "fontkit.narrow_symbol_widths"
    "fontkit.rename_nerd_family"
    "fontkit.verify2to1"
    "fontkit.embolden"
    "fontkit.measure"
    "fontkit.manifest"
  ];

  meta = {
    description = "Shared build steps for the AKR font families";
    license = lib.licenses.mit;
  };
}

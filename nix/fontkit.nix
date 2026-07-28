# fontkit — lib/ packaged for the Nix python environment.
#
# The devShell gets this so `python3 -m fontkit.<step>` works from a bare shell,
# and the per-step derivations Phase 1 introduces can depend on it without
# needing the repo checkout on PYTHONPATH.
#
# Note the build steps still prefer the working copy: <family>/scripts/common.sh
# prepends lib/ to PYTHONPATH, so an edit is live without a rebuild and CI
# always gates the code that is actually committed.
{ lib
, buildPythonPackage
, setuptools
, fonttools
, skia-pathops
, pytestCheckHook
}:

buildPythonPackage {
  pname = "fontkit";
  version = "0.1.0";
  pyproject = true;

  src = lib.cleanSource ../lib;

  build-system = [ setuptools ];

  dependencies = [
    fonttools
    skia-pathops
  ];

  nativeCheckInputs = [ pytestCheckHook ];
  # tests/ lives next to the package inside lib/, so it ships in src and runs here.
  pytestFlagsArray = [ "tests" ];

  pythonImportsCheck = [
    "fontkit"
    "fontkit.fix_nerd_widths"
    "fontkit.fix_terminal_metrics"
    "fontkit.narrow_symbol_widths"
    "fontkit.rename_nerd_family"
    "fontkit.verify2to1"
    "fontkit.embolden"
    "fontkit.measure"
  ];

  meta = {
    description = "Shared build steps for the AKR font families";
    license = lib.licenses.mit;
  };
}

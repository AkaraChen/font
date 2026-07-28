# fontkit — lib/ packaged for the Nix python environment.
#
# The devShell gets this so `fontkit <step>` works from a bare shell, and the
# per-step derivations depend on it rather than on a repo checkout.
#
# It also installs the `fontkit` console script (lib/pyproject.toml), which is
# how every build step is invoked. serif is the last caller of the
# `python3 -m fontkit.<module>` form, via its own common.sh.
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
    "fontkit.cli"
    "fontkit.nerd_patch"
    "fontkit.package"
    "fontkit.prepare_cjk"
    "fontkit.merge_radon_wenkai"
    "fontkit.expand_ligatures"
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

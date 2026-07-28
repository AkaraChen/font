"""`fontkit <step>` is what the derivations call, so its dispatch table is load-bearing.

A typo in `STEPS` would not fail evaluation and would not fail the build until a
family's step ran, hours in — and only for that family. Cheap to pin here.
"""

from __future__ import annotations

import importlib

import pytest

from fontkit import cli


@pytest.mark.parametrize("step", sorted(cli.STEPS))
def test_every_step_resolves_to_a_module_with_main(step):
    module = importlib.import_module(f"fontkit.{cli.STEPS[step]}")
    assert callable(module.main)


@pytest.mark.parametrize("step", sorted(cli.STEPS))
def test_every_step_accepts_an_argv_list(step):
    """`main()` reading sys.argv instead of its argument would make the CLI
    dispatch silently parse the *wrapper's* arguments."""
    module = importlib.import_module(f"fontkit.{cli.STEPS[step]}")
    with pytest.raises(SystemExit) as excinfo:
        module.main(["--help"])
    assert excinfo.value.code == 0


def test_unknown_step_is_an_error_not_a_traceback():
    assert cli.main(["no-such-step"]) == 2


def test_bare_invocation_is_an_error():
    assert cli.main([]) == 2

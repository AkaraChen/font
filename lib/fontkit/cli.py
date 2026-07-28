"""`fontkit <step> …` — the one entry point every build step goes through.

Before Phase 3 a build step was a shell script that sourced a 104-line
`common.sh` to work out which interpreter to use, then ran
`"${PY}" -m fontkit.<step>`. The interpreter question is answered by the
derivation now, so what is left is a dispatch table.

Each subcommand is the module's own `main(argv)` — this file adds no arguments
and parses none of its own, so `fontkit merge --help` is exactly
`python3 -m fontkit.merge --help`. Both spellings keep working;
the module form is what the unit tests call.
"""

from __future__ import annotations

import importlib
import sys

# subcommand -> module under fontkit.
#
# Names are the build vocabulary (`prepare-cjk`, `nerd-patch`), not the module
# names, which still carry the family they were extracted from.
STEPS = {
    "embolden": "embolden",
    "scale-upem": "scale_upem",
    "prepare-cjk": "prepare_cjk",
    "merge": "merge",
    "expand-ligatures": "expand_ligatures",
    "nerd-patch": "nerd_patch",
    "rename-nerd-family": "rename_nerd_family",
    "fix-nerd-widths": "fix_nerd_widths",
    "narrow-symbol-widths": "narrow_symbol_widths",
    "fix-terminal-metrics": "fix_terminal_metrics",
    "verify-2to1": "verify2to1",
    "measure": "measure",
    "manifest": "manifest",
    "package": "package",
}


def usage() -> str:
    width = max(len(name) for name in STEPS)
    lines = ["usage: fontkit <step> [args…]", "", "steps:"]
    lines += [f"  {name:<{width}}  fontkit.{module}" for name, module in sorted(STEPS.items())]
    lines += ["", "`fontkit <step> --help` for a step's own arguments."]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(usage())
        return 0 if argv else 2
    step, rest = argv[0], argv[1:]
    if step not in STEPS:
        print(f"fontkit: unknown step {step!r}\n", file=sys.stderr)
        print(usage(), file=sys.stderr)
        return 2
    module = importlib.import_module(f"fontkit.{STEPS[step]}")
    return module.main(rest) or 0


if __name__ == "__main__":
    raise SystemExit(main())

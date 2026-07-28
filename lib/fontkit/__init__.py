"""fontkit — the build steps every family in this repo shares.

Before this package the same five scripts lived in four or five copies under
`<family>/scripts/`, byte-identical in most families and quietly drifted in
serif and pixel. A fix landed in one copy and the other three kept the bug.

The modules here are run as `python3 -m fontkit.<module>`, both from the family
build steps and by hand. Where a family genuinely needs different behaviour
(serif's Sarasa sources are dual-width from upstream; the other families reach
2:1 by merging), that difference is a documented flag, not a forked file.
"""

__all__ = [
    "embolden",
    "fix_nerd_widths",
    "fix_terminal_metrics",
    "measure",
    "narrow_symbol_widths",
    "rename_nerd_family",
    "verify2to1",
]

__version__ = "0.1.0"

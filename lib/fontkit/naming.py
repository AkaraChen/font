"""The product name vocabulary, in one place.

Two things live here because the merge engine, the Nerd rename step and the
manifest validator all need the same answers and must not drift:

* **Composition** — a product name is `AKR <Style> <Region> <Variant>`, built
  from segments rather than written out once per region. Five regions times
  seven families is thirty-five literal family names nobody could keep in sync;
  the segments are the source of truth and the string is derived.

* **The RIBBI split** — which of that name goes in name ID 1 and what name ID 2
  is allowed to say. Windows' name ID 2 recognises exactly four values, so a
  three-weight family cannot put `Light` there: the weight moves into ID 1 and
  ID 2 falls back to `Regular`. ID 16/17 carry the real grouping.

Nothing here reads a manifest — `fontkit.manifest` owns that and calls in.
"""

from __future__ import annotations

import re

# Windows' font menu groups by name ID 1 and only understands these four values
# in name ID 2. Everything else has to be expressed through ID 16/17.
RIBBI = ("Regular", "Bold", "Italic", "Bold Italic")

# GDI truncates a longer name ID 1, and the truncated string is what the user
# then has to type into a config file.
WINDOWS_FAMILY_LIMIT = 31


def compose(house: str, style: str, region: str, variant: str) -> str:
    """`AKR` + `Sans` + `sc` + `NFM` → ``AKR Sans SC NFM``."""
    parts = [house, style, region.upper(), variant]
    return " ".join(part for part in parts if part)


def postscript(family: str) -> str:
    """The PostScript spelling of a family name: no spaces, no punctuation."""
    return re.sub(r"[^A-Za-z0-9]", "", family)


def ribbi_split(subfamily: str) -> tuple[str, str]:
    """Split a product subfamily into (name ID 1 suffix, name ID 2 value).

    ``Light`` is the case that matters:

        Light        → ("Light", "Regular")       ID1 "<family> Light"
        Regular      → ("",      "Regular")       ID1 "<family>"
        Bold         → ("",      "Bold")          ID1 "<family>"
        Light Italic → ("Light", "Italic")
        Bold Italic  → ("",      "Bold Italic")

    A weight that is not Regular or Bold becomes part of the legacy family name
    and hands ID 2 back the RIBBI value its slope alone implies. That is the
    standard three-weight arrangement: consumers that read only ID 1/2 (the GDI
    path, some installers) see two separate two-style families, and consumers
    that read ID 16/17 see one family with three weights.
    """
    parts = subfamily.split()
    italic = bool(parts) and parts[-1] == "Italic"
    weight = " ".join(parts[:-1]) if italic else subfamily

    if weight in ("", "Regular"):
        return "", ("Italic" if italic else "Regular")
    if weight == "Bold":
        return "", ("Bold Italic" if italic else "Bold")
    return weight, ("Italic" if italic else "Regular")


def legacy_family(family: str, subfamily: str) -> str:
    """Name ID 1 for one product — the family plus a non-RIBBI weight."""
    suffix, _ = ribbi_split(subfamily)
    return f"{family} {suffix}" if suffix else family


def full_name(family: str, subfamily: str) -> str:
    """Name ID 4, built from the ID 1 / ID 2 pair so the three agree."""
    id1 = legacy_family(family, subfamily)
    _, id2 = ribbi_split(subfamily)
    return id1 if id2 == "Regular" else f"{id1} {id2}"

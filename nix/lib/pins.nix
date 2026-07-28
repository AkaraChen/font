# Read a family's `pins.env` from Nix.
#
# pins.env is a shell fragment that the family build scripts `source`. Nix reads
# that same file rather than a transcription of it — a second copy of a URL and
# a sha256 is a copy that drifts, and drift between "what the script downloads"
# and "what Nix fetched" is the one failure mode this phase must not introduce.
#
# Phase 4 (KIT-278) replaces pins.env with font.toml. When it lands, this parser
# is the only thing that changes; every caller keeps its attrset interface.
#
# Supported subset — exactly what the seven pins.env files use:
#
#   KEY=bare
#   KEY='single quoted'          (no interpolation, as in sh)
#   KEY="double quoted ${EARLIER_KEY}"
#
# Blank lines and whole-line `#` comments are skipped. Anything else is a hard
# error: a pins.env line Nix cannot read must never be silently dropped, because
# the symptom would be a missing artifact three phases later.
{ lib }:

let
  trim =
    s:
    let
      m = builtins.match "[[:space:]]*(.*[^[:space:]])?[[:space:]]*" s;
      g = if m == null then null else builtins.head m;
    in
    if g == null then "" else g;

  # Expand ${NAME} against the keys parsed so far. Forward references are an
  # error rather than an empty string — sh would silently produce a broken URL.
  expand =
    acc: file: s:
    lib.concatMapStrings
      (
        part:
        if builtins.isList part then
          let
            k = builtins.head part;
          in
            acc.${k} or (throw "pins: ${toString file} references \${${k}} before it is defined")
        else
          part
      )
      # Bracket expressions rather than backslash escapes. `\$` and `\{` are
      # undefined in POSIX ERE, and the two std::regex implementations disagree:
      # this pattern evaluated fine on the maintainer's darwin nix and was
      # rejected outright on the CI runner ("invalid regular expression").
      # `[$]` / `[{]` / `[}]` are unambiguous everywhere.
      (builtins.split "[$][{]([A-Za-z_][A-Za-z0-9_]*)[}]" s);

  parseValue =
    acc: file: raw:
    let
      n = builtins.stringLength raw;
      first = builtins.substring 0 1 raw;
      last = builtins.substring (n - 1) 1 raw;
      inner = builtins.substring 1 (n - 2) raw;
    in
    if n >= 2 && first == "'" && last == "'" then
      inner
    else if n >= 2 && first == "\"" && last == "\"" then
      expand acc file inner
    else
      expand acc file raw;

  readPins =
    file:
    let
      step =
        acc: line:
        let
          t = trim line;
        in
        if t == "" || lib.hasPrefix "#" t then
          acc
        else
          let
            m = builtins.match "([A-Za-z_][A-Za-z0-9_]*)=(.*)" t;
          in
          if m == null then
            throw "pins: cannot parse ${toString file}: ${t}"
          else
            acc // { ${builtins.elemAt m 0} = parseValue acc file (builtins.elemAt m 1); };
    in
    builtins.foldl' step { } (lib.splitString "\n" (builtins.readFile file));

  # Fetch a key, naming the file in the error. `pins.FOO or (throw …)` at every
  # call site reads worse and is easy to forget, which turns a missing pin into
  # an eval-time `attribute missing` with no context.
  require =
    pins: file: key:
      pins.${key} or (throw "pins: ${toString file} has no ${key}");

in
{
  inherit readPins require;

  # Read one family's pins and return { pins, get } where `get` already knows
  # which file to blame.
  readFamily =
    root: family:
    let
      file = root + "/${family}/pins.env";
      pins = readPins file;
    in
    {
      inherit family file pins;
      get = require pins file;
    };
}

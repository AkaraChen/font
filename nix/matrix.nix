# The build matrix, flattened to one row per cell.
#
# `[[build.matrix]]` groups by profile and lists regions, which is the right
# shape to *write* and the wrong shape to *read* — "what can I build" wants one
# line per thing you can build. This is that reading, and it is the only one:
# `just matrix` prints it and `just build <family> <profile> <region>` takes any
# row of it, so the completion criterion "just matrix 与 [build.matrix] 一致"
# (KIT-282) is true by construction rather than by somebody remembering.
#
# Deliberately pkgs-free: it reads font.toml and nothing else, so it lives in
# the system-independent `lib` output and `nix eval .#lib.matrix` needs no
# platform.
{ lib, root }:

let
  families = lib.filter
    (name: builtins.pathExists (root + "/${name}/font.toml"))
    (lib.attrNames (builtins.readDir root));

  cellsOf =
    family:
    let
      data = builtins.fromTOML (builtins.readFile (root + "/${family}/font.toml"));
    in
    lib.concatMap
      (entry: map
        (region: {
          inherit family region;
          inherit (entry) profile weights;
          formats = entry.formats or [ "ttf" ];
          attr = "${family}-${entry.profile}-${region}";
        })
        entry.regions)
      data.build.matrix;

in
lib.concatMap cellsOf families

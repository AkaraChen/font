# A content-addressed view of every pinned artifact.
#
# It began as the bridge to the shell build steps: they already knew the sha256
# of everything they downloaded, so the cheapest lookup was a directory of files
# named by their own hash. No build reads it any more (KIT-280 removed the last
# shell pipeline), but the view is what makes the CI source layer one GC root,
# and `manifest.tsv` / `sizes.tsv` are how the 10 GB budget stays legible:
#
#   by-sha256/<hex>            the bytes
#   by-name/<family>/<file>    the same bytes, human-navigable
#   manifest.tsv               sha256, bytes, kind, family, filename
#
# An artifact shared by five families is fetched once, and
# `nix build .#source-cache` is a single GC root covering every input in the
# repo — which is what makes the CI source layer cacheable as one unit
# (docs/caching.md).
{ pkgs
, lib ? pkgs.lib
, sources
,
}:

let
  # Two families pinning the same bytes must produce one entry, not a
  # last-one-wins collision at `ln -s` time.
  byHash = lib.groupBy (e: e.sha256) sources.entries;

  linkHash =
    sha: es:
    let
      e = lib.head es;
    in
    "ln -s ${e.drv} $out/by-sha256/${sha}";

  linkName = e: ''
    mkdir -p $out/by-name/${e.family}
    ln -s ${e.drv} $out/by-name/${e.family}/${lib.escapeShellArg e.file}
  '';

  manifestRow =
    e:
    let
      owners = lib.concatStringsSep "," (map (x: x.family) byHash.${e.sha256});
    in
    "${e.sha256}\t${e.kind}\t${owners}\t${e.file}";

  manifest = lib.concatStringsSep "\n" (
    lib.unique (map manifestRow sources.entries)
  );

in
pkgs.runCommand "font-source-cache"
{
  passthru = { inherit (sources) entries; };
}
  ''
    mkdir -p $out/by-sha256 $out/by-name
    ${lib.concatStringsSep "\n" (lib.mapAttrsToList linkHash byHash)}
    ${lib.concatMapStrings linkName sources.entries}

    # Recorded rather than computed at read time: the sizes are the input to the
    # 10 GB GHA-cache budget, and a table nobody has to re-measure is a table
    # that stays honest.
    {
      printf 'sha256\tkind\tfamilies\tfile\n'
      printf '%s\n' ${lib.escapeShellArg manifest} | sort -k4
    } > $out/manifest.tsv

    {
      printf 'bytes\tfile\n'
      for f in $out/by-sha256/*; do
        printf '%s\t%s\n' "$(stat -Lc %s "$f" 2>/dev/null || stat -Lf %z "$f")" \
          "$(basename "$f")"
      done | sort -rn
    } > $out/sizes.tsv
  ''

# Read and validate a family's semantic `font.toml`.
#
# `builtins.fromTOML` is deliberately the only parser. Python independently
# validates the same bytes with Pydantic; there is no generated Nix or shell
# manifest that can drift. `legacy` is a compatibility view for build modules
# whose command-line wiring still uses the former uppercase names. It contains
# no copied values and can disappear without changing the manifest schema.
{ lib }:

let
  require =
    data: file: path:
    lib.attrByPath path
      (throw "manifest: ${toString file} has no ${lib.concatStringsSep "." path}")
      data;

  optional =
    data: path: fallback:
    lib.attrByPath path fallback data;

  artifact =
    data: source: name:
    require data null [ "sources" source "artifacts" name ];

  capitalize =
    value:
    lib.toUpper (builtins.substring 0 1 value)
    + builtins.substring 1 (builtins.stringLength value - 1) value;

  commonLegacy =
    data:
    let
      metric = optional data [ "metrics" "coding" ] { };
      calibration = data.calibration or { };
      regular = calibration.regular or { };
      bold = calibration.bold or { };
      nerd = data.nerd or { };
      grid = data.grid;
      naming = data.naming;
    in
    {
      EN_ADV = grid.en_adv;
      CJK_ADV = grid.cjk_adv;
      UPM = grid.upm;
      FAMILY_NAME = naming.family;
      FAMILY_PS = naming.ps;
      PRODUCT_STEM = naming.stem;
      FAMILY_SUFFIX = naming.suffix or "";
      PRODUCT_VERSION = naming.version or "0.1.0";
    }
    // lib.optionalAttrs (naming ? base_family) {
      BASE_FAMILY_NAME = naming.base_family;
      BASE_FAMILY_PS = naming.base_ps;
    }
    // lib.optionalAttrs (naming ? product_name_zh) {
      PRODUCT_NAME_ZH = naming.product_name_zh;
    }
    // lib.optionalAttrs (grid ? latin_src_adv) { LATIN_SRC_ADV = grid.latin_src_adv; }
    // lib.optionalAttrs (grid ? latin_src_upm) { LATIN_SRC_UPM = grid.latin_src_upm; }
    // lib.optionalAttrs (grid ? latin_target_upm) { LATIN_TARGET_UPM = grid.latin_target_upm; }
    // lib.optionalAttrs (grid ? latin_narrow_adv) { LATIN_NARROW_ADV = grid.latin_narrow_adv; }
    // lib.optionalAttrs (grid ? latin_uniform_scale) { LATIN_UNIFORM_SCALE = grid.latin_uniform_scale; }
    // lib.optionalAttrs (metric ? hhea_ascent) {
      HHEA_ASCENT = metric.hhea_ascent;
      HHEA_DESCENT = metric.hhea_descent;
      HHEA_LINE_GAP = metric.hhea_line_gap or 0;
    }
    // lib.optionalAttrs (metric ? os2_typo_ascender) {
      OS2_TYPO_ASCENDER = metric.os2_typo_ascender;
      OS2_TYPO_DESCENDER = metric.os2_typo_descender;
      OS2_TYPO_LINE_GAP = metric.os2_typo_line_gap;
      OS2_WIN_ASCENT = metric.os2_win_ascent;
      OS2_WIN_DESCENT = metric.os2_win_descent;
    }
    // lib.optionalAttrs (regular ? embolden) {
      CJK_EMBOLDEN_REGULAR = regular.embolden;
      CJK_SLANT_DEG = regular.slant_deg or 0;
      CJK_SLANT_PIVOT_Y = regular.slant_pivot_y or 375;
    }
    // lib.optionalAttrs (bold ? embolden) {
      CJK_EMBOLDEN_BOLD = bold.embolden;
    }
    // lib.optionalAttrs (nerd ? commit) {
      NERD_FONTS_PATCHER_VERSION = nerd.version;
      NERD_FONTS_PATCHER_COMMIT = nerd.commit;
      NERD_FONTS_PATCHER_HASH = nerd.hash;
    };

  familyLegacy =
    data:
    let
      a = source: name: artifact data source name;
      s = data.sources;
      c = data.calibration or { };
      o = data.options or { };
    in
    if data.family == "casual" then {
      RECURSIVE_REPO = s.recursive.repository;
      RECURSIVE_RELEASE_TAG = s.recursive.version;
      RECURSIVE_ZIP_URL = (a "recursive" "archive").url;
      RECURSIVE_ZIP_SHA256 = (a "recursive" "archive").sha256;
      RECURSIVE_TTF_REGULAR = (a "recursive" "regular").member;
      RECURSIVE_TTF_BOLD = (a "recursive" "bold").member;
      RECURSIVE_SHA256_REGULAR = (a "recursive" "regular").sha256;
      RECURSIVE_SHA256_BOLD = (a "recursive" "bold").sha256;
      YOZAI_REPO = s.yozai.repository;
      YOZAI_RELEASE_TAG = s.yozai.version;
      YOZAI_TTF_URL_REGULAR = (a "yozai" "regular").url;
      YOZAI_TTF_URL_MEDIUM = (a "yozai" "medium").url;
      YOZAI_SHA256_REGULAR = (a "yozai" "regular").sha256;
      YOZAI_SHA256_MEDIUM = (a "yozai" "medium").sha256;
      YOZAI_FOR_REGULAR = capitalize c.regular.source_weight;
      YOZAI_FOR_BOLD = capitalize c.bold.source_weight;
    } else if data.family == "handwriting" then {
      MONASPACE_REPO = s.monaspace.repository;
      MONASPACE_RELEASE_TAG = s.monaspace.version;
      MONASPACE_NF_ZIP_URL = (a "monaspace" "regular").url;
      RADON_NF_MEMBER_REGULAR = (a "monaspace" "regular").member;
      RADON_NF_MEMBER_BOLD = (a "monaspace" "bold").member;
      RADON_NF_SHA256_REGULAR = (a "monaspace" "regular").sha256;
      RADON_NF_SHA256_BOLD = (a "monaspace" "bold").sha256;
      WENKAI_REPO = s.wenkai.repository;
      WENKAI_RELEASE_TAG = s.wenkai.version;
      WENKAI_TTF_URL_REGULAR = (a "wenkai" "regular").url;
      WENKAI_TTF_URL_MEDIUM = (a "wenkai" "medium").url;
      WENKAI_SHA256_REGULAR = (a "wenkai" "regular").sha256;
      WENKAI_SHA256_MEDIUM = (a "wenkai" "medium").sha256;
      WENKAI_FOR_REGULAR = capitalize c.regular.source_weight;
      WENKAI_FOR_BOLD = capitalize c.bold.source_weight;
      SRC_UPM = o.src_upm;
      LIGATURE_SETS = lib.concatStringsSep "," o.ligature_sets;
    } else if data.family == "pixel" then {
      FUSION_REPO = s.fusion.repository;
      FUSION_RELEASE_TAG = s.fusion.version;
      FUSION_ZIP_URL = (a "fusion" "archive").url;
      FUSION_ZIP_SHA256 = (a "fusion" "archive").sha256;
      FUSION_TTF = o.fusion_ttf;
      FUSION_TTF_HALFWIDTH_DONOR = o.fusion_ttf_halfwidth_donor;
      FUSION_FONT_SIZE = o.fusion_font_size;
      PX_UNIT = o.px_unit;
      PIXEL_H = o.pixel_h;
    } else if data.family == "rounded" then {
      IOSEVKA_REPO = s.iosevka.repository;
      IOSEVKA_RELEASE_TAG = s.iosevka.version;
      IOSEVKA_ZIP_URL = (a "iosevka" "archive").url;
      IOSEVKA_ZIP_SHA256 = (a "iosevka" "archive").sha256;
      IOSEVKA_VARIANT = o.iosevka_variant;
      IOSEVKA_STYLE_NOTE = o.iosevka_style_note;
      IOSEVKA_TTF_REGULAR = o.iosevka_ttf_regular;
      IOSEVKA_TTF_BOLD = o.iosevka_ttf_bold;
      RHR_REPO = s.rhr.repository;
      RHR_RELEASE_TAG = s.rhr.version;
      RHR_ZIP_URL = (a "rhr" "archive").url;
      RHR_ZIP_SHA256 = (a "rhr" "archive").sha256;
      RHR_TTF_REGULAR = o.rhr_ttf_regular;
      RHR_TTF_BOLD = o.rhr_ttf_bold;
    } else if data.family == "sans" then {
      LILEX_REPO = s.lilex.repository;
      LILEX_RELEASE_TAG = s.lilex.version;
      LILEX_ZIP_URL = (a "lilex" "archive").url;
      LILEX_ZIP_SHA256 = (a "lilex" "archive").sha256;
      LILEX_TTF_REGULAR = o.lilex_ttf_regular;
      LILEX_TTF_BOLD = o.lilex_ttf_bold;
      LILEX_SRC_ADV = data.grid.latin_src_adv;
      PLEX_SANS_SC_REPO = s.plex.repository;
      PLEX_SANS_SC_RELEASE_TAG = s.plex.version;
      PLEX_SANS_SC_COMMIT = s.plex.commit;
      PLEX_SANS_SC_TTF_REGULAR_URL = (a "plex" "regular").url;
      PLEX_SANS_SC_TTF_BOLD_URL = (a "plex" "bold").url;
      PLEX_SANS_SC_TTF_REGULAR_SHA256 = (a "plex" "regular").sha256;
      PLEX_SANS_SC_TTF_BOLD_SHA256 = (a "plex" "bold").sha256;
      PLEX_SANS_SC_ZIP_URL = (a "plex" "legacy_archive").url;
      PLEX_SANS_SC_ZIP_SHA256 = (a "plex" "legacy_archive").sha256;
    } else if data.family == "serif" then {
      SARASA_REPO = s.sarasa.repository;
      SARASA_REF = s.sarasa.ref;
      SARASA_COMMIT = s.sarasa.commit;
      SARASA_SRC_HASH = s.sarasa.hash;
      LXGW_REPO = s.lxgw.repository;
      LXGW_TAG = s.lxgw.version;
      LXGW_ASSET = o.lxgw_asset;
      LXGW_URL = (a "lxgw" "regular").url;
      LXGW_SHA256 = (a "lxgw" "regular").sha256;
      CJK_TARGET_UPM = data.grid.upm;
      BUILD_TARGET = o.build_target;
      SARASA_TERM_ARCHIVE_URL = (a "sarasa_term" "archive").url;
      SARASA_TERM_ARCHIVE_SHA256 = (a "sarasa_term" "archive").sha256;
      SARASA_TERM_REGULAR = o.sarasa_term_regular;
      SARASA_TERM_BOLD = o.sarasa_term_bold;
    } else if data.family == "typewriter" then {
      COURIER_PRIME_REPO = s.courier_prime.repository;
      COURIER_PRIME_COMMIT = s.courier_prime.commit;
      COURIER_PRIME_TTF_REGULAR_URL = (a "courier_prime" "regular").url;
      COURIER_PRIME_TTF_BOLD_URL = (a "courier_prime" "bold").url;
      COURIER_PRIME_TTF_REGULAR_SHA256 = (a "courier_prime" "regular").sha256;
      COURIER_PRIME_TTF_BOLD_SHA256 = (a "courier_prime" "bold").sha256;
      COURIER_PRIME_SRC_UPM = o.courier_prime_src_upm;
      COURIER_PRIME_SRC_ADV = o.courier_prime_src_adv;
      ZHUQUE_REPO = s.zhuque.repository;
      ZHUQUE_RELEASE_TAG = s.zhuque.version;
      ZHUQUE_ZIP_URL = (a "zhuque" "archive").url;
      ZHUQUE_ZIP_SHA256 = (a "zhuque" "archive").sha256;
      ZHUQUE_TTF_IN_ZIP = o.zhuque_ttf_in_zip;
    } else
      throw "manifest: unsupported family ${data.family}";

  stringify = lib.mapAttrs (_: value: toString value);

  readManifest =
    file:
    let
      data = builtins.fromTOML (builtins.readFile file);
      allArtifacts = lib.concatMap
        (source: lib.attrValues (source.artifacts or { }))
        (lib.attrValues data.sources);
      matrixValues = axis: lib.concatMap (entry: entry.${axis}) data.build.matrix;
      declared = axis: data.build.${axis};
      axisValid = axis: lib.all (value: lib.elem value (declared axis)) (matrixValues axis);
      matrixProfilesValid =
        lib.all (entry: lib.elem entry.profile data.build.profiles) data.build.matrix;
      cjkRegions = lib.concatMap
        (source: if source.role == "cjk" then source.regions else [ ])
        (lib.attrValues data.sources);
      matrixRegionsHaveSource = lib.all (region: lib.elem region cjkRegions) (matrixValues "regions");
      matrixWeightsHaveCalibration =
        data.family == "pixel"
        || lib.all (weight: builtins.hasAttr weight data.calibration) (matrixValues "weights");
      checked =
        assert lib.assertMsg (data.schema_version or null == 1)
          "manifest: ${toString file} has unsupported schema_version";
        assert lib.assertMsg (data.grid.cjk_adv == data.grid.en_adv * 2)
          "manifest: ${toString file} grid is not strict 2:1";
        assert lib.assertMsg (data.build.slopes != [ ])
          "manifest: ${toString file} must declare at least one slope";
        assert lib.assertMsg (lib.all (a: a ? url && a ? sha256) allArtifacts)
          "manifest: ${toString file} has an artifact without url + sha256";
        assert lib.assertMsg matrixProfilesValid
          "manifest: ${toString file} matrix references an undeclared profile";
        assert lib.assertMsg
          (lib.all axisValid [ "regions" "weights" "formats" "slopes" ])
          "manifest: ${toString file} matrix references an undeclared axis value";
        assert lib.assertMsg matrixRegionsHaveSource
          "manifest: ${toString file} matrix region has no corresponding CJK source";
        assert lib.assertMsg matrixWeightsHaveCalibration
          "manifest: ${toString file} matrix weight has no calibration";
        data;
      legacy = stringify (commonLegacy checked // familyLegacy checked);
    in
    {
      inherit data legacy;
      # Compatibility for the family modules. Both names resolve into data
      # derived from this TOML; no second manifest exists.
      pins = legacy;
      get = key: legacy.${key}
        or (throw "manifest: ${toString file} has no compatibility field ${key}");
    };

in
{
  inherit readManifest;

  readFamily =
    root: family:
    let
      file = root + "/${family}/font.toml";
      manifest = readManifest file;
    in
    manifest // { inherit family file; };
}

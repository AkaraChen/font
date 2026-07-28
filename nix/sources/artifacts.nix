# Which pinned artifact each family needs, expressed as pins.env key pairs.
#
# This table holds no URLs and no hashes — only the *names of the keys* that
# carry them. pins.env stays the single source of truth; changing a pin never
# touches Nix.
#
# `file` is the canonical filename the artifact is published under in the
# by-name view. It is documentation and human navigation only: the build scripts
# resolve artifacts by sha256 (see tools/src-cache.sh), so a rename here cannot
# break a build.
{
  casual = {
    plain = {
      "ArrowType-Recursive.zip" = {
        url = "RECURSIVE_ZIP_URL";
        sha256 = "RECURSIVE_ZIP_SHA256";
      };
      "Yozai-Regular.ttf" = {
        url = "YOZAI_TTF_URL_REGULAR";
        sha256 = "YOZAI_SHA256_REGULAR";
      };
      "Yozai-Medium.ttf" = {
        url = "YOZAI_TTF_URL_MEDIUM";
        sha256 = "YOZAI_SHA256_MEDIUM";
      };
    };
  };

  handwriting = {
    plain = {
      "LXGWWenKai-Regular.ttf" = {
        url = "WENKAI_TTF_URL_REGULAR";
        sha256 = "WENKAI_SHA256_REGULAR";
      };
      "LXGWWenKai-Medium.ttf" = {
        url = "WENKAI_TTF_URL_MEDIUM";
        sha256 = "WENKAI_SHA256_MEDIUM";
      };
    };
    # The only Monaspace asset with pre-patched Nerd Font builds is a 315 MiB
    # zip holding two ~2.3 MiB OTFs. Standard Nix fetchers cannot do partial
    # downloads, so these go through a fixed-output derivation that keeps the
    # existing HTTP-range extractor. See zipMembers in ./default.nix.
    zipMembers = {
      "MonaspaceRadonNF-Regular.otf" = {
        url = "MONASPACE_NF_ZIP_URL";
        member = "RADON_NF_MEMBER_REGULAR";
        sha256 = "RADON_NF_SHA256_REGULAR";
      };
      "MonaspaceRadonNF-Bold.otf" = {
        url = "MONASPACE_NF_ZIP_URL";
        member = "RADON_NF_MEMBER_BOLD";
        sha256 = "RADON_NF_SHA256_BOLD";
      };
    };
  };

  pixel = {
    plain = {
      "fusion-pixel-12px-monospaced-ttf.zip" = {
        url = "FUSION_ZIP_URL";
        sha256 = "FUSION_ZIP_SHA256";
      };
    };
  };

  rounded = {
    plain = {
      "PkgTTF-IosevkaCurly.zip" = {
        url = "IOSEVKA_ZIP_URL";
        sha256 = "IOSEVKA_ZIP_SHA256";
      };
      "RHR-CN.7z" = {
        url = "RHR_ZIP_URL";
        sha256 = "RHR_ZIP_SHA256";
      };
    };
  };

  sans = {
    plain = {
      "Lilex.zip" = {
        url = "LILEX_ZIP_URL";
        sha256 = "LILEX_ZIP_SHA256";
      };
      "IBMPlexSansSC-Regular.ttf" = {
        url = "PLEX_SANS_SC_TTF_REGULAR_URL";
        sha256 = "PLEX_SANS_SC_TTF_REGULAR_SHA256";
      };
      "IBMPlexSansSC-Bold.ttf" = {
        url = "PLEX_SANS_SC_TTF_BOLD_URL";
        sha256 = "PLEX_SANS_SC_TTF_BOLD_SHA256";
      };
    };
  };

  serif = {
    plain = {
      "LXGWNeoZhiSongPlus.ttf" = {
        url = "LXGW_URL";
        sha256 = "LXGW_SHA256";
      };
      "SarasaTermSlabSC-TTF-Unhinted.7z" = {
        url = "SARASA_TERM_ARCHIVE_URL";
        sha256 = "SARASA_TERM_ARCHIVE_SHA256";
      };
    };
  };

  typewriter = {
    plain = {
      "CourierPrime-Regular.ttf" = {
        url = "COURIER_PRIME_TTF_REGULAR_URL";
        sha256 = "COURIER_PRIME_TTF_REGULAR_SHA256";
      };
      "CourierPrime-Bold.ttf" = {
        url = "COURIER_PRIME_TTF_BOLD_URL";
        sha256 = "COURIER_PRIME_TTF_BOLD_SHA256";
      };
      "ZhuqueFangsong.zip" = {
        url = "ZHUQUE_ZIP_URL";
        sha256 = "ZHUQUE_ZIP_SHA256";
      };
    };
  };
}

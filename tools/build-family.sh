#!/usr/bin/env bash
# Run one family's existing build, one numbered step at a time, with wall-clock
# timing per step.
#
# Phase 0 changes no build logic. This wrapper does not reimplement build.sh —
# it *reads* the ordered step list out of <family>/scripts/build.sh and runs
# exactly those scripts, so the two can never silently drift. If the parse comes
# back empty or disagrees with what is on disk, we fall back to invoking
# build.sh whole and time it as a single step rather than guessing.
#
# Timings land in <family>/work/step-timings.tsv and, under GitHub Actions, in
# the job summary. They are the input to the caching decisions in KIT-265 —
# the plan has no measured wall-clock numbers yet.

set -euo pipefail

REPO_ROOT="${FONTKIT_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

log()  { printf '==> %s\n' "$*" >&2; }
die()  { printf 'error: %s\n' "$*" >&2; exit 1; }

# mapfile is bash 4+; macOS ships 3.2. Inside `nix develop` you get bash 5.
[[ ${BASH_VERSINFO[0]} -ge 4 ]] \
  || die "bash >= 4 required (got ${BASH_VERSION}); run inside \`nix develop\`"

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
  shift
fi

FAMILY="${1:-}"
[[ -n "${FAMILY}" ]] || die "usage: build-family.sh [--dry-run] <family>"

FAMILY_DIR="${REPO_ROOT}/${FAMILY}"
BUILD_SH="${FAMILY_DIR}/scripts/build.sh"
[[ -x "${BUILD_SH}" ]] || die "no executable ${BUILD_SH}"

# fontTools reads SOURCE_DATE_EPOCH for head.modified. fontforge embeds its own
# timestamps regardless, which is why the regression net fingerprints normalised
# dumps rather than file hashes — but killing the noise we *can* kill is free.
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-0}"
# fontforge is pinned by the devShell; never fall through to the docker path.
export NERD_PATCH_METHOD="${NERD_PATCH_METHOD:-fontforge}"

# Extract the ordered "${SCRIPT_DIR}/NN-name.sh" invocations from build.sh.
mapfile -t STEPS < <(
  grep -oE '\$\{SCRIPT_DIR\}/[0-9]{2}-[A-Za-z0-9._-]+\.sh' "${BUILD_SH}" \
    | sed 's|.*/||'
)

if [[ ${#STEPS[@]} -eq 0 ]]; then
  log "warning: could not parse steps out of ${BUILD_SH}; running it whole"
  STEPS=("build.sh")
fi

for step in "${STEPS[@]}"; do
  [[ -x "${FAMILY_DIR}/scripts/${step}" ]] \
    || die "${BUILD_SH} references ${step}, which is not an executable script"
done

if [[ ${DRY_RUN} -eq 1 ]]; then
  printf '%s\n' "${STEPS[@]}"
  exit 0
fi

TIMINGS="${FAMILY_DIR}/work/step-timings.tsv"
mkdir -p "$(dirname "${TIMINGS}")"
printf 'family\tstep\tseconds\tstatus\n' > "${TIMINGS}"

total_start=$SECONDS
status=0
for step in "${STEPS[@]}"; do
  log "[${FAMILY}] ${step}"
  step_start=$SECONDS
  if "${FAMILY_DIR}/scripts/${step}"; then
    step_status=ok
  else
    step_status=FAILED
    status=1
  fi
  elapsed=$(( SECONDS - step_start ))
  printf '%s\t%s\t%s\t%s\n' "${FAMILY}" "${step}" "${elapsed}" "${step_status}" \
    >> "${TIMINGS}"
  log "[${FAMILY}] ${step} — ${elapsed}s (${step_status})"
  [[ ${status} -eq 0 ]] || break
done
total=$(( SECONDS - total_start ))
printf '%s\t%s\t%s\t%s\n' "${FAMILY}" "TOTAL" "${total}" \
  "$([[ ${status} -eq 0 ]] && echo ok || echo FAILED)" >> "${TIMINGS}"

log "step timings → ${TIMINGS}"
column -t -s $'\t' "${TIMINGS}" >&2 || cat "${TIMINGS}" >&2

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    echo "### \`${FAMILY}\` step timings"
    echo
    echo "| step | seconds | status |"
    echo "| --- | ---: | --- |"
    tail -n +2 "${TIMINGS}" | while IFS=$'\t' read -r _ step secs st; do
      echo "| \`${step}\` | ${secs} | ${st} |"
    done
    echo
  } >> "${GITHUB_STEP_SUMMARY}"
fi

exit "${status}"

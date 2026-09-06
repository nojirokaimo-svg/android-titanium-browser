#!/usr/bin/env bash
set -Eeuo pipefail

KIT_ROOT="$(cd "$(dirname "$0")" && pwd)"
UPSTREAM_REPOSITORY="https://github.com/jqssun/android-titanium-browser.git"
UPSTREAM_REF=""
UPDATE_ROOT="$KIT_ROOT/upstream-update-work"
REPORT="$KIT_ROOT/output/kiwi-patch-report.md"
RESOLVE_ONLY=false
GITHUB_OUTPUT_FILE=""

usage() {
  echo "Usage: $0 [--ref REF] [--repository URL] [--work-dir DIR] [--report FILE] [--resolve-only] [--github-output FILE]"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ref) UPSTREAM_REF="$2"; shift 2 ;;
    --repository) UPSTREAM_REPOSITORY="$2"; shift 2 ;;
    --work-dir) UPDATE_ROOT="$2"; shift 2 ;;
    --report) REPORT="$2"; shift 2 ;;
    --resolve-only) RESOLVE_ONLY=true; shift ;;
    --github-output) GITHUB_OUTPUT_FILE="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

TITANIUM_DIR="$UPDATE_ROOT/titanium"
mkdir -p "$UPDATE_ROOT"
if [[ ! -d "$TITANIUM_DIR/.git" ]]; then
  git clone --filter=blob:none --no-checkout "$UPSTREAM_REPOSITORY" "$TITANIUM_DIR"
fi
git -C "$TITANIUM_DIR" remote set-url origin "$UPSTREAM_REPOSITORY"
if [[ -n "$UPSTREAM_REF" ]]; then
  git -C "$TITANIUM_DIR" fetch --depth 1 origin "$UPSTREAM_REF"
else
  git -C "$TITANIUM_DIR" fetch --depth 1 origin HEAD
fi
git -C "$TITANIUM_DIR" checkout --detach --force FETCH_HEAD
TITANIUM_COMMIT="$(git -C "$TITANIUM_DIR" rev-parse HEAD)"
git -C "$TITANIUM_DIR" submodule update --init --recursive --depth 1
VANADIUM_COMMIT="$(git -C "$TITANIUM_DIR/vanadium" rev-parse HEAD)"
CHROMIUM_VERSION="$(grep -m1 -o '[0-9]\+\(\.[0-9]\+\)\{3\}' "$TITANIUM_DIR/vanadium/args.gn")"
CHROMIUM_COMMIT="$(git ls-remote https://chromium.googlesource.com/chromium/src.git "refs/tags/$CHROMIUM_VERSION^{}" | awk 'NR == 1 {print $1}')"
if [[ -z "$CHROMIUM_COMMIT" ]]; then
  CHROMIUM_COMMIT="$(git ls-remote https://chromium.googlesource.com/chromium/src.git "refs/tags/$CHROMIUM_VERSION" | awk 'NR == 1 {print $1}')"
fi
test -n "$CHROMIUM_COMMIT"

emit_outputs() {
  [[ -z "$GITHUB_OUTPUT_FILE" ]] && return 0
  {
    echo "titanium_commit=$TITANIUM_COMMIT"
    echo "vanadium_commit=$VANADIUM_COMMIT"
    echo "chromium_version=$CHROMIUM_VERSION"
    echo "chromium_commit=$CHROMIUM_COMMIT"
  } >> "$GITHUB_OUTPUT_FILE"
}
emit_outputs

echo "Titanium: $TITANIUM_COMMIT"
echo "Vanadium: $VANADIUM_COMMIT"
echo "Chromium: $CHROMIUM_COMMIT ($CHROMIUM_VERSION)"
if $RESOLVE_ONLY; then
  exit 0
fi

export KIWI_BUILD_ROOT="$UPDATE_ROOT"
export KIWI_BUILD_PHASE=prepare
export KIWI_PATCH_MODE=best-effort
export KIWI_PATCH_REPORT="$REPORT"
export TITANIUM_REPOSITORY="$UPSTREAM_REPOSITORY"
export TITANIUM_COMMIT VANADIUM_COMMIT CHROMIUM_COMMIT CHROMIUM_VERSION
"$KIT_ROOT/build_kiwi_ui_arm64.sh"

echo "Kiwi patches applied cleanly. Continue with the checkpoint build workflow."

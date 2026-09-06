#!/usr/bin/env bash
set -Eeuo pipefail

KIT_ROOT="$(cd "$(dirname "$0")" && pwd)"
BUILD_ROOT="${KIWI_BUILD_ROOT:-$KIT_ROOT/work}"
TITANIUM_DIR="$BUILD_ROOT/titanium"
TITANIUM_REPOSITORY="${TITANIUM_REPOSITORY:-https://github.com/jqssun/android-titanium-browser.git}"
TITANIUM_COMMIT="${TITANIUM_COMMIT:-80ffcdf1cebe51cddc593f571a6f26c3374aea2e}"
VANADIUM_COMMIT="${VANADIUM_COMMIT:-150a27e23302cc265baf8a7fb7c0f0112bddf2fd}"
CHROMIUM_COMMIT="${CHROMIUM_COMMIT:-506c834ecceaa943c5f41e6cfe7f68acb5c45346}"
VERSION="${CHROMIUM_VERSION:-152.0.7977.64}"
PHASE="${KIWI_BUILD_PHASE:-all}"
PATCH_MODE="${KIWI_PATCH_MODE:-strict}"

if [[ "$PHASE" != "all" && "$PHASE" != "prepare" && "$PHASE" != "compile" ]]; then
  echo "Unknown KIWI_BUILD_PHASE: $PHASE" >&2
  exit 2
fi

if [[ "$PHASE" != "compile" ]]; then
mkdir -p "$BUILD_ROOT"
if [[ ! -d "$TITANIUM_DIR/.git" ]]; then
  git clone "$TITANIUM_REPOSITORY" "$TITANIUM_DIR"
fi
git -C "$TITANIUM_DIR" fetch --depth 1 origin "$TITANIUM_COMMIT"
git -C "$TITANIUM_DIR" checkout --detach "$TITANIUM_COMMIT"
git -C "$TITANIUM_DIR" submodule update --init --recursive --depth 1
test "$(git -C "$TITANIUM_DIR/vanadium" rev-parse HEAD)" = "$VANADIUM_COMMIT"

export DEBIAN_FRONTEND=noninteractive
sudo apt-get update
sudo apt-get install -y sudo lsb-release file git curl python3 python3-pillow imagemagick librsvg2-bin ninja-build
sudo dpkg --add-architecture i386
sudo apt-get update
sudo apt-get install -y libgcc-s1:i386

if [[ ! -d "$BUILD_ROOT/depot_tools/.git" ]]; then
  git clone --depth 1 https://chromium.googlesource.com/chromium/tools/depot_tools.git \
    "$BUILD_ROOT/depot_tools"
fi
export PATH="$BUILD_ROOT/depot_tools:$PATH"

# gclient hooks apply patches with plain `git am` inside nested repositories
# (notably V8). Fresh GitHub runners have no author identity configured, which
# makes git-am exit before printing an "Applying:" line and crashes Vanadium's
# patch helper with IndexError. Give all hook-created repositories a disposable
# build identity before running the hooks.
git config --global user.name "Titanium-Kiwi build"
git config --global user.email "build@example.invalid"

mkdir -p "$TITANIUM_DIR/chromium/src/out/Default"
cd "$TITANIUM_DIR/chromium/src"
if [[ ! -d .git ]]; then git init; fi
if ! git remote get-url origin >/dev/null 2>&1; then
  git remote add origin https://chromium.googlesource.com/chromium/src.git
fi
git fetch --depth 1 origin "+refs/tags/$VERSION:refs/tags/$VERSION"
git checkout --detach --force "refs/tags/$VERSION"
test "$(git rev-parse HEAD)" = "$CHROMIUM_COMMIT"
cp "$TITANIUM_DIR/.gclient" ../.gclient

# Match the exclusions in the pinned Titanium build script exactly.
rm -f "$TITANIUM_DIR"/vanadium/patches/*trichrome-{apk-build-targets,browser-apk-targets}.patch
rm -f "$TITANIUM_DIR"/vanadium/patches/*{detailed,supported}-language*.patch
rm -f "$TITANIUM_DIR"/vanadium/patches/*javascript-optimizer-{site-setting,settings-UI}.patch
rm -f "$TITANIUM_DIR"/vanadium/patches/*component-updates.patch
rm -f "$TITANIUM_DIR"/vanadium/patches/*{pdf,PDF,for-content-public,toolbar-button,configs-from-config-app,new-tab-card,predictive-back*}*.patch

replace_tree() {
  local directory="$1" old="$2" new="$3"
  find "$directory" -type f -exec sed -i "s@${old}@${new}@g" {} +
}
replace_tree "$TITANIUM_DIR/vanadium/patches" VANADIUM TITANIUM
replace_tree "$TITANIUM_DIR/vanadium/patches" Vanadium Titanium
replace_tree "$TITANIUM_DIR/vanadium/patches" vanadium titanium
git -c user.name="Titanium-Kiwi build" -c user.email="build@example.invalid" \
  am --whitespace=nowarn --keep-non-patch "$TITANIUM_DIR"/vanadium/patches/*.patch

gclient sync -D --no-history --nohooks
gclient runhooks
./build/install-build-deps.sh --no-prompt

export SCRIPT_DIR="$TITANIUM_DIR"
# patch.sh normally inherits this helper from Titanium's build.sh/common.sh.
# Define it locally so sourcing common.sh cannot overwrite SCRIPT_DIR with the
# location of this wrapper script.
version_lt() {
  [[ "$1" != "$2" ]] && [[ "$(printf '%s\n%s\n' "$1" "$2" | sort -V | head -n1)" == "$1" ]]
}
source "$TITANIUM_DIR/patch.sh"
PATCH_ARGS=()
if [[ "$PATCH_MODE" == "best-effort" ]]; then
  PATCH_ARGS+=(--best-effort --report "${KIWI_PATCH_REPORT:-$KIT_ROOT/output/kiwi-patch-report.md}")
elif [[ "$PATCH_MODE" != "strict" ]]; then
  echo "Unknown KIWI_PATCH_MODE: $PATCH_MODE" >&2
  exit 2
fi
python3 "$KIT_ROOT/kiwi_port/apply.py" "$PWD" "${PATCH_ARGS[@]}"

cp "$TITANIUM_DIR/args.gn" out/Default/args.gn
python3 - <<'PY'
from pathlib import Path
p = Path("out/Default/args.gn")
s = p.read_text(encoding="utf-8")
s = s.replace('target_cpu = "arm"', 'target_cpu = "arm64"')
s = s.replace(
    'chrome_public_manifest_package = "io.github.jqssun.helium"',
    'chrome_public_manifest_package = "io.github.nojirokaimo.titaniumkiwi"',
)
# A full Chromium official release build only reached ~43% before the fixed
# six-hour GitHub-hosted runner limit. This is an installable validation APK,
# so trade release optimization and symbols for a substantially faster local
# debug-code build. Functional/UI behavior remains testable; a distributable
# optimized release can be produced later on a persistent/larger builder.
s = s.replace('is_debug = false', 'is_debug = true')
s = s.replace('is_official_build = true', 'is_official_build = false')
s = s.replace('symbol_level = 1', 'symbol_level = 0')
s = s.replace('generate_linker_map = true', 'generate_linker_map = false')
s += '\nblink_symbol_level = 0\nv8_symbol_level = 0\nuse_thin_lto = false\n'
p.write_text(s, encoding="utf-8")
PY

gn gen out/Default
fi

if [[ "$PHASE" == "prepare" ]]; then
  exit 0
fi

export PATH="$BUILD_ROOT/depot_tools:$PATH"
cd "$TITANIUM_DIR/chromium/src"

# GitHub-hosted jobs are forcibly terminated at six hours. Stop Siso/Ninja
# ourselves while enough time remains to save out/Default, then let the next
# job restore the checkpoint and continue from the completed object files.
BUILD_STATUS=0
BUILD_COMMAND=(autoninja -C out/Default chrome_public_apk)
if [[ "${KIWI_INCREMENTAL_NINJA:-false}" == "true" ]]; then
  # Siso's interrupted-build state is not portable across fresh hosted runners:
  # it re-executed roughly the same 28k edges after every cache restore. Ninja's
  # timestamp graph reuses the restored object files and only builds missing or
  # genuinely stale outputs. The composite action makes restored outputs newer
  # than the identical pinned source tree before selecting this mode.
  # Direct Ninja has no autoninja-managed Android build server. Force Chromium's
  # build-server-aware actions to run inline, preserving the cached Ninja graph.
  BUILD_COMMAND=(env INVOKED_BY_BUILD_SERVER=1 /usr/bin/ninja -C out/Default -j "${KIWI_NINJA_JOBS:-4}" chrome_public_apk)
fi
printf 'Build command:'
printf ' %q' "${BUILD_COMMAND[@]}"
printf '\n'
if [[ -n "${KIWI_BUILD_BUDGET_MINUTES:-}" ]]; then
  timeout --signal=INT --kill-after=5m \
    "${KIWI_BUILD_BUDGET_MINUTES}m" \
    "${BUILD_COMMAND[@]}" || BUILD_STATUS=$?
else
  "${BUILD_COMMAND[@]}" || BUILD_STATUS=$?
fi

APK="$(find out/Default/apks -type f -name 'Chrome*.apk' 2>/dev/null | sort | head -n 1 || true)"
if [[ -z "$APK" ]]; then
  if [[ "$BUILD_STATUS" -eq 124 || "$BUILD_STATUS" -eq 130 || "$BUILD_STATUS" -eq 137 ]]; then
    echo "Build budget reached; out/Default is ready for the next checkpoint stage."
    exit 0
  fi
  echo "APK was not produced (autoninja status: $BUILD_STATUS)." >&2
  if [[ "$BUILD_STATUS" -eq 0 ]]; then
    exit 1
  fi
  exit "$BUILD_STATUS"
fi
mkdir -p "$KIT_ROOT/output"
cp "$APK" "$KIT_ROOT/output/Titanium-Kiwi-core-$VERSION-arm64-v8a.apk"

APKSIGNER="$(find third_party/android_sdk/public/build-tools -type f -name apksigner | sort | tail -n 1)"
test -x "$APKSIGNER"
"$APKSIGNER" verify --verbose \
  "$KIT_ROOT/output/Titanium-Kiwi-core-$VERSION-arm64-v8a.apk"
sha256sum "$KIT_ROOT/output/Titanium-Kiwi-core-$VERSION-arm64-v8a.apk" \
  > "$KIT_ROOT/output/SHA256SUMS.txt"
touch "$KIT_ROOT/output/BUILD_COMPLETE"

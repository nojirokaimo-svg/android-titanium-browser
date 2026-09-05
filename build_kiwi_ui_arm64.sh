#!/usr/bin/env bash
set -Eeuo pipefail

KIT_ROOT="$(cd "$(dirname "$0")" && pwd)"
BUILD_ROOT="${KIWI_BUILD_ROOT:-$KIT_ROOT/work}"
TITANIUM_DIR="$BUILD_ROOT/titanium"
TITANIUM_COMMIT="80ffcdf1cebe51cddc593f571a6f26c3374aea2e"
VANADIUM_COMMIT="150a27e23302cc265baf8a7fb7c0f0112bddf2fd"
CHROMIUM_COMMIT="506c834ecceaa943c5f41e6cfe7f68acb5c45346"
VERSION="152.0.7977.64"

mkdir -p "$BUILD_ROOT"
if [[ ! -d "$TITANIUM_DIR/.git" ]]; then
  git clone https://github.com/jqssun/android-titanium-browser.git "$TITANIUM_DIR"
fi
git -C "$TITANIUM_DIR" fetch --depth 1 origin "$TITANIUM_COMMIT"
git -C "$TITANIUM_DIR" checkout --detach "$TITANIUM_COMMIT"
git -C "$TITANIUM_DIR" submodule update --init --recursive --depth 1
test "$(git -C "$TITANIUM_DIR/vanadium" rev-parse HEAD)" = "$VANADIUM_COMMIT"

export DEBIAN_FRONTEND=noninteractive
sudo apt-get update
sudo apt-get install -y sudo lsb-release file git curl python3 python3-pillow imagemagick librsvg2-bin
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
python3 "$KIT_ROOT/kiwi_port/apply.py" "$PWD"

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
p.write_text(s, encoding="utf-8")
PY

gn gen out/Default
autoninja -C out/Default chrome_public_apk

APK="$(find out/Default/apks -type f -name 'Chrome*.apk' | sort | head -n 1)"
test -n "$APK"
mkdir -p "$KIT_ROOT/output"
cp "$APK" "$KIT_ROOT/output/Titanium-Kiwi-core-$VERSION-arm64-v8a.apk"

APKSIGNER="$(find third_party/android_sdk/public/build-tools -type f -name apksigner | sort | tail -n 1)"
test -x "$APKSIGNER"
"$APKSIGNER" verify --verbose \
  "$KIT_ROOT/output/Titanium-Kiwi-core-$VERSION-arm64-v8a.apk"
sha256sum "$KIT_ROOT/output/Titanium-Kiwi-core-$VERSION-arm64-v8a.apk" \
  > "$KIT_ROOT/output/SHA256SUMS.txt"

#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
LOCK="${ROOT}/os/image-source.lock.json"
MANIFEST="${ROOT}/os/package-manifest.csv"
RESOLVER="${ROOT}/tools/atlas/resolve-package-manifest.py"
BUILD_ROOT="${ROOT}/build/atlas"
OUTPUT_ROOT="${ROOT}/dist"
REPRO_CHECK=1

usage() {
  echo "Usage: $0 [--no-repro-check]"
  echo "Builds the pinned Fedora 44 KDE live ISO and UEFI QCOW2 from the Fedora KIWI source lock."
}
for arg in "$@"; do
  case "$arg" in
    --no-repro-check) REPRO_CHECK=0 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $arg" >&2; usage >&2; exit 2 ;;
  esac
done

fail() { echo "ERROR: $*" >&2; exit 2; }
require_command() { command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"; }

[[ -r /etc/os-release ]] || fail "/etc/os-release is unavailable"
# shellcheck disable=SC1091
. /etc/os-release
[[ "${ID:-}" == fedora && "${VERSION_ID:-}" == 44 ]] || fail "build host must be Fedora 44"
[[ "$(uname -m)" == x86_64 ]] || fail "build host must be x86_64"

for cmd in git python3 dnf5 kiwi-ng sha256sum rpm; do require_command "$cmd"; done
[[ -f "$LOCK" ]] || fail "source lock is missing: $LOCK"
[[ -f "$MANIFEST" ]] || fail "package manifest is missing: $MANIFEST"

# Validate lock shape and expose only fixed, reviewed build inputs.
eval "$(python3 - "$LOCK" <<'PY'
import json, shlex, sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
source = data["source"]
platform = data["platform"]
assert data["schema_version"] == 1
assert platform == {"fedora_release": "44", "architecture": "x86_64", "firmware": "uefi"}
assert source["ref"] == "f44"
assert len(source["commit"]) == 40 and all(c in "0123456789abcdef" for c in source["commit"])
assert len(data["artifacts"]) == 2
for item in data["artifacts"]:
    assert item["id"] and item["image_type"] and item["image_profile"]
for key, value in {
    "UPSTREAM_URL": source["repository"],
    "UPSTREAM_REF": source["ref"],
    "UPSTREAM_COMMIT": source["commit"],
    "DESCRIPTION_FILE": source["description_file"],
    "DESCRIPTION_BLOB": source["description_blob"],
    "WRAPPER_FILE": source["wrapper_file"],
    "WRAPPER_BLOB": source["wrapper_blob"],
    "KDE_FILE": source["kde_profile_file"],
    "KDE_BLOB": source["kde_profile_blob"],
    "ISO_PROFILE": data["artifacts"][0]["image_profile"],
    "DISK_PROFILE": data["artifacts"][1]["image_profile"],
}.items():
    print(f"{key}={shlex.quote(value)}")
PY
)" || fail "invalid image source lock"

mkdir -p "$BUILD_ROOT" "$OUTPUT_ROOT"
UPSTREAM_DIR="$BUILD_ROOT/fedora-kiwi-descriptions"
if [[ ! -d "$UPSTREAM_DIR/.git" ]]; then
  git clone --no-checkout "$UPSTREAM_URL" "$UPSTREAM_DIR"
fi
git -C "$UPSTREAM_DIR" fetch --no-tags origin "$UPSTREAM_COMMIT"
git -C "$UPSTREAM_DIR" checkout --detach "$UPSTREAM_COMMIT"
ACTUAL_COMMIT="$(git -C "$UPSTREAM_DIR" rev-parse HEAD)"
[[ "$ACTUAL_COMMIT" == "$UPSTREAM_COMMIT" ]] || fail "upstream checkout mismatch: $ACTUAL_COMMIT"
for pair in "$DESCRIPTION_FILE:$DESCRIPTION_BLOB" "$WRAPPER_FILE:$WRAPPER_BLOB" "$KDE_FILE:$KDE_BLOB"; do
  path="${pair%%:*}"
  expected="${pair##*:}"
  actual="$(git -C "$UPSTREAM_DIR" rev-parse "HEAD:$path")"
  [[ "$actual" == "$expected" ]] || fail "upstream source blob mismatch for $path: $actual"
done

# The resolver is read-only and fails closed on an empty manifest or repository failure.
python3 "$RESOLVER" --manifest "$MANIFEST" --output "$BUILD_ROOT/package-resolution.json"

KIWI_VERSION="$(kiwi-ng --version 2>&1 | head -n 1)"
DNF_VERSION="$(dnf5 --version 2>&1 | head -n 1)"
SOURCE_DATE_EPOCH="$(git -C "$UPSTREAM_DIR" show -s --format=%ct "$UPSTREAM_COMMIT")"
export SOURCE_DATE_EPOCH
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="$BUILD_ROOT/run-$RUN_ID"
mkdir -p "$RUN_DIR"

build_pair() {
  local destination="$1"
  mkdir -p "$destination/iso" "$destination/disk"
  (
    cd "$UPSTREAM_DIR"
    ./kiwi-build --kiwi-file=Fedora.kiwi --image-type=iso --image-profile="$ISO_PROFILE" --output-dir "$destination/iso"
    ./kiwi-build --kiwi-file=Fedora.kiwi --image-type=oem --image-profile="$DISK_PROFILE" --output-dir "$destination/disk"
  )
  (cd "$destination" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 -r sha256sum > SHA256SUMS)
  [[ -s "$destination/SHA256SUMS" ]] || fail "KIWI produced no files in $destination"
}

build_pair "$RUN_DIR/first"
if [[ "$REPRO_CHECK" == 1 ]]; then
  build_pair "$RUN_DIR/repeat"
  diff -u "$RUN_DIR/first/SHA256SUMS" "$RUN_DIR/repeat/SHA256SUMS" || fail "reproducibility check failed: artifact hashes differ"
fi

cp "$RUN_DIR/first/SHA256SUMS" "$OUTPUT_ROOT/SHA256SUMS"
python3 - "$LOCK" "$BUILD_ROOT/package-resolution.json" "$OUTPUT_ROOT/build-metadata.json" "$ACTUAL_COMMIT" "$KIWI_VERSION" "$DNF_VERSION" "$SOURCE_DATE_EPOCH" "$RUN_ID" "$REPRO_CHECK" <<'PY'
import datetime, json, platform, sys
from pathlib import Path
lock_path, resolution_path, output_path, commit, kiwi, dnf, epoch, run_id, repro = sys.argv[1:]
lock = json.loads(Path(lock_path).read_text(encoding="utf-8"))
resolution = json.loads(Path(resolution_path).read_text(encoding="utf-8"))
metadata = {
    "schema_version": 1,
    "run_id": run_id,
    "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source_commit": commit,
    "source_lock_sha256": __import__("hashlib").sha256(Path(lock_path).read_bytes()).hexdigest(),
    "fedora_release": lock["platform"]["fedora_release"],
    "architecture": platform.machine(),
    "firmware_target": lock["platform"]["firmware"],
    "kiwi_version": kiwi,
    "dnf5_version": dnf,
    "source_date_epoch": int(epoch),
    "upstream_repository": lock["source"]["repository"],
    "upstream_ref": lock["source"]["ref"],
    "upstream_commit": lock["source"]["commit"],
    "package_manifest_sha256": resolution["manifest_sha256"],
    "resolved_packages": resolution["packages"],
    "reproducibility_check": "passed" if repro == "1" else "not_tested",
    "artifact_checksums": "SHA256SUMS"
}
Path(output_path).write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

echo "Build outputs: $RUN_DIR/first"
echo "Checksums: $OUTPUT_ROOT/SHA256SUMS"
echo "Metadata: $OUTPUT_ROOT/build-metadata.json"

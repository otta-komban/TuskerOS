#!/usr/bin/env bash
set -Eeuo pipefail

# ATLAS-01 Fedora 44 KIWI proof-of-concept host preflight.
# This script validates prerequisites only; it does not install packages or build images.

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
warn() { printf 'WARN: %s\n' "$*" >&2; }
info() { printf 'INFO: %s\n' "$*"; }

[[ -r /etc/os-release ]] || fail "Cannot identify the build host: /etc/os-release is missing."
# shellcheck disable=SC1091
. /etc/os-release

[[ "${ID:-}" == "fedora" ]] || fail "Build host must be Fedora; detected ID=${ID:-unknown}."
[[ "${VERSION_ID:-}" == "44" ]] || fail "POC baseline is Fedora 44; detected VERSION_ID=${VERSION_ID:-unknown}."
[[ "$(uname -m)" == "x86_64" ]] || fail "Initial POC architecture is x86_64; detected $(uname -m)."

for command_name in kiwi-ng qemu-system-x86_64 qemu-img rpm dnf; do
  command -v "$command_name" >/dev/null 2>&1 || fail "Required command not found: $command_name"
done

if ! command -v virt-install >/dev/null 2>&1; then
  warn "virt-install is missing; direct QEMU boot remains possible, but libvirt automation is unavailable."
fi

if ! command -v sha256sum >/dev/null 2>&1; then
  fail "sha256sum is required for artifact evidence."
fi

if ! rpm -q edk2-ovmf >/dev/null 2>&1; then
  warn "edk2-ovmf RPM not detected; locate and record a valid UEFI firmware image before boot tests."
fi

info "Host identity: $PRETTY_NAME"
info "Architecture: $(uname -m)"
info "Kernel: $(uname -r)"
info "KIWI: $(kiwi-ng --version 2>&1 | head -n 1)"
info "QEMU: $(qemu-system-x86_64 --version | head -n 1)"
info "DNF: $(dnf --version | head -n 1)"
info "RPM: $(rpm --version)"
info "Preflight passed. This does not certify that the image description builds or boots."

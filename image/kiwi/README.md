# Fedora 44 KIWI NG Proof of Concept

**Owner:** ATLAS-01  
**Branch:** `01-fedora-base`  
**Status:** Build not yet executed. This runbook defines the reproducible acceptance procedure; it is not evidence of a successful image.

## Objective

Determine whether KIWI NG can produce a Fedora 44 x86_64 KDE/Wayland desktop image and a UEFI virtual-disk artifact from one version-controlled package source without making Tusker services a boot/login dependency.

## POC decision boundaries

- Candidate builder: KIWI NG.
- Host: Fedora 44 x86_64.
- Guest: Fedora 44 x86_64.
- Required outputs: bootable ISO and QCOW2 virtual disk.
- Firmware: UEFI first; Secure Boot is a separate test gate.
- Desktop: Fedora 44 KDE Plasma 6.6.4, Wayland-first.
- Update model: conventional mutable RPM/DNF for the initial MVP unless PHOENIX-10 and the project architecture explicitly approve bootc.
- No AI model weights, developer toolchain, remote-control daemon or Tusker-critical service is part of the base POC.

## Required inputs before build

1. A Fedora 44 x86_64 build host or a clean, reproducible Fedora 44 build VM.
2. KIWI NG version recorded from `kiwi-ng --version`; use a version supported by the current KIWI documentation and pin it for repeat builds.
3. QEMU/KVM and UEFI firmware (OVMF) installed.
4. A package manifest reviewed with NOVA-02. Plasma package names and the Fedora 44 login manager/session package set must be resolved against the exact enabled Fedora repository metadata. Do not guess package names from another Fedora release.
5. Repository metadata snapshot or a recorded repository metadata timestamp, plus resolved package NEVRAs.
6. PHOENIX-10 agreement on ISO installer behavior, disk image expectations and recovery requirements.

## Host preflight

Run from a clean checkout on Fedora 44 x86_64:

```bash
bash tools/atlas/poc-preflight.sh
```

The script is read-only. It checks host release, architecture, KIWI, QEMU, RPM, DNF, checksum tooling and reports optional virtualization/firmware gaps. It does not install dependencies or claim image validity.

Record the complete output in the POC evidence directory.

## Build procedure

The exact KIWI command and image description schema are deliberately gated on a minimal schema-validation commit. Do not copy a command from an older KIWI release without verifying it against the installed version.

Once `image/kiwi/description/` contains a reviewed, schema-valid description:

1. Record source commit and tool versions.
2. Resolve repositories and package inputs; store the exact resolved RPM NEVRAs.
3. Build in a clean workspace with no untracked source changes.
4. Save KIWI logs and exit status.
5. Inventory all output artifacts and compute SHA-256 checksums.
6. Build a second time from the same inputs and compare package manifest, metadata and artifact hashes. Explain nondeterministic fields rather than claiming bit-for-bit reproducibility.

## VM validation

Boot the QCOW2 using QEMU/KVM with UEFI firmware. Boot the ISO separately and verify the expected installer/live path with PHOENIX-10.

Minimum guest checks:

- UEFI boot reaches the expected boot menu and desktop/installer.
- Plasma Wayland session starts and user login succeeds.
- Keyboard, pointer, display resolution and basic rendering work.
- Network device appears and NetworkManager can connect.
- Storage is visible and usable.
- Audio devices enumerate through the Fedora audio stack.
- Shutdown and reboot complete.
- Tusker services are absent or disabled; KDE login and ordinary OS functions still work.
- Deliberately stop or mask any optional Tusker service and confirm the desktop remains usable.

Record guest logs, screenshots where useful, QEMU command line, firmware path/version and test results. VM evidence must not be represented as physical laptop compatibility.

## Evidence layout

Use a unique directory per run, for example:

```text
artifacts/atlas-poc/<source-commit>/
  host-preflight.txt
  kiwi-version.txt
  qemu-version.txt
  build.log
  package-nevras.txt
  repository-metadata.txt
  artifact-sha256.txt
  vm-boot.log
  guest-validation.md
  reproducibility.md
```

Do not commit large ISO/QCOW2 artifacts to Git. Store release candidates in the approved artifact store and commit checksums, metadata and provenance.

## Acceptance checklist

- [ ] Fedora 44 x86_64 host preflight passes.
- [ ] KIWI image description passes schema validation.
- [ ] KDE package manifest reviewed by NOVA-02 and resolved against Fedora 44 repositories.
- [ ] ISO build succeeds.
- [ ] QCOW2 build succeeds from the same package source.
- [ ] UEFI VM boot succeeds for both artifacts.
- [ ] Plasma Wayland login succeeds.
- [ ] Network, storage, audio enumeration, reboot and shutdown pass.
- [ ] Tusker-disabled desktop remains usable.
- [ ] Clean second build and package/artifact comparison completed.
- [ ] PHOENIX-10 reviews installer and recovery behavior.
- [ ] AEGIS-06 reviews Secure Boot and signing implications before support is claimed.

## Current blockers

- No build host or QEMU execution environment has been made available to this agent session.
- No KIWI image description or Fedora 44 package manifest has been validated by an actual DNF repository query.
- NOVA-02 and PHOENIX-10 contract confirmations are pending.
- Therefore no ISO/QCOW2 build, UEFI boot or reproducibility result is claimed.

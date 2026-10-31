# ATLAS-01 Build Technology Evaluation

**Phase:** P1.1 — image architecture  
**Date:** 2026-10-31  
**Status:** Research-backed provisional recommendation; production selection awaits a build/boot proof-of-concept.

## Executive recommendation

Use **KIWI NG as the leading candidate for the first unified custom desktop image pipeline**, subject to a Fedora 44 x86_64 proof-of-concept that produces and boots both a live/install ISO and an OEM/virtual disk artifact. KIWI NG 11.1.6 documents Fedora 43+ among its tested/supported build hosts and supports ISO and virtual disk image targets from one declarative image description.

Keep Fedora Image Builder/osbuild as a serious alternative and possible complementary tool for standard Fedora 44 image targets. Its Fedora 44 image catalogue is extensive, but the current workstation-live-installer blueprint only accepts installer customization and distro metadata, not package/group customizations. The generic-qcow2 target accepts package and service customizations but starts from a cloud-server base image. This creates a packaging mismatch for a highly customized KDE desktop if the objective is one canonical package manifest for both live ISO and VM output.

Do not select bootc as the mandatory update model yet. It has compelling transactional update and rollback properties, but changes the filesystem/update model and must be evaluated with PHOENIX-10's installer, recovery, and /etc state requirements. Do not treat bootc and Image Builder as interchangeable: bootc defines an OS deployment/update model; Image Builder composes artifacts.

## Requirements and evaluation criteria

- Fedora 44 currently supported; Fedora 45 GA transition must be explicitly reviewed.
- KDE Plasma and Wayland package set must be customizable.
- Build at least x86_64 UEFI media and a virtual disk image; keep aarch64 as a later target after CI/physical validation.
- Prefer one source description and one package manifest across output formats.
- Declarative, version-controlled, reviewable inputs.
- Build offline from a local package cache where practical; record repository metadata/snapshot inputs for release builds.
- Avoid executing untrusted shell hooks as root where a declarative feature exists.
- Produce useful logs, checksums, artifact metadata, and a clear build-host contract.
- VM boot tests must be automated and repeatable.
- The build tool must not impose a mandatory immutable root filesystem or make Tusker a boot dependency.

## Evidence-based comparison

| Candidate | Fedora 44 evidence | Custom desktop packages | ISO | VM/disk | Key limitation / role |
|---|---|---|---|---|---|
| KIWI NG 11.1.6 | Docs list Fedora 43+ in tested distributions | Image description contains packages/repositories/groups and controlled hooks | ISO live/install types documented | Virtual disk, OEM and cloud targets documented | Strong single-description candidate; validate Fedora 44 KDE live ISO and UEFI/BIOS behavior in POC |
| Fedora Image Builder / osbuild | Fedora 44 image descriptions are published and current as of 2026-10-30 | generic-qcow2 supports packages/groups/services; workstation-live-installer does not expose package customizations | workstation-live-installer and minimal-installer targets exist | generic-qcow2 and other disk targets exist | Excellent Fedora-native composition; image-type-specific customizations can split the desktop package workflow |
| Lorax / livemedia-creator | Fedora installer toolchain; current docs include livemedia-creator interface | Kickstart defines install content | Explicit live ISO output | Disk, filesystem, tar and other output modes | Best fallback if KIWI cannot satisfy Fedora-specific live installer behavior; verify current Fedora 44 workflow and maintenance |
| bootc | Fedora bootc docs include Fedora 44 base image example | Containerfile installs packages in image build | Needs a separate conversion/installer path | Disk-image conversion and image update workflow | Update/deployment model, not a standalone desktop ISO builder; /etc and /var semantics need recovery design |
| mkosi | systemd project actively maintained; wrapper around distro package managers | Highly configurable package-root build | Supports image artifacts, but desktop installer workflow is not its primary role | Disk and OCI artifacts | Excellent development/test harness; avoid making it a second production image pipeline without need |

## Detailed findings

### KIWI NG

Official documentation describes a two-step workflow: prepare creates a root tree from an image description and repositories; create produces one or more artifacts. The documentation states Fedora Linux 43+ is among the distributions officially tested/supported. It describes ISO live/install, virtual disk, OEM expandable disk, cloud and container targets.

Advantages:
- Single declarative image description and package/repository configuration.
- Multi-target outputs from a prepared root tree.
- Fedora 44 is within the documented Fedora 43+ support range.
- Supports custom boot configuration and UEFI/BIOS considerations.

Risks to test:
- Fedora 44 KDE/Plasma package group resolution.
- Live ISO boot and installer handoff.
- UEFI Secure Boot behavior and firmware-specific boot paths.
- Whether a single description can produce both desired install media and a clean VM disk without conditional customization drift.
- Rebuild reproducibility when upstream repositories change.

Official sources:
- https://osinside.github.io/kiwi/
- https://osinside.github.io/kiwi/image_description/elements.html
- https://osinside.github.io/kiwi/commands/kiwi.html

### Fedora Image Builder / osbuild

Official documentation describes TOML blueprints, versioned blueprint inputs and compose artifacts. Fedora 44 has a published image catalogue including workstation-live-installer, minimal-installer, generic-qcow2, kinoite-installer, and other outputs. The catalogue is generated from the current image-builder-cli and was updated 2026-10-30.

Critical compatibility detail:
- Fedora 44 workstation-live-installer supports only customizations.installer and distro beyond metadata; it does not list packages, groups, or arbitrary system customizations.
- Fedora 44 generic-qcow2 supports packages, groups, customizations.services, repositories and many system customizations, but its base package set is a Fedora Cloud Server image.
- Fedora 44 minimal-installer supports package/group customizations and may be a path to a custom Anaconda installer, but it is not a live KDE desktop ISO.
- Fedora 44 kinoite-installer is an Atomic KDE path, not the same thing as a conventional mutable Fedora KDE install.

This makes Image Builder viable but requires a POC to determine whether the custom KDE installer can be delivered without maintaining divergent package sets or an unwanted cloud/server base.

Official sources:
- https://osbuild.org/docs/user-guide/introduction/
- https://osbuild.org/docs/user-guide/blueprint-reference/
- https://osbuild.org/docs/user-guide/image-descriptions/fedora-44/
- https://osbuild.org/docs/user-guide/image-descriptions/fedora-44/workstation-live-installer/
- https://osbuild.org/docs/user-guide/image-descriptions/fedora-44/generic-qcow2/
- https://osbuild.org/docs/user-guide/image-descriptions/fedora-44/minimal-installer/

### Lorax / livemedia-creator

The documented workflow uses Anaconda, Kickstart and Lorax to create bootable media through the normal system installation path. It supports live ISO and partitioned disk image outputs. This is a credible Fedora-native fallback for a custom installer, but current Fedora 44 reproducibility and CI integration must be demonstrated before selection.

Source: https://weldr.io/lorax/livemedia-creator.html

### bootc

Fedora documentation describes bootable containers as OCI images containing the operating system, kernel and bootloader; updates deploy a new image and reboot into it. The documented filesystem model has immutable system content with /etc and /var as mutable state. Rollback semantics can restore /etc to the previous deployment state; persistent user data belongs under /var.

This could improve update consistency and rollback, but requires explicit design for:
- third-party kernel modules and driver delivery,
- system configuration persistence and migration,
- rollback of application/system state,
- image registry trust, signing and update cadence,
- installer and recovery integration,
- offline update staging and recovery.

Source: https://docs.fedoraproject.org/en-US/bootc/getting-started/

### mkosi

mkosi is documented by systemd as a wrapper around distro package managers (including DNF) to generate bespoke OS disk images. Its upstream repository has integration tests that build and boot full images. It is attractive for developer smoke tests or a build sandbox but is not yet the leading production choice for a user-facing live installer.

Source: https://github.com/systemd/mkosi

## Proof-of-concept gate

No tool is approved for production until this checklist is passed:

- [ ] Build host setup is scripted and documented; capture exact Fedora 44 host and tool versions.
- [ ] Build a minimal Fedora 44 x86_64 KDE/Plasma live/install ISO from version-controlled source.
- [ ] Build a Fedora 44 x86_64 UEFI virtual disk image from the same package source.
- [ ] Boot both outputs under QEMU/KVM with UEFI firmware; capture logs and artifact checksums.
- [ ] Verify KDE Plasma Wayland session can start and log in.
- [ ] Verify networking, audio device enumeration, storage visibility and shutdown in VM.
- [ ] Verify Tusker services are absent/disabled and the desktop remains usable.
- [ ] Repeat the build from a clean checkout and compare package manifests and artifact metadata.
- [ ] Document nondeterministic artifact fields; do not claim bit-for-bit reproducibility until measured.
- [ ] Review output artifact and install behavior with PHOENIX-10.

## Decision gate

**Current candidate:** KIWI NG for unified custom desktop artifacts.  
**Fallback:** Lorax/livemedia-creator for Fedora-native installer media, with a separately generated VM image only if necessary.  
**Alternative to retain:** Image Builder/osbuild, especially if the minimal-installer path can deliver the desired KDE install experience with a shared package manifest.  
**Not yet selected:** bootc deployment/update model.

This is a provisional architecture recommendation, not a completed build test or production tool lock. The next step is the POC gate above.

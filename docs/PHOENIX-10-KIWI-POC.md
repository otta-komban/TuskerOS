# PHOENIX-10 — Fedora 44 KIWI / Anaconda Proof of Concept

**Status:** Planned; not yet executed  
**Owner:** PHOENIX-10  
**Inputs:** ATLAS-01 provisional base/image recommendation (2026-10-31)  
**Target:** x86_64, Fedora 44, UEFI QEMU/KVM  
**Purpose:** Decide whether KIWI NG can produce TuskerOS desktop artifacts from one reviewed package source, and whether the resulting live ISO can launch a safe, supported Anaconda installation workflow.

## 1. Decision under test

The leading candidate is KIWI NG for image composition, conventional Fedora RPM/DNF for the first MVP, and Anaconda Live for installation. These are distinct components:

- KIWI NG composes a root tree and image artifacts from a declarative image description.
- The live ISO must include and successfully launch the selected Anaconda Live installer.
- An Anaconda install performs target-disk partitioning and OS installation.
- A KIWI OEM `installiso` is a separate direct-image deployment mode. It is not an Anaconda installer and is not accepted as a substitute without a separate product/security decision.

No custom installer UI or destructive install implementation is in scope until this POC and the NEXUS-07/AEGIS-06 contracts pass review.

## 2. Evidence baseline

- KIWI NG 11.1.6 documentation lists Fedora 43+ among tested/supported build-host distributions.
- Fedora 44 provides KIWI packages including `kiwi-systemdeps-iso-media` and `dracut-kiwi-live`.
- Fedora 44 provides `anaconda-live` and `anaconda-webui` packages.
- Fedora's Anaconda WebUI rollout documentation identifies unfinished areas for non-Workstation variants, including keyboard and timezone configuration. Therefore, package availability is not proof that the UI is production-ready for TuskerOS.
- Fedora's public image-building guidance recommends using the build tool used by the relevant Fedora variant and documents the KIWI workflow.
- Pagure was sunset in mid-2026 and is now an archive. The historical Fedora wiki still points at Pagure. Before cloning any Fedora KIWI descriptions, identify and record the current Fedora Forge canonical mirror/repository and the Fedora 44 release ref. Do not build from an archived Pagure checkout or an unpinned Rawhide branch.

## 3. Build host and source capture

Run on a disposable Fedora 44 x86_64 build VM or dedicated CI runner, not a user's workstation.

- [ ] Record `cat /etc/os-release`, `uname -a`, CPU architecture, available RAM and free disk.
- [ ] Record virtualization and build-host configuration.
- [ ] Record KIWI NG version (`kiwi-ng --version`) and all RPM NEVRAs for build dependencies.
- [ ] Verify exact package availability before installation:
  - [ ] `kiwi`
  - [ ] `kiwi-systemdeps-iso-media`
  - [ ] `dracut-kiwi-live`
  - [ ] QEMU/KVM and OVMF/UEFI firmware packages appropriate to the Fedora 44 host
- [ ] Identify current Fedora Forge repository URL for Fedora KIWI descriptions and its Fedora 44 release branch/ref.
- [ ] Record exact Git commit and verify repository provenance.
- [ ] Preserve upstream description files and wrapper scripts; make Tusker changes in a clearly separated overlay/patch.
- [ ] Pin Fedora repository IDs and metadata snapshot/timestamp for the POC.
- [ ] Record any external repository and its signing key, owner, license and justification; default is Fedora official repositories only.

KIWI upstream recommends at least 15 GB free disk for a build. A KDE desktop build will require additional working space; record actual peak usage and do not treat 15 GB as a Tusker sizing guarantee.

## 4. POC build sequence

### 4.1 Toolchain smoke test

- [ ] Install KIWI and the Fedora 44 live-ISO host dependencies from Fedora repositories.
- [ ] Run `kiwi-ng --version`.
- [ ] Run the upstream/Fedora-maintained build wrapper against a small known Fedora 44 profile to prove the toolchain, package resolution and output bundling work.
- [ ] Capture complete stdout/stderr, exit status, build duration, package list and checksums.
- [ ] If the official source repository/ref is unavailable or no longer maintained, stop and raise the source-of-truth issue rather than silently using a mirror of unknown provenance.

### 4.2 Tusker desktop ISO

- [ ] Start from the Fedora 44 KDE/Plasma profile or closest official live profile in the pinned Fedora KIWI descriptions.
- [ ] Add only the package layer changes accepted by ATLAS-01 and NOVA-02.
- [ ] Include the Fedora live-install path and Anaconda Live dependencies.
- [ ] Verify the installer launch mechanism, desktop session, user/session setup and logs.
- [ ] Build an x86_64 hybrid UEFI ISO.
- [ ] Verify artifact type, size, checksum, embedded release identity and package manifest.
- [ ] Boot ISO under QEMU/KVM with OVMF in UEFI mode; capture serial and journal logs.
- [ ] Verify KDE Plasma Wayland login, networking, storage enumeration, audio device enumeration, shutdown and restart.
- [ ] Verify the desktop remains usable with all Tusker services absent or disabled.
- [ ] Launch Anaconda; verify language/keyboard/timezone, disk selection, manual/custom storage availability, encryption options, destructive-action summary, confirmation, install and reboot.
- [ ] Record any Anaconda WebUI gaps; test the supported fallback installer if a required screen/flow is incomplete.

### 4.3 Tusker QCOW2

- [ ] Build x86_64 UEFI QCOW2 from the same reviewed package source and version identity.
- [ ] Boot QCOW2 under QEMU/KVM with OVMF.
- [ ] Verify first boot, KDE session, networking, storage, audio enumeration and shutdown.
- [ ] Verify no required Tusker service is a hard dependency for login.
- [ ] Compare resolved RPM NEVRAs with the ISO build; document intentional differences (live-only packages, installer packages, kernel/boot packages).
- [ ] Record disk layout, filesystem, bootloader and first-boot behavior.

## 5. Secure Boot gate

UEFI boot is not Secure Boot validation.

- [ ] Record OVMF firmware variant and Secure Boot state.
- [ ] Verify the complete boot chain: firmware trust database, shim, GRUB/systemd-boot as selected, kernel and initramfs.
- [ ] Confirm signatures and key enrollment/trust model using AEGIS-06's proposed policy.
- [ ] Test both Secure Boot enabled and disabled.
- [ ] Test rejection of an intentionally unsigned/untrusted boot component in a disposable VM.
- [ ] Confirm recovery media follows the same trust policy.
- [ ] Do not claim Secure Boot support until all checks pass on at least one VM and a representative physical device.

## 6. Reproducibility and provenance

- [ ] Run the same build twice from clean checkouts and identical declared inputs.
- [ ] Compare source commit, Fedora repo metadata snapshot, KIWI version, package NEVRAs, generated metadata and artifact hashes.
- [ ] Distinguish expected nondeterminism (timestamps, filesystem UUIDs, generated identifiers) from unexplained drift.
- [ ] Do not claim bit-for-bit reproducibility unless the artifact hashes match or nondeterministic fields are normalized and verified.
- [ ] Retain build logs, package manifests, checksums, source commit, tool versions and SBOM/provenance output.
- [ ] Generate a build report with PASS/FAIL/BLOCKED for every gate; never infer pass from a successful command alone.

## 7. Installer authorization and typed-operation contract\n\nThe POC must validate the installer boundary against NEXUS-07 and AEGIS-06 proposals before implementing writes:\n\n- [ ] Define a typed operation for selecting/preflighting a target disk; no arbitrary command or raw shell string.\n- [ ] Resolve a stable device identity and precondition snapshot; do not use enumeration order or a transient `/dev/sdX` name as the sole identity.\n- [ ] Bind the approval to an immutable action digest, exact disk identity, partition plan, requester, policy version and expiry.\n- [ ] Revalidate identity and preconditions immediately before the write; reject stale approval or changed target.\n- [ ] Return a structured operation result with status, side effects, operation ID and postcondition state.\n- [ ] Treat timeout/uncertain completion as `unknown_outcome`; query state before retrying.\n- [ ] Emit correlated audit events without passwords, LUKS keys, recovery keys or private data.\n- [ ] Ensure recovery path does not depend on AI runtime or the normal Tusker daemon.\n\nNEXUS-07 owns the operation/execution contract; AEGIS-06 owns risk, approval and audit policy. PHOENIX-10 owns the installer workflow and tests only after both owners confirm the boundary.\n\n## 8. Install safety test matrix

All destructive tests use disposable virtual disks only. No developer or host disk is a target.

| Test | Expected result |
|---|---|
| One empty target disk | Installer shows exact disk identity and complete change summary before confirmation |
| Two disks attached | No default target; user explicitly chooses one; second disk remains unchanged |
| USB/removable disk present | Removable status is visible; never auto-selected |
| Target removed/re-attached or identity changes | Installer aborts before destructive writes |
| Unsupported/ambiguous storage topology | Fail closed with diagnostic and safe exit |
| Encryption enabled | User sees recovery-key custody warning; secrets never enter logs |
| Install cancelled before confirmation | No target disk modifications |
| Install interrupted after partitioning | Clear failure state and documented recovery; no false claim of rollback |
| Secure Boot enabled with trusted chain | Boot succeeds only when trust policy is satisfied |
| Untrusted boot component | Boot is rejected by configured trust chain |

## 9. Acceptance criteria

The POC passes only if all required items are evidenced:

- [ ] A pinned Fedora 44 KIWI description and toolchain build without undocumented manual steps.
- [ ] A live/install ISO and UEFI QCOW2 are produced from the same reviewed package source.
- [ ] Both artifacts boot in QEMU/KVM with UEFI firmware.
- [ ] KDE Plasma Wayland login, networking, storage, audio enumeration and shutdown pass.
- [ ] The ISO launches Anaconda Live and the complete supported install path is demonstrated against a disposable VM disk.
- [ ] The installer does not touch a non-selected disk and aborts on target identity change.
- [ ] Secure Boot status is explicitly tested and reported; unsupported behavior is clearly documented.
- [ ] RPM NEVRAs, source refs, tool versions, build logs and SHA-256 checksums are retained.
- [ ] A clean second build is compared and nondeterminism documented.
- [ ] ATLAS-01, NEXUS-07 and AEGIS-06 review their respective base, hardware and security contracts.

A failed required item means the POC is **FAIL** or **BLOCKED**, not "mostly supported". If KIWI fails the live ISO or Anaconda integration, evaluate Lorax/livemedia-creator for installer media while preserving a single reviewed package manifest where feasible.

## 10. Evidence record template

For each run, append a report under `tests/installer/poc/<date>-<run-id>/` containing:

- Host OS, architecture, firmware, CPU/RAM/disk and build tool versions.
- Upstream Fedora KIWI repository URL, branch/ref and commit.
- Tusker source commit and image-description diff.
- Fedora repository IDs/metadata timestamps.
- Build commands, logs, exit codes and duration.
- Artifact names, sizes, SHA-256 hashes and package manifests.
- QEMU/KVM command lines, OVMF firmware files and Secure Boot state.
- Screenshots/log excerpts for desktop, Anaconda and storage tests.
- Test matrix PASS/FAIL/BLOCKED with defect references.
- Known limitations and reviewer sign-off.

## 11. References

- Fedora image-building guide: https://fedoraproject.org/wiki/Building_a_Fedora
- Fedora KIWI descriptions (historical project page; Pagure is archived): https://pagure.io/fedora-kiwi-descriptions/
- Fedora Forge (canonical current repository location must be confirmed before use): https://forge.fedoraproject.org/
- KIWI NG 11.1.6: https://osinside.github.io/kiwi/
- KIWI NG quick start: https://osinside.github.io/kiwi/quickstart.html
- KIWI NG image types and output metadata: https://osinside.github.io/kiwi/image_types_and_results.html
- KIWI NG image-description schema: https://osinside.github.io/kiwi/image_description/elements.html
- Fedora 44 KIWI live ISO dependencies: https://packages.fedoraproject.org/pkgs/kiwi/kiwi-systemdeps-iso-media/
- Fedora 44 KIWI live dracut module: https://packages.fedoraproject.org/pkgs/kiwi/dracut-kiwi-live/
- Fedora 44 Anaconda Live package: https://packages.fedoraproject.org/pkgs/anaconda/anaconda-live/
- Fedora 44 Anaconda WebUI package: https://packages.fedoraproject.org/pkgs/anaconda-webui/anaconda-webui/
- Anaconda WebUI Fedora Spins readiness notes: https://fedoraproject.org/wiki/Changes/AnacondaWebUIforFedoraSpins

## 12. Cross-agent contract inputs

Reviewed on 2026-10-31:

- NEXUS-07 `system-integration/INTERFACE_CONTRACTS.md` on `07-system-integration`: typed request/result envelope, mutation metadata, stable errors, deadlines, idempotency, postconditions and unknown-outcome semantics.
- AEGIS-06 `security/SECURITY_ARCHITECTURE.md` on `06-security-gatekeeper`: deterministic policy, deny-by-default, exact action-digest approval binding, one-time expiry, broker validation and audit requirements.
- ATLAS-01 `os/BASE-SYSTEM-CONTRACTS.md` on `01-fedora-base`: recovery must not depend on Tusker daemon/model; no arbitrary root API; package/service ownership remains with the responsible agent.

These are proposals pending cross-agent approval. They are not runtime implementations and do not authorize PHOENIX-10 to create privileged operations independently.

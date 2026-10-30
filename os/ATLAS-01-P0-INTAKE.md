# ATLAS-01 P0 Intake and Phase 1 Plan

**Agent:** ATLAS-01 — Fedora Base & OS Build Engineer  
**Branch:** `01-fedora-base`  
**Repository:** `otta-komban/TuskerOS`  
**Plan date:** 2026-10-31  
**Status:** P0 intake recorded; implementation architecture remains provisional pending validation.

## 1. Mission and invariants

Deliver a supported Fedora-based foundation, a maintainable image build workflow, modular package composition, and reliable OS defaults for TuskerOS. The base operating system must remain fully usable when Tusker, model runtimes, remote-control services, themes, or optional developer components are absent, disabled, or broken.

Non-negotiable invariants:

- Fedora-supported packages and repositories only by default; document any third-party repository exception and its trust/licensing implications.
- Local-first and offline-capable operation; no cloud inference or paid API dependency.
- No AI service is required for boot, login, KDE Plasma, networking, updates, or recovery.
- Least privilege: no unrestricted root process for Tusker; privileged operations are owned by AEGIS-06/NEXUS-07.
- Keep the base lean; large models, developer toolchains, and optional services are not part of the mandatory base.
- Reproducible build inputs, explicit versions/refs, verifiable artifacts, SBOM/provenance where supported.
- Distinguish CI, VM, and physical-hardware evidence. Never claim hardware compatibility based only on a VM.

## 2. Repository and branch baseline

Inspected on 2026-10-31:

- Repository exists and is accessible.
- Default branch is `main`.
- Working branch `01-fedora-base` exists.
- Branch head at intake: `8c463dcec409fc9354b2adcb9b51a722d7c97fe5` (initial commit).
- Branch root contains only `LICENSE`.
- No `logs/` or `coordination/` directory exists on this branch.
- No existing build scripts, package manifests, OS configuration, CI, or tests were found.

This is a greenfield branch. Do not infer implementation or test status from planning documents.

## 3. Fedora release assessment (initial, time-sensitive)

As of 2026-10-31, Fedora 44 is the current released KDE Plasma desktop download and a supported stable baseline. Fedora 45 is still pre-release on 2026-10-31: the Fedora 45 final Go/No-Go meeting on 2026-10-29 declared the release GO, with the target date of 2026-11-03. Therefore:

- **Provisional development baseline: Fedora 44.**
- Do not pin production images to Fedora 45 until Fedora Project marks it GA and the selected build tooling supports it in a stable/reproducible way.
- Re-evaluate Fedora 45 immediately after GA and record an explicit upgrade decision/ADR.
- Track Fedora lifecycle on the official Releases/Lifecycle pages; plan upgrades before EOL rather than treating the minor release number as a permanent base.

Sources checked:
- Fedora KDE download page: https://fedoraproject.org/kde/download/
- Fedora 45 final Go/No-Go meeting log: https://meetbot.fedoraproject.org/meeting_matrix_fedoraproject-org/2026-10-29/f45-final-go-no-go-meeting.2026-10-29-18.02.html
- Fedora release lifecycle: https://docs.fedoraproject.org/en-US/releases/lifecycle/
- Fedora image building overview: https://fedoraproject.org/wiki/Building_a_Fedora

## 4. Build technology evaluation — no final selection yet

Evaluate at least:

1. **Fedora Image Builder / osbuild:** Fedora-native declarative image composition; inspect supported output types, installer path, customization support, build host requirements, CI suitability, and release maturity.
2. **bootc + image-builder:** immutable/image-based update model; assess operational benefits against complexity, rollback semantics, package layering constraints, installer and recovery integration.
3. **KIWI:** used by several Fedora variants; compare existing Fedora descriptions, profile support, and maintenance burden.
4. **Lorax / livemedia-creator / Kickstart / Anaconda:** assess where these remain the supported route for a live ISO or installer composition.
5. **mkosi:** evaluate as a developer/test harness, not assume it is the best production distribution pipeline.

Do not combine multiple image systems prematurely. Choose one primary supported path after a small reproducible proof-of-concept and document the reason in an ADR. Keep image composition, package manifests, and release assembly separable.

## 5. Phase 1 (P1) architecture plan

### P1.1 Base and image architecture
- [x] Compare Image Builder/osbuild, bootc, KIWI NG, Lorax/livemedia-creator and mkosi against a written decision matrix (see os/BUILD-TOOL-EVALUATION.md).
- [ ] Select the first supported Fedora release after verifying lifecycle and KDE/Wayland compatibility.
- [ ] Define image variants and artifact targets (development VM first; installer/live media only in coordination with PHOENIX-10).
- [ ] Define architecture support explicitly; begin with x86_64 unless build/test evidence supports additional architectures.
- [ ] Record an architecture decision record with alternatives, trade-offs, evidence, and review date.

### P1.2 Package and layer contracts
- [x] Define logical package layers: base core, KDE desktop, Tusker integration, diagnostics, optional developer tools, optional model/runtime and remote control (see os/BASE-SYSTEM-CONTRACTS.md).
- [x] Define provisional package source policy, RPM signature verification, third-party repository exception process, license inventory and update cadence (see os/BASE-SYSTEM-CONTRACTS.md).
- [x] Define optional component install/disable/remove requirements without coupling the base to Tusker (see os/BASE-SYSTEM-CONTRACTS.md).
- [ ] Define package naming/versioning and dependency ownership for other agents' components.
- [ ] Coordinate image/package interfaces with PHOENIX-10 before installer/release implementation.

### P1.3 System integration contracts
- [x] Document provisional systemd unit conventions, service account, filesystem ownership, hardening boundaries, dependencies and failure behavior (see os/BASE-SYSTEM-CONTRACTS.md).
- [x] Document provisional D-Bus, Polkit, journald, filesystem and user-session boundaries (see os/BASE-SYSTEM-CONTRACTS.md).
- [x] Define requirement that Tusker services are independently disableable and non-blocking for desktop login (see os/BASE-SYSTEM-CONTRACTS.md).
- [ ] Coordinate KDE session assumptions with NOVA-02.
- [ ] Coordinate hardware/system capability interfaces with NEXUS-07.
- [ ] Coordinate privileged service boundaries with AEGIS-06.

### P1.4 Reproducibility, supply chain and release inputs
- [x] Define provisional pinned build-input and controlled-update policy; avoid unreviewed floating refs for release builds (see os/BUILD-TOOL-EVALUATION.md and os/BASE-SYSTEM-CONTRACTS.md).
- [x] Define required build metadata fields: source revision, Fedora release, architecture, package NEVRAs, repository metadata, tool versions and checksums (see os/BUILD-TOOL-EVALUATION.md).
- [ ] Define checksum/signature verification and SBOM/provenance outputs supported by chosen toolchain.
- [ ] Define CI validation and image smoke-test boundaries.
- [ ] Define clean rebuild and artifact comparison criteria; document known non-deterministic inputs.

### P1.5 Quality and acceptance contracts
- [ ] Define boot/login/network/display/audio/input/shutdown smoke tests for a disposable UEFI VM.
- [ ] Define Tusker-disabled and Tusker-crash desktop availability tests.
- [ ] Define package install/remove/upgrade and repository-unavailable failure tests.
- [ ] Define performance measurements for boot time, idle RAM/CPU, disk footprint and service startup; establish targets only after baseline measurement.
- [ ] Define a hardware matrix for UEFI/Secure Boot, Wi-Fi, Bluetooth, audio, GPU, touchpad, suspend/resume and firmware.
- [ ] Report physical hardware coverage separately from virtual-machine coverage.

## 6. P0/P1 risks and mitigations

| Risk | Impact | Mitigation / owner |
|---|---|---|
| Fedora 45 schedule delay or release regressions | Unstable base selection | Use Fedora 44 provisionally; re-check after GA; ATLAS |
| Fedora short lifecycle | Unsupported installed systems | Publish upgrade cadence and lifecycle checks; ATLAS + PHOENIX |
| Image-builder/bootc tooling mismatch with desired live installer | Build pipeline rework | Prototype outputs before selection; ATLAS + PHOENIX |
| Immutable update model adds operational complexity | Recovery/driver customization risk | Compare mutable and image-based paths; ADR before commitment |
| KDE and Wayland integration drift | Login/session failures | Use Fedora KDE baseline and cross-agent test contract; NOVA |
| Tusker service becomes boot/login dependency | OS unusable when AI fails | Separate optional units, dependencies and failure tests; ATLAS + AEGIS |
| Third-party repositories or proprietary drivers | Supply-chain/licensing/support risk | Explicit opt-in policy, provenance and documented exceptions; ATLAS |
| VM results mistaken for hardware support | Misleading compatibility claims | Separate evidence classes and publish hardware matrix; ATLAS + PHOENIX |

## 7. Dependencies and coordination requests

- **NOVA-02:** request KDE Plasma/Wayland session assumptions, required packages, D-Bus names, user-session integration points and desktop startup requirements.
- **NEXUS-07:** request system capability discovery contract, supported OS tool/service dependencies, D-Bus and systemd requirements.
- **AEGIS-06:** request Polkit action naming/ownership, privileged broker packaging expectations, service account and hardening requirements.
- **PHOENIX-10:** request target installer/media format, first-boot and update model assumptions, image metadata/signing contract, and recovery/rollback expectations.

Until these interfaces are agreed, use provisional examples only; do not publish incompatible service names or package contracts as final.

## 8. Immediate execution sequence

1. Record this P0 intake and plan on `01-fedora-base`.
2. Establish the ATLAS JSONL completion log and readable ledger on this branch.
3. Research official Fedora lifecycle and image tooling; capture the release-date caveat.
4. Produce a small image-builder/bootc/KIWI/Lorax comparison and a decision matrix.
5. Open coordination issues for NOVA-02, NEXUS-07, AEGIS-06 and PHOENIX-10.
6. Complete the P1 architecture ADR and package/service contracts.
7. Only then start P2 build skeleton and manifests; no production image pipeline is claimed at this stage.

## 9. Phase 1 research and coordination evidence\n\n- Build-tool comparison: [os/BUILD-TOOL-EVALUATION.md](BUILD-TOOL-EVALUATION.md).\n- Provisional package/system integration contracts: [os/BASE-SYSTEM-CONTRACTS.md](BASE-SYSTEM-CONTRACTS.md).\n- Hardware compatibility and base-install policy: [os/HARDWARE-COMPATIBILITY.md](HARDWARE-COMPATIBILITY.md).\n- PHOENIX-10 image/update model response: [GitHub issue #2](https://github.com/otta-komban/TuskerOS/issues/2).\n- NEXUS-07 system interface review request: [GitHub issue #5](https://github.com/otta-komban/TuskerOS/issues/5).\n\nP0 discovery evidence now includes the Fedora release assessment, build-tool comparison, hardware requirements matrix, hardware-tier strategy, base-install profiles and package-source/driver policy. Actual physical-device inventory and testing remain open. The build-tool selection and update model remain provisional until the POC and cross-agent reviews are complete.\n\n## 10. Exit criteria

P0 is complete when the branch/repository baseline, supported-release research, requirements, risks, ownership boundaries and acceptance criteria are documented. P1 is complete only when the architecture/tool decision, package/service contracts, reproducibility plan and dependent-agent interfaces have reviewable records. A document or plan is not a bootable image and is not a passed test.

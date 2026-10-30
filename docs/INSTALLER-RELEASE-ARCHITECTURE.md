# PHOENIX-10 — Installer, Update, Recovery & Release Architecture

**Status:** Phase 1 proposal; architecture decisions remain provisional pending ATLAS-01 and security review  
**Owner:** PHOENIX-10  
**Branch:** `10-installer-recovery`  
**Last reviewed:** 2026-10-31  
**Scope:** `installer/`, `updates/`, `recovery/`, release automation, installation/update/recovery tests and release documentation

## 1. Repository intake and project constraints

The TuskerOS master blueprint defines a Fedora-based, KDE Plasma distribution; local-first/offline-capable operation; least privilege; explicit approval for destructive actions; modularity; and evidence-backed claims. PHOENIX-10 owns installation, first boot, updates, backup/restore, recovery, release assembly, release test matrix and published artifacts.

The blueprint's phase gates apply unchanged: P0 discovery, P1 architecture/contracts, P2 foundation, P3 working MVP, P4 feature completion, P5 integration, P6 verification/hardening and P7 release/handover. The 100-response goal is accounting only, not a quality or delivery substitute.

### Verified repository baseline (2026-10-31)

- Repository: `otta-komban/TuskerOS`; public; default branch `main`.
- At intake, `main` and `10-installer-recovery` contained only `LICENSE` (Apache-2.0). The PHOENIX-10 branch now contains the architecture and completion records described in this work log.
- The assigned branch already exists at commit `8c463dcec409fc9354b2adcb9b51a722d7c97fe5` (initial commit); it is unprotected.
- No README, source tree, build scripts, CI workflows, coordination files, issues or pull requests were present at intake.
- At initial intake no Fedora version, image format, package manifest, release key, artifact registry or test hardware was selected. ATLAS-01 has since proposed Fedora 44, mutable RPM/DNF, KIWI NG, x86_64 UEFI ISO and QCOW2 as provisional POC targets; none is production-approved.
- The Project Markdown blueprint is the planning source; its proposed coordination files have not yet been committed to this repository.

Do not assume an absent contract, image or upstream agent deliverable exists. Keep integration decisions provisional until owners confirm them.

## 2. Technology assessment and provisional direction

Research checked on 2026-10-31 against upstream documentation:

| Technology | Relevant capability | PHOENIX-10 assessment |
|---|---|---|
| KIWI NG | Fedora-supported image composition; declarative package/repository descriptions; live ISO and OEM/virtual-disk outputs | Leading POC candidate for the mutable Fedora 44 desktop image pipeline; production selection depends on Fedora 44 KDE/Wayland ISO and QCOW2 boot tests |
| Anaconda Live installer | Fedora live-install workflow, storage/user setup and guided/manual partitioning | Candidate installation engine inside the live ISO; verify Fedora 44 KDE integration and WebUI readiness; retain supported fallback |
| Fedora Image Builder / osbuild | Fedora-native blueprint and image composition with multiple image types | Retained alternative; ATLAS-01 identified Fedora 44 package-customization limitations in workstation-live-installer vs generic-qcow2 |
| Lorax / livemedia-creator | Fedora installer-media composition with Kickstart and Anaconda | Fallback if KIWI cannot produce a reliable Fedora 44 KDE live installer ISO |
| Fedora bootc / rpm-ostree | Image-based OS deployment, staged update and rollback model | Future option only; not the first MVP update model unless ATLAS-01 and PHOENIX-10 approve persistence, migration and recovery semantics |
| Traditional RPM/DNF | Mutable Fedora package-managed OS and familiar RPM transaction model | Provisional first-MVP update model; PHOENIX-10 must not claim bootc-style atomic rollback |

### Provisional recommendation (ADR-PHX-001; reconciled with ATLAS-01 on 2026-10-31)

ATLAS-01 has supplied a research-backed proposal in `01-fedora-base`:

- Fedora 44 is the provisional stable development baseline.
- Fedora 45 has a GO decision but was not yet GA on the date of that proposal; do not pin release artifacts to it before GA and post-GA validation.
- Keep the first MVP on conventional mutable Fedora RPM/DNF unless the master plan explicitly requires image-based updates.
- KIWI NG is the leading image-composition candidate because one declarative description may produce both a custom live/install ISO and a virtual disk image.
- Initial artifact POC targets are x86_64 UEFI hybrid ISO and x86_64 UEFI QCOW2. aarch64 is deferred until CI and hardware/VM validation.
- Secure Boot must be tested independently; UEFI boot success is not proof of Secure Boot support.

**PHOENIX-10 position:** accept these as the POC baseline, not as frozen production decisions. The POC must build from a version-controlled package source, boot both artifacts in QEMU/KVM with UEFI firmware, verify KDE Plasma/Wayland and core hardware services, and capture logs, checksums and resolved RPM NEVRAs. See `docs/PHOENIX-10-KIWI-POC.md`.

**Installer distinction:** KIWI image composition and Anaconda installation are separate concerns. A KIWI live ISO can be used as the environment that launches Anaconda; a KIWI OEM `installiso` is a different direct-image deployment flow and must not be represented as the Anaconda installer. The POC must explicitly verify the chosen live ISO launches a supported Anaconda installer, including storage UI and destructive-operation safeguards. Fedora's Anaconda WebUI is available in Fedora 44 packages, but its suitability for TuskerOS KDE, partitioning, keyboard and locale workflows must be tested; keep the existing supported installer path as a fallback until validated.

**Bootc remains deferred.** It offers attractive deployment-based updates and rollback, but changes filesystem, configuration and recovery semantics. Revisit only after a separate ADR evaluates `/etc` migration/rollback, `/var` persistence, drivers, offline updates, installer and recovery. Do not conflate an image builder with an OS update model.

**Build pipeline:** prefer Fedora's maintained KIWI descriptions and build wrapper as the initial reference rather than inventing a Fedora boot pipeline from scratch. Fork/adapt only the minimum required, retain upstream provenance and pin the release branch/repository metadata for repeatable builds.

### Primary research sources

- Fedora image-building guidance and Fedora's KIWI workflow: https://fedoraproject.org/wiki/Building_a_Fedora
- Fedora-maintained KIWI descriptions: https://pagure.io/fedora-kiwi-descriptions
- KIWI NG 11.1.6 documentation and supported build-host list: https://osinside.github.io/kiwi/
- KIWI image-description schema: https://osinside.github.io/kiwi/image_description/elements.html
- KIWI image types and output metadata: https://osinside.github.io/kiwi/image_types_and_results.html
- Fedora 44 KIWI live-ISO host dependencies: https://packages.fedoraproject.org/pkgs/kiwi/kiwi-systemdeps-iso-media/
- Fedora 44 KIWI live-image dracut module: https://packages.fedoraproject.org/pkgs/kiwi/dracut-kiwi-live/
- Fedora 44 Anaconda live-install package: https://packages.fedoraproject.org/pkgs/anaconda/anaconda-live/
- Fedora 44 Anaconda WebUI package: https://packages.fedoraproject.org/pkgs/anaconda-webui/anaconda-webui/
- Fedora Anaconda WebUI for Spins status and known caveats: https://fedoraproject.org/wiki/Changes/AnacondaWebUIforFedoraSpins
- Fedora 44 KDE edition and official verification instructions: https://fedoraproject.org/kde/download/

This is an evidence-backed POC direction, not a completed compatibility test or production tool lock.

## 3. System architecture

### 3.1 Build and release pipeline

```text
Reviewed source + pinned build inputs
        |
        v
Fedora base/image definition (ATLAS-01 owns)
        |
        v
Image composition (KIWI NG POC; retain osbuild/Lorax alternatives)
        |
        +--> package/dependency manifest + SBOM
        +--> build metadata + provenance attestation
        |
        v
Live/install media (KIWI NG) -> Anaconda Live installer (only after KDE/storage UX validation)
        |
        v
Automated VM install / boot / smoke / recovery tests
        |
        v
Release candidate (immutable version + digest)
        |
        v
Independent artifact verification + signing
        |
        v
Staged publication -> release manifest/checksums/notes
        |
        v
Update channel metadata -> client staged update -> health gate
        |
        +--> accept deployment
        +--> retain previous deployment / rollback
        +--> recovery media and user-data restore path
```

Build inputs must be versioned: source commit, Fedora release/repositories, image definition, package locks or repository snapshot identifiers, build tool versions, architecture, build environment and signing identity. Reproducibility target is initially *repeatable with fully declared inputs*; bit-for-bit reproducibility is a stronger claim and must be demonstrated, not assumed.

### 3.2 Installer stages

1. Boot media and verify signed boot chain where supported by the chosen Fedora/firmware configuration.
2. Run hardware and storage discovery; show clear machine-readable device identity (model, capacity, serial suffix where safe, bus) and distinguish removable media.
3. Preflight: architecture, RAM/storage thresholds, firmware mode, Secure Boot status, power, target availability, network requirement (if any), existing OS and encryption state.
4. Present install mode: guided clean install first; advanced/manual partitioning only after tests; dual-boot only when explicitly supported and tested.
5. Show an explicit destructive-operation summary: target disk, partitions to be created/removed, encryption choice, data-loss warning and final confirmation.
6. Apply partition/filesystem/encryption layout using supported Anaconda storage APIs/Kickstart; fail closed on ambiguous or changed device identity.
7. Deploy image and bootloader; verify deployment/image identity and installer result.
8. Configure initial user and first-boot setup without logging secrets.
9. Reboot to installed system, run first-boot readiness checks and provide a useful diagnostic/recovery path if setup fails.

**Safety invariants**
- No disk write before a user confirms a specific target and a rendered change summary.
- Never default to the first disk or infer a target from enumeration order.
- Re-enumerate and revalidate the selected device immediately before destructive writes; abort if identity/capacity/topology changed.
- Installation must not silently repartition a second disk.
- No plaintext passwords, LUKS keys, recovery keys or tokens in logs, Kickstart artifacts, crash reports or telemetry.
- If encryption is selected, recovery-key handling and backup responsibility must be explicit; never imply TuskerOS can recover a lost key.
- A cancel/failure path must leave the user with a clear status and safe next step; do not claim rollback of a partially modified disk unless it is actually implemented.

### 3.3 First boot

First-boot setup is idempotent and resumable. It should:
- complete account/session onboarding and locale/time-zone/network choices;
- verify storage, boot deployment, package/image identity, networking, audio/display/input basics and firmware state where available;
- apply default theme and desktop choices through NOVA-02/PIXEL-03 contracts;
- offer optional model selection/download through ORBIT-05 without requiring cloud inference;
- expose diagnostics and support information;
- mark setup complete only after required steps pass; optional network/model steps may be deferred;
- safely resume after power loss without repeating destructive operations.

### 3.4 Updates and rollback

For the provisional mutable RPM/DNF MVP:
- fetch metadata and image by immutable digest, validate trust policy, architecture, channel and minimum version;
- stage/download without changing the running deployment;
- verify disk space, image signature/provenance and compatibility before activation;
- schedule reboot/activation with user-visible control and clear deferral;
- run post-boot health checks; record the deployment that was booted and test result;
- keep a known-good deployment and expose a documented rollback path;
- suppress/reconcile automatic update scheduling during rollback so the failed release is not immediately reapplied;
- handle boot failure, interrupted downloads and failed health checks without corrupting the currently running deployment.

For a traditional mutable RPM/DNF base, do not claim bootc-style atomicity. Define package transaction policy, snapshots (if available), backups and recovery separately with ATLAS-01.

### 3.5 Backup and restore boundaries

Backup targets are user-selected and documented:
- user files and selected application data;
- Tusker settings/preferences and user-approved conversation/history export;
- system configuration allowlist, with secrets excluded or separately protected;
- optional large model files as an explicit opt-in.

Exclude by default: caches, temporary files, runtime sockets, secrets/credentials, ephemeral state, package databases that cannot safely be restored independently, and system files already supplied by the OS image. Provide versioned manifests, checksums, encryption-at-rest options, retention controls and restore previews. Restore must prevent path traversal, symlink escape and overwrite of unrelated files; it must support dry-run and conflict handling.

## 4. Security and release integrity

- Build in a controlled CI environment from reviewed commits and pinned inputs; use least-privilege short-lived CI credentials.
- Sign release metadata and artifacts with a dedicated release identity; keep private signing keys outside the repository and ordinary build runners.
- Publish SHA-256 (and optionally stronger) checksums plus detached signatures; verification instructions must use a separately trusted public key/fingerprint.
- Use a versioned manifest containing release version, architecture, image/media type, byte size, digest, signature reference, source commit, Fedora base, build recipe/tool versions, SBOM and provenance references, channel and minimum supported updater version.
- Generate an SBOM (SPDX or CycloneDX, decision pending ATLAS-01/toolchain) and provenance attestation; retain build logs and test reports with the artifact.
- Protect against rollback/downgrade attacks with signed metadata, monotonic version/security epoch policy and explicit downgrade authorization for recovery.
- Validate repository/channel metadata, image digests, TLS and signatures before install/update; fail closed on unknown keys, invalid signatures, wrong architecture or malformed metadata.
- Rotate signing keys with documented overlap, revocation and emergency response procedures.
- Separate developer/test keys from production release keys. Never publish a test-signed artifact as stable.
- Release is blocked by unresolved critical security/data-loss defects unless the Chief Architect records an explicit accepted exception.

## 5. Cross-agent contracts and dependencies

| Partner | Required agreement |
|---|---|
| ATLAS-01 | Fedora release/lifecycle, rootfs model (bootc vs mutable), image format, image build outputs, package/service manifests, bootloader/Secure Boot expectations, update substrate and base rollback semantics |
| NEXUS-07 | Hardware/storage inventory API, health-check interfaces, safe system service operations, recovery diagnostics and postcondition/event schema |
| AEGIS-06 | Signature/trust policy, privileged action approvals, disk-operation authorization boundary, audit events, key/secret handling and recovery permissions |
| NOVA-02 | First-run UX, progress/error states, update/reboot prompts and recovery affordances |
| PIXEL-03 | Installer/first-boot theme defaults and safe fallback |
| ORBIT-05 | Optional model setup/download and model backup policy |
| FORGE-09 | Package/extension compatibility metadata, signed bundle/provenance conventions |
| TUSKER-04 | Task lifecycle and user-visible status for long-running install/update/recovery assistance; no AI bypass of deterministic controls |
| PILOT-08 | Remote visibility only if explicitly allowed; remote destructive installation/recovery must remain disabled unless separately threat-modeled and approved |

All cross-agent changes are coordinated by GitHub Issues and reviewed PRs. PHOENIX-10 does not modify another agent's owned paths.

## 6. Risks and mitigations

| Risk | Impact | Mitigation / evidence required |
|---|---|---|
| KIWI/Anaconda integration not proven for Tusker KDE | Installer media may boot but fail to install or have incomplete partitioning UX | Use Fedora-maintained KIWI descriptions as reference; validate live ISO, Anaconda launch, storage UI and fallback path in POC |\n| Mutable RPM/DNF update cannot promise atomic rollback | Failed update may require repair/reinstall and user-data restore | Define signed package transactions, backups and recovery; do not advertise bootc-style rollback |\n| Base image strategy not frozen | Installer/update architecture could be invalidated | Treat Fedora 44 + KIWI + RPM/DNF as provisional POC only; require owner-reviewed ADR before release lock |
| Fedora release/tool support drift | Broken build/install at release time | Pin supported Fedora version and toolchain; revalidate on each release |
| Disk selection ambiguity/race | Irrecoverable user data loss | Stable device identity, revalidation, explicit summary/confirmation, destructive VM tests |
| Dual-boot/firmware diversity | Boot failure or data loss | Defer dual boot until UEFI/GPT/Secure Boot matrix passes |
| Encryption key loss | Permanent data loss | Clear key custody and recovery instructions; no false recovery promise |
| Bootc rollback misunderstood as full-system restore | User data/config loss or failed recovery | Separate OS rollback from user backup; test `/etc`, `/var`, home and model state |
| Auto-update reverses rollback | Repeat boot failure | Update-controller state machine and rollback suppression test |
| Signing-key compromise | Malicious OS updates | Offline/protected key, rotation/revocation drill, independent verification |
| Non-reproducible image | Supply-chain uncertainty | Pin inputs, retain provenance/SBOM, compare repeat builds and document nondeterminism |
| Installer VM success mistaken for hardware support | Misleading compatibility claims | Report VM and physical hardware evidence separately |
| Backup restore path traversal/overwrite | User data compromise | Archive/path validation, symlink-safe extraction, dry-run and adversarial tests |
| Release pipeline credential leakage | Artifact/repository compromise | Short-lived scoped CI identity, secret scanning, no private keys in repo |

## 7. Phase plan and granular checklist

### P0 — Discovery and requirements
- [ ] P0.1 Define clean-install journey, supported dual-boot boundary and minimum install requirements.
  - [ ] P0.1.a Define target architecture(s) and supported firmware mode(s).
  - [ ] P0.1.b Define minimum RAM, storage, CPU and display assumptions with ATLAS-01.
  - [ ] P0.1.c Define clean install, preserve-data and manual partitioning scope.
  - [ ] P0.1.d Define account, locale, network and encryption choices.
- [ ] P0.2 Research current Fedora-supported installer/image/recovery options.
  - [x] P0.2.a Review Anaconda/Kickstart documentation and bootc Kickstart support.
  - [x] P0.2.b Review osbuild Image Builder Fedora installation and bootc ISO documentation.
  - [x] P0.2.c Review bootc staged upgrade and rollback semantics.
  - [ ] P0.2.d Validate exact Fedora version/tool availability after ATLAS-01 selects the base.
  - [ ] P0.2.e Compare selected path against a traditional Anaconda/Lorax alternative.
- [ ] P0.3 Define backup, restore, rollback and disaster recovery journeys.
  - [ ] P0.3.a Distinguish OS deployment rollback from user-data restore.
  - [ ] P0.3.b Define recovery media and offline recovery requirements.
  - [ ] P0.3.c Define backup inclusions, exclusions, encryption and retention.
- [ ] P0.4 Define release channels, supported hardware, minimum requirements and artifact policy.
  - [ ] P0.4.a Define prototype/alpha/beta/RC/stable channel semantics.
  - [ ] P0.4.b Define versioning, support window and update cadence proposal.
  - [ ] P0.4.c Define checksum, signature, SBOM and provenance requirements.
  - [ ] P0.4.d Define install/update/recovery release acceptance criteria.
- [ ] P0.5 Record compatibility matrix, assumptions, risk register and reviewed requirements.

### P1 — Architecture and contracts
- [ ] P1.1 Approve Fedora 44 + mutable RPM/DNF + KIWI/Anaconda direction after POC and owner review.
- [ ] P1.2 Define installer state machine, storage contract and destructive-operation authorization.
- [ ] P1.3 Define partition, filesystem, encryption, bootloader and Secure Boot profiles.
- [ ] P1.4 Define first-boot state schema, idempotency and resumability.
- [ ] P1.5 Define signed update metadata, manifest schema, channels and downgrade policy.
- [ ] P1.6 Define staged update, activation, health-check and rollback state machine.
- [ ] P1.7 Define backup manifest, restore preview, conflict policy and secret exclusions.
- [ ] P1.8 Define recovery environment, offline operation and diagnostic bundle policy.
- [ ] P1.9 Agree package/version/provenance contracts with all component owners.
- [ ] P1.10 Publish ADRs, threat model and cross-agent contract review.

### P2 — Foundation
- [ ] P2.1 Create owned directory skeleton and configuration/schema validation.
- [ ] P2.2 Establish build/test automation and reproducible VM fixtures.
- [ ] P2.3 Implement non-destructive hardware/storage preflight.
- [ ] P2.4 Implement signed manifest parsing and checksum/signature verification tests.
- [ ] P2.5 Implement first-boot state persistence and resume-safe framework.
- [ ] P2.6 Create recovery scaffold and diagnostics collection with secret redaction.
- [ ] P2.7 Add static checks, unit tests, documentation and CI status reporting.

### P3 — Working MVP
- [ ] P3.1 Build bootable install media or supported deployment artifact for the chosen base.
- [ ] P3.2 Boot installer in disposable UEFI VM and verify storage discovery.
- [ ] P3.3 Implement explicit target-disk selection and destructive-action confirmation.
- [ ] P3.4 Complete user creation and first-boot readiness checks.
- [ ] P3.5 Install, reboot, login and demonstrate normal desktop operation.
- [ ] P3.6 Publish repeatable VM installation script and test evidence.

### P4 — Complete feature set
- [ ] P4.1 Implement update channel selection, notification, download/staging and activation UX.
- [ ] P4.2 Implement pre-activation integrity, compatibility, free-space and policy checks.
- [ ] P4.3 Implement health-gated acceptance and rollback workflow.
- [ ] P4.4 Implement user-data backup, manifest, checksums and restore preview.
- [ ] P4.5 Implement safe restore with path/symlink/overwrite protections.
- [ ] P4.6 Implement recovery tools for failed boot, failed update and corrupted configuration.
- [ ] P4.7 Implement release-channel settings and upgrade compatibility warnings.
- [ ] P4.8 Document recovery-key custody and encryption recovery limits.

### P5 — Integration
- [ ] P5.1 Assemble full image from ATLAS-01's approved manifests and component versions.
- [ ] P5.2 Integrate first-run/update/recovery UX with NOVA-02 and PIXEL-03.
- [ ] P5.3 Integrate optional model setup and model backup policy with ORBIT-05.
- [ ] P5.4 Integrate trust, approvals and audit with AEGIS-06.
- [ ] P5.5 Integrate hardware inventory and health checks with NEXUS-07.
- [ ] P5.6 Integrate bundle compatibility/provenance with FORGE-09.
- [ ] P5.7 Run full-stack install, first boot, AI, approvals, update and recovery VM flows.

### P6 — Verification and hardening
- [ ] P6.1 Test UEFI boot and supported Secure Boot behavior.
- [ ] P6.2 Test wrong-disk prevention, changed-device identity and ambiguous storage.
- [ ] P6.3 Test insufficient storage, no network, corrupt media and install cancellation.
- [ ] P6.4 Test interrupted download, staging, activation, power loss and failed health checks.
- [ ] P6.5 Test rollback, rollback failure and automatic-update interaction.
- [ ] P6.6 Test backup/restore interruption, disk-full, corrupt archive and malicious paths.
- [ ] P6.7 Verify signing, checksum, manifest, SBOM, provenance and version consistency.
- [ ] P6.8 Run VM/hardware matrix and publish exact environments/results.
- [ ] P6.9 Triage findings; block release for unresolved critical security/data-loss defects.

### P7 — Release and handover
- [ ] P7.1 Produce signed install media and release artifacts for supported architectures.
- [ ] P7.2 Publish versioned manifest, checksums, detached signatures, SBOM and provenance.
- [ ] P7.3 Publish install, upgrade, backup, restore, recovery and troubleshooting documentation.
- [ ] P7.4 Publish test report, known issues, compatibility limits and rollback instructions.
- [ ] P7.5 Complete release sign-off and define support/update maintenance policy.
- [ ] P7.6 Update completion ledger, progress and successor handover with evidence.

## 8. Phase 1 exit criteria

P0 is complete only when:
- requirements and acceptance criteria are reviewed;
- Fedora/image/installer choices are verified against the selected supported Fedora release;
- ATLAS-01 confirms the base-image direction;
- install/update/recovery threat and risk assumptions are recorded;
- release and compatibility policy has an owner-reviewed baseline.

P1 is complete only when dependent owners accept the image, packaging, trust, hardware and update contracts and the corresponding ADRs are recorded. No build or install success is claimed at this stage.

## 9. Immediate next actions

1. Obtain ATLAS-01's proposed Fedora version, image model, package manifest and build artifact contract.
2. Open coordination issues for ATLAS-01, NEXUS-07 and AEGIS-06 with concrete interface questions.
3. Verify selected Fedora release support for osbuild Image Builder, Anaconda bootc Kickstart, Secure Boot and bootc update/rollback.
4. Create the owned installer/update/recovery skeleton only after the architecture boundary is agreed.
5. Establish a disposable UEFI VM test profile before destructive installer implementation.

## 10. Cross-agent architecture update — 2026-10-31

ATLAS-01 response is recorded on GitHub issue #2. Its files `os/BUILD-TOOL-EVALUATION.md` and `os/BASE-SYSTEM-CONTRACTS.md` on `01-fedora-base` are provisional source contracts. Key implications for PHOENIX-10:

- The first MVP should use mutable RPM/DNF unless the master plan requires image-based updates.
- KIWI NG is the leading POC candidate; Fedora 44 package availability for KIWI's live ISO dependencies is visible in Fedora's package catalog.
- Fedora-maintained KIWI descriptions should be used as the reference implementation and minimally adapted.
- The image POC is not complete until both the live/install ISO and QCOW2 boot from the same package source.
- Secure Boot, Anaconda UI and physical hardware support remain unverified.
- NEXUS-07 and AEGIS-06 contracts remain outstanding; no destructive installation implementation is authorized by this proposal alone.

The exact build/boot procedure and pass/fail evidence template are maintained in `docs/PHOENIX-10-KIWI-POC.md`.

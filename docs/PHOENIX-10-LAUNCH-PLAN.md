# PHOENIX-10 Launch Plan — 2026-10-31

**Agent:** PHOENIX-10 — Installer & Recovery  
**Assigned branch:** `10-PHOENIX`  
**Verified base / live main:** `345fc5a3d0f831fc714bae0cc88fa842cd9bed79`  
**Branch comparison:** `10-PHOENIX` is identical to `main` (0 ahead / 0 behind).  
**Planning status:** Read-only baseline complete; next implementation task awaits Chief Architect assignment.  
**Assignment blocker:** [Issue #78](https://github.com/otta-komban/TuskerOS/issues/78)

## 1. Verified baseline

- The launch mapping and role guide assign PHOENIX-10 exclusively to `10-PHOENIX`.
- Repository rules require branch isolation, focused commits, exact-SHA test evidence, and Chief Architect task IDs before implementation.
- The new assigned branch currently points at the live `main` SHA above. This remote comparison does not expose a local checkout, so no local working-tree cleanliness claim is made.
- `PHOENIX-10-REL-001` (Issue #52) was implemented on historical branch `agent/10-installer-recovery` and merged through PR #55. Do not duplicate it or blindly port its 124-commit history.
- PR #55's release-validation workflow run [41181257090](https://github.com/otta-komban/TuskerOS/actions/runs/41181257090) completed successfully. Its job ran `py_compile` and `python -m unittest discover -s tests -p 'test_verify_release_manifest.py' -v`.
- PR #55's unified validation run [41181257048](https://github.com/otta-komban/TuskerOS/actions/runs/41181257048) completed successfully with all eight jobs successful. These are PR-head CI results, not VM/image acceptance.

## 2. Existing PHOENIX deliverable

**REL-001 — local release-manifest and artifact integrity verifier**

Delivered implementation already present on the current baseline:
- `scripts/verify_release_manifest.py`
- `tests/test_verify_release_manifest.py`
- `.github/workflows/phoenix-release-validation.yml`
- `docs/PHOENIX-10-RELEASE-VERIFIER.md`

The verifier performs local manifest/schema and artifact-byte checks, rejects duplicate JSON keys and unsafe paths, and deliberately keeps `promotion_ready=false`. It does **not** verify cryptographic signatures, choose trust roots, fetch remote evidence, prove source commits, or semantically parse SBOM/provenance. No claim of release promotion readiness is made.

## 3. Remaining work plan and acceptance criteria

The following are proposed work packages within the PHOENIX role. They are not new task authorizations until the Chief Architect assigns task IDs and acceptance criteria.

### A. Artifact build and release evidence

**Dependencies**
- ATLAS-01 owns the Fedora base, package manifest, repository snapshot and image-build inputs.
- AEGIS-06 / release maintainers must select the release trust envelope and key-custody model before cryptographic verification is implemented.

**Current evidence / blockers**
- ATLAS-01 has now confirmed the canonical Fedora Forge source `https://forge.fedoraproject.org/releng/kiwi-descriptions.git`, ref `f44`, commit `dfc49a5a10f69941179fdadd96aa6a5984f7c677`, and profiles `KDE-Desktop-Live` (`iso`) plus `KDE-Desktop-Disk` (`oem`). The live `main` lock file `os/image-source.lock.json` records these IDs and source blob hashes; it explicitly records that the upstream commit signature is **not verified**.
- `os/package-manifest.csv` was fetched from live `main` and still contains no package rows. ATLAS says build automation fails closed until reviewed exact NEVRAs and repository snapshot inputs are supplied.
- No actual ISO/QCOW2 build, checksum production, or VM boot evidence is present in the inspected handoff. The source/profile handoff is materially advanced, but the package inputs and actual build remain open.
- AEGIS has described TUF and detached OpenPGP as alternative designs; neither is selected pending release-channel and key-custodian decisions. AEGIS also issued `SEC-INST-001` against a stale NFC-normalization statement in the historical PHOENIX conformance plan; any future digest implementation must preserve exact JSON Unicode code points per JCS and reject invalid surrogate sequences. This is a review finding, not a change to shared schemas or authorization to implement trust.

**Acceptance**
- Reviewed non-empty package manifest and repository snapshot lock.
- Actual Fedora 44 build produces both agreed artifacts from the pinned source and reviewed package inputs.
- Retain exact build command, environment, source/recipe SHA, logs, artifact sizes and SHA-256, SBOM and provenance.
- Run the existing local verifier against the produced release manifest and artifacts.
- Report signature/trust, provenance semantics, Secure Boot and promotion gates separately; never infer them from digest matching.

### B. Installer storage preflight and destructive-operation boundary

**Dependencies**
- NEXUS-07 must publish authoritative stable storage identity, registered operation IDs/schemas, typed partition-plan representation, authenticated broker interface, atomic one-time authorization consumption, and operation reconciliation for `unknown_outcome`.
- AEGIS-06 owns R4 risk, exact approval binding, authorization and audit requirements. The AEGIS decision requires explicit local confirmation and fail-closed behavior.
- PHOENIX consumes these contracts; it must not invent shared operation IDs, schemas, digest envelopes or broker methods.

**Current blockers**
- [Issue #3](https://github.com/otta-komban/TuskerOS/issues/3): NEXUS storage identity and operation contract confirmation remains outstanding in the inspected issue thread.
- [Issue #4](https://github.com/otta-komban/TuskerOS/issues/4): AEGIS has supplied security decisions, but NEXUS runtime transport/consume and ATLAS packaging inputs remain unresolved.

**Acceptance**
- Read-only inventory/preflight is schema- and runtime-conformant with NEXUS.
- No implicit disk selection; target identity is stable and re-resolved immediately before execution.
- Exact partition plan, resource identity, principal/session/device, policy/registry and precondition snapshot are bound to approval.
- DENY, REQUIRE_APPROVAL, stale identity/preconditions, or unavailable policy/identity/audit produce zero handler calls.
- Any post-dispatch timeout is reconciled as `unknown_outcome`; never blindly retry destructive work.
- Destructive tests run only against disposable virtual disks and require explicit approval.

### C. UEFI boot, install and recovery acceptance

**Dependencies**
- A real ISO/QCOW2 from work package A.
- Approved installer/storage contracts from work package B.
- Disposable QEMU/KVM/OVMF environment and retained test evidence.

**Acceptance**
- UEFI boot, Secure Boot (separately), desktop smoke, Anaconda install, interrupted-install recovery and post-install verification are tested.
- Record VM configuration, firmware, disk identities, image SHA-256, exact commands, logs and outcomes.
- Test multiple disks and target changes; prove unselected disks remain unchanged.
- Mark every criterion PASS / FAIL / NOT RUN / UNVERIFIED. Static CI is not VM evidence.

## 4. AEGIS schema-audit handoff (read-only review)

A fresh read of `06-security-gatekeeper/security/SCHEMA_CONSISTENCY_AUDIT.md` and `security/INSTALLER-RELEASE-TRUST-DECISION.md` records additional AEGIS findings. These are security-owner draft/candidate artifacts, not PHOENIX-owned contracts:

- Approval-request schema v0.2.0 adds a required nested binding object for session/device bindings, registry version, canonical resource scope and precondition digest. Trusted derivation, producer/consumer compatibility and broker consume-time enforcement remain unaccepted.
- Audit-event v0.1.0 now requires explicit `task_id` and `step_id` keys (nullable values). A separate v0.2.0 candidate proposes registry-resolution state/version, executor/reason fields and package transaction correlation. It remains candidate-only.
- The candidate still has unresolved lifecycle coverage for presentation, dismissal, invalidation, revocation, consume acceptance/rejection and reconciliation. Registry-unavailable event semantics and trusted provenance must be accepted by NEXUS-07/TUSKER-04 before migration.
- AEGIS reports schema/fixture CI passing for its candidate, but explicitly says this is not evidence of a live producer, durable audit persistence, trusted identity derivation, broker atomicity or privileged runtime conformance.
- The release-trust recommendation prefers TUF for a maintained update channel, with detached OpenPGP as an offline-only alternative. Neither is selected by project release maintainers; key custody and release-channel contract remain open.
- The security decision's digest section still contains an NFC-normalization instruction, while the later AEGIS finding SEC-INST-001 says JCS must preserve exact parsed Unicode code points and reject invalid surrogate sequences. Treat this as an unresolved cross-document inconsistency; obtain AEGIS owner correction/clarification before implementing any digest path. PHOENIX must not independently redefine JCS.

**PHOENIX action:** consume only owner-approved, versioned schemas and runtime interfaces. Do not copy candidate schemas into the installer, invent lifecycle event names, or claim schema-fixture CI proves runtime safety. Privileged storage execution remains blocked.

## 5. Stop conditions

Until task assignment and required dependencies are accepted:
- No privileged installer or broker integration.
- No disk mutation or destructive storage prototype.
- No cryptographic trust-root implementation or release-promotion claim.
- No ISO/QCOW2 build, boot, install, Secure Boot or recovery success claim without actual reproducible evidence.
- No edits to shared schemas, security boundaries or cross-agent contracts without Chief Architect approval.

## 6. Next action

Chief Architect: assign the next PHOENIX-10 task ID and bounded acceptance criteria, or designate an existing handoff issue as the authorized next deliverable. See [Issue #78](https://github.com/otta-komban/TuskerOS/issues/78).

## 7. Evidence references

- [PHOENIX-10 role guide](https://github.com/otta-komban/TuskerOS/blob/10-PHOENIX/docs/agents/launch/10-PHOENIX-10.md)
- [Issue #52 — REL-001](https://github.com/otta-komban/TuskerOS/issues/52)
- [PR #55 — merged verifier implementation](https://github.com/otta-komban/TuskerOS/pull/55)
- [PHOENIX CI run 41181257090](https://github.com/otta-komban/TuskerOS/actions/runs/41181257090)
- [Unified CI run 41181257048](https://github.com/otta-komban/TuskerOS/actions/runs/41181257048)
- [ATLAS handoff / Issue #2](https://github.com/otta-komban/TuskerOS/issues/2)
- [Live ATLAS source lock](https://github.com/otta-komban/TuskerOS/blob/main/os/image-source.lock.json)
- [Live package manifest (still header/comments only)](https://github.com/otta-komban/TuskerOS/blob/main/os/package-manifest.csv)
- [NEXUS storage handoff / Issue #3](https://github.com/otta-komban/TuskerOS/issues/3)
- [AEGIS installer and release trust / Issue #4](https://github.com/otta-komban/TuskerOS/issues/4)

**Validation note:** This is a repository and coordination audit. No local test command, image build, VM boot, installer run or destructive operation was executed during this planning pass.

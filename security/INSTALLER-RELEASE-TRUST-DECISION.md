# Installer Destructive-Operation and Release-Trust Security Decision

**Owner:** AEGIS-06  
**Consumers:** PHOENIX-10, NEXUS-07, ATLAS-01  
**Status:** AEGIS security baseline proposal; producer/runtime details and release key custody remain unaccepted  
**Scope:** Disk/partition mutation authorization, pre-dispatch audit, release artifact trust and ownership boundaries.

This document answers the AEGIS-owned security questions in repository issue #4. It does not assign unreviewed action IDs, broker methods, Polkit IDs, package names, service accounts or private-key custodians. It does not authorize destructive installer execution.

## 1. Destructive installer action envelope

The installer must submit the existing typed AEGIS action-proposal envelope. NEXUS-07 must assign the canonical action ID, broker operation ID, strict argument schema and result schema; the installer must not invent or select these identifiers.

The operation-specific arguments must represent the complete reviewed plan, not a display string:

- A stable target-disk identity resolved by the trusted storage provider. /dev/sdX, a UI label, a mount path or a caller-supplied symlink is not sufficient identity by itself.
- The exact ordered partition plan: start/end sectors or equivalent unambiguous extents, partition type identifiers, filesystem and mount choices, boot/EFI treatment, encryption mode and other mutation-affecting options.
- The exact operation and options that the broker will execute.
- A stable transaction identifier for installer correlation.

The explicit resource list must contain the canonical resolved target resource and requested access mode. The installer must not implicitly select a disk. Multiple eligible disks, missing/ambiguous identity, unresolved aliases, changed capacity/topology, or inability to prove the target mapping causes DENY.

Every mutation proposal requires an idempotency key. The operation-specific schema must reject unknown fields and caller-supplied identity, risk, approval or authorization claims. Secret material (encryption keys, recovery secrets, credentials) must not be embedded in proposal or audit payloads.

## 2. Canonical digest and approval binding

Use the AEGIS policy-engine canonicalization; PHOENIX must not define a competing hash:

1. Validate the typed proposal and operation-specific argument schema.
2. Resolve the disk to a canonical storage resource through the trusted inventory/provider.
3. Normalize strings to NFC, sort resource tuples deterministically and reject duplicate/ambiguous resources.
4. Canonicalize the validated action, complete typed arguments/partition plan, resolved resources, authenticated principal binding, operation-schema version, and policy/registry versions with RFC 8785 JCS.
5. Hash with SHA-256 and encode as sha256:<lowercase hex>.

The approval binding additionally requires the existing v0.2.0 fields: principal binding, session binding, device binding, registry version, exact resource scope and precondition digest. The precondition digest must commit to a fresh snapshot of the target identity and relevant installed/storage state (including the partition-table/topology facts used to preview the plan). A display name, disk path alone or caller-supplied digest is not proof.

Any change to the target identity, partition plan, options, resource set, principal/session/device, operation schema, policy/registry version or relevant storage snapshot invalidates the approval. Re-resolve and recheck immediately before dispatch; a changed snapshot requires a new preview and approval.

## 3. Risk and authorization lifecycle

- Destructive partition-table, filesystem, encryption-layout, bootloader-target or whole-disk writes are R4 and require explicit human approval with exact target and impact.
- A request that changes a security trust root, policy engine, authorization mechanism or audit-integrity control is R5 and is DENY by default. It is not made acceptable merely by bundling it into an R4 install plan.
- Risk is derived from the reviewed operation registration, validated arguments, resolved resources and current state. Installer/UI/model risk labels are ignored. Ambiguous target or impact escalates; if it cannot be resolved safely, DENY.

Approval follows the AEGIS handoff contract:

1. Initial evaluation returns DENY or REQUIRE_APPROVAL; REQUIRE_APPROVAL has no authorization reference and causes zero executor calls.
2. The approval UI displays the exact disk identity, partition plan, impact, requesting principal and reversibility from trusted validated data.
3. After an authenticated eligible approval, AEGIS re-evaluates the complete proposal and current snapshot. Only a fresh ALLOW with a new short-lived opaque authorization_ref may proceed.
4. The broker independently authenticates its IPC peer and compares that identity with trusted authorization context. It atomically consumes only the fresh authorization_ref; approval_request_id is correlation-only and never a bearer capability.
5. The consume operation rechecks audience, operation, digest, principal/session/device, resource scope, policy/registry version, expiry, revocation and precondition digest. Exactly one concurrent consumer may succeed.
6. The broker revalidates the storage target and preconditions immediately before the first write. Any mismatch, stale snapshot, replay or indeterminate check means no grant/zero handler calls.

The authority/broker must persist the required pre-dispatch authorization/dispatch-intent audit evidence before returning a usable grant or invoking the destructive handler. If policy, identity, clock, authorization store, registry or required audit storage is unavailable, fail closed and perform zero disk writes. A timeout or disconnect after possible dispatch is UNKNOWN; read back the operation and target state before any retry. Cancellation is not completion until termination is confirmed. Recovery/rollback is a separate operation with a separately reviewed and authorized compensating plan.

## 4. Audit and correlation requirements

At minimum, installer audit records must correlate the AEGIS proposal/decision/operation, principal binding, origin, policy/registry version, action digest, executor, result, reason and correlation ID. PHOENIX must preserve a stable transaction correlation identifier across preview, authorization, dispatch, read-back and recovery. The audit must reference the exact plan and precondition/snapshot digests without storing secrets or unnecessary package/device metadata.

The candidate audit-event v0.2.0 schema is not yet a producer-approved contract. SEC-SCHEMA-006 remains open: the current candidate does not yet define every lifecycle event required by the normative lifecycle (presentation, dismissal, invalidation, revocation, consume acceptance/rejection and reconciliation). NEXUS-07 and TUSKER-04 must agree on canonical event names, status mappings, trusted producer and correlation semantics before candidate promotion. The installer must not invent new audit event names or silently overload fields to conceal this gap.

Required audit failure before dispatch is a hard deny. Do not treat a queued in-memory log, best-effort file write or later telemetry upload as durable pre-dispatch evidence.

## 5. Release artifact signature and trust proposal

**Reconciled recommendation:** TUF metadata is the preferred framework for the full update/release channel because its root, targets, snapshot and timestamp roles provide explicit delegation, freshness and rollback protections. An offline detached OpenPGP signature over a canonical release manifest is a simpler alternative for a minimal offline-only artifact channel, but it is not equivalent to TUF's repository freshness/rollback metadata. These are alternative trust-envelope designs, not two required signatures to stack by default. Project release maintainers must select and approve one canonical distribution contract before implementation.

For the preferred TUF path, bind an in-toto/SLSA provenance attestation to each release target. For the OpenPGP alternative, sign the canonical manifest and bind the same provenance digest inside that manifest. In either case, the signed release statement should bind:

- artifact digest and size;
- TuskerOS release/version and target architecture/image type;
- source commit and reviewed build-definition revision;
- build workflow identity/run and builder provenance;
- Fedora repository snapshot/identifiers, package NEVRAs and SBOM digest;
- metadata/manifest sequence and validity interval.

Common trust and lifecycle requirements:

1. Pin an initial trusted root in the installer/recovery environment. Verify signatures and target hashes before installation or update; never accept an unsigned manifest or a model/caller-provided checksum as trust evidence.
2. Keep root authority offline and separated from routine CI. Use threshold authorization by multiple independent root-key custodians; exact threshold, identities and hardware custody require release-owner approval.
3. Delegate narrowly scoped release-signing authority. CI must not hold root keys. Protect delegated keys with hardware-backed storage where supported, scope them to intended targets, rotate them on a documented schedule and revoke them through authenticated signed metadata.
4. Use monotonically increasing metadata/manifest sequence values and expiry to detect rollback/freeze. TUF provides versioned root/targets/snapshot/timestamp metadata; an OpenPGP-only channel must separately define authenticated rotation/revocation and freshness metadata. Reject lower-version state, invalid signatures, expired metadata, digest mismatch and unknown trust roots.
5. Embed the trusted root and required verification metadata in offline installation media so artifact verification does not require a cloud service. A missing/expired/invalid trust chain or uncertain clock fails closed for destructive installation; do not provide a user-facing bypass.
6. Do not claim hardware-enforced anti-rollback on systems without protected monotonic state. Where supported, bind the minimum accepted release/security epoch to TPM-backed state; otherwise document the weaker local-state guarantee and ensure the update client still rejects rollback against locally trusted metadata.
7. Publish root rotation, key compromise, revocation, recovery-media refresh and emergency trust-root recovery procedures before production releases.

No private signing keys, seed material or credentials belong in Git, image build logs or the installer. No production key owner, HSM, root threshold or public-key distribution channel is selected by this proposal. The earlier C0033 OpenPGP recommendation is retained as the simpler alternative; this C0034 reconciliation prefers TUF for a maintained update/release channel but does not select either on behalf of the project release maintainers.

## 6. Ownership and packaging boundary

| Concern | Owner | AEGIS decision |
|---|---|---|
| Policy semantics, risk classification, canonical digest, approval binding, audit requirements | AEGIS-06 | Owns security rules and review; no caller/model authority |
| Stable action IDs, typed operation/argument/result schemas, broker method mapping, IPC identity, atomic consume and UNKNOWN/reconciliation | NEXUS-07 | Must publish the runtime contract; no arbitrary shell or generic root API |
| Installer preview, target selection UX, partition plan generation, storage snapshot, transaction lifecycle and read-back workflow | PHOENIX-10 | Consumes AEGIS/NEXUS contracts; never mints authorization |
| Fedora package/service/policy-file integration and trust-root packaging | ATLAS-01 | Packages only owner-approved IDs, files, service accounts and dependencies |
| Release root-key custody and release approval authority | Project release maintainers (to be named) | AEGIS specifies trust policy; custodians and operational process require explicit project decision |

AEGIS owns the eventual exact Polkit action identifiers and security policy content, but will not publish placeholder identifiers before NEXUS fixes the broker method/operation boundary. ATLAS must not invent package names, service accounts, paths or Polkit IDs. No allow-all Polkit rule, unrestricted root command runner or installer-owned bypass is permitted.

## 7. Required acceptance evidence

Before destructive installer implementation is enabled, require:

- NEXUS-07 acceptance of stable disk identity resolution, typed partition-plan schema, fixed operation/broker mapping, peer authentication, atomic consume, idempotency and UNKNOWN reconciliation.
- PHOENIX-10 acceptance of the exact proposal/approval fields, preview and immediate pre-write snapshot revalidation, cancellation and read-back semantics.
- ATLAS-01 acceptance of packaging boundaries and trust-root delivery without privileged bypass.
- A versioned operation registration and schema fixtures for exact target/plan binding, changed target, changed partition plan, stale snapshot, multiple disks, ambiguous identity, missing idempotency key, expired/revoked/replayed reference and audit/policy/identity outage.
- Executable negative tests asserting zero disk writes for DENY, REQUIRE_APPROVAL, mismatch, replay, unavailable policy/identity/audit and stale target; race tests proving one consume winner; crash/disconnect tests proving UNKNOWN reconciliation.
- Disposable-VM destructive tests and verified read-back/postconditions before any production target is enabled.
- A separately reviewed TUF root/targets metadata policy, signing-key custody and rotation/revocation procedure, offline verification and rollback tests.

Until these decisions and tests exist, destructive install operations remain BLOCKED. Read-only inventory and preflight may proceed only after NEXUS confirms their typed interfaces. This decision is a security contract proposal, not implementation, test-pass evidence or release approval.

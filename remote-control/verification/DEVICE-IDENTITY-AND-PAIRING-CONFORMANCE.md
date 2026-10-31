# PILOT-08 Device Identity & Pairing Conformance Specification

**Status:** Implementation-neutral conformance proposal; not a frozen API, UX approval, implementation, or security acceptance.
**Owner:** PILOT-08
**Branch:** `agent/08-remote-control`
**Task:** `PILOT-08-P08-02`
**Baseline:** `8bf66079f9e021244eda432fa8455e83b59e2165`
**Security source:** AEGIS-06 `security/REMOTE_DEVICE_SECURITY_CONTRACT.md`, branch `06-security-gatekeeper`, blob `d72feb9d78c81da769c8bca009b721b69bf8032c`
**Product decision state:** NOVA-02 DEC-NOV-001..004 still lack owner-authored dispositions in issue #15 at review time.
**Disposition:** NO-GO for pairing runtime/UI until repository reauthorization and the remaining P0 contracts close.

## 1. Purpose and boundary

This document translates AEGIS-06's accepted DEC-AEG-001 and DEC-AEG-002 requirements into a testable device-identity and enrollment sequence. It adds no new security authority and does not choose an API route, persistence technology, UI layout, QR/deep-link format, platform storage API, or product recovery behavior.

The local owner device is the trust anchor for enrollment. A remote client cannot initiate enrollment, choose a principal, or convert possession of a challenge into an authenticated session without explicit local owner confirmation.

The pairing service is only an enrollment boundary. A successfully enrolled device is still subject to session authentication, request signatures, AEGIS policy checks, revocation, and the TUSKER Core task boundary on every later operation.

## 2. Binding requirements from AEGIS-06

The following values are accepted requirements, not PILOT proposals:

| Requirement | Binding behavior |
|---|---|
| Device key | Each remote device generates its own Ed25519 key pair locally. |
| Private-key storage | Private key stays in OS-protected secure storage and is non-exportable where supported. If secure storage is unavailable, pairing is disabled; no plaintext-file fallback. |
| Device identity | Server registry binds the public key and SHA-256 public-key thumbprint to one local owner. A label, IP, VPN peer name, or user-agent is not identity. |
| Initiation | Pairing starts only from a locally authenticated owner session. An unpaired remote client cannot create a challenge or enroll itself. |
| Challenge | 32-byte CSPRNG secret; server stores only its cryptographic hash; bound to owner and pairing transaction; expires after 5 minutes. |
| Proof | Remote client signs a domain-separated transcript including challenge identifier/secret, server identity, and public-key thumbprint. |
| Human verification | Client and local UI show the same 10-hex-character short authentication fingerprint. Local UI shows device label and fingerprint and requires explicit owner confirmation. Mismatch means cancel. |
| Consume | Valid proof plus local confirmation are required before atomic single-use challenge consumption/enrollment. Expired, replayed, consumed, or mismatched challenges fail. |
| Attempts | Maximum 5 proof attempts per challenge. Exhaustion invalidates the challenge and requires a new local ceremony. |
| Failure privacy | Rate-limit challenge creation and proof failures per owner and source. Do not disclose whether an owner/device identifier exists. |
| Audit | Enrollment and cancellation are durable lifecycle events. Failed, expired, or cancelled attempts create no device or session. |

Source: AEGIS-06 remote device contract, sections 1–2. The contract freezes these security requirements only; it does not establish that a PILOT runtime exists or has passed tests.

## 3. Required enrollment state machine

The following is a logical state model for conformance testing, not a prescribed UI or endpoint design.

```text
UNPAIRED
  |
  | local authenticated owner starts pairing
  v
CHALLENGE_PENDING
  |-- expired / cancelled / attempts exhausted --> TERMINAL_NO_ENROLLMENT
  |
  | valid proof from proposed device key
  v
PROOF_VALIDATED
  |-- fingerprint or label mismatch / owner rejects --> TERMINAL_NO_ENROLLMENT
  |
  | explicit local owner confirmation
  v
CONFIRMED_PENDING_CONSUME
  |
  | atomic one-time challenge consume + durable registry write
  v
ENROLLED
  |
  | session authentication is a separate ceremony
  v
SESSION_ELIGIBLE
```

Required invariants:

1. No transition to `ENROLLED` occurs from remote proof alone.
2. No transition to `ENROLLED` occurs from a local confirmation without valid proof for the same transaction and key.
3. The fingerprint shown for confirmation is derived from the exact signed transcript and is the same value displayed by the remote client.
4. A challenge can cause at most one enrollment, including under concurrent confirmation requests.
5. Any failed, expired, cancelled, exhausted, or mismatched transaction leaves no paired device and issues no session.
6. Challenge consumption and durable device-registry creation must have atomic, crash-safe semantics. If the implementation cannot prove the outcome after a crash, it must not report success or issue a session; it must reconcile the durable transaction state.
7. Pairing does not itself authorize task reads, task mutations, tool invocation, or approval.

## 4. Protocol and data-handling constraints

### 4.1 Device-side key lifecycle

- Generate the Ed25519 key pair on the remote client; private material must not leave the platform-protected key store.
- Fail closed when a suitable secure store is unavailable or inaccessible.
- Bind the registered device to the public key/thumbprint and the locally authenticated owner record.
- Do not use device labels, source addresses, user-agent strings, VPN peer names, or client-supplied principal IDs as authentication factors.
- Do not include private keys, raw challenge secrets, session secrets, signatures, or full private task payloads in logs, telemetry, URLs, or diagnostics.

### 4.2 Challenge lifecycle

- Challenge creation requires a local authenticated owner context.
- Server stores only a cryptographic hash of the 32-byte challenge secret.
- Challenge record is bound to one owner and one pairing transaction, and expires at 5 minutes.
- Count proof attempts atomically. The sixth proof attempt must not be accepted; after five unsuccessful attempts the challenge is invalid.
- Proof validation and local confirmation must be bound to the same challenge, public key, server identity, and transcript.
- Consume the challenge exactly once. A retry after a successful consume must not create a second device or session.
- Rate-limit challenge creation and failed proofs. Exact rate-limit windows/buckets are not numerically specified by the AEGIS contract and must not be invented by PILOT.

### 4.3 Confirmation ceremony

The local confirmation must present, at minimum, the remote device label and the 10-hex-character fingerprint, and must require an affirmative local owner action. The local owner must be able to reject/cancel. The remote client must independently display the matching fingerprint.

This specification does not decide the visual layout, copy, QR scanning flow, accessibility treatment, timeout presentation, or retry UX. Those are NOVA-02 product/UX decisions and remain open.

### 4.4 Registry and session separation

- Registry identity is the public-key thumbprint with owner binding and revocation state.
- A device record is not a session.
- A successful enrollment must not silently mint a long-lived bearer credential.
- Session issuance follows the separate AEGIS-06 session protocol: opaque 32-byte secret, server-side hash only, 8-hour absolute lifetime, 15-minute idle timeout, no refresh token, and signed device proof on every HTTP request.
- A session request must be bound to the registered key and current registry/revocation state.

## 5. Key rotation, loss, and recovery boundaries

AEGIS-06 specifies that planned key rotation requires proof from the currently registered key plus fresh local owner confirmation. If the old key is lost, the device must be revoked and paired again; remote-only recovery is prohibited.

The exact rotation API, transaction schema, overlap window, rollback semantics, and UX are not defined in the AEGIS contract. They remain design inputs for a later reviewed contract; this document does not invent them.

NOVA-02 DEC-NOV-004 (lost-device recovery UX) remains unanswered. Until the owner decision is recorded:
- do not implement recovery UI or a recovery endpoint;
- do not allow a remote device to recover or replace its own lost key;
- do not infer an account recovery factor or bypass local owner confirmation.

## 6. Conformance test matrix

These are required future tests. They are **specified, not implemented or executed**. Every negative test must assert no device enrollment, no session issuance, no protected handler/Core call, and no secret-bearing audit output unless the exact scenario is a successful enrollment.

| Test ID | Attack / condition | Required assertion |
|---|---|---|
| PAIR-C01 | Remote client attempts to create a challenge without a locally authenticated owner | Reject; no challenge, device, or session |
| PAIR-C02 | Secure key storage unavailable, denied, or unsupported | Pairing remains disabled; no plaintext fallback or exported private key |
| PAIR-C03 | Device key generated or reused across two devices | Reject shared identity; each device must have an independent key |
| PAIR-C04 | Challenge secret is not 32 bytes or is generated without CSPRNG | Reject invalid challenge generation; no challenge becomes usable |
| PAIR-C05 | Challenge secret appears in server persistence, logs, URLs, or diagnostics | Fail privacy/security test; only a cryptographic hash may be persisted |
| PAIR-C06 | Challenge expires at or after 5 minutes | Reject proof; no enrollment/session |
| PAIR-C07 | Challenge proof is replayed after successful consume | Reject replay; exactly one device record exists |
| PAIR-C08 | Two valid confirmation requests race on one challenge | At most one atomic consume and one enrollment succeed |
| PAIR-C09 | Six invalid proof attempts are submitted | At most five attempts are processed; challenge invalidated after exhaustion |
| PAIR-C10 | Proof uses another challenge, owner, server identity, or public-key thumbprint | Reject transcript mismatch; no enrollment |
| PAIR-C11 | Local UI fingerprint differs from remote-client fingerprint | Confirmation cannot proceed; cancel leaves no device/session |
| PAIR-C12 | Device label matches but fingerprint does not | Reject; label alone is never sufficient |
| PAIR-C13 | Valid proof is submitted but local owner does not confirm | Remain unpaired; no session |
| PAIR-C14 | Local owner rejects or cancels | Durable cancellation event; no device/session |
| PAIR-C15 | Challenge is already consumed, expired, or cancelled | Reject without disclosing sensitive transaction existence |
| PAIR-C16 | Crash occurs between proof validation, confirmation, consume, and registry persistence | Recovery is atomic/reconciled; never report false success or issue a session for an uncommitted enrollment |
| PAIR-C17 | Client supplies principal, role, owner ID, device ID, or policy outcome | Reject/ignore as untrusted; owner/principal comes from local authenticated context |
| PAIR-C18 | Challenge creation/proof failures are flooded | Per-owner/source limits bound resource use; response does not enumerate owners/devices |
| PAIR-C19 | Device is enrolled then immediately revoked before session issuance | Session issuance fails against authoritative revocation state |
| PAIR-C20 | Planned key rotation lacks old-key proof or fresh local confirmation | Reject rotation; old key remains authoritative until approved atomic rotation |
| PAIR-C21 | Lost device attempts remote-only recovery | Reject; revoke and fresh local pairing is required |
| PAIR-C22 | Audit inspection after success and failure paths | Durable typed lifecycle events; no raw challenge, private key, session secret, signature, or private task body |

### Required test instrumentation

For every negative test capture:
- synthetic owner/device/challenge identifiers only;
- challenge state before and after;
- proof-attempt counter and atomic-consume outcome;
- device-registry row count and public-key thumbprint only;
- session-registry row count;
- handler/Core dispatch counter (must remain zero for all pairing-only failures);
- typed lifecycle audit event IDs and redaction assertions;
- process/crash/restart evidence where applicable.

Never include private keys, raw challenge secrets, reusable enrollment tokens, live session secrets, or production personal data in fixtures or reports.

## 7. Cross-agent closure matrix

| Gate | Owner | Current evidence | Status / required closure |
|---|---|---|---|
| Ed25519, secure storage, challenge, fingerprint, confirmation, attempt limit | AEGIS-06 | Accepted contract v0.1.0, sections 1–2 | Security requirements accepted; implementation and test evidence still absent |
| Pairing initiation/confirmation/cancel UI and error states | NOVA-02 | Issue #15 has PILOT request but no NOVA-authored decision | **P0 OPEN** — provide explicit DEC-NOV-001 disposition and UX state flow |
| Device inventory/revocation UX | NOVA-02 | No owner-authored disposition located | **P0 OPEN** — provide DEC-NOV-002 |
| Visible remote status and local global disable/re-enable UX | NOVA-02 | AEGIS defines global disable/re-enable security semantics; no NOVA UX disposition located | **P0 OPEN** — provide DEC-NOV-003 and align UI with durable revoke-before-success |
| Lost-device recovery UX | NOVA-02 | AEGIS requires revoke + fresh local pairing; no NOVA UX disposition located | **P1 OPEN** — provide DEC-NOV-004; no remote-only recovery |
| Repository implementation reauthorization | Admin/coordinator | PR #49 gate not independently verified; required-check configuration evidence incomplete | **OPEN** — no runtime implementation authorization inferred |
| Session/request proof | AEGIS-06 | Accepted contract section 3 | Security requirements accepted; separate session implementation/conformance work required |
| Authorization and task path | AEGIS-06 / TUSKER-04 / NEXUS-07 | AEGIS accepted policy boundary; TUSKER decisions remain REVISE; NEXUS consume/context boundary unresolved | **P0 OPEN** for protected task operations; pairing conformance does not waive it |

## 8. Explicit exclusions

This proposal does not authorize:
- pairing, registry, key-rotation, recovery, or session runtime code;
- a network listener, HTTPS/WSS route, QR/deep-link endpoint, or desktop UI;
- remote task submission, cancellation, event streaming, NEXUS calls, or broker consumption;
- remote approvals (disabled for MVP);
- pause/resume (excluded from MVP);
- any plaintext key fallback, remote-only recovery, or caller-supplied identity/authorization context.

## 9. Acceptance and evidence status

The document is ready for AEGIS-06 and NOVA-02 review as an implementation-neutral conformance proposal. It is not a signed protocol contract.

Before pairing implementation can start, require:
1. PR #49 repository reauthorization gate closed and verified by the coordinator/admin.
2. NOVA-02 DEC-NOV-001..003 P0 decisions recorded with a concrete local UX state flow.
3. PILOT/AEGIS agreement on any missing pairing transaction/rotation wire semantics without changing accepted AEGIS invariants.
4. A test harness and platform secure-storage capability contract selected under the approved implementation plan.
5. A traceable implementation plan covering PAIR-C01..C22 and durable audit evidence.

**Current result:** 22 pairing conformance cases specified; 0 pairing runtime tests executed; 0 runtime features established; NO-GO remains in force.

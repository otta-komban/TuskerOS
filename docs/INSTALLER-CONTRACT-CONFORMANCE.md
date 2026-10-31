# Installer contract conformance plan

Owner: PHOENIX-10. Branch: `10-installer-recovery`.

Status: draft consumer-side test plan. This document does not define APIs or authorize privileged operations.

## Ownership

- NEXUS-07 owns typed operation registration, arguments/results, preconditions, idempotency, cancellation and postcondition evidence.
- AEGIS-06 owns authenticated identity, deterministic risk, action digest, approval, authorization and audit policy.
- PHOENIX-10 owns installer workflow and test evidence.
- ATLAS-01 owns Fedora packaging and OS integration.

## Installer operation candidates

Read-only storage inventory; read-only target preflight; install-plan preview; registered destructive install operation; read-only operation status and postcondition verification; separately authorized recovery operation if supported. These are semantic candidates only. NEXUS-07 must assign canonical identifiers and schemas.

## Required invariants

1. No generic shell or arbitrary executable interface.
2. No implicit target selection. A target must have a stable canonical identity.
3. The complete partition, filesystem and encryption plan must be previewed before approval.
4. Approval binds the exact operation, target, arguments, principal/session, policy and registry versions, preconditions and expiry.
5. A changed target or precondition invalidates approval; revalidate immediately before execution.
6. DENY and REQUIRE_APPROVAL both imply zero executor calls.
7. Policy, identity, approval-store or required audit unavailability fails closed.
8. An uncertain timeout is `unknown_outcome`; query operation and target state before retry.
9. Cancellation is not complete until termination is confirmed.
10. A success result requires a verified postcondition.
11. Secrets never enter logs or audit payloads.
12. All destructive tests use disposable virtual disks.

## Digest ownership

AEGIS-06's current draft specifies RFC 8785 JCS, SHA-256, exact Unicode code-point preservation, and deterministic resource ordering. Do not apply NFC, NFD, NFKC, NFKD, case-folding, trimming, or any other generic text rewrite as JCS preprocessing. Preserve parsed JSON strings and property names exactly; reject invalid Unicode, including unpaired surrogates. Any operation-specific identifier normalization belongs in the trusted resource resolver: retain the original validated argument in the digest envelope and separately bind the resolver-produced canonical resource identifier. AEGIS-06 owns the canonical envelope and digest implementation; PHOENIX-10 consumes it and must not invent a competing hash format. See `security/POLICY_ENGINE_SPEC.md` §5 and `security/JCS_UNICODE_TEST_VECTORS.json` on `06-security-gatekeeper`.

## Planned negative/race tests

| Test | Expected result |
|---|---|
| Policy DENY | Zero executor calls |
| Approval required | Zero executor calls until fresh authorization |
| Policy/identity/audit unavailable | Fail closed |
| Digest, identity, policy or target mismatch | Reject before mutation |
| Expired/replayed/consumed approval | Reject |
| Target changes after preview | Precondition failure; zero writes |
| Multiple disks | No implicit target; unselected disks unchanged |
| Timeout after dispatch | `unknown_outcome`; verify before retry |
| Cancellation race | Do not report cancelled until confirmed stopped |
| Postcondition unavailable | Do not report success |
| Power loss mid-install | Report actual partial state; no false rollback claim |

## Open decisions

NEXUS-07: stable storage identity, operation schemas, typed partition plan, idempotency, timeout/cancel and postcondition contracts.

AEGIS-06: canonical action envelope, resource binding, authorization consumption, install risk mapping and audit fail-closed behavior.

ATLAS-01: Fedora storage tooling/package ownership, broker packaging boundary, and current Fedora Forge KIWI source/ref/profile/wrapper.

## Gate

Only read-only inventory/preflight prototyping may begin after NEXUS-07 confirms those interfaces. Destructive implementation remains blocked until NEXUS-07 and AEGIS-06 publish compatible reviewed contracts and authorization tests.

No ISO build, VM boot, Anaconda install, Secure Boot test or installer contract test is claimed. This is a planned test specification, not execution evidence.

## Coordination follow-up (2026-10-31)

After reviewing the current owner drafts, PHOENIX-10 posted explicit decision requests:
- NEXUS-07 issue #3 comment 6531617901: canonical storage identity/re-resolution, registered read-only inventory/preflight schemas, typed partition-plan representation, unknown-outcome status/evidence query, and authoritative health/preflight schemas.
- AEGIS-06 issue #4 comment 6531618606: canonical partition-plan/resource digest binding, one-time authorization-reference consumption, installer risk classification, pre-execution audit/fail-closed behavior, and release signing/key lifecycle ownership.
- ATLAS-01 issue #2 remains open for the current Fedora Forge KIWI clone URL, immutable Fedora 44 ref, profile path and exact build wrapper. No replacement source is assumed.

These are requests for owner decisions, not accepted contracts. The implementation gates in this document remain unchanged.


## Unicode digest conformance vectors (SEC-INST-001)

The installer consumer must preserve the exact JSON string data covered by the approval/action digest. The following AEGIS-owned RFC 8785 reference cases are mandatory integration vectors:

| Vector | Input string code points | Canonical UTF-8 hex | SHA-256 |
|---|---|---|---|
| JCS-UNICODE-001 | U+00E9 (precomposed `é`) | `7b226e616d65223a22c3a9227d` | `2f16b8477146a1b2ba7d6bb7cf7c9979c191cc2838a107dbf5f0d920b4cb3ba1` |
| JCS-UNICODE-002 | U+0065 U+0301 (decomposed `é`) | `7b226e616d65223a2265cc81227d` | `6a547588c4055916e090ed61467326046dd52810679d03bfb84d862a7123522e` |

The two inputs are canonically equivalent under Unicode normalization but MUST remain distinct for JCS and produce the distinct byte sequences and digests above. Reject invalid Unicode/unpaired surrogates before digest creation. Operation-specific identifier resolution is separate from JCS and must not rewrite the original argument.

The PHOENIX fixture test added alongside this correction verifies these two string-only reference vectors and invalid-surrogate UTF-8 rejection. It is not a full RFC 8785 implementation test and does not establish that an installer/policy/broker runtime uses a conforming canonicalizer. NEXUS/AEGIS integration tests must run the vectors through the actual production digest path before any destructive operation is enabled.

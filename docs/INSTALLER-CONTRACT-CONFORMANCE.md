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

AEGIS-06's draft specifies RFC 8785 JCS, SHA-256, NFC normalization and deterministic resource ordering. AEGIS-06 owns the canonical envelope and digest implementation; PHOENIX-10 consumes it and must not invent a competing hash format.

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

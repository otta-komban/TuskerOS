# Privileged Operations Release Security Gate

**Status:** Draft acceptance gate; no runtime implementation is certified by this document.  
**Owner:** AEGIS-06 (policy semantics); NEXUS-07 (broker/runtime evidence); dependent owners as noted.

This gate is a release blocker for any build that enables privileged OS operations. A passing document review is not a substitute for executable evidence from the shipped build.

## 1. Non-negotiable release invariants

- [ ] No model, planner, extension, remote client or UI response can grant authority.
- [ ] Every operation is registered; an empty, unreadable, invalid or untrusted registry denies all operations.
- [ ] Every registered action, including reads, is evaluated by the deterministic policy boundary.
- [ ] DENY and REQUIRE_APPROVAL produce zero executor/broker mutation calls.
- [ ] ALLOW is fresh and bound to the canonical proposal digest, authenticated principal/session, operation, resources, policy/registry version and expiry.
- [ ] Approval is action-specific, single-use and consumed atomically; concurrent consumers cannot both succeed.
- [ ] Broker independently authenticates its IPC peer and validates authorization evidence; it does not trust caller-supplied identity fields.
- [ ] Broker exposes fixed typed handlers only; no arbitrary command, shell string, executable path or unrestricted root interface.
- [ ] Mutation idempotency is durable. A timeout/disconnect after dispatch is UNKNOWN until reconciled; it is never blindly retried.
- [ ] Security audit is durable for required events, access-controlled and secret-redacted. Audit failure follows the documented fail-closed policy.
- [ ] Cancellation, rollback and compensation remain distinct authorized operations with independently verified outcomes.
- [ ] Local and remote entry points enforce the same policy and approval semantics.

## 2. Required evidence before enabling privileged operations

| Evidence | Minimum acceptance | Owner |
|---|---|---|
| Contract compatibility | Versioned proposal, decision, approval, registry and broker interfaces agree across Core and broker | AEGIS-06, TUSKER-04, NEXUS-07 |
| Runtime identity | Broker verifies OS-authenticated peer credentials and principal/session binding | NEXUS-07, PILOT-08 |
| Authorization transport | Reference/token audience, lookup, signing (if any), rotation, revocation and expiry are specified and tested | AEGIS-06, NEXUS-07 |
| Atomic consume | Durable transactional one-time consume returns a unique consumption ID; race test proves exactly one winner | NEXUS-07 |
| Registry integrity | Runtime verifies registry provenance, schema, version and fixed handler mapping; rollback/revocation is tested | NEXUS-07, AEGIS-06 |
| Policy conformance | All policy vectors run against the release implementation; non-ALLOW cases prove zero executor calls | AEGIS-06, NEXUS-07 |
| Broker conformance | Positive and negative peer, authorization, argument, precondition, idempotency and UNKNOWN tests run | NEXUS-07 |
| Audit and recovery | Tamper/access controls, redaction, disk-full behavior, reconciliation and recovery are exercised | AEGIS-06, NEXUS-07 |
| OS confinement | Service account, systemd sandboxing, SELinux policy and narrow privilege boundaries are reviewed on supported Fedora target | ATLAS-01, NEXUS-07 |
| Remote parity | Remote-origin requests cannot bypass principal binding, approval or replay controls | PILOT-08, AEGIS-06 |
| UI trust boundary | UI displays the exact action/resources being approved and cannot mint authorization | NOVA-02, AEGIS-06 |
| Extension boundary | Extensions receive declared capabilities only; untrusted extensions cannot access broker internals | FORGE-09, AEGIS-06 |

## 3. Mandatory negative tests

Release evidence must include executable tests proving all of the following:

1. Unknown action, unknown handler, malformed schema and missing registry deny by default.
2. Forged principal/origin fields do not alter trusted identity.
3. Expired, revoked, replayed, wrong-digest, wrong-principal, wrong-session, wrong-operation and wrong-resource authorization is rejected.
4. Two simultaneous consume attempts yield exactly one success.
5. Policy, registry, identity, authorization store, clock or required audit dependency failure does not fall back to execution.
6. Broker rejects an untrusted IPC peer and any unregistered operation.
7. Mutation retry with the same idempotency key does not duplicate side effects.
8. Lost response after dispatch returns UNKNOWN and reconciliation prevents blind re-execution.
9. Cancellation does not falsely report rollback; compensation requires a separate authorization.
10. Remote and extension-originated requests are subject to the same controls.

Each negative test must assert the observable side effect boundary (for example, executor invocation count is zero), not merely an error response.

## 4. Release decision

- **BLOCKED:** Any invariant or required evidence is missing, any negative test fails, or a required dependency is unavailable without a defined fail-closed behavior.
- **CONDITIONAL:** Only non-privileged preview functionality may ship; privileged handlers remain disabled by construction.
- **APPROVED:** All required evidence is attached to the release record, all mandatory tests pass on the release candidate, and AEGIS-06 plus NEXUS-07 sign off. OS, remote, UI and extension owners sign off their respective rows.

A checklist tick without a linked test result, build identifier and reviewer is not release evidence.

## 5. Current known status

At publication, this repository contains draft contracts and expected-outcome vectors only. NEXUS-07 has not confirmed authorization-reference transport, atomic consume implementation, registry runtime ownership, authenticated IPC details or the privileged execution result contract. No privileged runtime is approved; no executable policy/broker tests are claimed.

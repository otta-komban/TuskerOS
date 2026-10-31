# NEXUS-07 Integration Verification Plan

**Status:** Draft; planned scenarios are not execution evidence.

## Purpose
Define layered checks for the provisional system-integration contracts without implying that tests have run or owner-controlled interfaces are approved.

## Verification layers

| Layer | Checks | Owners | Evidence |
|---|---|---|---|
| Contract | JSON Schema fixtures, invalid inputs, typed JSON values, descriptor cross-field constraints | NEXUS-07 | Full test output and environment |
| Adapter | Canonical descriptor resolution, opaque task/step IDs, correlation propagation, deadline cap, typed results | NEXUS-07 and TUSKER-04 | Adapter tests and reviewed mapping |
| Authorization | Trusted IPC identity, AEGIS preflight, DENY and REQUIRE_APPROVAL stop conditions, fail-closed handling | AEGIS-06 and NEXUS-07 | AEGIS-approved fixtures and provider-call assertions |
| Provider lifecycle | Cancellation races, timeout/disconnect, unknown outcome, postcondition evidence and reconciliation | NEXUS-07 and TUSKER-04 | Deterministic fake-provider traces |
| D-Bus/service | Introspection, activation, restart, disable/removal and least privilege | NEXUS-07, ATLAS-01 and AEGIS-06 | Disposable VM logs and owner review |
| OS independence | Boot, login, networking, KDE and recovery without Tusker services | ATLAS-01, NOVA-02 and PHOENIX-10 | VM test matrix and dependency inspection |

## Required negative scenarios

1. Unknown descriptor name or invalid input schema: reject before provider dispatch.
2. Deadline above the descriptor limit or 300000 ms cap: reject or clamp according to the finalized adapter contract before dispatch; never silently extend it.
3. Caller JSON identity labels conflict with transport credentials: transport credentials remain authoritative.
4. AEGIS DENY or REQUIRE_APPROVAL: provider invocation count remains zero.
5. Missing, malformed, stale, mismatched, unverifiable or unavailable authorization context: fail closed; provider invocation count remains zero.
6. Timeout/disconnect after a side effect may have started: return unknown_outcome and reconcile through a separate verification operation before retry.
7. Cancellation accepted while work is running: do not report termination until confirmed by provider lifecycle.
8. Success without adequate postcondition evidence: report incomplete/uncertain evidence rather than inventing success proof.
9. Tusker services disabled or removed: base OS boot, login, networking, KDE and recovery remain functional.
10. Model runtime and remote services absent: base capability discovery and recovery remain independent.

## Positive and compatibility scenarios

- Validate every committed valid fixture and reject malformed fixtures/unsupported enum values.
- Preserve result values exactly for object, array, string, integer, float, boolean and null.
- Preserve request/task/step/correlation IDs end-to-end; consumers must treat task/step IDs as opaque.
- Resolve tool names only through canonical registered descriptor names.
- Enforce timeout ordering and idempotency support/scope consistency in the catalogue loader.
- Verify capability availability and descriptor risk never substitute for authorization.
- Verify read-only registered actions follow the AEGIS policy contract once AEGIS defines its authoritative interface.
- Verify the proposed system-bus API remains read-only and exposes no arbitrary command execution, raw file reads or privileged mutations.

## Execution gates

- **A — local contracts:** install `system-integration/requirements-test.txt`; run `python -m unittest discover -s system-integration/tests -v`; retain full output and dependency versions.
- **B — CI:** record workflow URL, commit SHA and terminal conclusion. A workflow file is not evidence of a successful run.
- **C — owner reviews:** obtain AEGIS-06 authorization review, ATLAS-01 service/namespace review and TUSKER-04 adapter freeze decision before marking shared contracts stable.
- **D — runtime:** run fake-provider and disposable-VM tests; retain provider traces, service logs and recovery evidence.
- **E — release:** ATLAS-01 and PHOENIX-10 verify package removal/upgrade/recovery; NOVA-02 verifies desktop-session independence.

## Result record template
For each executed scenario record test ID, contract revision/commit, environment, command/procedure, expected and observed result, artifact/log reference, owner, pass/fail/blocked status and follow-up issue. Mark unexecuted scenarios NOT RUN. Do not mark an owner-dependent scenario passed by using a mock that assumes the missing contract.

## Open dependencies

- **AEGIS-06:** authoritative principal binding, decision transport/vocabulary, freshness/replay/resource binding, error mapping and audit propagation.
- **ATLAS-01:** controlled reverse-DNS namespace, system-bus/service-account conventions, activation and package lifecycle review.
- **TUSKER-04:** final schema 1.0 adapter freeze decision and deadline/tool-name compatibility confirmation.
- **Runtime implementation:** provider adapters and a real D-Bus service are not evidenced by this plan.

## Non-claims
This document adds no implementation, executes no tests, approves no owner-controlled contract and does not freeze schema 1.0. Every scenario remains planned until supported by retained execution evidence.

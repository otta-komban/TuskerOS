# NEXUS-07 Initial Intake Review

**Task:** NEXUS-07-SI-001 / Issue #5 review and historical-work intake  
**Agent / branch:** NEXUS-07 / `07-NEXUS`  
**Review date:** 2026-10-31  
**Status:** Review delivered; implementation gates recorded  
**Scope:** Source/contract/branch review only. No adapter code or shared contract was changed.

## 1. Verified branch baseline

- Repository: `otta-komban/TuskerOS`
- Assigned branch exists: `07-NEXUS`
- Live `main` and `07-NEXUS` both resolve to `345fc5a3d0f831fc714bae0cc88fa842cd9bed79`.
- GitHub compare reports 0 ahead / 0 behind.
- The remote branch has no branch-only commits at intake. A local working-tree state is not exposed by the GitHub repository API and is therefore unverified.
- The role guide launch base (`5162de3...`) is historical; current live `main` is the baseline for this task. No rebase or history rewrite is proposed.

## 2. Historical branch review — exact diff before porting

Two historical refs were found:

| Ref | Comparison to current main | Review result |
|---|---:|---|
| `07-system-integration` | 0 ahead / 1697 behind | Retired/stale source ref; do not merge. |
| `agent/07-system-integration` | 99 ahead / 635 behind | Diverged legacy implementation; review only, no blind cherry-pick/merge. |

The GitHub compare result for `agent/07-system-integration` identifies these nine branch-only path changes:

1. `.github/workflows/system-integration-contracts.yml` — modified.
2. `system-integration/CAPABILITY_PERMISSION_MATRIX.md` — added.
3. `system-integration/COMPLETION_LOG.jsonl` — added (historical branch log; preserve unchanged).
4. `system-integration/SECURITY_CONTRACT_GAPS.md` — added.
5. `system-integration/adapters/README.md` — added.
6. `system-integration/adapters/__init__.py` — added.
7. `system-integration/adapters/dbus_readonly.py` — added.
8. `system-integration/tests/test_dbus_readonly.py` — added.
9. `system-integration/tests/test_dbus_readonly_lifecycle.py` — added.

### Read-only adapter review

The legacy prototype exposes only two fixed, read-only `org.freedesktop.DBus` calls (`GetId`, `ListNames`) through a fixed `busctl` invocation. It does not accept caller-selected bus names, paths, interfaces, methods, or command arguments. Source review shows bounded timeout/output, cancellation cleanup, strict response parsing, bus UUID/name validation, and a fail-closed injected authorization callback.

The prototype is deliberately not registered as a public invocation tool. Its callback accepts only a boolean decision for a fixed operation string; it is a test/composition seam, not the AEGIS consume contract. It does not independently authenticate the IPC peer, resolve a fresh authorization reference, perform durable one-time consume, or establish durable pre-dispatch audit. The legacy README explicitly says it has not been proven against a real system bus or production AEGIS integration. Historical completion records state that tests were authored but not executed locally; no passing CI result was established by the source review.

**Port decision:** do not port the adapter or its tests yet. Preserve the old branch and log. Port only after the trusted broker boundary and runtime composition contract are approved; then re-run and extend tests on this branch.

## 3. Current contract/security findings

### Blocker NX-B01 — caller-reachable authorization context

The current public `system-integration/contracts/tool-invocation.schema.json` has top-level `additionalProperties: false`, but also explicitly permits optional `authorization_context` as an object with `additionalProperties: true`. The public example in `INTERFACE_CONTRACTS.md` also includes that field. The schema cannot distinguish broker-injected trusted context from caller-authored JSON.

AEGIS records this as SEC-INT-008 in `security/SCHEMA_CONSISTENCY_AUDIT.md` and requests removal from the public caller envelope, an out-of-band or separately typed broker-internal context, and negative tests for caller-supplied `authorization_context`, `principal`, `decision`, and `authorization_ref`. A positive test must show that only independently authenticated context reaches AEGIS consume.

**Required decision:** Chief Architect approval for the shared public/internal boundary. NEXUS must not silently edit this shared contract or invent a substitute authority format.

### Blocker NX-B02 — broker transport/runtime not frozen

`security/BROKER_CONTRACT.md` and `security/AUTHORIZATION_LIFECYCLE.md` are version 0.1.0 drafts. NEXUS accepted the security invariants in principle in Issue #17 comment 6540736530: fresh opaque `authorization_ref`; atomic durable consume with unique `consumption_id`; AEGIS-owned policy/authority; NEXUS-owned registry loading and fixed handler mapping; independently authenticated IPC peer credentials; durable idempotency/dispatch records; typed consume outcomes; zero handler calls for every non-`CONSUMED` outcome; and UNKNOWN plus reconciliation after possible dispatch.

That acceptance is semantic only. The concrete IPC transport/API, runtime language, trusted peer injection, authority service/store, registry artifact provenance, and Fedora packaging details remain unselected or unapproved. No production broker or privileged execution is evidenced.

### Contract posture

- Keep privileged/mutating handlers disabled and fail-closed.
- Do not treat catalogue metadata, caller labels, a boolean callback, or `needs_approval` as authorization.
- No handler dispatch on DENY, REQUIRE_APPROVAL, mismatch, unavailable identity/authority/audit/clock/registry, or indeterminate consume.
- A timeout/disconnect after possible dispatch is UNKNOWN; reconcile the same execution before retry.

## 4. TUSKER-04 lifecycle mapping review

Reviewed the current TUSKER-04 proposal `04-TUSKER:tusker-core/TUSKER-04-TRANSITION-EVENT-PROPOSAL.md` (commit `cce53e2b91a3f9173f1004950f8e852d7ca1cebf`) and the NEXUS v0.2 interface draft.

NEXUS confirms the following provider-operation mapping for Core review:

- Operation statuses remain `succeeded`, `rejected`, `needs_approval`, `running`, `cancelled`, `failed`, and `unknown_outcome`.
- Cancellation request state (`not_requested`, `received`, `rejected`, `accepted`) is distinct from operation state (`running`, `stopped`, `completed`, `unknown`). Acceptance is not proof of stop.
- Core may mark a task `cancelled` only after all active operations are confirmed stopped and no further work can dispatch. A cancellation race may still complete a side effect.
- `unknown_outcome` is not failure or cancellation. Reconcile the same operation/idempotency identity through an authoritative read before retry; never blindly retry.
- Preserve `request_id`, `operation_id`, `task_id`, `step_id`, and `correlation_id` wherever present. Task/Plan/Step aggregate state remains TUSKER-owned; NEXUS owns provider-operation lifecycle and postcondition evidence.
- Descriptor idempotency declarations must be backed by provider behavior. They do not waive reconciliation after an unknown outcome.
- `needs_approval` is not an AEGIS preflight result and never authorizes dispatch.

This confirms the provider-to-Core mapping only. It does not approve TUSKER's proposed task transition/event semantics, event sequencing/version coupling, or freeze either side's schemas. Chief Architect approval remains required for those shared decisions.

## 5. Other coordination dependencies

- **AEGIS-06:** finalize the public-vs-internal trusted context boundary, typed consume request/outcomes, audit sequencing, and registry binding.
- **TUSKER-04:** approve the operation-to-step mapping above; separately obtain Chief Architect approval for task/event semantics.
- **ATLAS-01:** provide the requested Fedora 44 RPM dependency handoff (Issue #5 comment 6540960034); validate system API reuse, service activation and packaging only after identifiers/transport are approved.
- **NOVA-02 / PILOT-08 / FORGE-09 / ORBIT-05:** retain their existing review dependencies; do not invent session, remote-origin, extension, or inference contracts.

## 6. First implementation plan and acceptance criteria

| Step | Deliverable | Acceptance |
|---|---|---|
| 1 | Close NX-B01 with an approved public invocation / broker-internal trust boundary | Public schema rejects caller authority fields; explicit negative smuggling tests; positive trusted-context provenance test. |
| 2 | Freeze NEXUS↔AEGIS broker transport and identity contract | Typed consume API; kernel-authenticated peer/session binding; fresh authorization reference; atomic one-time consume; durable audit/dispatch ordering; fixed registry mapping. |
| 3 | Port the reviewed read-only adapter as an isolated provider primitive | Typed interface, validated inputs, bounded output/deadlines, cancellation, sanitized errors, health/readiness; no public registration until composition is approved. |
| 4 | Add authorization and provider regression coverage | Every non-CONSUMED/indeterminate outcome proves zero handler calls; positive authorized path proves exactly one call; replay/concurrency/timeout/cancellation/reconciliation tests. |
| 5 | Validate platform integration | Fedora 44 dependency evidence from ATLAS; disposable D-Bus integration; service disable/removal and failure-degradation checks. |
| 6 | Integrate lifecycle and operations docs | TUSKER mapping accepted; stable versioned contracts; exact commands, tested SHA, CI links, rollback and limitations recorded. |

**Not run in this review:** unit tests, contract test suite, GitHub Actions, D-Bus runtime integration, broker/IPC tests. This document reports source/contract review only.

## 7. Evidence

- Assigned branch comparison: `main...07-NEXUS` (identical at `345fc5a3d0f831fc714bae0cc88fa842cd9bed79`).
- Historical branch comparisons: `main...07-system-integration`; `main...agent/07-system-integration`.
- NEXUS task/review: https://github.com/otta-komban/TuskerOS/issues/5
- AEGIS review: https://github.com/otta-komban/TuskerOS/issues/17
- TUSKER activation/lifecycle blocker and proposal: https://github.com/otta-komban/TuskerOS/issues/53
- Owner authorization: https://github.com/otta-komban/TuskerOS/issues/35#issuecomment-6540346389
- Chief Architect suspension lift: https://github.com/otta-komban/TuskerOS/issues/34#issuecomment-6540711800

No historical branch was modified, merged, rebased, or cherry-picked.

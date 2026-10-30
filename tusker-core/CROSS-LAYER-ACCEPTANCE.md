# Core Cross-Layer Acceptance Matrix

**Owner:** TUSKER-04  
**Branch:** `04-tusker-core`  
**Status:** Review baseline; not a frozen shared API  
**Reviewed:** 2026-10-31

This matrix records what Core can safely map from the current NEXUS-07 and AEGIS-06 drafts, what is confirmed by the owners, and what remains a release blocker. It deliberately does not define the missing authorization transport or broker wire format.

## 1. Accepted mapping baseline

| Boundary | Current source contract | Core handling | Acceptance status |
|---|---|---|---|
| Tool identity | NEXUS invocation `tool`, descriptor `name` | Resolve only through the registered catalogue; validate arguments against descriptor input schema before dispatch | Accepted in principle; NEXUS owner confirmation still requested |
| Invocation correlation | NEXUS `request_id`, `task_id`, `step_id`, `correlation_id` | Preserve request ID for one invocation and task/step/correlation IDs across lifecycle events; treat bounded task/step strings as opaque | Compatible; Core UUID producer rule is a valid subset |
| Caller metadata | NEXUS `caller.component`, `caller.instance_id` | Treat as descriptive only; never use as principal identity | Accepted; identity must come from trusted IPC peer/authenticated context |
| Authorization result | AEGIS decision `DENY`, `REQUIRE_APPROVAL`, `ALLOW` | Only fresh, correctly bound ALLOW may proceed; DENY and REQUIRE_APPROVAL cause zero executor calls | AEGIS semantics confirmed; transport/consume handoff unresolved |
| Authorization binding | AEGIS digest, principal binding, policy version, expiry, opaque reference | Retain returned decision metadata as evidence; do not accept caller/model-supplied identity, decision, risk or bearer reference | Semantic baseline accepted; exact broker context schema pending |
| Mutation idempotency | AEGIS requires key for every mutation; NEXUS invocation supports optional key | Require a key for mutation at Core catalogue/dispatch boundary; do not retry uncertain mutations blindly | AEGIS owner confirmed; durable NEXUS persistence/reconciliation details pending |
| Tool outcome | NEXUS result status, postcondition, side effects, cancellation and evidence refs | Map typed status to Core step/task state; `unknown_outcome` enters reconciliation, not failure-and-retry | Schema mapping feasible; NEXUS implementation contract/owner sign-off pending |
| Cancellation | NEXUS separates request state from operation state | Acknowledged cancellation request is not proof the operation stopped; Core marks cancelled only after confirmed stop and stopped remaining work | Semantics compatible; provider-specific guarantees remain descriptor-driven |
| Catalogue risk metadata | NEXUS descriptor risk, privilege, side effects, pre/postconditions | Use for planning, display and policy proposal context only; never treat metadata as an authorization grant | Compatible; AEGIS evaluates each registered action |

## 2. AEGIS decisions Core treats as confirmed

- Core may retain UUID generation for task and step IDs; consumers must treat identifiers as opaque bounded strings.
- Every mutation requires an idempotency key; policy denies a mutation missing one.
- ALLOW is rejected if expiry or authorization reference is absent, expired, or mismatched to digest, principal/session, operation or resources, or if revoked/replayed.
- DENY has null expiry, approval request ID and authorization reference.
- REQUIRE_APPROVAL has an approval request ID and null authorization reference.
- AEGIS policy schema package is draft v0.1.0. These confirmations do not freeze transport or broker-consumption protocol.

## 3. Hard dispatch gate

Core MUST require all of the following before a mutating handler can be reached:

1. Trusted ingress principal/session context obtained outside caller-controlled payload fields.
2. A registered operation and schema-valid, bounded arguments.
3. A fresh AEGIS ALLOW bound to the exact proposal digest, principal/session, operation and canonical resources.
4. Non-empty valid expiry and opaque authorization reference.
5. A mutation idempotency key where the operation mutates state.
6. NEXUS/broker-side independent peer, operation, resource, precondition and authorization validation, including atomic one-time consumption as specified by AEGIS.
7. No unresolved prior execution for the same idempotency scope/key.

Any absent, denied, expired, mismatched, replayed, revoked or indeterminate authorization condition fails closed with zero handler dispatch. The Core-side check is not a substitute for broker-side validation.

## 4. Open decisions — do not implement by assumption

| Owner | Required decision | Blocking consequence |
|---|---|---|
| NEXUS-07 | Exact strict `authorization_context` schema and trusted injection boundary | Core cannot safely serialize or validate broker authorization context |
| NEXUS-07 + AEGIS-06 | Whether broker invokes atomic AEGIS consume immediately before handler dispatch, or Core calls consume first; exact request/response and typed errors | No privileged/mutating broker adapter implementation |
| AEGIS-06 | Approval completion semantics: fresh ALLOW/reference versus direct consumption of approved request reference | Core cannot implement approval resume/handoff |
| NEXUS-07 | Durable consumption/execution identifiers, concurrent replay behavior, lost-response reconciliation and mutation idempotency across restart | No retry/recovery implementation for uncertain mutations |
| NEXUS-07 + AEGIS-06 | Typed outcomes for authority outage, invalid/replayed/already-consumed reference, expiry, revocation and required audit failure | Core maps only generic fail-closed errors; no detailed recovery policy |
| ORBIT-05 | Normative inference request/event/error schemas and disconnect/cancellation terminal semantics | No frozen inference adapter |
| ATLAS-01 | Per-user IPC, peer identity, systemd --user lifecycle, XDG paths and SQLite/WAL recommendation | No service/persistence ADR |

## 5. Review and implementation gates

- [x] Compare NEXUS invocation/result/descriptor schema fields against Core lifecycle identifiers.
- [x] Record AEGIS owner-confirmed decision semantics and mutation idempotency.
- [x] Define Core fail-closed dispatch invariants without inventing wire fields.
- [ ] Obtain explicit NEXUS acceptance of Core mapping and exact authorization/broker contract.
- [ ] Obtain AEGIS approval-handoff and typed consume outcome decisions.
- [ ] Freeze versioned shared schemas after owner sign-off.
- [ ] Implement transport adapter only after ATLAS IPC decision and NEXUS/AEGIS consume contract.
- [ ] Add executable cross-boundary tests, including zero-dispatch denial, replay/concurrency and lost-response reconciliation.
- [ ] Run tests and verify CI; no test pass is claimed by this document.

**Evidence:** NEXUS issue #5 review thread; AEGIS issue #16 review thread; Core `AUTHORIZATION-ADAPTER.md`; AEGIS `AUTHORIZATION_LIFECYCLE.md` and `BROKER_CONTRACT.md`; NEXUS `tool-invocation.schema.json`, `tool-result.schema.json` and `tool-descriptor.schema.json`.

This is a Core review artifact, not an authorization grant, implementation approval or replacement for owner-controlled contracts.

# AEGIS-06 Audit Lifecycle Coverage Review

**Task:** AEGIS-06-P1.2 — read-only audit schema/lifecycle reconciliation  
**Branch:** `06-AEGIS`  
**Status:** Review finding; candidate schema and producer semantics are not approved  
**Scope:** Compare `security/AUTHORIZATION_LIFECYCLE.md`, `security/SECURITY_CONTRACTS.md`, the active audit-event v0.1.0 schema, and the candidate v0.2.0 schema.

## Result

The current candidate v0.2.0 event vocabulary covers request receipt, authorization, dispatch/execution, cancellation, compensation, and three approval outcomes. It does **not** provide distinct event types for several transitions explicitly required by the authorization lifecycle. The active v0.1.0 schema has the same lifecycle coverage limitation and additionally lacks the candidate's registry status/version fields.

This is a schema/prose coverage audit only. No shared schema, producer, consumer, transport, or runtime behavior was changed.

## Lifecycle-to-schema matrix

| Normative lifecycle evidence | Candidate v0.2.0 representation | Coverage | Review note |
|---|---|---|---|
| Request created / received | `requested` / `accepted` | Direct | Candidate also permits the narrowly defined unavailable-registry request receipt. |
| Approval request presented to approver | None | Missing | Presentation is a security-relevant disclosure/UI event and needs correlation to the request and authenticated presenter. |
| Approver approves | `approval_granted` / `accepted` | Direct | Must remain distinct from fresh authorization issuance and broker consume. |
| Approver denies | `approval_denied` / `denied` | Direct | Preserve a stable reason code and approver provenance. |
| Approver dismisses | No dedicated event | Partial / ambiguous | Lifecycle prose permits a terminal denial with a distinct dismissal reason or an explicit dismissal state. Candidate semantics do not state whether `approval_denied` plus a dedicated reason is sufficient. |
| Approval expires | `approval_expired` / `denied` | Direct | Candidate mapping exists; trusted clock and expiry boundary remain producer/runtime responsibilities. |
| Approval invalidated by changed binding | None | Missing | Must not be confused with user denial or policy denial; include invalidation reason and changed-binding correlation without leaking sensitive values. |
| Approval / authorization revoked | None | Missing | Requires an authenticated revocation source and stable reason; should identify which authority state was revoked. |
| Authorization consume accepted | None | Missing | `authorized` is fresh policy ALLOW, not proof of atomic broker consume. Do not overload it. |
| Authorization consume rejected | None | Missing | Must distinguish binding mismatch, expiry, replay, unavailable authority, and audit failure using typed outcomes/reasons. |
| Consume / execution reconciliation outcome | None | Missing | `outcome_unknown` is an execution uncertainty state, not a reconciliation result. Reconciliation must state whether an existing consume/dispatch was found and must not imply a new grant. |
| Broker dispatch started | `started` / `pending` | Direct | Must follow confirmed consume and durable dispatch intent. |
| Execution succeeded / failed | `succeeded` / `success`; `failed` / `failure` | Direct | Postcondition evidence remains owned by the execution adapter. |
| Cancellation / compensation | Existing cancellation and compensation event types | Direct for listed types | Cancellation acceptance is not proof that work stopped; compensation remains a separately authorized action. |

## Required owner decisions

Before promoting candidate v0.2.0 or changing any shared schema:

1. **NEXUS-07:** identify the trusted producer for presentation, consume, revocation, and reconciliation events; define the exact event timing relative to atomic consume and durable dispatch intent.
2. **TUSKER-04:** confirm task/step/correlation identifiers and event ordering in the Core event model.
3. **NOVA-02:** confirm which trusted UI/presentation evidence is available and whether dismissal is represented as a distinct event or as a denial with a dedicated reason.
4. **Chief Architect:** approve any new event names, required fields, conditional status mappings, and schema-version migration.
5. **AEGIS-06:** keep the candidate's event/status mapping, registry provenance, and denial/failure reason constraints internally consistent; add producer-level tests only after the producer contract is accepted.

## Candidate design questions (not decisions)

- Should presentation be `approval_presented` with an explicit result status and trusted presenter identity, or be represented in a separate UI security event stream?
- Should dismissal be `approval_dismissed`, or `approval_denied` with a mandatory stable `APPROVAL_DISMISSED` reason? Do not assume equivalence without NOVA/TUSKER agreement.
- Should invalidation and revocation be separate event types, since their authorities and incident meaning differ?
- Should consume use `authorization_consumed` and `authorization_consume_rejected`, each correlated by approval request, authorization reference hash/identifier, and consumption ID where available? Never log the raw authorization reference.
- Should reconciliation be a typed `consume_reconciled` / `execution_reconciled` event with a bounded outcome enum, or separate event types? It must not be conflated with `outcome_unknown`.
- Which result-status values and reason codes are valid for each proposed event, and which producer owns them?

## Verification and limits

- Source review: lifecycle prose, security contract minimum audit fields, active audit-event v0.1.0 schema, and candidate audit-event v0.2.0 schema.
- No schema or runtime tests were run for this document-only review.
- No producer, UI, authority, broker, persistence, or reconciliation behavior is claimed.
- Privileged operations remain **BLOCKED** under `security/PRIVILEGED_RELEASE_GATE.md` until cross-agent runtime evidence and owner sign-offs exist.

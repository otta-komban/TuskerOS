# AEGIS-06 Audit Lifecycle Coverage Review

**Task:** AEGIS-06-P1.2 — read-only audit schema/lifecycle reconciliation  
**Branch:** `06-AEGIS`  
**Status:** Field-level source review complete; event vocabulary and producer semantics remain unapproved  
**Scope:** Compare `security/AUTHORIZATION_LIFECYCLE.md`, `security/SECURITY_CONTRACTS.md`, active audit-event v0.1.0, candidate v0.2.0, schema tests, and the latest NEXUS-07 handoff.

## Result

The candidate v0.2.0 schema adds explicit registry provenance/status and remote device/session digest constraints, plus stricter required-key and result/reason validation. It does not add lifecycle event types for presentation, dismissal, invalidation, revocation, authorization consume, or reconciliation. The v0.1.0 and v0.2.0 event vocabularies and their 15 event/result-status pairings are otherwise the same.

The field-level review is complete as a source review. It identifies several conditional-field questions that require owner decisions before the candidate can be frozen. This is not approval to migrate producers or change shared contracts.

## Lifecycle-to-schema matrix

| Normative lifecycle evidence | Candidate v0.2.0 representation | Coverage | Review note |
|---|---|---|---|
| Request created / received | `requested` / `accepted` | Direct | Candidate permits the narrowly defined unavailable-registry request receipt. |
| Approval request presented to approver | None | Missing | Presentation is a security-relevant disclosure/UI event and needs correlation to the request and authenticated presenter. |
| Approver approves | `approval_granted` / `accepted` | Direct | Must remain distinct from fresh authorization issuance and broker consume. |
| Approver denies | `approval_denied` / `denied` | Direct | Preserve a stable reason code and approver provenance. |
| Approver dismisses | No dedicated event | Partial / ambiguous | Lifecycle prose permits a terminal denial with a distinct dismissal reason or an explicit dismissal state. Candidate semantics do not choose between them. |
| Approval expires | `approval_expired` / `denied` | Direct | Trusted clock and expiry boundary remain producer/runtime responsibilities. |
| Approval invalidated by changed binding | None | Missing | Must not be confused with user or policy denial. |
| Approval / authorization revoked | None | Missing | Requires an authenticated revocation source and stable reason. |
| Authorization consume accepted / rejected | None | Missing | `authorized` means fresh policy ALLOW, not proof of atomic broker consume. Typed consume outcomes remain separate. |
| Consume / execution reconciliation outcome | None | Missing | `outcome_unknown` is an execution uncertainty state, not a reconciliation result. |
| Broker dispatch started | `started` / `pending` | Direct | Must follow confirmed consume and durable dispatch intent. |
| Execution succeeded / failed | `succeeded` / `success`; `failed` / `failure` | Direct | Postcondition evidence remains owned by the execution adapter. |
| Cancellation / compensation | Existing cancellation and compensation event types | Direct for listed types | Cancellation acceptance is not proof that work stopped; compensation remains separately authorized. |

## Field-level required / nullable / conditional audit

### Shared base envelope (v0.1.0 and v0.2.0)

| Field(s) | Required key? | Nullability / constraint | Review finding |
|---|---:|---|---|
| `schema_version` | Yes | Exact version constant | Correctly separates 0.1.0 and 0.2.0 envelopes. |
| `event_id`, `timestamp_utc` | Yes | UUID and date-time formats | Format assertions must remain enabled in validators. |
| `event_type`, `origin`, `risk_class`, `result_status` | Yes | Closed enums | Event/status pairings are constrained in v0.2.0; vocabulary still lacks lifecycle transitions listed above. |
| `principal_binding`, `action_digest` | Yes | Lowercase SHA-256 digest pattern | No raw principal/session/credential material should be substituted. |
| `proposal_id`, `operation_id`, `policy_version`, `correlation_id` | Yes | UUID, bounded non-empty strings as defined | Correlation semantics and event-specific presence are not further constrained. |
| `task_id`, `step_id` | Yes | String or null | TUSKER-04 must confirm when these may be null, since the proposal contract calls for task/step correlation. |
| `decision_id` | Yes | UUID or null | Candidate does not condition non-null decision IDs on decision/authorization event types. |
| `approval_request_id` | No | If present, UUID or null | Lifecycle events involving approval should be correlated to the approval request; schema does not require this key or a non-null value for approval events. |
| `executor_id` | v0.1: No; v0.2: Yes | String or null | v0.2 requires the key even for pre-execution events, where null is valid. Producer must distinguish “not applicable” from missing data. |
| `reason_code` | v0.1: No; v0.2: Yes | String or null; v0.2 requires non-empty string for denied/failure | v0.2 closes omission for ordinary events while preserving explicit null when no reason applies. |

### v0.2.0 additions and conditional rules

| Field(s) / rule | Required key? | Nullability / condition | Review finding |
|---|---:|---|---|
| `registry_status` | Yes | `resolved` or `unavailable` | Must come from trusted registry resolution, not caller input. |
| `registry_version` | Yes | String or null; resolved requires non-empty string; unavailable requires null | Good explicit status/version pairing. NEXUS says version is derived from the verified immutable registry artifact. |
| Unavailable registry | Conditional | Only `requested`/`accepted` with null reason, or `policy_denied`/`denied` with `POLICY_REGISTRY_UNAVAILABLE` | Prevents post-request authorization/dispatch events while registry is unavailable. |
| `device_binding`, `session_binding` | Conditional | Both required for remote origin; SHA-256 digests; forbidden for non-remote origin | Schema shape is strict; trusted remote adapter derivation remains unproven by schema tests. |
| `transaction_id`, `snapshot_digest` | No | Optional as a pair; if either appears, both are required; digest must be SHA-256 | Pairing is enforced, but schema does not limit them to a specific transaction/event family. Confirm whether that breadth is intentional. |
| Denial/failure reason | Conditional | `reason_code` must be a non-empty string when result is `denied` or `failure` | Consistent with stable failure reason requirement. |

### Schema test coverage observed in source

The current `security/tests/test_security_schemas.py` contains schema-level checks for:
- v0.1.0 required task/step keys with explicit null accepted;
- v0.2.0 required `registry_version`, `registry_status`, `executor_id`, and `reason_code` keys, including explicit null executor/reason;
- resolved/unavailable registry pairing and rejection of authorization/post-request events while registry is unavailable;
- all 15 declared event/result-status pairs and deliberately inconsistent pairs;
- transaction/snapshot digest pair presence and digest format;
- remote device/session digest requirements and rejection of raw identity/credential/payload fields.

These are source observations, not a claim that tests were executed in this review. They validate schema envelopes, not trusted producer provenance, event timing, audit persistence, broker behavior, or live identity derivation.

## NEXUS-07 handoff and ownership clarification

The latest NEXUS-07 response on issue #17 accepts the security invariants in principle: fresh opaque `authorization_ref`, durable atomic one-time consume with unique `consumption_id`, NEXUS ownership of runtime registry verification/fixed handler mapping, independent IPC peer authentication, and durable idempotency with UNKNOWN reconciliation. These are design acceptances, not implementation evidence or approval of a wire format.

The handoff clarifies event ownership:
- **AEGIS-06:** approval, presentation, expiry, invalidation, revocation, and authorization-consume audit events.
- **NEXUS-07:** broker dispatch, provider-operation, and execution-reconciliation events.
- **TUSKER-04:** task/step lifecycle events and correlation mapping.
- **NOVA-02:** trusted UI/presentation evidence and dismissal semantics remain to be confirmed.

NEXUS supports explicit lifecycle event types rather than overloading execution events and prefers a single reconciliation-completed event with a typed outcome. AEGIS still owns the final event names and enum vocabulary. Candidate v0.2.0 is not approved for producer migration by the NEXUS response.

## Required owner decisions

Before promoting candidate v0.2.0 or changing any shared schema:

1. **NEXUS-07:** define trusted producer timing for consume acceptance/rejection, dispatch, and execution reconciliation; identify the durable authority/store and confirm the single reconciliation-completed event proposal.
2. **TUSKER-04:** confirm task/step/correlation identifiers, nullability, and event ordering in the Core event model.
3. **NOVA-02:** confirm trusted presentation evidence and whether dismissal is a distinct event or denial with a dedicated reason.
4. **Chief Architect:** approve new event names, required fields, conditional status mappings, and schema-version migration.
5. **AEGIS-06:** preserve consistent event/status/reason constraints and add producer-level tests only after the producer contract is accepted.

## Candidate design questions (not decisions)

- Should presentation be `approval_presented` or a separate UI security event stream?
- Should dismissal be `approval_dismissed`, or `approval_denied` with a mandatory stable `APPROVAL_DISMISSED` reason?
- Should invalidation and revocation be separate event types?
- Should consume use distinct accepted/rejected events correlated by approval request, non-secret authorization reference identifier/hash, and consumption ID where available? Never log the raw authorization reference.
- Should reconciliation be one completion event with a bounded typed outcome, as NEXUS recommends, or separate consume/execution reconciliation events?
- Should `approval_request_id` be required and non-null for all approval lifecycle events? Which event types require a non-null `decision_id`, `task_id`, or `step_id`?
- Are transaction/snapshot fields intended for all event types or only package/transaction lifecycle events?
- Which result-status values and reason codes are valid for each proposed event, and which producer owns them?

## Verification and limits

- Source review: authorization lifecycle, security contract, active v0.1.0 schema, candidate v0.2.0 schema, schema test source, and latest NEXUS-07 issue response.
- No tests were run for this documentation-only update.
- No schema, event vocabulary, producer, consumer, UI, authority, broker, persistence, transport, or runtime behavior was changed.
- Privileged operations remain **BLOCKED** under `security/PRIVILEGED_RELEASE_GATE.md` until cross-agent runtime evidence and owner sign-offs exist.

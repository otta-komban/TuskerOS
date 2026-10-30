# Audit event registry-version schema proposal

**Owner:** AEGIS-06  
**Status:** Candidate v0.2.0 schema and envelope tests implemented on `06-security-gatekeeper`; producer-owner acceptance pending  
**Current schema:** audit-event 0.1.0-draft  
**Finding:** SEC-SCHEMA-003

## Problem

`security/AUTHORIZATION_LIFECYCLE.md` requires audit records to include both policy and registry version. The current `security/schemas/audit-event.schema.json` requires `policy_version` but has no `registry_version` property. A schema-valid event therefore cannot identify the exact operation-registry revision used for the decision.

## Proposed wire-format change

Publish a separate audit-event schema version `0.2.0`; preserve 0.1.0 as a historical draft and do not silently reinterpret existing events.

Add the following property and include it in the top-level `required` array:

| Property | Type | Constraint | Source |
|---|---|---|---|
| `registry_status` | enum | `resolved` or `unavailable`; sourced by trusted registry authority | Registry resolution outcome |
| `registry_version` | string or null | non-empty 1–128 chars when resolved; null only for narrowly defined pre-evaluation/unavailable events | Trusted immutable operation-registry snapshot used during policy evaluation |

The proposed 0.2.0 schema identifier should end in `audit-event-0.2.0.json`, and `schema_version` must be the constant `0.2.0`.

## Producer and consumer rules

1. The policy/registry authority supplies the exact immutable registry version used for the decision. Do not accept a model, extension, remote caller or UI assertion as authoritative.
2. The producer records the same registry version that was included in the authorization/action digest and that the broker rechecks at consume time.
3. `registry_status` is derived only by the trusted registry authority. When `resolved`, `registry_version` MUST be a concrete non-empty immutable version. When `unavailable`, `registry_version` MUST be explicit null and the event is restricted to a pre-evaluation `requested`/`accepted` record with null reason, or a `policy_denied`/`denied` record with `POLICY_REGISTRY_UNAVAILABLE`. No authorization, consume, dispatch or execution event is valid with unavailable registry status. A missing, corrupt, unverifiable, stale or unavailable registry fails closed.
4. Consumers reject a 0.1.0 event when a 0.2.0 envelope is required, and vice versa. No implicit default such as `unknown`, empty string or current registry version is allowed.
5. Preserve `task_id` and `step_id` as required keys with nullable values, per SEC-SCHEMA-002.
6. Keep `policy_version` and `registry_version` distinct: policy rules and the registered operation set have independent version lifecycles.

## Required validation

Positive:
- valid 0.2.0 audit event with a non-empty registry version;
- distinct policy and registry versions are both preserved;
- explicit null `task_id` and `step_id` remain valid.

Negative:
- missing `registry_version` or `registry_status`; null/empty version with `registry_status: resolved`; non-null version with `registry_status: unavailable`;
- unavailable registry paired with any authorization/dispatch/execution event, or denial without `POLICY_REGISTRY_UNAVAILABLE`;
- registry version longer than 128 characters;
- 0.1.0 payload presented to the 0.2.0 validator and vice versa;
- unknown additional fields and malformed timestamp/UUID/digest values.

## Owner review

- **NEXUS-07:** authoritative registry version source, snapshot immutability and producer/broker handoff.
- **TUSKER-04:** audit producer correlation and action-digest compatibility.
- **AEGIS-06:** security semantics, schema and negative-test review.

This proposal does not modify the 0.1.0 schema and does not claim producer integration, audit persistence, integrity protection or runtime enforcement. Keep SEC-SCHEMA-003/005 open until the owners accept registry-state provenance and event timing and tests pass against the actual producer.


## Additional minimum audit fields — SEC-SCHEMA-004

The normative audit contract also lists `executor_id` and `reason_code` as minimum fields. The current 0.1.0 schema defines both as nullable properties but does not require their keys. Include the following in the same candidate 0.2.0 revision as `registry_version`, subject to producer-owner acceptance:

| Property | Proposed type | Constraint | Semantics |
|---|---|---|---|
| `executor_id` | string or null | maxLength 128 when string | Required key; null before an executor is assigned. Producers supply the stable executor identity once known. |
| `reason_code` | string or null | maxLength 96 when string | Required key; null when no reason applies. Denial/failure producers should provide a stable reason code. |

### Additional validation cases

Positive:
- 0.2.0 event with concrete executor_id and reason_code;
- explicit `executor_id: null` for a pre-execution event;
- explicit `reason_code: null` when no reason applies.

Negative:
- omitted executor_id or reason_code key;
- non-string, non-null executor_id or reason_code;
- denial/failure event without a stable reason_code.

These cases remain proposed. Do not change the current 0.1.0 audit schema or claim producer conformance until NEXUS-07/TUSKER-04 agree on event lifecycle semantics and migration.


## Candidate implementation evidence — AEGIS-06 C0023

A separate candidate file now exists at `security/schemas/audit-event-0.2.0.schema.json`. The active `audit-event.schema.json` remains v0.1.0 and is unchanged by this candidate.

The candidate combines SEC-SCHEMA-003 and SEC-SCHEMA-004:
- requires non-empty `registry_version` (1–128 characters);
- requires `executor_id` and `reason_code` keys while preserving nullable values;
- requires a non-empty string `reason_code` when `result_status` is `denied` or `failure`;
- retains required nullable `task_id` and `step_id`;
- fixes `schema_version` to `0.2.0` and uses a distinct schema identifier.

The test suite now loads the candidate through the same Draft 2020-12 validator and format checker used for the existing schemas. Added positive/negative cases cover required fields, explicit nulls, invalid and overlength values, denial/failure reason requirements, and rejection of cross-version envelopes. GitHub Actions run 41128179870 passed 47 tests in 0.45s for the initial candidate before SEC-SCHEMA-005 registry-state semantics were added.

This establishes schema-level candidate behavior only. It does not establish that a trusted producer can supply registry_version, that executor/reason semantics are accepted by event producers, or that audit persistence/integrity is implemented. Keep the candidate unpromoted until NEXUS-07 and TUSKER-04 accept provenance, lifecycle semantics and migration.


## Open design question — registry unavailable before evaluation (SEC-SCHEMA-005)

The required non-empty `registry_version` above is not yet sufficient to define every lifecycle event. `AUTHORIZATION_LIFECYCLE.md` requires request-created and denial events, while `OPERATION_REGISTRY.md` requires deny-all when no trustworthy registry snapshot is available. The proposal does not yet define a truthful registry field for those pre-evaluation/failure events.

Do not fabricate `unknown`, use an empty string, or silently omit the event. Before freezing 0.2.0, NEXUS-07 and TUSKER-04 must decide whether a pre-evaluation event carries an explicit null plus a separate registry-resolution state/reason, while ALLOW/CONSUMED/dispatch events require a concrete immutable version. The decision must preserve correlation across decision, consume and execution audit records. This remains an open question; the proposed non-null field is not approved for all event types.


## SEC-SCHEMA-005 candidate resolution — AEGIS-06 draft semantics

The candidate v0.2.0 schema now requires both `registry_status` and `registry_version` keys:

- `registry_status: resolved` requires a concrete non-empty `registry_version`.
- `registry_status: unavailable` requires `registry_version: null` and permits only:
  - `event_type: requested`, `result_status: accepted`, `reason_code: null` for the received request before registry resolution; or
  - `event_type: policy_denied`, `result_status: denied`, `reason_code: POLICY_REGISTRY_UNAVAILABLE` for fail-closed rejection.
- No ALLOW/authorization, consume, dispatch, success, failure or UNKNOWN execution event can use unavailable registry status. Those events require a resolved immutable registry version.

This is an AEGIS schema proposal, not a claim that NEXUS-07 has accepted the state source or that producers can currently emit it. The registry authority must derive `registry_status` and `registry_version`; caller/model/UI values are untrusted. Keep SEC-SCHEMA-005 open for owner review and producer lifecycle validation.


## Registry-unavailable semantics and validation — C0025

The candidate now requires `registry_status` and `registry_version` as a pair:

- `registry_status: resolved` requires a concrete non-empty immutable version.
- `registry_status: unavailable` requires `registry_version: null` and permits only a pre-evaluation `requested`/`accepted` event with null reason, or a fail-closed `policy_denied`/`denied` event with `POLICY_REGISTRY_UNAVAILABLE`.
- No authorization, consume, dispatch or execution event can validate with unavailable status.

The first CI attempt after adding these rules failed two tests because the schema edit accidentally replaced (rather than preserved) the prior denial/failure non-empty reason-code condition. That failure was corrected by retaining all three independent conditional rules. GitHub Actions run 41128922282 then passed **54 tests in 0.60s** on Python 3.12.

The active v0.1.0 schema remains unchanged. This is schema-level validation only; the trusted status source, producer event timing and migration still require NEXUS-07/TUSKER-04 acceptance. The candidate must not be treated as runtime conformance.


## Event lifecycle/status consistency — C0029

The v0.2.0 candidate now constrains `event_type` to its corresponding `result_status` rather than accepting arbitrary cross-products of the two enums. The explicit pairs are: requested/accepted; authorized/success; started/pending; succeeded/success; failed/failure; cancellation_requested/accepted; cancelled/cancelled; outcome_unknown/unknown; compensation_started/pending; compensation_verified/success; compensation_failed/failure; approval_granted/accepted; approval_denied/denied; approval_expired/denied; and policy_denied/denied. Denial/failure reason-code requirements remain independently enforced. These are proposed producer semantics; runtime-owner acceptance is still required before the candidate is frozen.

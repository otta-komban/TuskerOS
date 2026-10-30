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
| `registry_version` | string | minLength 1, maxLength 128 | Trusted immutable operation-registry snapshot used during policy evaluation |

The proposed 0.2.0 schema identifier should end in `audit-event-0.2.0.json`, and `schema_version` must be the constant `0.2.0`.

## Producer and consumer rules

1. The policy/registry authority supplies the exact immutable registry version used for the decision. Do not accept a model, extension, remote caller or UI assertion as authoritative.
2. The producer records the same registry version that was included in the authorization/action digest and that the broker rechecks at consume time.
3. If the registry version is unavailable, ambiguous or changes before execution, privileged execution fails closed and the audit event must not fabricate a version.
4. Consumers reject a 0.1.0 event when a 0.2.0 envelope is required, and vice versa. No implicit default such as `unknown`, empty string or current registry version is allowed.
5. Preserve `task_id` and `step_id` as required keys with nullable values, per SEC-SCHEMA-002.
6. Keep `policy_version` and `registry_version` distinct: policy rules and the registered operation set have independent version lifecycles.

## Required validation

Positive:
- valid 0.2.0 audit event with a non-empty registry version;
- distinct policy and registry versions are both preserved;
- explicit null `task_id` and `step_id` remain valid.

Negative:
- missing, null or empty `registry_version`;
- registry version longer than 128 characters;
- 0.1.0 payload presented to the 0.2.0 validator and vice versa;
- unknown additional fields and malformed timestamp/UUID/digest values.

## Owner review

- **NEXUS-07:** authoritative registry version source, snapshot immutability and producer/broker handoff.
- **TUSKER-04:** audit producer correlation and action-digest compatibility.
- **AEGIS-06:** security semantics, schema and negative-test review.

This proposal does not modify the 0.1.0 schema and does not claim producer integration, audit persistence, integrity protection or runtime enforcement. Keep SEC-SCHEMA-003 open until the owners accept the versioned field and tests pass against the actual producer.


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

The test suite now loads the candidate through the same Draft 2020-12 validator and format checker used for the existing schemas. Added positive/negative cases cover required fields, explicit nulls, invalid and overlength values, denial/failure reason requirements, and rejection of cross-version envelopes. CI execution is pending.

This establishes schema-level candidate behavior only. It does not establish that a trusted producer can supply registry_version, that executor/reason semantics are accepted by event producers, or that audit persistence/integrity is implemented. Keep the candidate unpromoted until NEXUS-07 and TUSKER-04 accept provenance, lifecycle semantics and migration.


## Open design question — registry unavailable before evaluation (SEC-SCHEMA-005)

The required non-empty `registry_version` above is not yet sufficient to define every lifecycle event. `AUTHORIZATION_LIFECYCLE.md` requires request-created and denial events, while `OPERATION_REGISTRY.md` requires deny-all when no trustworthy registry snapshot is available. The proposal does not yet define a truthful registry field for those pre-evaluation/failure events.

Do not fabricate `unknown`, use an empty string, or silently omit the event. Before freezing 0.2.0, NEXUS-07 and TUSKER-04 must decide whether a pre-evaluation event carries an explicit null plus a separate registry-resolution state/reason, while ALLOW/CONSUMED/dispatch events require a concrete immutable version. The decision must preserve correlation across decision, consume and execution audit records. This remains an open question; the proposed non-null field is not approved for all event types.

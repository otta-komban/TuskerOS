# Core-to-NEXUS Adapter Profile

**Owner:** TUSKER-04  
**Status:** Provisional implementation profile; NEXUS contract v0.2 remains unapproved  
**Applies to:** Core Plan/Step -> NEXUS tool invocation -> NEXUS result  
**Source:** `07-system-integration/system-integration/INTERFACE_CONTRACTS.md` on branch `07-system-integration`

This profile turns the currently published NEXUS compatibility notes into explicit Core adapter behavior. It does not freeze the shared API, define the unresolved AEGIS authorization-context shape, or claim an implemented adapter.

## 1. Identifier mapping

| Core value | NEXUS value | Adapter rule |
|---|---|---|
| Plan Step `operation_id` | Invocation `tool`; descriptor `name` | Resolve only through the registered descriptor. Require the descriptor's canonical dotted name; never derive it from user/model text. |
| Core Task `task_id` | Invocation/result `task_id` | Preserve the UUID string byte-for-byte. Treat it as opaque. |
| Core Step `step_id` | Invocation/result `step_id` | Preserve the UUID string byte-for-byte. Treat it as opaque. |
| Per-dispatch invocation ID | `request_id` | Generate a fresh UUID for each actual dispatch; do not reuse the task's submission request ID. Preserve it through result/progress/cancellation correlation. |
| Core trace context | `correlation_id` | Preserve the same trace ID across the step lifecycle. |
| Step mutation key | `idempotency_key` | Stable for the logical mutation attempt group and scoped as NEXUS specifies. Never synthesize a new key merely because the response was lost. |
| Trusted adapter identity | `caller` metadata + authenticated IPC peer | Caller JSON is descriptive only. Obtain identity from trusted IPC peer credentials and the AEGIS-approved context. |
| AEGIS authorization | `authorization_context` | Pass only the owner-approved trusted context. Never accept model-, user-, file- or remote-body-supplied identity/authority claims. Exact shape/transport remains blocked on AEGIS/NEXUS agreement. |

## 2. Deadline negotiation

NEXUS invocation `deadline_ms` has a hard schema ceiling of 300000 ms. The selected descriptor supplies minimum, default and maximum timeout values.

1. Validate descriptor metadata before use: `minimum <= default <= maximum`, all values positive integers.
2. For an explicitly requested Core timeout, require it to be within the descriptor range and no greater than 300000 ms. If outside the supported range, reject the plan/step with a typed validation error and explain the supported bound; do not silently increase or clamp the user's requested duration.
3. If the Core request omits a timeout, use the descriptor default, provided it is no greater than 300000 ms.
4. Effective deadline must not exceed the requested timeout, descriptor maximum, or 300000 ms. The adapter must not silently extend a deadline.
5. Re-check the descriptor at dispatch time; a stale cached descriptor cannot authorize an out-of-range call.

Core's current Plan schema requires `timeout_ms` and caps it at 300000 ms. A later schema revision may make omission representable if Core wants descriptor-default behavior; until then, the required field is authoritative.

## 3. Result fidelity

NEXUS `result` accepts any JSON value, including object, array, string, number, boolean and null. The adapter must preserve the exact JSON type and value. It must not coerce primitives into objects, stringify values, or drop null.

Map NEXUS status, error, side effects, postcondition, cancellation, timing and evidence references into Core's typed step outcome/evidence model. Unknown or malformed status values are rejected as protocol errors; they are never treated as success. `unknown_outcome` remains unresolved until a separate safe reconciliation/read operation establishes the actual state.

## 4. Dispatch and retry gates

- Resolve the operation from the trusted registry and validate its descriptor and argument schema.
- Run Core preconditions and AEGIS authorization immediately before dispatch.
- DENY, REQUIRE_APPROVAL, malformed/stale/mismatched authorization, policy unavailability or required audit failure means **zero NEXUS executor dispatches**.
- NEXUS `needs_approval` is a provider/broker result, not a replacement for Core's AEGIS preflight. Return to the approval workflow; do not continue execution.
- A mutation with unknown outcome is not blindly retried. Reconcile actual state first. Preserve the same logical idempotency key across outcome reconciliation.
- Cancellation acceptance is not proof of stopped execution. Core marks a step cancelled only after NEXUS confirms the operation stopped and side effects are accounted for.

## 5. Contract conformance cases (test plan)

| Case | Input/condition | Required adapter behavior |
|---|---|---|
| ID preservation | UUID task/step IDs | Pass unchanged; no UUID parsing or rewriting. |
| Request correlation | Two dispatch attempts | Each actual dispatch gets a distinct request_id; task/step/correlation IDs remain stable. |
| Descriptor bounds | minimum > default, default > maximum, non-positive values | Reject descriptor; do not dispatch. |
| Invocation ceiling | timeout > 300000 ms | Reject before dispatch. |
| Descriptor ceiling | timeout > descriptor maximum | Reject before dispatch; no silent clamp/extension. |
| Operation lookup | Unknown or non-canonical operation | Reject before dispatch; never fall back to shell execution. |
| Result fidelity | result is array/string/number/boolean/null | Preserve exact JSON type and value. |
| Authorization stop | DENY or REQUIRE_APPROVAL | Assert executor dispatch count is zero. |
| Unknown mutation | NEXUS returns unknown_outcome | Reconcile before retry; preserve idempotency key. |
| Cancellation race | cancellation accepted but operation completes | Do not report cancelled until actual stopped/side-effect state is confirmed. |

These are required future tests, not tests executed in this completion. The current JSON Schema harness remains authored but not verified as passing.

## 6. Open integration blockers

1. AEGIS/NEXUS must approve the exact authorization_context transport, peer-binding and consume request/response.
2. AEGIS must confirm approval handoff and typed consume failure outcomes.
3. NEXUS must confirm invocation/result/cancellation contract version and durable idempotency/reconciliation behavior.
4. Core implementation language, IPC, persistence and service lifecycle remain dependent on ATLAS-01.

Until those decisions are recorded by the owners, this profile is a Core-side implementation guide only.

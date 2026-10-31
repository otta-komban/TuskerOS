# Security contract integration gaps

**Owner:** NEXUS-07 (system integration)  
**Status:** Tracking note; not an AEGIS contract or schema proposal  
**Source:** Security workstream report supplied on 2026-10-31  
**Scope:** Record cross-workstream blockers and define NEXUS-side acceptance evidence without changing shared contracts.

## Findings reported by Security

The supplied Security report identifies:

1. **High — approval binding coverage:** the approval schema does not fully represent the session/device, registry, resource, and precondition bindings required by the lifecycle contract.
2. **Medium — audit minimum fields:** the audit schema does not require `task_id` and `step_id`, although the normative contract lists them as minimum fields.

These are reported findings from the Security workstream. NEXUS has not independently inspected or changed the authoritative schemas in this increment.

## NEXUS integration impact

| Finding | NEXUS risk | Required owner resolution | NEXUS acceptance evidence |
|---|---|---|---|
| Approval binding omissions | A locally authorized operation could not be proven to belong to the intended session/device, registry version, resource, and precondition set. | AEGIS and TUSKER owners must publish the approved binding fields, provenance rules, and validation semantics; Chief Architect approval is required for shared interface changes. | Negative tests reject missing, mismatched, stale, or caller-authored bindings; a positive test demonstrates bindings derived from trusted broker context. |
| Audit task/step omissions | An authorization or dispatch decision may not be attributable to the exact task and step required by the lifecycle contract. | AEGIS/TUSKER owners must confirm the normative audit schema and durable-write boundary. | Tests prove required task/step identifiers are present in durable audit evidence before any protected provider dispatch. |

## Current NEXUS safeguards and limitations

- The read-only D-Bus adapter remains an isolated provider primitive and is not registered as a public invocation tool.
- Its injected authorization callback is an internal test/composition seam, not an AEGIS wire contract. A boolean callback does not prove fresh-reference resolution, one-time consumption, trusted peer identity, durable audit, or task/step binding.
- The adapter accepts no caller-supplied `authorization_context`, `authorization_ref`, `principal`, or `decision` parameters. This local property does not remediate any open-ended field in a separate invocation schema.
- Missing authorization, exceptions, and any value other than literal `True` fail closed before provider execution.
- No shared schema, invocation schema, AEGIS broker API, or cross-agent interface was changed in response to this report.

## Release gates

Do not register the adapter or expose system operations to invocation callers until all of the following are satisfied:

1. Chief Architect approves the shared authority and lifecycle interface changes.
2. AEGIS publishes an owner-approved broker contract covering trusted IPC peer identity, fresh authorization reference, atomic one-time consume, registry integrity/version, and durable audit sequencing.
3. The approval binding and audit-field gaps above are resolved in their owning schemas.
4. NEXUS adds negative tests for caller-supplied authority fields and missing/mismatched trusted bindings, plus a positive independently authenticated broker-context test.
5. Disposable-environment end-to-end evidence demonstrates authorization denial causes zero provider calls and authorized invocation follows the approved consume/audit sequence.

Until then, these items remain explicit integration blockers rather than assumptions to be filled by NEXUS.

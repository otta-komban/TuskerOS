# Tool Catalogue Contract
**Owner:** NEXUS-07 · **Status:** Draft 1.0 proposal · **Approval:** pending TUSKER-04 and AEGIS-06

## Purpose
A tool descriptor is the discoverable, versioned metadata record for one typed provider operation. It describes what an operation can do and the operational limits the executor must enforce. It is not itself an authorization grant and must never be treated as caller identity.

## Machine-readable form
- Schema: `contracts/tool-descriptor.schema.json`
- Example: `contracts/examples/tool-descriptor.valid.json`
- Tests: `tests/test_contracts.py`

## Required descriptor fields
| Field | Meaning |
|---|---|
| `name`, `version` | Stable dotted operation identifier and semantic version |
| `input_schema_ref`, `output_schema_ref` | Versioned argument/result schema references |
| `risk`, `privilege` | Impact classification and execution context; AEGIS owns policy mapping |
| `side_effects` | Declared externally observable effects |
| `preconditions`, `postconditions` | Conditions checked before execution and evidence checked after |
| `timeout_ms` | Default and allowed execution deadline bounds |
| `idempotency` | Whether repeat execution is safe and the scope of deduplication |
| `cancellation` | Whether cancellation is supported and its guarantee |
| `rollback` | Explicit rollback capability; no rollback is presumed |
| `required_capabilities` | Capability identifiers required to expose/invoke this tool |
| `availability` | Current discoverability state, not authorization |
| `provider` | Owning component and activation model |

## Enforcement and ownership
1. Catalogue metadata is descriptive input to validation and policy; it cannot override AEGIS-06 authorization decisions.
2. A mutating operation MUST complete trusted identity establishment and AEGIS policy preflight before provider execution.
3. The caller's JSON component/instance labels are descriptive only. Trusted IPC peer credentials establish the caller.
4. A timeout or transport loss after a possible side effect yields `unknown_outcome`; the orchestrator must verify current state before retry.
5. Cancellation support does not imply confirmed termination. Return request acceptance separately from operation state.
6. An idempotency declaration must be backed by provider behavior and tests; scope `none` means no deduplication promise.
7. Availability is not permission. A tool may be discoverable but denied to a caller.
8. The descriptor contains no Polkit action ID, principal schema, or policy expression; AEGIS-06 owns those contracts.

## Open review points
- TUSKER-04: confirm descriptor shape and mapping into the orchestration tool catalogue.
- AEGIS-06: confirm risk/privilege semantics and whether an opaque policy reference is appropriate.
- ATLAS-01: review provider activation vocabulary against packaging/service conventions.
- Cross-field validation (for example minimum <= default <= maximum timeout) must be enforced by catalogue loader logic and tests; JSON Schema alone does not express numeric relationships between sibling properties in this draft.

This contract is provisional. Do not freeze API 1.0 or ship activation units until relevant owners approve identifiers and semantics.

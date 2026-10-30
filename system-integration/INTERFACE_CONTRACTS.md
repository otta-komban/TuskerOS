# TuskerOS Interface Contracts
**Owner:** NEXUS-07 · **Status:** Draft v0.1 · **Compatibility:** provisional until cross-agent approval

## 1. Contract principles
- Every externally consumed interface is typed, documented, versioned, and testable.
- Use semantic versioning for published schemas: major = incompatible shape/meaning; minor = backward-compatible additions; patch = clarification/bug fix with no contract change.
- Consumers MUST ignore unknown optional fields, reject unknown major versions, and validate required fields before execution.
- Mutations require explicit side-effect and risk metadata, preconditions, authorization, bounded deadlines, and a verifiable postcondition.
- No arbitrary shell string is an acceptable public tool contract. Use operation identifiers and typed argument objects.
- Errors are machine-readable and stable; human-readable messages are supplementary.

## 2. Common tool invocation (proposal)
```json
{
  "schema_version": "1.0",
  "request_id": "uuid",
  "task_id": "task-123",
  "step_id": "step-2",
  "correlation_id": "corr-123",
  "idempotency_key": "opaque-client-generated-key",
  "caller": {"component": "tusker-core", "instance_id": "opaque"},
  "tool": "system.info",
  "arguments": {},
  "deadline_ms": 5000,
  "cancellation_token": "opaque-optional-token",
  "authorization_context": {}
}
```
The caller component/instance fields are descriptive routing metadata only. They are not proof of identity. Authenticated caller identity must be derived from trusted IPC peer credentials and the AEGIS-06-approved principal/decision context. Caller-supplied JSON identity claims MUST NOT authorize an operation. For every mutating tool, policy preflight is mandatory before invocation; NEXUS rejects a missing, invalid or stale authorization context. The exact principal and decision schema belongs to AEGIS-06. Every invocation carries task_id, step_id and correlation_id; TUSKER-04 remains authoritative for task/plan/step state.

## 3. Common tool result (proposal)
```json
{
  "schema_version": "1.0",
  "request_id": "same-request-id",
  "operation_id": "stable-operation-id",
  "task_id": "task-123",
  "step_id": "step-2",
  "correlation_id": "corr-123",
  "status": "succeeded",
  "result": {},
  "postcondition": {"state": "verified", "details": {}},
  "side_effects": [],
  "cancellation": {"request_state": "not_requested", "operation_state": "completed"},
  "evidence_refs": ["system-snapshot:op-123"],
  "timing": {"duration_ms": 12},
  "error": null
}
```
Allowed statuses: `succeeded`, `rejected`, `needs_approval`, `running`, `cancelled`, `failed`, `unknown_outcome`. Cancellation request state (`not_requested`, `received`, `rejected`, `accepted`) is distinct from operation state (`running`, `stopped`, `completed`, `unknown`); cancellation acceptance is not proof that execution stopped. A cancellation race may still complete a side effect. Results include task/step/correlation identifiers and evidence references. Postcondition state: `verified`, `not_verified`, `not_applicable`, `unknown`.

## 4. Error taxonomy
Stable codes (initial proposal):
- `INVALID_ARGUMENT`: schema/type/range validation failed.
- `UNSUPPORTED_VERSION`: incompatible major version.
- `NOT_FOUND`: requested resource does not exist.
- `PERMISSION_DENIED`: policy or OS permission denied.
- `APPROVAL_REQUIRED`: authorization requires explicit user approval.
- `PRECONDITION_FAILED`: resource state changed or requirement not met.
- `CONFLICT`: idempotency key or state conflict.
- `TIMED_OUT`: deadline expired; mutation outcome may be unknown.
- `CANCELLED`: operation cancellation confirmed.
- `UNAVAILABLE`: provider/service/dependency unavailable.
- `UNSUPPORTED_OPERATION`: capability is not implemented on this host.
- `POSTCONDITION_FAILED`: requested state was not observed.
- `INTERNAL_ERROR`: unexpected failure; include a correlation ID, not sensitive internals.

## 5. Operation metadata (required for every tool)
`name`, `version`, `description`, `input_schema`, `output_schema`, `risk` (`read_only`, `low`, `moderate`, `high`, `destructive`), `privilege` (`user` or `elevated`), `side_effects`, `preconditions`, `postconditions`, `timeout_ms`, `idempotent`, `idempotency_scope`, `cancellable`, `rollback` (`supported`, `best_effort`, `not_supported`), `required_capabilities`, `availability`.

## 6. D-Bus conventions (proposal; names not frozen)
- Use reverse-DNS names under an agreed TuskerOS namespace; do not squat on org.freedesktop names.
- Interface names use PascalCase components; methods use stable operation verbs; properties are read-only unless mutation semantics are explicit; signals represent state/event notifications.
- Keep methods bounded and avoid long-running work on synchronous method calls. Return an operation ID and emit progress/completion signals for long work.
- Document bus type (session/system), well-known name, object path, interface, method signatures, authorization requirements, activation policy, and compatibility policy together.
- Do not expose raw process command lines, secrets, or unrestricted filesystem access through generic D-Bus methods.
- Prefer standard interfaces (systemd, UPower, NetworkManager, BlueZ, portals, KDE APIs) over custom duplicates after compatibility review.

## 7. Event envelope (proposal)
Required fields: `event_version`, `event_id`, `event_type`, `occurred_at` (UTC RFC3339), `producer`, `correlation_id`, `subject_id`, `sequence`, `payload`. Events are notifications, not an authorization channel. Consumers must handle duplicate, delayed, reordered, and missing events; authoritative state is read from the owning service.

## 8. Lifecycle and health
Health states: `starting`, `ready`, `degraded`, `stopping`, `failed`. Include component version, contract major versions, last successful operation time, and dependency status. Health checks must be cheap, bounded, side-effect free, and must not reveal sensitive configuration.

## 9. Cross-agent approval required
- TUSKER-04: tool invocation/result, operation lifecycle, task correlation and cancellation.
- AEGIS-06: authenticated caller, authorization/approval handshake, privilege broker, audit fields and risk mapping.
- ATLAS-01: Fedora/systemd/D-Bus/Polkit integration and packaging/activation conventions.
- NOVA-02: desktop event/status consumption and user-session APIs.
- ORBIT-05: only device capability/telemetry fields consumed for model suitability; no model runtime control ownership.
- PILOT-08: remote principal/device identity propagation and task-origin fields.
- FORGE-09: extension capability discovery and permission projection.

## 10. Machine-readable schema artifacts
Provisional JSON Schema Draft 2020-12 documents and valid example fixtures live under `system-integration/contracts/`:
- `tool-invocation.schema.json`
- `tool-result.schema.json`
- `event-envelope.schema.json`
- `health-status.schema.json`

The test harness is `system-integration/tests/test_contracts.py` and the test-only dependency is `system-integration/requirements-test.txt`. Run from repository root with `python -m pip install -r system-integration/requirements-test.txt` followed by `python -m unittest discover -s system-integration/tests -v`. Fixtures and tests are provisional and do not imply cross-agent approval. Test execution is pending; no passing result is claimed.

## 11. Candidate NEXUS service identifiers
See `system-integration/SERVICE_IDENTIFIERS.md`. Candidate system-bus name `org.tuskeros.SystemTools1`, object path `/org/tuskeros/SystemTools1`, and interface `org.tuskeros.SystemTools1.Manager` are not frozen. The project must confirm control of the reverse-DNS namespace and obtain ATLAS-01/AEGIS-06 review before packaging or implementation. No Polkit action IDs or privileged methods are assigned by NEXUS.

## 12. TUSKER-04 lifecycle review reconciliation
TUSKER-04 reviewed v0.1 and requested task/step/correlation identifiers, trusted transport identity, mandatory authorization preflight for mutations, explicit cancellation semantics, evidence references and idempotency scope. These are incorporated into the provisional schemas. TUSKER-04 remains authoritative for Task/Plan/Step/TaskEvent state; NEXUS owns the tool catalogue and provider operation lifecycle. Every task lifecycle/progress/cancel/verification event must preserve the relevant task_id, step_id, request_id, operation_id and correlation_id in its typed payload. Exact authorization principal/decision fields remain AEGIS-06-owned. See Issue #5 comment 6531017768 and NEXUS acknowledgement 6531070583.

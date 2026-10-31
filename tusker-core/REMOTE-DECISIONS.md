# TUSKER-04 Remote Adapter Decision Record

Owner: TUSKER-04. Branch: 04-tusker-core. Status: draft v0.1, not a frozen API.

DEC-TUS-001 Submission contract: REVISE. Accept adapter-only routing, authenticated server-derived principal, canonical Core lifecycle, request/correlation IDs and idempotency key. Exact bounded context-reference and request/response schemas remain open.

DEC-TUS-002 State and safe projection: REVISE. Accept canonical task states and minimized summaries. Field-level visibility and projection schema remain open; raw prompts, paths, tool output and evidence payloads are not exposed by default.

DEC-TUS-003 Idempotency: REVISE. Scope to authenticated principal plus idempotency key. Same canonical payload returns the original task; different payload conflicts. Uncertain mutations require reconciliation before retry. Retention and durable restart semantics await the persistence decision.

DEC-TUS-004 Cancellation: REVISE. Cancellation is a request, distinct from confirmed stop. Report accepted, stop-confirmed, still-running or unknown-outcome, authoritative state and possible side effects. Terminal cancelled requires confirmed stop. Response schema and race tests remain open.

DEC-TUS-005 Pause/resume: DEFER. Excluded from MVP until safe checkpoint capability and recovery tests exist.

DEC-TUS-006 Events/replay: REVISE. Accept unique event IDs, monotonic per-task sequence, duplicate tolerance and snapshot recovery on gaps/reconnect. Cursor format, retention and replay consistency remain open.

DEC-TUS-007 Trusted context: REVISE. Principal, origin, device/session and correlation context must be injected by the authenticated adapter, never request JSON or model output. Exact principal shape and AEGIS audit mapping remain open.

Core invariants: PILOT is an adapter, not a second planner/executor; all registered operations including reads pass AEGIS policy; DENY and REQUIRE_APPROVAL produce zero executor calls; remote approval remains disabled for MVP; uncertain mutation outcomes are reconciled, never blindly retried; event consumers recover from authoritative snapshots; public projections omit hidden reasoning, credentials, private prompts and raw tool output.

Implementation gate: this review does not authorize remote runtime implementation. AEGIS identity, authorization and audit decisions remain independent mandatory gates. Existing Core schemas do not yet provide a finalized remote submission/response schema, safe projection schema, cancellation response schema, durable idempotency store or event cursor/replay API. Validator tests are authored but no test or CI pass is claimed.

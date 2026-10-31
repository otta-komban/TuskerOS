# Provider Adapter Lifecycle and Conformance Test Plan

Owner: ORBIT-05  
Status: Proposal; provider contract v0.1.0 remains unapproved  
Scope: provider-neutral InferenceProvider adapter behavior; ModelStore conformance is specified separately

## 1. Purpose

Every adapter must satisfy the same observable lifecycle, streaming, cancellation, health and failure semantics. Tests use a deterministic fake provider first, then run the same applicable suite against each pinned real provider version. A provider capability marked `unsupported` or `unknown` is reported honestly; a test is skipped only when the capability is not advertised, and the skip is recorded.

## 2. Adapter lifecycle state machine

States: `discovered`, `starting`, `ready`, `degraded`, `stopping`, `stopped`, `failed`.

Allowed transitions:

| From | To | Trigger / invariant |
|---|---|---|
| discovered | starting | Explicit start request; no implicit boot/login start |
| starting | ready | Health probe and required initialization succeed |
| starting | failed | Startup deadline, executable failure or invalid configuration |
| ready | degraded | Non-fatal provider failure or capability loss; health details identify impact |
| ready | stopping | Explicit stop or controlled shutdown |
| degraded | ready | Health probe confirms recovery |
| degraded | stopping | Explicit stop or shutdown |
| stopping | stopped | Owned work drained/cancelled and owned process exited |
| stopping | failed | Shutdown deadline or owned process cannot be stopped |
| stopped | starting | Explicit restart |
| failed | starting | Explicit retry after failure state is observable |

No transition may silently restart a shared daemon, change effective network binding, or broaden privileges. Repeated start/stop calls must be idempotent or return a typed conflict. A provider already managed externally is not terminated by this adapter.

## 3. Request lifecycle and event invariants

For each request ID:

1. Validate request shape, provider/model readiness, capability and configured bounds before dispatch.
2. Emit at most one `started` event, before any delta or usage event.
3. Event sequence numbers are strictly increasing and timestamps are nondecreasing within the request stream.
4. Deltas preserve provider order. Partial tool-call JSON remains explicitly untrusted and incomplete until the provider marks it final; it is never executed here.
5. Usage/resource events are optional and may be unknown. Do not synthesize token counts or resource measurements.
6. Emit exactly one terminal event (`completed`, `cancelled` or `failed`) after start. A validation rejection before dispatch returns a typed error without pretending that generation started.
7. No event may follow a terminal event. A disconnected stream before terminal completion is surfaced as `provider_disconnected`.
8. Request IDs are unique among in-flight requests. Duplicate IDs are rejected or isolated by a documented idempotency policy; they must never merge output streams.

## 4. Cancellation, deadlines and concurrency

- Cancellation is request-scoped. Cancelling request A must not cancel request B or terminate a shared provider daemon.
- Cancellation before dispatch prevents provider work. Cancellation during generation stops the request within a documented adapter grace period where the provider supports it.
- If a provider cannot cancel one request safely, advertise cancellation as unsupported; do not emulate it by killing a shared process.
- Caller cancellation, provider deadline expiry and provider crash map to distinct outcomes.
- Concurrency limits are enforced before dispatch. A rejected request returns a stable capacity/resource error; it is not silently queued unless queueing is an explicit configured policy.
- On provider crash, all affected in-flight requests terminate with a safe structured error; no request is reported completed without a terminal provider result.
- Automatic retries are disabled for generation by default. Any future retry policy must define idempotency and duplicate-output behavior.

## 5. Health and capability semantics

- `ready` means the adapter can accept a request for at least one advertised usable model/capability, not that every model is loaded.
- Health probes have bounded timeouts and must not trigger expensive model loads.
- Capability values are `supported`, `unsupported` or `unknown`; unknown never implies support.
- Provider-native model inventory is distinct from Tusker's managed artifact catalog.
- A health response reports adapter state, provider version when known, last successful probe, safe diagnostic code and capability map. It excludes prompts, generated text, credentials and environment secrets.

## 6. Deterministic conformance suite

| ID | Scenario | Expected assertion |
|---|---|---|
| PA-001 | Discover adapter with executable absent | `unavailable`; desktop/runtime remains usable |
| PA-002 | Start healthy fake provider | `discovered -> starting -> ready`; bounded completion |
| PA-003 | Startup timeout / invalid config | `failed`; actionable safe error; no false ready state |
| PA-004 | Duplicate start and stop | Idempotent result or documented typed conflict; no duplicate process |
| PA-005 | Provider health degradation/recovery | `ready -> degraded -> ready`; capabilities refreshed |
| PA-006 | Valid single-turn inference | Ordered start, deltas and one completed terminal event |
| PA-007 | Multi-delta stream | Monotonic sequence and preserved text order |
| PA-008 | Empty output / usage unavailable | Valid terminal result; unknown usage remains unknown |
| PA-009 | Provider disconnect mid-stream | One failed terminal outcome; never completed |
| PA-010 | Request cancellation before dispatch | No provider generation; cancellation outcome is unambiguous |
| PA-011 | Cancel one of two concurrent requests | Target stops; unrelated request continues |
| PA-012 | Cancellation unsupported by provider | Capability not advertised as supported; no process kill workaround |
| PA-013 | Deadline expiry | `deadline_exceeded`, distinct from caller cancellation |
| PA-014 | Concurrency limit reached | Deterministic rejection/queue policy; no unbounded work |
| PA-015 | Context/output limit exceeded | Typed validation/resource error before unsafe dispatch |
| PA-016 | Duplicate in-flight request ID | Rejected or isolated per documented policy |
| PA-017 | Tool proposal partial JSON | Preserved as untrusted data; no execution or authorization |
| PA-018 | Provider crash with multiple requests | All affected requests terminate once; adapter state degrades/fails |
| PA-019 | Health probe timeout | Bounded degraded/unknown health; no hang |
| PA-020 | Sensitive prompt in provider error | Prompt, output, credentials and secrets absent from default logs |
| PA-021 | Stop externally managed daemon | Adapter does not terminate daemon it does not own |
| PA-022 | Local listener effective bind check | Non-loopback bind rejected unless separately approved and authenticated |
| PA-023 | Network disconnected after model readiness | Local inference continues when provider and artifact support it |
| PA-024 | Unsupported modality request | `unsupported_capability`; no implicit cloud fallback |

## 7. Provider-specific verification matrix

Run the shared suite against pinned Ollama and llama.cpp versions. Capture exact versions, configuration, request/response traces with sensitive content redacted, and observed capability results. The following behaviors are explicitly not assumed until tested:

- Ollama: request-scoped cancellation semantics, keep-alive/unload behavior, model digest visibility, effective listener binding, and concurrent request isolation.
- llama.cpp server: request-scoped cancellation, slot isolation, server shutdown ownership, model inventory semantics, and bind/auth configuration.
- Both: exact structured-output/tool-call behavior, context limit errors, disconnect behavior, and whether offline operation remains successful after all artifacts are installed.

## 8. Execution and evidence format

Each run records test ID, adapter name/version, provider version/commit, OS/kernel, model revision/digest (or fake fixture), configuration, timestamp, result (`pass | fail | skip`), observed behavior, log reference and issue link. A skip requires a recorded unsupported/unknown capability. Never mark a test passed from source inspection alone.

The fake-provider suite is a prerequisite for real-provider testing. Real-provider failures are retained as evidence and do not get converted to skips unless the capability is explicitly unsupported by design.

## 9. Exit criteria

- All applicable fake-provider tests pass in CI.
- Real provider suite has no unexplained failures for advertised capabilities.
- Unsupported and unknown behaviors are surfaced to TUSKER-04 without false capability claims.
- AEGIS-06 approves process ownership, cancellation escalation, logging and bind checks.
- TUSKER-04 approves request/event/error semantics before facade freeze.


## 9. Machine-readable event envelope

The JSON Schema at `tusker-ai/schemas/inference-event.schema.json` defines the common request ID, monotonic sequence field, RFC 3339 timestamp and typed payload for each event kind. The accompanying synthetic trace at `tusker-ai/tests/fixtures/inference-events-valid.json` demonstrates a successful started → text_delta → usage → completed stream. It is a contract fixture, not a provider observation.

The schema validates individual event shape; trace-level rules (single start, exactly one terminal event, terminal-last ordering, stable request ID and increasing sequence) are separate assertions in `tusker-ai/tests/test_inference_event_schema.py`. Adapters must still enforce stream ordering at runtime. A valid JSON event is untrusted model/provider data and is never permission to execute a tool. Run with the isolated test requirements in `tusker-ai/requirements-test.txt`; execution status is recorded only after an actual test run.


## 10. Automated contract validation

The GitHub Actions workflow `.github/workflows/tusker-ai-contracts.yml` installs only `tusker-ai/requirements-test.txt` and runs the schema/fixture tests on relevant pushes and pull requests targeting `main`. This job validates JSON Schema structure, synthetic manifest/event fixtures, negative cases and the event trace invariants. It does not test a live inference provider, hardware compatibility, model quality, or license approval. A workflow run must complete successfully before this gate can be marked passed.

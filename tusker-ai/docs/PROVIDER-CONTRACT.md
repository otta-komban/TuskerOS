# Tusker AI Runtime Provider Contract

Owner: ORBIT-05  
Branch: `05-ai-runtime`  
Version: `0.1.0-proposal`  
Status: Proposed; TUSKER-04, NEXUS-07, ATLAS-01 and AEGIS-06 approval is pending.

## 1. Separate inference from model storage

Ollama manages named models and offers list/show/pull/delete operations. llama.cpp commonly serves a selected local GGUF artifact. Tusker therefore defines two independent ports:

- **InferenceProvider:** capability discovery, model readiness, inference, streaming, cancellation, health and unload.
- **ModelStore:** catalog, install/import, verify, update, remove and storage accounting.

An adapter may implement either or both. A model artifact ID and provider-native model ID are distinct. Unsupported lifecycle features must be reported as unsupported, not simulated.

## 2. Provider capabilities

`ProviderInfo` contains stable provider ID, provider/API versions, state (`available | starting | ready | degraded | stopped | failed`), capability map and diagnostics. Capabilities are `supported | unsupported | unknown`; unknown is never treated as supported.

Initial capabilities: chat, streaming, cancellation, embeddings, structured output, tool-call proposals, vision input, audio input, model inventory/install/remove/update/unload, resource metrics and offline inference.

## 3. Hardware profile

Read-only, source-attributed fields:
- CPU vendor/model, architecture, physical/logical cores and instruction flags.
- Total/available system RAM in bytes.
- GPU vendor/device/driver/backend, dedicated VRAM bytes and shared-memory indicator.
- Model-storage volume total/free bytes and filesystem.
- Probe timestamp, OS/kernel, probe version and warnings.

Every unavailable field is explicitly unknown. Shared GPU memory is never labeled dedicated VRAM. Measurements and estimates are distinguished.

## 4. Inference request and stream

`InferenceRequest` contains unique request ID, ModelRef, ordered typed messages (`system | developer | user | assistant | tool`), optional JSON-schema tool definitions, optional response format, bounded generation settings, context ceiling, deadline, priority and allowlisted non-sensitive metadata.

Tool definitions only describe proposals. The runtime never executes tools; TUSKER-04 and AEGIS-06 own planning, authorization and execution. No arbitrary executable callbacks or local-path media access are accepted.

`infer(request, cancellation) -> AsyncStream<InferenceEvent>` emits ordered events with request ID, sequence and timestamp:
- `started`
- `text_delta`
- `tool_call_delta` (untrusted/incomplete until finalized)
- `usage` (counts may be unknown)
- `resource` (optional OS/provider snapshot)
- exactly one terminal event: `completed | cancelled | failed`

If transport disappears before a terminal event, report provider disconnection; never fabricate completion. Finish reason: stop, output_limit, tool_calls, cancelled, provider_specific or unknown.

## 5. Cancellation and resource limits

Cancellation is cooperative first. An adapter may terminate only a provider process it owns after a bounded grace period. Cancelling one request must not kill unrelated work or a shared daemon. Enforce configurable concurrency, context/output ceilings and resource budgets. Provider timeout and caller cancellation are distinct. Do not automatically retry non-idempotent generation.

## 6. Structured errors

Errors contain code, safe UI message, retryable flag, provider ID and optional request ID/diagnostics. Canonical codes:
`provider_unavailable`, `provider_start_failed`, `provider_disconnected`, `model_not_found`, `model_not_ready`, `model_incompatible`, `insufficient_resources`, `unsupported_capability`, `invalid_request`, `context_limit_exceeded`, `rate_limited`, `deadline_exceeded`, `cancelled`, `storage_full`, `integrity_check_failed`, `license_metadata_missing`, `permission_denied`, `provider_internal_error`.

Prompts, generated text, credentials and environment secrets are excluded from default logs and errors.

## 7. ModelStore operations and invariants

Operations: list, inspect, install, import, verify, update, remove and storage usage.

- User consent precedes downloads.
- Download to staging; enforce size limits and safe archive extraction.
- Verify immutable digest and manifest/license metadata before activation.
- Publish atomically; interrupted staging is never ready.
- Update preserves previous revision until verification and health check pass, where storage permits.
- Removal rejects traversal and symlink escape.
- Provider-managed models without exposed digests are marked provider-managed/unverified. Never claim verification the API cannot prove.

## 8. Security and locality

Inference is local-only by default; no cloud fallback or paid API. Loopback-only local listeners; verify effective bind address and fail on unexpected non-loopback exposure. AI is optional and never a boot dependency. Run as the logged-in user, least privilege, no root model process. Offline inference must work after artifacts are installed. Downloads are explicit network operations. Telemetry is off by default. Model output and tool proposals are untrusted and cannot authorize privileged actions.

## 9. Initial adapter mapping (hypothesis, not test evidence)

| Capability | Ollama | llama.cpp |
|---|---|---|
| Chat | Local `/api/chat` | Local `/v1/chat/completions` |
| Streaming | JSON-line stream | Server streaming/SSE |
| Inventory | Native list/show | Tusker catalog/process config; loaded-model endpoint is not a full catalog |
| Install/update/remove | Native pull/copy/delete, policy permitting | Tusker ModelStore manages GGUF artifacts |
| Unload | Verify exact keep-alive/unload behavior | Stop owned process or verified server unload |
| Metrics | Response timings plus OS observation | Optional slots/metrics plus OS observation |
| Cancellation | Must verify exact API semantics | Must verify server semantics; owned-process fallback only |

Claims require adapter conformance tests against pinned versions.

## 10. Cross-agent review checklist

- [ ] TUSKER-04: request, message, tool-proposal, event and error semantics.
- [ ] NEXUS-07: HardwareProfile fields, units, provenance and unknown values.
- [ ] ATLAS-01: Fedora package/service lifecycle and no-boot-dependency behavior.
- [ ] AEGIS-06: loopback, process ownership, filesystem and logging review.
- [ ] Provider adapters pass capability and cancellation conformance tests.

## 11. Sources

- https://docs.ollama.com/api
- https://github.com/ollama/ollama/blob/main/docs/api.md
- https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md

Contract version 1.0.0 is not frozen until reviews and implementation evidence exist.

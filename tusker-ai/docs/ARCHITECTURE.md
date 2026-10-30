# ORBIT-05 — Local AI Runtime Architecture (P0/P1 baseline)

**Status:** Initial architecture proposal; provider and model selections remain provisional pending current-source review and repeatable benchmarks.
**Owner:** ORBIT-05
**Owned root:** `tusker-ai/`
**Branch:** `05-ai-runtime`

## 1. Mission and boundaries

Tusker AI Runtime supplies optional, local inference and model lifecycle management. It MUST NOT be a boot dependency, a prerequisite for KDE, or a privileged system-control component. The OS and desktop remain useful when the runtime is absent, stopped, out of memory, or broken.

Non-goals for the first vertical slice: training/fine-tuning, automatic model downloads without user consent, mandatory cloud inference, arbitrary shell access, exposing a model server to the LAN, or promising a particular tokens/second figure before measurement.

## 2. Proposed component boundaries

- **Runtime API / facade:** stable, versioned interface consumed by TUSKER-04. Does not expose provider-specific HTTP endpoints or SDK types.
- **Provider registry:** discovers installed adapters and their capabilities. Initial candidates: Ollama and llama.cpp (direct process/library/server integration to be selected after P0 evaluation).
- **Provider adapter:** translates the common inference and lifecycle contract to one provider.
- **Model catalog:** locally cached, signed-or-checksummed metadata with provenance, license, version/revision, size, quantization, context limit, capabilities and hardware requirements.
- **Model manager:** explicit install/import, verify, list, activate, update, remove, storage accounting and rollback-safe state changes.
- **Hardware probe:** read-only discovery of CPU features, logical/physical cores, RAM, GPU vendor/device/driver, VRAM where available, and free storage. Missing fields are represented as unknown, never guessed.
- **Scheduler / resource guard:** bounded concurrency, context and token limits, load/unload policy, cancellation, memory-pressure response and CPU/GPU selection.
- **Diagnostics & benchmark harness:** records machine profile, runtime/provider/model versions, quantization, context, warm/cold state, latency, throughput, peak memory and errors.

No model process receives elevated OS privileges. Provider services bind to loopback by default; network exposure is out of scope unless separately approved and authenticated.

## 3. Provider-neutral contract (proposal)

The stable facade should expose these operations, with typed schemas and explicit errors:

- `list_providers() -> ProviderInfo[]`
- `list_models(provider_id?) -> ModelInfo[]`
- `inspect_hardware() -> HardwareProfile`
- `recommend_models(profile, task, constraints) -> Recommendation[]`
- `install_model(manifest_id, destination, progress, cancellation) -> InstallResult`
- `import_model(source, manifest_or_metadata) -> ImportResult`
- `verify_model(model_id) -> VerificationResult`
- `activate_model(model_id) / deactivate_model(model_id)`
- `update_model(model_id, target_revision) -> UpdateResult`
- `remove_model(model_id) -> RemovalResult`
- `infer(request, cancellation) -> AsyncStream<InferenceEvent>`
- `health() -> RuntimeHealth`

Inference request fields: request ID, model ID, messages/input, task hint, optional bounded context/output limits, sampling settings, deadline and cancellation token. Events: started, token/delta, usage/resource snapshot, completed, cancelled or structured error. The contract must distinguish provider unavailable, model missing, insufficient resources, unsupported capability, invalid request, timeout, cancellation and provider crash.

The adapter owns provider translation; TUSKER-04 owns planning, tool selection and task policy. Runtime output is untrusted model content, never authorization.

## 4. Model manifest (minimum fields)

- Stable model ID, display name, family, publisher and revision.
- Source URI plus provenance record; immutable artifact digest (SHA-256 minimum) and byte size.
- License identifier and license text/URL; redistribution/use restrictions and review status.
- Format, quantization, architecture, parameter count (if known), tokenizer/template identity.
- Context limit, recommended context, supported task capabilities (chat/reasoning/code/vision/audio), modalities and tool-call compatibility.
- Minimum/recommended RAM, GPU/VRAM and disk requirements; supported backends and architecture/driver notes.
- Runtime compatibility, release date, deprecation/security status and manifest schema version.

A model is not installable from a catalog entry lacking provenance, license metadata and a verifiable digest. User-imported models may have incomplete metadata but must be visibly marked unverified and cannot be recommended as curated.

## 5. Hardware tiers — conservative starting hypotheses

These are planning guardrails, not performance guarantees or final model assignments. Actual fit depends on OS baseline memory, model architecture, quantization, context/KV cache, runtime overhead, GPU sharing and concurrent applications.

| System RAM | Initial policy | Model guidance |
|---|---|---|
| 4 GB | Keep runtime optional and unloaded by default; protect desktop responsiveness. | No useful general-purpose model promised. Evaluate only tiny, heavily quantized models as opt-in experiments; graceful no-model mode is valid. |
| 8 GB | Small-model tier; conservative context and single-request concurrency. | Benchmark compact 1–3B-class candidates at low-bit quantization; warn that quality and speed may be limited. |
| 16 GB+ | Main local-inference evaluation tier. | Benchmark 3–8B-class candidates at practical quantization; larger models only when measured RAM/VRAM headroom supports them. |
| Dedicated GPU | Separate capability dimension, not a RAM-tier substitute. | Select backend only after vendor/driver/VRAM compatibility and fallback tests. Shared-memory GPUs are not treated as dedicated VRAM. |

Recommendations must be based on available memory after reserving an OS safety margin, measured model footprint, target context/KV cache, runtime overhead and current load. If evidence is absent, say “not benchmarked” rather than infer throughput.

## 6. Offline, privacy and lifecycle rules

- After runtime and model artifacts are installed, inference must function with network disconnected.
- Default inference path makes no cloud API calls. No paid account or API key is required.
- Model downloads are user-initiated; verify digest before activation and install atomically to avoid partial models becoming active.
- Store models in a user-owned data location with restrictive permissions; do not store credentials in model directories.
- Update by staging and verifying a new revision before switching; preserve prior revision until health check succeeds when storage permits.
- Removal reports reclaimed storage and refuses unsafe path traversal/symlink escapes.
- Network access is limited to catalog/download/update operations and documented provider requirements; telemetry disabled by default.
- Provider process crash, model OOM or missing runtime must not affect OS boot or desktop session.

## 7. Security and reliability constraints

- Run as the logged-in user, least privilege, with bounded CPU/RAM/disk and request limits.
- Loopback-only listener by default; firewall/network exposure is not part of the first release.
- Validate model IDs, paths, manifest schema, digests, archive members and symlinks.
- Do not execute model-supplied code or trust model cards as executable instructions.
- Cancellation and timeouts must propagate; kill/reap only the owned provider process.
- Logs contain metadata and error codes, not prompts/model outputs by default; redact secrets.
- Model text cannot approve privileged operations. AEGIS-06 and TUSKER-04 enforce deterministic authorization.

## 8. P0 research and benchmark decision gates

Compare Ollama and llama.cpp against: Fedora packaging/support, maintenance cadence, license and transitive dependencies, CPU backends, AMD/NVIDIA/Intel acceleration, model formats, service/process model, memory/context behavior, streaming/cancellation, offline behavior, observability, and integration complexity.

Evaluate model families using license/provenance, task quality, tool-call reliability, multilingual capability, quantization availability, memory footprint, context behavior, and reproducible benchmarks. Popularity is not a selection criterion.

Benchmark protocol must pin machine profile, OS/kernel/driver, runtime commit/version, model revision/digest, quantization, context, prompt/output lengths, warm/cold state and concurrency. Report load time, time-to-first-token, generation tokens/s, peak RSS/VRAM, CPU/GPU utilization, energy/thermal/battery observations when measurable, and failure rate. Separate synthetic VM profiles from physical laptop results.

No default provider or model is selected until current-source review and at least one repeatable benchmark run exists.

## 9. Cross-agent contracts

- **TUSKER-04:** agree versioned inference request/event/error schema, model capability discovery, routing hints, cancellation, context limits and runtime health. TUSKER-04 remains provider-agnostic.
- **NEXUS-07:** hardware facts are obtained through an approved read-only interface or a documented runtime-local probe; do not duplicate privileged system tooling. Agree stable hardware profile fields and unknown-value semantics.
- **ATLAS-01:** agree optional package/service boundaries, Fedora packaging approach, user-session lifecycle and no-boot-block behavior.
- **AEGIS-06:** review process isolation, filesystem permissions, local endpoint exposure and threat model.
- **NOVA-02 / PIXEL-03 / FORGE-09:** model management UI and optional install workflow consume the stable facade; they do not call provider-specific endpoints.

## 10. Phase 1 exit criteria

- [ ] Current runtime research and source links recorded.
- [ ] Candidate model families and license review recorded; no unsupported license claims.
- [ ] Hardware tiers and no-model fallback reviewed.
- [ ] Provider-neutral interface and manifest schema reviewed with TUSKER-04.
- [ ] Hardware profile contract reviewed with NEXUS-07/ATLAS-01.
- [ ] Threat and offline requirements reviewed.
- [ ] Benchmark plan executable and first results recorded where hardware is available.
- [ ] Architecture decision record updated with accepted decisions and unresolved questions.

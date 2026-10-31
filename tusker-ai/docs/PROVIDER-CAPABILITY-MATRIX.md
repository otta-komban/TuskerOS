# ORBIT-05 Provider Capability Matrix

**Status:** implementation planning baseline; not a provider conformance result  
**Contract source:** prior ORBIT-05 proposal, provider contract v0.1.0-proposal  
**Target branch baseline:** `main` at `8bf66079f9e021244eda432fa8455e83b59e2165`  
**Decision:** start with a local Ollama adapter as the first provider candidate; keep llama.cpp as a second adapter candidate. This is an implementation-order decision, not a claim that Ollama is installed, approved, or conformant.

## Capability semantics

- **Supported (verified):** observed against a pinned live provider version by an executable conformance test.
- **Unsupported (verified):** observed or explicitly documented as unavailable for the pinned version/configuration.
- **Unknown:** not yet verified. Unknown MUST NOT be treated as supported.
- **Tusker-managed:** implemented by Tusker's model store rather than delegated to a provider.

No provider capability is currently marked verified in this matrix. The earlier adapter mapping was explicitly a hypothesis and did not include live-provider evidence.

## Capability matrix

| Capability | Common contract meaning | Ollama candidate | llama.cpp server candidate | Required evidence / adapter rule |
|---|---|---|---|---|
| Chat completion | Typed messages mapped to provider chat API | Unknown | Unknown | Live single-turn and multi-turn request/response |
| Streaming | Ordered text deltas until one terminal event | Unknown | Unknown | Parse stream framing; enforce event ordering and terminal invariants |
| Request-scoped cancellation | Cancel one request without affecting others | Unknown | Unknown | Concurrent A/B test; cancel A and prove B completes |
| Deadline / timeout | Bounded request and health operations | Tusker-enforced | Tusker-enforced | Deadline test against a deliberately slow live request |
| Model inventory | Provider-native installed model listing | Candidate native list/show | Server-loaded model visibility is not a complete artifact catalog | Compare provider inventory with Tusker artifact inventory; never conflate them |
| Model install / pull | Provider-managed model acquisition | Candidate native pull | Tusker-managed artifact download | Consent, staging, size bound, digest verification, cancellation |
| Model update | New immutable revision without losing prior active revision | Unknown; native pull semantics require verification | Tusker-managed immutable revision | Failed update leaves prior active revision usable |
| Model removal | Remove selected model safely | Candidate native delete | Tusker-managed artifact removal | Exact target binding, containment, symlink and active-model checks |
| Unload | Release loaded model resources | Unknown | Unknown | Measure memory before/after; verify exact unload semantics |
| Embeddings | Embedding generation | Unknown | Unknown | Live request, dimensions, model identity and error mapping |
| Structured output | Constrained JSON/schema response | Unknown | Unknown | Valid and invalid schema-constrained prompts against pinned version |
| Tool-call proposals | Structured, untrusted tool proposal output | Unknown | Unknown | Capture partial/final tool calls; runtime never executes them |
| Vision input | Image-bearing inference request | Unknown | Unknown | Real fixture image, supported model, modality mismatch negative test |
| Audio input | Audio-bearing inference request | Unknown | Unknown | Live audio fixture and capability mismatch negative test |
| Resource metrics | Provider/OS resource observations | Unknown | Unknown | Label source and units; never synthesize unavailable measurements |
| Health | Bounded readiness probe without model load | Unknown | Unknown | Healthy, unavailable, timeout and degraded cases |
| Offline inference | Inference after artifacts are present and network is disconnected | Unknown | Unknown | Disable network after install; successful local request |
| Effective listener binding | Local endpoint is loopback-only | Unknown | Unknown | Inspect effective socket bind; fail closed on non-loopback exposure |

## Cross-contract audit

### Provider contract

The existing proposal separates `InferenceProvider` from `ModelStore`, distinguishes provider-native IDs from Tusker artifact IDs, and requires capability values `supported | unsupported | unknown`. It also requires request-scoped cancellation, caller deadlines, bounded concurrency, safe structured errors, no implicit cloud fallback, and no execution of model-proposed tools.

Implementation must preserve those boundaries. A provider adapter may implement inference, model lifecycle, or both; it must not claim a lifecycle operation it cannot prove.

### Model manifest

The earlier `model-manifest.schema.json` proposal requires immutable revision, source, per-file size/SHA-256, model architecture/context/modalities, license review, provenance, and catalog review state. It does **not** currently express task capabilities (chat, reasoning, code, embeddings, tool-call compatibility), per-provider compatibility, or provider capability evidence. Its `modalities` field is not a substitute for task capability.

This is a schema gap, not permission to silently extend a shared schema. ORBIT will keep runtime-discovered provider capabilities separate from manifest-declared artifact metadata until the Chief Architect approves any schema evolution.

### Inference event envelope

The prior event schema covers `started`, `text_delta`, `tool_call_delta`, `usage`, `resource`, and terminal `completed | cancelled | failed` events. Stream-level rules (one start, one terminal, stable request ID, increasing sequence, terminal last) require runtime assertions beyond per-event JSON Schema validation.

The new implementation must also keep prompts, generated text, credentials, environment secrets, and raw provider error bodies out of default traces.

### Model-store contract

The proposed transaction contract requires explicit user consent, bounded staging, safe archive handling, exact file-set/size/digest verification, atomic active-revision replacement, rollback, request cancellation, cleanup containment, and deterministic startup reconciliation. The current proposal leaves managed-root, filesystem durability and journal format open. Do not implement a cross-agent contract change or claim crash safety until those decisions are reviewed.

## Initial implementation order

1. Implement provider-neutral Python protocols and typed errors without changing the proposed wire schemas.
2. Implement Ollama chat/stream adapter behind a loopback-only endpoint configuration and explicit health check.
3. Implement request timeout and cancellation only where live semantics can be proved; otherwise report unsupported and use safe bounded adapter behavior without killing a shared daemon.
4. Keep artifact acquisition in a separate Tusker ModelStore. Do not treat provider-native pull as digest-verified installation unless exact artifact bytes and digest are available.
5. Run the same conformance suite against the fake adapter and a pinned live Ollama service. Fake tests are development evidence only.
6. Add llama.cpp only after the first provider path and benchmark protocol are executable.

## Evidence status

| Evidence | Status |
|---|---|
| Provider-neutral contract review | Reviewed as an unapproved proposal |
| Model manifest schema review | Reviewed as an unapproved proposal |
| Capability mapping | Defined; all provider-specific cells remain unknown |
| Fake-provider conformance | Not yet implemented |
| Live Ollama conformance | Not run |
| Model download / digest verification | Not implemented |
| Atomic activation / recovery | Not implemented |
| Actual inference artifact | Not available |
| Benchmark measurements | None; protocol must record host/software metadata |

This matrix is deliberately conservative. A row changes from Unknown only when a reproducible test records the provider version, runtime version, OS/kernel, configuration, exact test, result, and redacted evidence reference.

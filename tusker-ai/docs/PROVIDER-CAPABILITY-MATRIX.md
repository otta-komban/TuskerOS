# ORBIT-05 Provider Capability Matrix

**Status:** implementation planning baseline; not a provider conformance result  
**Contract source:** provider contract v0.1.0-proposal  
**Target branch baseline:** `main` at `8bf66079f9e021244eda432fa8455e83b59e2165`  
**Decision:** Ollama is the first adapter implementation candidate; llama.cpp remains a later candidate. This is an implementation-order decision, not a claim that Ollama is installed, approved, or conformant.

## Capability semantics

- **Supported (verified):** observed against a pinned live provider version by an executable conformance test.
- **Unsupported (verified):** observed or explicitly documented as unavailable for the pinned version/configuration.
- **Unknown:** not yet verified. Unknown MUST NOT be treated as supported.
- **Tusker-managed:** implemented by Tusker's model store rather than delegated to a provider.

No provider capability is currently marked verified. The earlier adapter mapping was explicitly a hypothesis. The initial Ollama adapter deliberately reports all provider capabilities as unknown until a pinned live version passes conformance.

## Capability matrix

| Capability | Common contract meaning | Ollama candidate | llama.cpp server candidate | Required evidence / adapter rule |
|---|---|---|---|---|
| Chat completion | Typed messages mapped to provider chat API | Unknown | Unknown | Live single-turn and multi-turn request/response |
| Streaming | Ordered text deltas until one terminal event | Unknown | Unknown | Parse stream framing; enforce event ordering and terminal invariants |
| Request-scoped cancellation | Cancel one request without affecting others | Unknown | Unknown | Concurrent A/B test; cancel A and prove B completes |
| Deadline / timeout | Bounded request and health operations | Tusker-enforced admission/deadline guard; live read behavior unknown | Unknown | Deadline test against a deliberately slow live request |
| Model inventory | Provider-native installed model listing | Unknown | Server-loaded model visibility is not a complete artifact catalog | Compare provider inventory with Tusker artifact inventory; never conflate them |
| Model install / pull | Provider-managed model acquisition | Unknown | Tusker-managed artifact download | Consent, staging, size bound, digest verification, cancellation |
| Model update | New immutable revision without losing prior active revision | Unknown | Tusker-managed immutable revision | Failed update leaves prior active revision usable |
| Model removal | Remove selected model safely | Unknown | Tusker-managed artifact removal | Exact target binding, containment, symlink and active-model checks |
| Unload | Release loaded model resources | Unknown | Unknown | Measure memory before/after; verify exact unload semantics |
| Embeddings | Embedding generation | Unknown | Unknown | Live request, dimensions, model identity and error mapping |
| Structured output | Constrained JSON/schema response | Unknown | Unknown | Valid and invalid schema-constrained prompts against pinned version |
| Tool-call proposals | Structured, untrusted tool proposal output | Unknown | Unknown | Capture partial/final tool calls; runtime never executes them |
| Vision input | Image-bearing inference request | Unknown | Unknown | Real fixture image, supported model, modality mismatch negative test |
| Audio input | Audio-bearing inference request | Unknown | Unknown | Live audio fixture and capability mismatch negative test |
| Resource metrics | Provider/OS resource observations | Unknown | Unknown | Label source and units; never synthesize unavailable measurements |
| Health | Bounded readiness probe without model load | Unknown pending live version test | Unknown | Healthy, unavailable, timeout and degraded cases |
| Offline inference | Inference after artifacts are present and network is disconnected | Unknown | Unknown | Disable network after install; successful local request |
| Effective listener binding | Local endpoint is loopback-only | Configured endpoint is constrained to loopback; effective service bind not independently verified | Unknown | Inspect effective socket bind; fail closed on non-loopback exposure |

## Cross-contract audit

### Provider contract

The contract proposal separates `InferenceProvider` from `ModelStore`, distinguishes provider-native IDs from Tusker artifact IDs, and requires capability values `supported | unsupported | unknown`. It also requires request-scoped cancellation, caller deadlines, bounded concurrency, safe structured errors, no implicit cloud fallback, and no execution of model-proposed tools.

The implementation preserves the separation and never kills the shared Ollama daemon. Cancellation semantics against a real Ollama release remain unknown. Adapter HTTP protocol behavior has only been exercised against a local HTTP fixture.

### Model manifest

The existing schema requires immutable revision, source, per-file size/SHA-256, model architecture/context/modalities, license review, provenance, and catalog review state. It does **not** express task capabilities (chat, reasoning, code, embeddings, tool-call compatibility), per-provider compatibility, or provider capability evidence. Its `modalities` field is not a substitute for task capability.

The schema already restricts file paths to canonical relative POSIX paths. The initial ModelStore is intentionally narrower: one HTTPS file with a basename only. It requires an approved weights-license review, exact source/provenance binding, declared size, and SHA-256. This implementation limitation does not justify silently widening or weakening the shared schema.

This is a schema gap, not permission to silently extend a shared schema. Runtime-discovered provider capabilities remain separate from manifest-declared artifact metadata until the Chief Architect approves any schema evolution.

### Inference event envelope

The event schema covers `started`, `text_delta`, `tool_call_delta`, `usage`, `resource`, and terminal `completed | cancelled | failed` events. Stream-level rules (one start, one terminal, stable request ID, increasing sequence, monotonic timestamps, terminal last) require runtime assertions beyond per-event JSON Schema validation.

The runtime validates those invariants and keeps prompts, generated text, credentials, environment secrets, and raw provider error bodies out of default traces.

### Model-store contract

The proposal requires explicit user consent, bounded staging, safe archive handling, exact file-set/size/digest verification, atomic active-revision replacement, rollback, request cancellation, cleanup containment, and deterministic startup reconciliation. The current implementation supports a single file, verifies size and digest before activation, makes the staged artifact read-only, atomically replaces the active pointer, supports post-install digest re-verification, and blocks active-revision removal.

It is **not** yet a journaled multi-file transaction manager: startup reconciliation, crash-recovery proof, post-activation provider health rollback, and filesystem durability testing remain open. The managed-root and AEGIS authorization seam also require integration review.

## Implementation status

| Deliverable | Status |
|---|---|
| Provider-neutral Python interface and typed errors | Implemented |
| Loopback-only Ollama chat/stream adapter | Implemented; live provider conformance not run |
| Capability reporting | All provider capabilities remain unknown pending pinned live tests |
| Runtime timeout, input/output/context bounds and concurrency | Implemented; unit tested |
| Memory protection | Configurable available-memory admission reserve; not a hard cgroup/process cap |
| Trace redaction and stream invariants | Implemented; unit tested |
| Model download and SHA-256 verification | Implemented for one HTTPS file; byte stream currently unit-fixtured |
| Staging and atomic active pointer | Implemented; unit tested |
| Model cancellation and cleanup | Implemented; unit tested |
| AEGIS authorization | Fail-closed callback seam only; production policy integration pending |
| Fake/local HTTP protocol and model-store tests | 27 tests passed locally |
| Live Ollama conformance / actual inference artifact | Not run / not available |
| Benchmark harness and protocol | Harness implemented; no measurements published |

## Next steps

1. Run the full schema and runtime test suite in GitHub Actions.
2. Run `tusker-ai/scripts/ollama-smoke.py` against a pinned live Ollama installation and record the generated metadata report.
3. Test live cancellation with two concurrent requests, timeout behavior, provider disconnect and offline inference.
4. Integrate the install authorization callback with the approved AEGIS contract; default behavior remains deny.
5. Add crash-journaled multi-file model transactions and filesystem recovery tests only after managed-root/journal decisions are approved.
6. Add llama.cpp only after the first live provider path is demonstrated.

A capability changes from Unknown only when a reproducible test records provider version, runtime commit, OS/kernel, configuration, exact test, result, and redacted evidence reference.

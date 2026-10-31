# Tusker AI Runtime — initial implementation slice

This package is optional and local-first. The first provider adapter targets an already-running Ollama daemon on loopback. It does not start, stop, or kill that shared daemon. There is no cloud fallback and model-proposed tool calls are never executed.

## Development tests

```sh
cd tusker-ai
PYTHONPATH=. python -m unittest discover -s tests -v
```

The suite uses deterministic provider tests, a local HTTP protocol fixture, and mocked download byte streams. It validates request guards, stream invariants, trace redaction, download verification, cancellation cleanup, path policy, and atomic active-pointer replacement. It does **not** prove live Ollama compatibility, hardware resource enforcement, or crash-recovery behavior.

## Live Ollama smoke / benchmark

Install and start Ollama separately, install a model through the user's explicit provider workflow, then run:

```sh
python tusker-ai/scripts/ollama-smoke.py --model MODEL_ID --repeats 5 --output ollama-smoke-report.json
```

The endpoint is constrained to loopback. The script sends a fixed, non-sensitive prompt and writes metadata, latency, provider usage counts when available, and an output hash. It does not store prompt or generated text. Supply `TUSKER_MODEL_SHA256` only when independently verified.

## Security and limits

- Model downloads require explicit consent and an injected authorization callback. The default callback denies; production must bind it to the approved AEGIS policy interface before enabling installation.
- The initial ModelStore supports one HTTPS file per manifest and requires approved license metadata, a declared size, and SHA-256. It stages privately, verifies bytes, makes the artifact read-only, and atomically replaces an active-revision pointer. It is not yet a crash-journaled multi-file transaction manager and does not implement startup reconciliation or post-activation provider health rollback.
- Runtime limits cover input size, output/context ceilings, request deadlines, concurrency, and an optional minimum available-memory reserve. The memory reserve is admission control, not a hard cap on a shared Ollama process. Hard process memory/CPU enforcement must be supplied by the packaged service/cgroup boundary (ATLAS integration).
- Cancellation is request-scoped at the adapter boundary; precise Ollama server cancellation semantics remain unknown until live conformance. The adapter never kills the shared daemon. Reads are bounded by a short socket timeout, so cancellation responsiveness is bounded by provider read behavior.
- Traces log only request ID, provider/model IDs, sequence, event type and elapsed time. Prompt text, generated deltas, credentials, environment values and raw provider error bodies are excluded.
- Provider capability claims remain `unknown` until pinned-version live tests prove them. The adapter can be explicitly exercised, but unknown capabilities are not advertised as supported.

See `docs/PROVIDER-CAPABILITY-MATRIX.md` for the contract audit and provider evidence matrix.

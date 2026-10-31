# ORBIT-05 Benchmark Protocol

Status: protocol and harness implemented; no live measurements have been performed.

## Environment record

Record OS/image and kernel, runtime version/commit, driver/backend, CPU model/architecture/instruction flags, physical/logical cores, installed and available RAM, GPU and dedicated VRAM (separate from shared memory), storage/filesystem/free bytes, power/thermal state, model revision and SHA-256, quantization, context, prompt corpus revision, generation settings, concurrency and network state. Mark VM results as VM evidence. Unknown values stay unknown.

## Workloads

1. Cold model load: process start to model-ready; seconds and peak memory.
2. Warm first-token latency: request submission to first token.
3. Generation throughput: output tokens divided by generation seconds; report prompt/output counts.
4. Prompt processing rate where provider metrics permit.
5. Peak process RSS, available-RAM delta, dedicated VRAM peak and shared-memory observations.
6. Cancellation completion latency, errors, crashes, OOM and thermal throttling.
7. Fixed quality tasks for instruction following, reasoning, coding, multilingual output and tool-call proposal formatting. Never execute model-proposed tools during quality tests.

## Procedure

Pin versions, artifact digest, prompts and settings. Record background load. Perform one documented cold run and at least five warm repetitions per configuration. Randomize order where practical, allow cooldown and record deviations. Report median/min/max and p95 only when sample size supports it. Test short and representative long contexts, concurrency 1 before higher concurrency, cancellation, timeout, offline inference, provider crash and insufficient-memory behavior. Preserve raw per-run results and exact commands. Verify digest and license metadata before testing downloaded artifacts.

## Local Ollama smoke

Run from the repository root after starting a pinned local Ollama service and installing the selected model through the explicit user-consent workflow:

```sh
python tusker-ai/scripts/ollama-smoke.py --model MODEL_ID --repeats 5 --output ollama-smoke-report.json
```

The harness sends a fixed non-sensitive prompt, checks for a fixed response marker, and stores metadata plus an output hash only. It does not persist prompts or generated text. `TUSKER_MODEL_SHA256` is optional and must only be set to an independently verified digest. The current portable harness does not probe GPU metadata; the report marks that limitation.

## Run record

Include run ID, UTC timestamp, non-identifying host alias, full environment, runtime, artifact digest, configuration, workload, prompt/output token counts, cold/warm state, load seconds, TTFT, prompt rate, generation tokens/s, peak RSS, peak dedicated VRAM, available-RAM delta, thermal/power observations, exit/error state, raw log reference and notes.

## Publication and acceptance boundary

Preserve raw results, failed runs and limitations. Do not rank non-equivalent hosts. No fabricated or manually estimated performance values.

A successful local HTTP fixture test proves only protocol parsing against the fixture. Runtime acceptance still requires the smoke command against a real local Ollama installation, with exact provider version, model digest, host metadata, report artifact, and the applicable live conformance cases. No benchmark measurements are included in this repository until such a run is executed.

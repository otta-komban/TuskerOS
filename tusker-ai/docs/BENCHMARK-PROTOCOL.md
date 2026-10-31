# ORBIT-05 Benchmark Protocol

Status: protocol and harness implemented; no live measurements have been performed.

## Environment record

Record OS/image and kernel, runtime version/commit, driver/backend, CPU model/architecture/instruction flags, physical/logical cores, installed and available RAM, cgroup memory current/limit where available, GPU and dedicated VRAM (separate from shared memory), storage/filesystem/free bytes, power/thermal state, model revision and SHA-256, quantization, context, prompt corpus revision, generation settings, concurrency and network state. Mark VM results as VM evidence. Unknown values stay unknown. The current harness reports Linux cgroup memory, output-parent disk capacity, CPU topology/flags when exposed by procfs, and NVIDIA GPU inventory only when nvidia-smi is available. Other GPU vendors are not probed.

## Workloads

1. Cold model load: process start to model-ready; seconds and peak memory. This requires an independently controlled unload/reload or provider instrumentation; the smoke harness does not measure it.
2. First-request latency: request submission to first token on the first request made by the harness. This is not evidence that the model was cold.
3. Subsequent-request latency: request submission to first token on later requests in the same process.
4. Generation throughput: output tokens divided by generation seconds; report prompt/output counts.
5. Prompt processing rate where provider metrics permit.
6. Peak process RSS, available-RAM delta, dedicated VRAM peak and shared-memory observations. The harness RSS field is explicitly scoped to the client process and must not be represented as Ollama daemon RSS.
7. Cancellation completion latency, errors, crashes, OOM and thermal throttling.
8. Fixed quality tasks for instruction following, reasoning, coding, multilingual output and tool-call proposal formatting. Never execute model-proposed tools during quality tests.

## Procedure

Pin versions, artifact digest, prompts and settings. Record background load. Perform one documented cold run and at least five subsequent-request repetitions per configuration. Randomize order where practical, allow cooldown and record deviations. Report median/min/max and p95 only when sample size supports it. Test short and representative long contexts, concurrency 1 before higher concurrency, cancellation, timeout, offline inference, provider crash and insufficient-memory behavior. Preserve raw per-run results and exact commands. Verify digest and license metadata before testing downloaded artifacts.

## Local Ollama smoke

Run from the repository root after starting a pinned local Ollama service and installing the selected model through the explicit user-consent workflow:

```sh
python tusker-ai/scripts/ollama-smoke.py --model MODEL_ID --repeats 5 --output ollama-smoke-report.json
```

The harness sends a fixed non-sensitive prompt, checks for a fixed response marker, and stores metadata plus an output hash only. It does not persist prompts or generated text. `TUSKER_MODEL_SHA256` is optional and must only be set to an independently verified digest. The report includes CPU topology/flags, memory and cgroup limits when available, output-volume capacity, and NVIDIA-only GPU metadata when `nvidia-smi` is available. The first request is labelled as first-request, not cold; model load state remains unknown because the harness does not unload or observe Ollama's model residency. Peak RSS is for the client harness, not the Ollama daemon. Model artifact download connections are pinned to validated globally routable DNS results, preserve TLS hostname verification, disable ambient HTTP proxies, and reject unsafe redirects.

## Optional live conformance command

```sh
cd tusker-ai
TUSKER_OLLAMA_MODEL=MODEL_ID PYTHONPATH=. python -m pytest -q tests/test_ollama_live.py -v
```

The live test checks a real streamed completion and a two-request cancellation-isolation scenario. It must run against a pinned, identified provider version. A skipped test is not evidence of conformance.

## Run record

Include run ID, UTC timestamp, non-identifying host alias, full environment, runtime, artifact digest, configuration, workload, prompt/output token counts, first/subsequent-request state, separately measured cold-load seconds if available, TTFT, prompt rate, generation tokens/s, process RSS with process identity, peak dedicated VRAM, available-RAM delta, thermal/power observations, exit/error state, raw log reference and notes. Do not label first-request latency as cold model-load time.

## Publication and acceptance boundary

Preserve raw results, failed runs and limitations. Do not rank non-equivalent hosts. No fabricated or manually estimated performance values.

A successful local HTTP fixture test proves only protocol parsing against the fixture. Runtime acceptance still requires the smoke command against a real local Ollama installation, with exact provider version, model digest, host metadata, report artifact, and the applicable live conformance cases. No benchmark measurements are included in this repository until such a run is executed.

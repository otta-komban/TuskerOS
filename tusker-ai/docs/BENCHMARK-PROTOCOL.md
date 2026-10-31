# ORBIT-05 Benchmark Protocol

Status: proposal only. No measurements have been performed.

## Environment record
Record OS/image and kernel, runtime version/commit, driver/backend, CPU model/architecture/instruction flags, physical/logical cores, installed and available RAM, GPU and dedicated VRAM (separate from shared memory), storage/filesystem/free bytes, power/thermal state, model revision and SHA-256, quantization, context, prompt corpus revision, generation settings, concurrency and network state. Mark VM results as VM evidence.

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

## Hardware recommendation method
Treat system RAM and dedicated VRAM as separate pools; never count shared GPU memory as dedicated VRAM. Reserve OS/application headroom. Include weights, runtime overhead, KV cache, temporary buffers and concurrency. Unknown requirements remain unknown. CPU-only is valid when measured within resource and latency expectations. 4 GB, 8 GB and 16 GB+ refer only to installed system RAM tiers, not guaranteed model fit. Publish a recommendation only after load, stability, headroom and quality checks on the relevant hardware class.

## Run record
Include run ID, UTC timestamp, non-identifying host alias, full environment, runtime, artifact digest, configuration, workload, prompt/output token counts, cold/warm state, load seconds, TTFT, prompt rate, generation tokens/s, peak RSS, peak dedicated VRAM, available-RAM delta, thermal/power observations, exit/error state, raw log reference and notes.

## Publication
Preserve raw results, failed runs and limitations. Do not rank non-equivalent hosts. No fabricated or manually estimated performance values. This protocol remains a proposal until reviewed.
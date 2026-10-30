# ORBIT-05 Hardware Recommendation Method

Status: proposed policy; no model-fit or performance claims are approved.  
Owner: ORBIT-05 · Branch: 05-ai-runtime

## Inputs and provenance

Consume a read-only, source-attributed system profile. Capture CPU architecture/model/instruction flags, physical and logical cores, total and available system RAM, GPU identity/backend/driver, dedicated VRAM, whether memory is shared, storage free space, timestamp and probe version. Preserve unknown values as unknown. Do not launch a model merely to probe hardware.

## Memory accounting

Never sum dedicated VRAM and shared GPU memory into one capacity. For CPU inference, budget from available system RAM after reserving OS, desktop, user applications and a safety margin. For GPU offload, separately account for model layers/weights resident on GPU, runtime buffers and KV cache; remaining layers may consume system RAM. Context length, batch size, concurrency, architecture and KV-cache precision materially affect memory.

The initial policy must use conservative configurable reserves rather than hard-coded universal claims. A recommendation record should expose measured available RAM/VRAM and probe timestamp; reserved OS/application headroom and policy version; estimated model weights, KV cache, runtime and temporary-buffer budgets; context and concurrency assumptions; unknown or vendor-specific requirements; and confidence (measured, estimated, unknown) for every nontrivial value.

If the runtime/model does not expose enough information to estimate a component, label it unknown and do not return a positive fit guarantee.

## Tier labels

The 4 GB, 8 GB and 16 GB+ labels describe installed system RAM bands only. They are not model-size promises, do not describe GPU VRAM, and do not imply a specific tokens-per-second result. Dedicated VRAM must be shown separately. CPU-only operation remains a valid fallback, subject to an actual load/stability check.

## Decision outcomes

- recommended: successful load and representative generation on equivalent hardware class, adequate measured headroom, acceptable quality and stability.
- possible_with_limits: fit evidence exists only with reduced context, CPU offload, lower concurrency or other explicit limitations.
- not_recommended: measured load failure, OOM, instability or unacceptable quality/latency for the declared workload.
- unknown: missing hardware/model data or no equivalent test evidence.

A recommendation is not a guarantee. Show assumptions and let users choose; never silently download a model or enable a paid/cloud provider.

## Validation required before release

1. Test physical CPU-only hosts across RAM tiers.
2. Test supported NVIDIA/AMD/Intel backends separately, with exact driver/runtime combinations.
3. Compare estimated versus measured peak RSS and dedicated VRAM.
4. Test short and long contexts, batch sizes and concurrency.
5. Validate behavior under memory pressure, disk pressure, GPU loss and provider restart.
6. Revise reserve policy from measured evidence and document uncertainty.

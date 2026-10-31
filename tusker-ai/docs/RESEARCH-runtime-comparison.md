# ORBIT-05 — Runtime Comparison: First Research Pass

**Date:** 2026-10-31 (Asia/Kolkata)
**Status:** Preliminary desk research only. No code was run and no performance benchmark was performed.
**Decision:** Keep both Ollama and llama.cpp as candidates. Do not select a default provider until a reproducible benchmark and Fedora integration test are available.

## 1. Ollama

### Evidence observed
- Official Linux documentation describes manual Linux installation, running `ollama serve`, and configuring a systemd service. AMD ROCm and ARM64-specific installation paths are documented.
- Fedora's package index lists Ollama and related packages including `ollama-base`, `ollama-rocm` and `ollama-vulkan`; Fedora's AI/ML SIG page documents package installation variants.
- Ollama's current product documentation includes both local execution and optional cloud models. TuskerOS must explicitly constrain its integration to local model identifiers and local endpoints; cloud inference must not be silently selected.

### Strengths for TuskerOS
- Relatively straightforward local service lifecycle and API integration.
- Fedora package availability may reduce custom packaging burden on supported Fedora versions.
- Convenient model inventory and lifecycle affordances for a first end-to-end MVP.

### Questions / risks to verify
- Package versions and backend availability vary by Fedora release; ATLAS-01's selected Fedora baseline is not yet known.
- Decide whether to use Fedora packages, upstream binaries, or a separately managed user-space installation. Do not blindly run a remote shell installer as part of OS setup.
- Verify service user, group, data-directory ownership, update channel, model artifact integrity, cloud-routing disablement, and network binding behavior.
- Audit the license set of the exact shipped package and dependencies; model licenses are separate from runtime licenses.

## 2. llama.cpp

### Evidence observed
- The upstream README describes a C/C++ inference implementation, GGUF-oriented workflows, CLI and OpenAI-compatible server usage, quantization levels, and CPU/GPU backend options.
- Documented backend options include CUDA, HIP, Vulkan, SYCL, OpenCL, and others, with support depending on platform/build maturity.
- Fedora packages exist for llama.cpp; Fedora package metadata reports a combined license expression. Exact source/package version and license files must be checked at the selected Fedora release.

### Strengths for TuskerOS
- Fine-grained control over quantization, context, process invocation and hardware backend selection.
- Useful for a lower-level provider adapter and controlled benchmarking.
- Can run as an owned process or local server, giving the runtime manager explicit lifecycle control.

### Questions / risks to verify
- Backend availability depends on build flags, drivers and Fedora package variants.
- More integration and model-management work may be required than with Ollama.
- Pin exact builds and test process lifecycle, server binding, model compatibility and cancellation behavior.

## 3. Preliminary comparison

| Criterion | Ollama | llama.cpp |
|---|---|---|
| Fedora package path | Fedora packages and backend subpackages observed | Fedora package observed |
| Integration shape | Managed service + local API | CLI/library/local server |
| Model management | More built-in lifecycle affordances | More of the lifecycle is likely Tusker-owned |
| Hardware controls | Backend/package dependent | Broad documented backend/build options |
| Best initial experiment | Fast MVP adapter | Control/benchmark adapter |
| Selection status | Candidate only | Candidate only |

This is a qualitative desk-research comparison, not a measured scorecard.

## 4. Fedora integration implications

- Wait for ATLAS-01 to select the supported Fedora release before freezing package names or versions.
- Prefer distro-managed packages when their version, license, security/update cadence and required backend meet acceptance criteria.
- Keep GPU acceleration optional. CPU-only operation must remain a supported fallback.
- Do not enable a system-wide inference daemon by default. Prefer user-session activation or an explicitly enabled optional service, subject to desktop/session architecture.
- Bind local APIs to loopback and test that no LAN listener is exposed.

## 5. Model-family and license policy

No model family is approved by this research pass. A model's weight license and acceptable use/redistribution terms are independent of the runtime's software license. Each catalog entry must record exact publisher, revision, source, digest, license text/identifier, restrictions, file size, quantization and capability metadata. Re-check the model's own license at the exact revision before shipping or recommending it.

## 6. Sources

- Ollama Linux download/install: https://ollama.com/download/linux
- Ollama Linux service/manual install docs: https://github.com/ollama/ollama/blob/main/docs/linux.mdx
- Ollama upstream documentation index: https://github.com/ollama/ollama/blob/main/docs/README.md
- Fedora AI/ML SIG Ollama packaging guidance: https://fedoraproject.org/wiki/SIGs/AI-ML
- Fedora Ollama package and license metadata: https://packages.fedoraproject.org/pkgs/ollama/ollama/
- llama.cpp upstream README and backend list: https://github.com/ggml-org/llama.cpp/blob/master/README.md
- llama.cpp build/backend documentation: https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md
- Fedora llama.cpp package metadata: https://packages.fedoraproject.org/pkgs/llama-cpp/llama-cpp/

## 7. Outstanding work

- [ ] Confirm the selected Fedora release with ATLAS-01 and re-check package versions on that release.
- [ ] Read exact upstream/package license files and transitive dependency notices for both providers.
- [ ] Compare provider APIs for streaming, cancellation, model inventory, health and resource reporting.
- [ ] Test default bind address and cloud-routing behavior.
- [ ] Evaluate candidate models and exact model licenses independently.
- [ ] Run controlled CPU-only and GPU benchmarks on named hardware.
- [ ] Record measured results; do not extrapolate VM results to physical laptop performance.

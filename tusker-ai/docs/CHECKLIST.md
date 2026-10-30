# ORBIT-05 — Engineering Checklist

This is the agent-specific execution checklist derived from the TuskerOS Ten-Agent Execution Blueprint. Checkboxes are only marked complete when evidence exists.

## P0 — Discovery and requirements
- [ ] Compare maintained local inference runtimes and model formats.
  - [ ] Verify current Ollama Linux support, packaging, service model and license.
  - [ ] Verify current llama.cpp Linux support, build/deployment options, acceleration backends and license.
  - [ ] Compare CPU, NVIDIA, AMD and Intel acceleration support on Fedora.
  - [ ] Compare memory behavior, context/KV cache controls, streaming, cancellation and observability.
  - [ ] Record source URLs, access dates, versions/commits and unresolved claims.
- [ ] Evaluate open-weight model families for fast interaction, reasoning, coding and optional vision.
  - [ ] Review model-specific license and redistribution/use restrictions.
  - [ ] Record provenance, immutable revision, quantizations and artifact sizes.
  - [ ] Define task-quality, tool-use, multilingual and context evaluation criteria.
- [ ] Define 4 GB, 8 GB and 16 GB+ hardware capability tiers.
  - [ ] Separate system RAM from dedicated VRAM and shared GPU memory.
  - [ ] Reserve OS headroom and account for context/KV cache and runtime overhead.
  - [ ] Define CPU-only and supported GPU cases.
  - [ ] Document honest no-model / reduced-capability behavior.
- [ ] Define offline, storage, provenance, update and privacy requirements.
  - [ ] Require user consent before large downloads.
  - [ ] Require digest verification before activation.
  - [ ] Define atomic install/update and safe removal.
  - [ ] Define default-off telemetry and no cloud inference requirement.
- [ ] Publish P0 runtime comparison, model/license criteria, preliminary hardware matrix and acceptance criteria.

## P1 — Architecture and contracts
- [ ] Define provider-neutral facade and adapter lifecycle.
  - [ ] Provider discovery and capability reporting.
  - [ ] Define adapter lifecycle state machine and process ownership.
  - [ ] Specify deterministic provider adapter conformance suite (see PROVIDER-CONFORMANCE.md).
  - [x] Publish language-neutral inference event JSON Schema and synthetic valid trace fixture; schema and trace tests pass in GitHub Actions run 41117411271.
  - [ ] Model inventory and manifest validation.
  - [ ] Inference request, streaming events and structured errors.
  - [ ] Cancellation, timeout, load/unload and health checks.
  - [ ] Resource limits, concurrency and OOM handling.
- [ ] Define versioned model manifest.
  - [ ] Identity, publisher, revision, source and provenance.
  - [ ] License identifier/text and review status.
  - [ ] SHA-256 digest, byte size, format and quantization.
  - [ ] Context, capabilities/modalities and compatibility.
  - [ ] RAM/VRAM/storage requirements.
- [ ] Agree contracts with TUSKER-04, NEXUS-07 and ATLAS-01.
- [ ] Record threat model, offline guarantees, data handling and network exposure constraints.
- [ ] Publish architecture and contract decision records.

## P2 — Foundation
- [ ] Create provider adapter skeleton and runtime lifecycle manager.
- [ ] Implement model catalog/registry and schema validation.
- [ ] Implement verified download/import and digest checks.
- [ ] Implement safe storage permissions and path/symlink validation.
- [ ] Implement inventory, health, resource monitoring and load/unload.
- [ ] Implement atomic update and safe removal.
- [ ] Add mock inference, adapter, checksum, interrupted-download and config tests.

## P3 — Working MVP
- [ ] Select a runtime only after current research and benchmark evidence.
- [ ] Integrate one runtime on the selected Fedora foundation.
- [ ] Demonstrate discovery, install, load, inference, stream, cancel, unload and remove.
- [ ] Demonstrate inference after network disconnection.
- [ ] Expose capability and health status through the stable TUSKER-04 contract.
- [ ] Record reproducible commands, environment and outputs.

## P4 — Complete feature set
- [ ] Add benchmark-supported fast/reasoning/coding profiles where appropriate.
- [ ] Keep vision optional and capability-declared.
- [ ] Implement hardware-aware model recommendations.
- [ ] Expose context, CPU/GPU, thread, quantization and storage controls.
- [ ] Implement GPU-to-CPU fallback where supported.
- [ ] Implement memory-pressure response, unload policy and user warnings.
- [ ] Evaluate offline speech only as a separately configurable module.

## P5 — Integration
- [ ] Integrate task-aware model routing with TUSKER-04.
- [ ] Integrate approved hardware telemetry with NEXUS-07/ATLAS-01.
- [ ] Integrate model manager UX through stable facade.
- [ ] Ensure remote access uses approved Tusker task API only.
- [ ] Verify model provider ports are not exposed unauthenticated.

## P6 — Verification and hardening
- [ ] Benchmark load time, TTFT, tokens/s, memory, CPU/GPU and context behavior.
- [ ] Measure thermal/battery impact on physical hardware where available.
- [ ] Test 4 GB, 8 GB and 16 GB+ profiles; label VM versus physical evidence.
- [ ] Test no-GPU and insufficient-RAM cases.
- [ ] Test disk-full, corrupt model, checksum mismatch and interrupted download.
- [ ] Test missing runtime binary, provider crash, timeout and cancellation.
- [ ] Verify offline operation and absence of mandatory cloud inference.
- [ ] Audit licenses, provenance, permissions, ports, telemetry and update authenticity.

## P7 — Release and handover
- [ ] Publish curated model catalog with revisions, licenses, checksums, sizes and hardware recommendations.
- [ ] Document provider installation, lifecycle, offline setup, troubleshooting and resource settings.
- [ ] Publish reproducible tests and runtime/model compatibility guidance.
- [ ] Publish benchmark archive, known limitations and maintenance handover.
- [ ] Obtain release sign-off based on actual evidence.


### Contract validation automation

- [x] Add isolated GitHub Actions job for model-manifest and inference-event schema/fixture tests.
- [x] Observe successful CI runs on this branch: 41116139411 (baseline) and 41117411271 (expanded manifest negative cases).
- [x] Execute the test suite in CI; run 41117411271 passed on commit af3bd90ee30f060e588d96a13427c7e77db1a3f1.

# ORBIT-05 Runtime Work Plan

**Task:** ORBIT-05-RUNTIME-01
**Owner:** ORBIT-05
**Working branch:** `05-ORBIT`
**Base/main SHA at initial inspection:** `345fc5a3d0f831fc714bae0cc88fa842cd9bed79`
**Plan status:** Active implementation; local proxy/redirect isolation change committed, focused tests pass, live Ollama remains unverified.

## Objective

Review the prior ORBIT runtime implementation and Issue #57, establish which artifacts are already present on the current unified main baseline, identify remaining gaps, and deliver small reviewed runtime increments without importing historical branch history wholesale.

## Verified starting evidence

- The assigned branch `05-ORBIT` existed at the unified main SHA when work began. The historical candidate `effb9fa93baea1309ba7cf77de36882b169547d9` is an ancestor of current `main`; no blind merge/cherry-pick was warranted.
- The current mainline already contains the historical provider contract, cross-agent alignment note, model-manifest schema, provider adapter and ModelStore implementation.
- The historical runtime PR #58 records 94 component tests passed and 2 opt-in live Ollama tests skipped on its earlier head. Those checks are not evidence of live inference.
- PR #58 contains an owner-directed freeze on its historical `agent/05-ai-runtime` branch. This work is isolated to the replacement branch `05-ORBIT`; the frozen branch and PR are not modified.
- The provider contract remains proposed pending TUSKER-04, NEXUS-07, ATLAS-01 and AEGIS-06 review. The AEGIS callback defaults to deny; hard daemon CPU/memory isolation is outside admission guards.

## Implemented in this iteration

- Replaced ambient `urlopen()` use in the Ollama adapter with an explicit opener configured with `ProxyHandler({})`, so HTTP(S)/ALL proxy environment variables cannot reroute local inference.
- Added a no-redirect handler. A local endpoint's 3xx response is rejected instead of forwarding a prompt-bearing request to another host.
- Added deterministic regression tests covering proxy-environment isolation for health and inference, and redirect rejection for both GET and POST paths.
- Local verification: `PYTHONPATH=. python -m unittest -v tests/test_ollama_http.py` — 4 passed; `python -m py_compile tusker_ai/providers/ollama.py tests/test_ollama_http.py` — passed. This focused local harness is not the full project suite or live Ollama conformance.

## Implemented in the next iteration

- Added a deterministic stream-cancellation regression: cancellation is triggered while the adapter is waiting for the next NDJSON frame, the request emits a `cancelled` terminal event rather than `completed`, and a subsequent independent request succeeds against the same HTTP fixture.
- The test uses the adapter's bounded socket-read timeout to observe cancellation. It does not prove server-side generation stops in Ollama; live cancellation conformance remains outstanding.
- GitHub Actions Tusker AI Runtime Unit Tests passed on source/test revision `87f45be297f921dd38b511236c64dd2e16f4e4e6` (run 60); PHOENIX release manifest integrity also passed. Tusker AI contract/schema tests passed after the cancelled attempt was re-queued (run 79). Unified validation run 530 was cancelled during rapid branch updates; no pass is claimed.

## Runtime lifecycle regression iteration

- Added tests proving the runtime semaphore is released when a provider raises after starting and when a consumer closes a partially consumed inference stream.
- These cases exercise the existing `finally` cleanup guarantee without changing runtime behavior or shared contracts. They guard against a stuck capacity slot that would otherwise block all later inference when configured concurrency is one.
- The first branch-head CI run exposed two fixture mistakes in the new tests (the reusable fake provider emitted a hard-coded request ID and the failure fixture failed every request). The fixtures were corrected so follow-up requests use their own IDs and only the first request fails. The corrected tests are committed; CI is running on the corrected head.

## Remaining work sequence

1. Re-run runtime unit tests and unified validation on the latest branch head after the new runtime slot-cleanup tests.
2. Review provider cancellation/deadline behavior and add focused tests for request isolation without terminating the shared daemon.
3. Verify current TUSKER lifecycle, AEGIS authorization, NEXUS hardware-source and ATLAS service/cgroup decisions. Do not modify shared contracts or infer approval from proposals.
4. Keep model install/remove fail-closed until the approved AEGIS action/session/device/resource/precondition authorization is integrated and tested.
5. On a host with a real local Ollama service and pinned model, run health/version, inference, streaming, cancellation-isolation and smoke/benchmark tests; record model digest and host metadata. If unavailable, mark NOT RUN.
6. Deliver a focused PR to `main` for integrator review. Do not self-merge.

## Acceptance criteria

- [x] Historical work and Issue #57 reconciled against current main with exact SHAs and no blind history import.
- [x] Proxy environment and redirect isolation added to the local Ollama adapter with regression tests.
- [x] Focused HTTP adapter tests and compile checks pass in the isolated local harness.
- [x] Runtime unit tests and contract/schema tests passed on the pre-slot-cleanup source revision; re-run runtime tests on latest head is pending.
- [ ] Any model install/remove path remains deny-by-default unless exact AEGIS authorization is integrated and tested.
- [ ] Resource limits distinguish admission control from enforced process isolation; live cancellation is tested without killing a shared daemon.
- [ ] Live inference report includes model digest, provider version, host metadata and reproducible command output, or is explicitly NOT RUN.
- [ ] Focused PR includes task ID, base/head SHA, tests, security impact, rollback and evidence.

## Dependencies and blockers

- **AEGIS-06:** approved authorization interface for model install/remove; until then the injected callback remains fail-closed.
- **TUSKER-04:** approved task/step lifecycle and event-version binding.
- **NEXUS-07:** approved source and semantics for hardware inventory/telemetry.
- **ATLAS-01:** optional user-service packaging and hard cgroup resource boundary for the provider process; admission checks alone are not hard isolation.
- **Live host:** Ollama binary/service and a pinned model are required for actual inference acceptance.

## Non-goals / safety boundaries

- No shared schema, lifecycle, privilege-boundary or package-trust changes without Chief Architect approval.
- No cloud fallback, root inference process, tool execution by the model runtime, or killing a shared Ollama daemon.
- No changes to the frozen historical `agent/05-ai-runtime` branch or PR #58.
- No blind cherry-pick/merge of historical branches, no direct main push, no force-push, no self-merge.
- No claim of live inference, hard resource enforcement, production authorization or release readiness without reproducible evidence.

## Rollback

Keep implementation changes in focused commits/PRs. If rejected, the integrator may revert the relevant commit on the ORBIT branch after review; preserve all historical branches, commits, logs and test evidence.

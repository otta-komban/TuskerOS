# ORBIT-05 Runtime Work Plan

**Task:** ORBIT-05-RUNTIME-01 (historical owner-assigned scope; revalidated against the replacement branch)
**Owner:** ORBIT-05
**Working branch:** `05-ORBIT`
**Base/main SHA at inspection:** `345fc5a3d0f831fc714bae0cc88fa842cd9bed79`
**Plan status:** Review-first; no implementation or runtime acceptance claimed.

## Objective

Review the prior ORBIT runtime implementation and Issue #57, establish which artifacts are already present on the current unified main baseline, identify remaining gaps, then deliver a small reviewed runtime increment without importing historical branch history wholesale.

## Verified starting evidence

- The assigned branch `05-ORBIT` exists and compares identical to live `main` (0 ahead / 0 behind).
- Historical Issue #57 records a prior candidate at `effb9fa93baea1309ba7cf77de36882b169547d9`, reported as 30 commits ahead / 0 behind at the time of that report.
- That historical candidate is now an ancestor of current `main`; GitHub compare reports current main 605 commits ahead of that candidate and 0 ahead of it. The historical `agent/05-ai-runtime` ref is also behind current main. No blind merge/cherry-pick is warranted.
- The current mainline contains the historical provider contract, cross-agent alignment note, model-manifest schema and runtime README. The README now documents recovery-inspection behavior beyond the historical report.
- The historical report records 29 passing / 2 skipped tests and a successful compile check in its isolated environment. The two skipped tests require real Ollama and a model; this is not live inference evidence.
- The provider contract remains explicitly proposed pending TUSKER-04, NEXUS-07, ATLAS-01 and AEGIS-06 review. The AEGIS callback defaults to deny; hard daemon CPU/memory isolation is outside admission guards.

## Work sequence

1. **Historical review (current):** compare Issue #57 and the old runtime branch/commit with current main; inventory already-integrated code, tests, docs, workflow evidence and unresolved findings.
2. **Contract/dependency review:** verify current TUSKER lifecycle, AEGIS authorization, NEXUS hardware-source and ATLAS service/cgroup decisions. Do not modify shared contracts or infer approval from proposals.
3. **Local validation:** run focused unit tests and compile checks in a reproducible checkout; record exact commands, exit codes, test counts and tested SHA. Keep real-Ollama tests opt-in.
4. **Implementation:** select one bounded, independently testable gap in ORBIT ownership. Keep install/remove disabled by default until the approved AEGIS contract is available. Do not claim hard isolation for a shared Ollama daemon.
5. **Runtime acceptance:** only on a host with a real local Ollama service and pinned model, run health/version, inference, streaming, cancellation-isolation and smoke/benchmark tests; record model digest and host metadata. If unavailable, mark NOT RUN and retain the blocker.
6. **Delivery:** update compatibility and rollback notes, commit focused changes on `05-ORBIT`, and open a PR to `main` for integrator review. Do not self-merge.

## Acceptance criteria

- [ ] Historical work and Issue #57 reconciled against current main with exact SHAs and no blind history import.
- [ ] Provider capability matrix and manifest behavior reviewed against implementation and tests.
- [ ] Focused unit tests and compile checks pass on the exact ORBIT branch head.
- [ ] Any model install/remove path remains deny-by-default unless exact AEGIS action/session/device/resource/precondition authorization is integrated and tested.
- [ ] Resource limits distinguish admission control from enforced process isolation; cancellation is tested without killing a shared daemon.
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
- No blind cherry-pick/merge of historical branches, no direct main push, no force-push, no self-merge.
- No claim of live inference, hard resource enforcement, production authorization or release readiness without reproducible evidence.

## Rollback

Keep implementation changes in a focused commit/PR. If rejected, the integrator may revert that commit on the ORBIT branch after review; preserve all historical branches, commits, logs and test evidence.

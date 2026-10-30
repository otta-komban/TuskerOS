# ORBIT-05 Cross-Agent Contract Alignment Note

**Date:** 2026-10-31  
**Owner:** ORBIT-05  
**Status:** Intake review only; no external contract is approved by this note.

This note records findings from inspecting the current proposal documents on the other agents' branches. ORBIT-05 has not modified those branches.

## 1. TUSKER-04 alignment

Inspected `04-tusker-core:tusker-core/ARCHITECTURE.md`.

Relevant existing proposal:
- ORBIT-05 owns model inference behind a provider-neutral adapter.
- Model adapter cannot call tools directly and cannot grant itself permission.
- TUSKER-04 expects model errors including `model_unavailable`, explicit context limits, and bounded cancellation/retry behavior.
- Core owns task/step correlation, planning, authorization handoff and event replay.

ORBIT-05 contract implication:
- Keep tool-call data as untrusted proposals; never execute it in the runtime.
- Add optional `task_id`, `step_id`, `correlation_id` to request tracing metadata; the trusted Core transport supplies/validates them.
- Map provider-specific missing/unavailable errors to Core's `model_unavailable` category without losing the underlying ORBIT provider error code.
- The runtime's request stream is separate from TUSKER task lifecycle events; Core owns task state and replay.

Review remains pending in [issue #20](https://github.com/otta-komban/TuskerOS/issues/20).

## 2. NEXUS-07 alignment

Inspected `07-system-integration:system-integration/INTERFACE_CONTRACTS.md` and `SERVICE_IDENTIFIERS.md`.

Relevant existing proposal:
- NEXUS defines a read-only system capability API, tentatively `org.tuskeros.SystemTools1`, with `GetCapabilities()`, `GetDeviceInventory()`, `GetSystemSnapshot()` and `GetHealth()`.
- NEXUS explicitly assigns ORBIT-05 only the device capability/telemetry fields consumed for model suitability; model runtime control remains ORBIT-owned.
- The proposed D-Bus namespace is not frozen and requires confirmation that the project controls the reverse-DNS domain.
- NEXUS discourages a resident daemon for one-shot reads and requires no boot/login dependency.

ORBIT-05 contract implication:
- Prefer NEXUS's approved read-only system snapshot/device inventory as the shared hardware source, rather than creating a competing system-wide hardware daemon.
- Request that NEXUS expose RAM availability, CPU facts, GPU device/driver/backend facts, dedicated-vs-shared VRAM, and model-volume free space where safely available.
- If a field is not exposed, use a documented runtime-local read-only fallback and label its source; do not duplicate privileged tooling.
- Keep hardware probing independent from whether an inference provider is running.
- Treat D-Bus service name and namespace as provisional until approved.

Review remains pending in [issue #22](https://github.com/otta-komban/TuskerOS/issues/22) and the shared NEXUS-07 P1 review issue [#5](https://github.com/otta-komban/TuskerOS/issues/5).

## 3. AEGIS-06 alignment

Inspected `06-security-gatekeeper:security/SECURITY_CONTRACTS.md`.

Relevant existing proposal:
- Model-generated arguments and all model output are untrusted.
- Only AEGIS policy service can produce authorization decisions.
- Caller identity comes from trusted transport/OS context, not JSON body fields.
- Privileged broker accepts typed operations, not shell strings or arbitrary executable paths.
- Retry must re-enter policy evaluation; approval/authorization is bound to an action digest and expiry.

ORBIT-05 contract implication:
- Runtime tool-call proposals are content only; they are not executable or authorized actions.
- Runtime must not carry or mint authorization grants.
- Do not trust model-supplied principal, origin, caller identity, resource scopes or approval state.
- Runtime logging must not duplicate the AEGIS audit ledger or record prompts/secret values by default.
- Cancellation of generation is distinct from cancellation of a system operation; Core/NEXUS/AEGIS own the latter lifecycle.

Security review is still required before adapter/service implementation.

## 4. Required contract follow-ups

- [ ] TUSKER-04 confirms task/step/correlation metadata and error mapping.
- [ ] NEXUS-07 confirms the shared hardware source, exact fields/units and unknown-value semantics.
- [ ] AEGIS-06 reviews local endpoint exposure, process ownership and sensitive logging.
- [ ] ATLAS-01 confirms Fedora package/service lifecycle, user-session activation and optional dependency handling.
- [ ] All agreed changes are recorded by the owning agent in its contract/decision record.

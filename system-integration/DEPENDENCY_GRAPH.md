# TuskerOS Integration Dependency Graph
**Owner:** NEXUS-07 · **Status:** Draft / validate with owners

## Directional rules
1. UI/presentation depends on public service contracts, never internal implementation details.
2. TUSKER-04 may request capabilities through the NEXUS typed tool boundary; NEXUS does not depend on planner internals.
3. NEXUS requests authorization from AEGIS-06 for every mutating/elevated operation; it cannot implement or weaken policy.
4. NEXUS adapters depend on supported OS APIs/utilities selected with ATLAS-01; do not duplicate package, network, power, or service managers.
5. ORBIT-05 provides inference/model-runtime capabilities to TUSKER-04; NEXUS only publishes relevant hardware/system facts.
6. NOVA-02 consumes task/status/device events; desktop availability must not depend on TUSKER or NEXUS being healthy.
7. PILOT-08 submits through the same task boundary as local clients; remote origin never bypasses local policy.
8. FORGE-09 extensions consume an allowlisted SDK capability facade, not raw D-Bus or root operations.
9. PIXEL-03 produces theme data/assets consumed by NOVA-02; theme rendering is not a system integration service.
10. PHOENIX-10 packages and updates components but does not own their runtime APIs.

## Major edges
| Producer / owner | Consumer | Contract to agree |
|---|---|---|
| ORBIT-05 | TUSKER-04 | Model provider, availability, context limits, errors |
| AEGIS-06 | NEXUS-07 | Authenticated caller, authorize/approve, execute, audit |
| NEXUS-07 | TUSKER-04 | Typed tool catalogue, invoke/result, progress/cancel/postcondition |
| NEXUS-07 | NOVA-02 | Device/system telemetry and task status events |
| ATLAS-01 | NEXUS-07 | Supported OS APIs, service lifecycle, packaging, D-Bus |
| TUSKER-04 | PILOT-08 | Task submission/status/event/approval routing |
| AEGIS-06 + NEXUS-07 | FORGE-09 | Capability metadata and permission model |
| PIXEL-03 | NOVA-02 | Theme schema, token names, preview/apply/revert |
| All agents | PHOENIX-10 | Package/install/update/recovery/release metadata |

## Failure containment
- A failed model runtime must not block OS tools or the desktop.
- A failed Tusker core must not block KDE or basic OS services.
- A failed tool provider disables affected capabilities and reports unavailable; it must not silently fall back to unsafe shell execution.
- A failed security broker blocks mutating/elevated tools closed; read-only tools may remain available only if their own policy allows.
- A failed remote service leaves local workflows unaffected.
- A failed theme returns to a known safe default.
- An extension crash is isolated to that extension.
- A failed telemetry source yields stale/unavailable data, not fabricated zero values.

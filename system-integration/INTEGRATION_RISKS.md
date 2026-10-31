# NEXUS-07 Integration Risks and Decision Register
**Owner:** NEXUS-07 · **Status:** Initial intake baseline · **Last reviewed:** 2026-10-31

## Risks
| ID | Risk | Impact | Mitigation / decision | Status |
|---|---|---|---|---|
| NX-R01 | Repository has no shared architecture, registry, contracts, ownership or decision files yet. | Parallel agents can invent incompatible names, payloads and ownership boundaries. | Keep NEXUS contracts explicitly provisional; request owners' review; create shared coordination baseline before freezing names. | Open |
| NX-R02 | D-Bus names and method signatures chosen before Fedora/KDE service research. | API churn, collisions, unsupported assumptions. | Prefer existing standard interfaces; ATLAS-01/AEGIS-06 review before freezing bus names. | Open |
| NX-R03 | Tool provider and privileged broker boundaries blur. | Privilege escalation or policy bypass. | AEGIS-06 owns policy and privileged broker; NEXUS validates typed operations and never grants itself elevated access. | Open |
| NX-R04 | Long-running synchronous IPC blocks clients or causes duplicate actions after timeout. | UI hangs, inconsistent state, repeated mutations. | Bounded calls; operation IDs, deadlines, idempotency keys, cancellation and explicit unknown-outcome state. | Proposed mitigation |
| NX-R05 | Services become always-on by default. | RAM/CPU overhead and reduced reliability. | On-demand activation and library reuse; daemon only for independent lifecycle/privilege/fault isolation. | Proposed mitigation |
| NX-R06 | Events treated as authoritative state or delivered exactly once. | Stale UI and incorrect task/device state. | Events are hints; consumers reconcile with owner service; tolerate duplicates, gaps and reordering. | Proposed mitigation |
| NX-R07 | Logging exposes prompts, clipboard, screenshots, file contents or credentials. | Privacy and security incident. | Structured sanitized logs; sensitive payloads excluded by default; audit data policy reviewed with AEGIS-06. | Open |
| NX-R08 | Cross-agent interface changes happen without versioning or migration tests. | Integration breakage. | SemVer schemas, compatibility tests, owner acknowledgements and decision records before breaking changes. | Open |
| NX-R09 | Tests are reported despite absent implementation or test harness. | False confidence and invalid release claims. | Mark tests not run until harness exists; preserve evidence and environment details. | Controlled |
| NX-R10 | Telemetry failure interpreted as zero/healthy. | Unsafe decisions and misleading dashboards. | Explicit unavailable/stale/unknown states; never synthesize zero values. | Proposed mitigation |

## Decisions (provisional)
- **NX-D01:** NEXUS owns shared integration contracts and OS tool adapters, not other agents' internals.
- **NX-D02:** AEGIS-06 is authoritative for authorization and privileged execution policy.
- **NX-D03:** TUSKER-04 is authoritative for task planning/orchestration; NEXUS is authoritative for tool execution semantics and postcondition evidence.
- **NX-D04:** Prefer existing system APIs and on-demand activation; do not create a daemon without a concrete lifecycle/security/isolation requirement.
- **NX-D05:** An operation timeout after a mutation begins means outcome unknown until observed; do not blindly retry.

All decisions remain subject to the repository's eventual shared decision process and impacted-owner approval.

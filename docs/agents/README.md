# TuskerOS Agent Workforce

**Current canonical baseline:** `main` at `8bf66079f9e021244eda432fa8455e83b59e2165` (baseline recorded when this operating guide was prepared). Always re-check the live main SHA before starting a task.

Ten specialist roles own bounded areas. The role IDs are stable; names are role identifiers, not separate autonomous GitHub accounts. One agent works on one assigned branch.

| ID | Agent | Ownership | Branch |
|---|---|---|---|
| ATLAS-01 | Fedora Base & Image Foundation | Fedora base, DNF5, package manifest, reproducible image pipeline | `agent/01-fedora-base` |
| NOVA-02 | Desktop Shell | Desktop session, shell integration, settings UX, persistence | `agent/02-desktop-shell` |
| PIXEL-03 | Theme Studio | Theme tokens, packs, validation, apply/reload, accessibility | `agent/03-theme-studio` |
| TUSKER-04 | Core Lifecycle | Task/operation lifecycle, typed events, cancellation, failure semantics | `agent/04-tusker-core` |
| ORBIT-05 | AI Runtime | Provider adapters, model store/lifecycle, inference, limits, traces | `agent/05-ai-runtime` |
| AEGIS-06 | Security Gatekeeper | Policy engine, approval binding, privileged boundary, audit | `agent/06-security-gatekeeper` |
| NEXUS-07 | System Integration | Tool descriptors, D-Bus/system adapters, broker integration, health | `agent/07-system-integration` |
| PILOT-08 | Remote Control | Pairing, authenticated remote API, sessions, authorization, network security | `agent/08-remote-control` |
| FORGE-09 | Ecosystem & Extensions | Catalog, resolution, trust, transactions, rollback, audit integration | `agent/09-ecosystem` |
| PHOENIX-10 | Installer & Recovery | Installer, storage safety, boot/image validation, recovery, provenance | `agent/10-installer-recovery` |

## Authority and coordination
- The Chief Architect owns cross-agent architecture, shared interfaces, dependency ordering, integration decisions, and contract versioning.
- Each specialist owns implementation and tests inside its assigned component.
- Specialists may propose shared-contract changes but must not unilaterally change them.
- The project owner/repository administrator owns repository settings, branch protection, credentials, and explicit high-impact approvals.
- The integrator merges reviewed PRs; agents do not merge their own work.

## Starting a work session
1. Confirm that the new cohort is authorized (see the reauthorization gate below).
2. Confirm the assigned branch exists and is based on the current approved `main` SHA. If it is stale, request a coordinated fast-forward; do not force-update it.
3. Select a task from `AGENT_TASKS.md` or an approved GitHub issue. Do not invent overlapping scope.
4. Record a task plan and dependencies before implementation.
5. Keep the task branch clean and submit a focused PR when acceptance criteria pass.

## Current authorization and safety gate
The owner authorization and Chief Architect suspension-lift decisions are recorded in Issues #35 and #34. The ten replacement agents may perform branch-isolated implementation on their assigned `agent/NN-...` branches. This authorization does not permit direct pushes to `main`, self-merging, force-push/history rewrite, branch deletion, or unapproved shared-contract/security-boundary changes. PIXEL-03 must resolve its specific Issue #50 blocker before theme implementation depending on the shared theme contract. Sensitive, privileged, destructive, irreversible, or externally consequential actions still require explicit owner approval.

Before each task, verify the live `main` SHA, assigned branch, dependencies, and applicable approvals. Branch-protection / required-check enforcement must be reported as unverified unless the live ruleset proves otherwise. The existence of a branch or an active ruleset alone is not proof that required checks are enforced.

## Baseline facts
At the recorded baseline, unified validation run `41174359784` passed 8/8 jobs. This validates the configured contract/static suites only. It is not evidence of bootable image, VM runtime, production broker, live inference, or release readiness. See `BUILD_AND_CI.md`.

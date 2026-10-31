# TuskerOS Agent Workforce

**Current canonical baseline at launch:** main at 5162de364a2f0b7dcf8aa14251a4c5ce5cf57e6d. Always re-check live main before starting a task.

Ten specialist roles own bounded areas. Role IDs are stable; names are role identifiers, not separate GitHub accounts. One agent works on one assigned branch.

| ID | Agent | Ownership | Launch branch |
|---|---|---|---|
| ATLAS-01 | Fedora Base & Image Foundation | Fedora base, DNF5, package manifest, reproducible image pipeline | 01-ATLAS |
| NOVA-02 | Desktop Shell | Desktop session, shell integration, settings UX, persistence | 02-NOVA |
| PIXEL-03 | Theme Studio | Theme tokens, packs, validation, apply/reload, accessibility | 03-PIXEL |
| TUSKER-04 | Core Lifecycle | Task/operation lifecycle, typed events, cancellation, failure semantics | 04-TUSKER |
| ORBIT-05 | AI Runtime | Provider adapters, model store/lifecycle, inference, limits, traces | 05-ORBIT |
| AEGIS-06 | Security Gatekeeper | Policy engine, approval binding, privileged boundary, audit | 06-AEGIS |
| NEXUS-07 | System Integration | Tool descriptors, D-Bus/system adapters, broker integration, health | 07-NEXUS |
| PILOT-08 | Remote Control | Pairing, authenticated remote API, sessions, authorization, network security | 08-PILOT |
| FORGE-09 | Ecosystem & Extensions | Catalog, resolution, trust, transactions, rollback, audit integration | 09-FORGE |
| PHOENIX-10 | Installer & Recovery | Installer, storage safety, boot/image validation, recovery, provenance | 10-PHOENIX |

The launch mapping and individual scopes are authoritative in docs/agents/LAUNCH-10-AGENTS-2026-10-31.md and docs/agents/launch/.

## Authority and coordination
- Chief Architect owns cross-agent architecture, shared interfaces, dependencies, integration decisions and contract versioning.
- Specialists own implementation/tests within assigned scope and must not unilaterally change shared contracts.
- Owner/repository administrator owns repository settings, credentials and high-impact approvals.
- Integrator merges reviewed PRs; agents do not merge their own work.

## Starting a work session
1. Read the launch manifest and your individual guide.
2. Verify assigned branch, live main SHA, dependencies and applicable approvals.
3. Inspect existing main implementation and legacy branch work before porting changes.
4. Record task plan and dependencies before implementation.
5. Keep branch scoped and submit focused PR when acceptance criteria pass.

## Safety gate
The owner authorization and suspension-lift decisions are recorded in Issues #35 and #34. This launch does not authorize direct pushes to main, self-merging, force-push/history rewrite, branch deletion or unapproved shared-contract/security-boundary changes. PIXEL-03 must resolve Issue #50 before dependent theme implementation. Sensitive, privileged, destructive, irreversible or externally consequential actions require explicit owner approval.

Before each task verify live main SHA, assigned branch, dependencies and approvals. Branch-protection/required-check enforcement remains unverified unless the live ruleset proves otherwise.

## Baseline facts
Latest known mainline unified validation and PHOENIX release-manifest checks passed at 5162de3. These validate configured CI suites only; they do not prove bootable image, VM runtime, production broker, live inference or release readiness. See docs/agents/BUILD_AND_CI.md.

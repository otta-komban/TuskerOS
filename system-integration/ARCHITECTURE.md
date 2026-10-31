# TuskerOS System Integration Architecture
**Owner:** NEXUS-07 · **Status:** Phase 1 proposal / provisional pending owner review · **Branch:** `07-system-integration`

## 1. Purpose and boundaries
NEXUS-07 owns cross-subsystem contracts and the OS capability/tool adapter layer. It does not own the internal implementation of KDE, AI planning, model inference, authorization policy, base-image composition, remote transport, or extension UI. Those remain with NOVA-02, TUSKER-04, ORBIT-05, AEGIS-06, ATLAS-01, PILOT-08, and FORGE-09 respectively.

The desktop and base OS must remain usable if any optional AI, remote, theme, or tool-provider component is stopped or crashes. Local-first and offline-capable behavior is the default. No cloud inference dependency is introduced by this architecture.

## 2. Proposed logical architecture
```text
KDE / NOVA-02 ── presentation & user intent ──┐
                                             v
TUSKER-04 planner/executor ── typed tool API / task events
             |                               |
             | model provider                v
             v                         NEXUS-07 tool host
        ORBIT-05                         |       |
                                         |       +-- read-only adapters
AEGIS-06 authorization broker <----------+       +-- user-session adapters
             |                                   +-- privileged operation handoff
             v
      narrowly scoped privileged operations
             |
ATLAS-01 systemd / D-Bus / Polkit / OS packages
             |
PHOENIX-10 packaging, update, recovery and release
PILOT-08 remote client -> TUSKER-04 same task boundary (never bypass AEGIS-06)
FORGE-09 extensions -> declared SDK capabilities (never direct privileged access)
PIXEL-03 theme data -> NOVA-02 theme surfaces (not an integration daemon)
```

This is a logical dependency view, not a claim that every box is a separate process. Prefer in-process libraries or existing system services when isolation is not required. Introduce a dedicated daemon only where independent lifecycle, privilege separation, cross-process reuse, or fault containment provides a concrete benefit.

## 3. Process and privilege model
- **User session:** desktop-facing and user-owned operations run in the logged-in session, under the user's UID and environment.
- **System services:** use existing systemd-managed services and D-Bus APIs where available. Avoid creating a second service manager or shadowing OS state.
- **Privileged operations:** NEXUS exposes typed requests; AEGIS-06 owns authorization decisions and broker policy. The model/planner never receives unrestricted root or arbitrary shell access.
- **D-Bus activation:** prefer system/user bus activation for on-demand components where appropriate. No always-on AI inference process is required for ordinary desktop operation.
- **Extensions:** invoke only capability APIs granted by policy; no direct access to privileged bus names or host process execution.

## 4. Lifecycle and resilience
Every long-lived component must document owner, activation mode, dependencies, readiness criteria, health semantics, restart policy, shutdown behavior, and resource budget. Use systemd restart policies only for recoverable service failures; avoid restart loops (rate-limit and expose failed state). A consumer must tolerate provider absence, timeout, version mismatch, and restart. Calls must have bounded deadlines and cancellation where the underlying operation supports it. A timed-out mutation is an **unknown outcome** until a postcondition query resolves it; never blindly retry a non-idempotent operation.

The desktop must degrade gracefully without Tusker. Read-only status surfaces should show unavailable/stale state rather than blocking the UI. Restarting a provider must not lose durable user data or silently replay a mutation.

## 5. Observability
Use structured, journal-compatible logs with stable component names, severity, event/category, correlation/request ID, operation ID, duration, and sanitized error code. Do not log credentials, tokens, clipboard contents, screenshots, full private file contents, or model prompts by default. Audit records for sensitive operations are coordinated with AEGIS-06 and must distinguish requester, authorizer, executor, and result. Health endpoints/interfaces expose state and version, not secrets.

## 6. Proposed integration sequence
1. Freeze ownership and versioned contracts with impacted agents.
2. Implement schema validation and mock adapters before privileged/mutating operations.
3. Deliver read-only discovery capabilities first.
4. Add a narrow safe local tool slice with AEGIS authorization and postcondition verification.
5. Integrate desktop progress/status without making the desktop depend on AI.
6. Add broader device/system tools only after contract and failure tests exist.

## 7. Open decisions
- Final D-Bus names, object paths, interface names and bus activation strategy require ATLAS-01 and AEGIS-06 review.
- Exact tool schema serialization and task event names require TUSKER-04 agreement.
- Authorization request/decision and audit fields require AEGIS-06 agreement.
- User-session KDE API choices require NOVA-02/ATLAS-01 compatibility review.
- Extension capability projection requires FORGE-09/AEGIS-06 review.
- Remote-origin identity propagation requires PILOT-08/TUSKER-04/AEGIS-06 review.

No proposed name in this document is a frozen cross-agent contract until the relevant owners acknowledge it and it is recorded in the shared decision log.


## 8. Confirmed base-system constraints from ATLAS-01 review
The ATLAS-01 provisional base contract on `01-fedora-base` confirms the following constraints, accepted by NEXUS-07 for integration planning: Tusker is not a dependency of boot, login, NetworkManager, systemd-logind or KDE startup; AI and remote services are optional/off by default; every Tusker service must be independently disableable and package-removable; OS health and Tusker health remain distinct; recovery must work without Tusker/model/remote services. ATLAS-01 owns Fedora packaging/build inputs, NOVA-02 owns Plasma/session integration, NEXUS-07 owns capability discovery and hardware-facing API identifiers, and AEGIS-06 owns Polkit identifiers and authorization policy. These are coordination constraints, not a claim that the entire base contract has final approval.

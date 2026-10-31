# NEXUS-07 Capability and Permission Inventory

**Task:** NEXUS-07-SI-001  
**Status:** Inventory proposal; not a frozen cross-agent contract  
**Branch:** `agent/07-system-integration`  
**Baseline:** `8bf66079f9e021244eda432fa8455e83b59e2165`

## Evidence boundary

The repository currently contains architecture, service-identifier proposals, tool schemas, fixtures and contract tests. It does not contain a D-Bus adapter runtime, production tool broker, AEGIS authorization client, or live system-tool service. The services below are therefore candidate integration targets, not verified TuskerOS-supported runtime capabilities.

The existing `SERVICE_IDENTIFIERS.md` namespace is explicitly provisional. Do not install activation files, claim a stable D-Bus API, or publish Polkit identifiers from this inventory.

## Candidate service inventory

| System service / API | Candidate NEXUS capability | Allowed initial scope | Explicit exclusions / owner dependency |
|---|---|---|---|
| systemd `org.freedesktop.systemd1` | `system.services.read` | Bounded unit state and service health metadata | Start/stop/restart, unit-file mutation, arbitrary unit properties; ATLAS packaging and AEGIS broker review |
| NetworkManager `org.freedesktop.NetworkManager` | `network.status.read` | Connectivity state and sanitized device/connection status | Connect/disconnect, profile edits, secrets, credentials and disruptive network changes; ATLAS/AEGIS review |
| UPower `org.freedesktop.UPower` | `power.status.read` | Battery and power-device state with bounded properties | Suspend, hibernate, power-off, charge-limit writes; NOVA/ATLAS/AEGIS review |
| BlueZ `org.bluez` | `bluetooth.status.read` | Adapter availability and sanitized device state | Pair, trust, connect/disconnect, remove device, raw stable device identifiers; ATLAS/AEGIS review |
| XDG Desktop Portal `org.freedesktop.portal.Desktop` (session bus) | `desktop.portal.request` | User-mediated portal requests only, after NOVA session integration | No direct screenshot, clipboard, arbitrary file access or session-bus privilege escalation; NOVA owns desktop/session integration |
| DNF5 / package-management APIs | No NEXUS-owned package mutation capability in this phase | Read-only package facts only if ATLAS exposes a supported API | Install/update/remove and repository mutation belong to ATLAS/FORGE and must use AEGIS authorization |
| systemd-logind `org.freedesktop.login1` | Not enabled in initial inventory | No session enumeration in MVP | Session/user identity data is privacy-sensitive; require a reviewed use case and NOVA/AEGIS approval |

No generic shell, arbitrary command execution, generic file read/write, raw process command-line, or unrestricted root operation is an accepted capability.

## Capability-to-permission mapping proposal

AEGIS owns the authoritative operation registry, risk classification, policy rules, principal binding and authorization decision. The following table maps NEXUS capability intent to a *required AEGIS policy preflight class*; it does not assign AEGIS action IDs or define a broker wire format.

| Capability family | Initial permission class | AEGIS preflight | Approval expectation | Runtime state |
|---|---|---|---|---|
| `system.info.read`, `system.services.read` | Read-only | Required for every registered action | Policy decision; no automatic grant inferred from read-only label | Not implemented |
| `network.status.read`, `power.status.read`, `bluetooth.status.read` | Read-only | Required for every registered action | Policy decision; no automatic grant inferred from availability | Not implemented |
| `desktop.portal.request` | User-mediated / privacy-sensitive | Required; portal's own consent is an additional boundary, not a substitute for AEGIS | Explicit user interaction as required by the portal and AEGIS policy | Not implemented |
| Network configuration, service control, Bluetooth pairing/control | Mutating / elevated | Mandatory AEGIS preflight and broker consumption before provider dispatch | Explicit approval when policy requires it; fail closed otherwise | Disabled |
| Package install/update/remove | Privileged / potentially destructive | AEGIS authorization plus ATLAS/FORGE transaction contract | Explicit approval for sensitive/destructive changes | Out of NEXUS direct execution scope |
| Clipboard, screenshots, broad file access | Privacy-sensitive | AEGIS preflight and separately reviewed consent/data handling | Explicit user consent; deny by default | Not enabled |

**Important:** read-only is not synonymous with authorization-free. The current NEXUS authorization-boundary note records TUSKER-04's requirement that AEGIS policy evaluate every registered action, including reads.

## Mandatory enforcement invariants

1. Capability availability is discovery metadata, never permission.
2. Caller-supplied component/instance strings are routing metadata, never authenticated identity.
3. No operation is dispatched based on descriptor risk, a logged-in session, previous approval, or a caller-supplied authorization field.
4. Every registered action must obtain a current AEGIS decision through the owner-approved trusted path before provider execution.
5. DENY, REQUIRE_APPROVAL, missing/invalid/stale authority, identity failure, registry failure, audit failure or broker unavailability must result in zero provider calls for the protected operation.
6. Mutations require durable idempotency and reconciliation. A timeout after possible side effects is unknown outcome, not safe failure or cancellation.
7. Service adapters expose typed, bounded properties only; no raw command output or unrestricted D-Bus proxy.
8. User-session portals remain separate from system-bus privilege boundaries.

## Approval and implementation gates

- **Chief Architect:** approve the NEXUS capability taxonomy and the cross-layer authorization boundary before publishing or freezing shared interfaces.
- **AEGIS-06:** freeze the trusted identity, policy preflight, fresh authorization reference, atomic consume, registry provenance, audit and typed outcome contract. The AEGIS broker contract reviewed on its branch is marked draft and says NEXUS implementation acceptance is pending.
- **TUSKER-04:** approve the invocation/result/cancellation and unknown-outcome integration semantics.
- **ATLAS-01:** confirm supported Fedora release, D-Bus libraries, service activation, systemd packaging, dependency versions and supported upstream service APIs.
- **NOVA-02:** approve any session-bus or portal-facing integration.
- **NEXUS-07:** implement read-only adapters first, then the broker-gated tool dispatcher and disposable-environment integration tests after the above approvals.

## Current blockers

- No production AEGIS broker or live system-tool runtime is present in the verified mainline baseline.
- AEGIS's `BROKER_CONTRACT.md` and `BROKER_INTEGRATION_DECISIONS.md` are draft/proposed artifacts on the AEGIS workstream; the latter explicitly records no NEXUS acceptance.
- The public NEXUS invocation schema currently permits an arbitrary top-level `authorization_context` object. AEGIS's cross-branch review says this is a caller-reachable authority-shaped field and requests removal plus negative tests. Changing this schema is a shared-contract change and is gated on Chief Architect approval.
- No D-Bus service API, runtime dependency, activation name or Polkit action is frozen for TuskerOS.

Until the approval gates close, this inventory is a design/evidence artifact only. No privileged or user-sensitive operation is enabled by it.

# NEXUS-07 System Service and D-Bus Identifier Proposal
**Owner:** NEXUS-07 · **Status:** Proposed for review, not frozen · **Revision:** 0.1

## Naming caveat
The identifiers below are a consistent candidate namespace for cross-agent review. They are not registered or approved identifiers. Before implementation, the TuskerOS project must confirm it controls/uses the `tuskeros.org` reverse-DNS namespace (or select its actual controlled domain) and AEGIS-06 must approve the privilege boundary. Do not ship activation files or Polkit policy using these names before that confirmation.

## Proposed NEXUS read-only system capability API
| Item | Proposed value |
|---|---|
| D-Bus bus | System bus |
| Well-known name | `org.tuskeros.SystemTools1` |
| Object path | `/org/tuskeros/SystemTools1` |
| Manager interface | `org.tuskeros.SystemTools1.Manager` |
| API major version | `1` |
| Activation | On-demand D-Bus/systemd activation, only if a separate process is justified |
| Default enablement | Not a boot/login requirement; package removable and service disableable |
| Privilege | Unprivileged service account; read-only discovery by default |

### Candidate methods
- `GetCapabilities()`: return supported capability identifiers and per-capability availability.
- `GetDeviceInventory()`: return sanitized device identity/class and capability metadata; omit serials and other stable personal identifiers by default.
- `GetSystemSnapshot()`: return bounded OS/kernel/architecture and selected resource facts, not raw command output.
- `GetHealth()`: return provider state/version and dependency availability.

### Candidate signals
- `CapabilitiesChanged`: capability catalogue changed.
- `DeviceInventoryChanged`: hardware inventory changed; consumers should re-read authoritative state.

Long-running work is not exposed as synchronous methods. No generic ExecuteCommand, arbitrary file read, privileged mutation, or raw process-command-line method is part of this interface.

## User-session boundary
NOVA-02 owns KDE/Plasma session integration. If a separate per-user Tusker API is justified, it must use a separately reviewed session-bus name and must not duplicate desktop portals or KDE APIs. No session-bus name is proposed here.

## Privileged operation boundary
NEXUS does not define Polkit action IDs or an elevated generic D-Bus method. AEGIS-06 owns those identifiers and semantics. NEXUS tool adapters must call the AEGIS-approved authorization path before privileged mutations; missing/invalid authorization fails closed.

## Service lifecycle assumptions
- No hard dependency from boot, display-manager, NetworkManager, systemd-logind or KDE session targets.
- Prefer direct library calls or existing system services where possible; do not create a resident daemon solely to wrap one-shot reads.
- If a daemon is needed for shared hardware discovery, use D-Bus activation and a narrow unprivileged service account.
- Restart rate-limited; client calls bounded; health distinguishes starting/ready/degraded/failed.
- Service failure means capability unavailable, not OS failure. Recovery must not depend on this service.

## Review requested
- ATLAS-01: validate Fedora/systemd/D-Bus activation and packaging assumptions.
- AEGIS-06: validate system-bus read-only scope, service account and authorization boundary.
- NOVA-02: confirm no duplicate Plasma/session service and identify any session-facing needs.
- Project owner: confirm controlled reverse-DNS namespace before freezing names.

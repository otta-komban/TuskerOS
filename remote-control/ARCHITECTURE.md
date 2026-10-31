# PILOT-08 — Remote Control Architecture & Phase Plan

**Status:** P0 discovery baseline / P1 proposal (not yet approved by dependent owners)  
**Owner:** PILOT-08  
**Branch:** `08-remote-control`  
**Last updated:** 2026-10-31

## 1. Scope and ownership

Owned paths: `remote-control/`, pairing/session services, remote dashboard/API, remote protocol tests and documentation.

PILOT-08 owns remote device trust, transport/API boundary, remote session lifecycle, remote task visibility/control, connection health, remote-specific audit context and documentation. It does not own system authorization policy, privileged execution, task orchestration, or desktop approval UI.

## 2. Product requirements

- Pair a second device with explicit local-user consent.
- Authenticate every request and bind it to a registered device and revocable session.
- View device/connection health and task list/status/progress.
- Submit tasks only through TUSKER-04's approved task interface.
- Pause, resume or cancel only where TUSKER-04 exposes those operations and AEGIS-06 authorizes them.
- Present approval requests and relay an explicit approve/deny response only where AEGIS-06 policy permits remote approval.
- Revoke one device immediately; support global remote-access disable and recovery after a lost device.
- Recover cleanly from network loss, service restart, expired credentials and clock/network changes.
- Work over private connectivity without requiring public exposure of administrative services.
- Keep remote desktop out of MVP; evaluate it as a separately permissioned future capability.

## 3. Trust boundaries and components

1. **Remote client:** untrusted until pairing; stores its device private key in the platform secure credential store where available.
2. **Transport edge:** TLS termination, strict origin/host validation, request-size limits, rate limits and protocol version negotiation.
3. **Pairing/device registry:** local-user-authorized enrollment, device public-key identity, device label, created/last-seen timestamps and revocation status.
4. **Session service:** opaque high-entropy session credentials, server-side hashed storage, bounded lifetime, rotation, idle expiry and revocation.
5. **Remote API/event gateway:** validates device/session on every request; emits only authorized task/event projections.
6. **AEGIS-06 policy service:** authoritative allow/deny/approval decision. Gateway checks are not a substitute for policy.
7. **TUSKER-04 task service:** authoritative task lifecycle and task operations.
8. **Audit sink:** structured security events with actor device, session identifier, action, decision, timestamp and correlation ID; never log credentials or private task content by default.

No remote request may call NEXUS-07 tools or a privileged broker directly. The path is remote gateway → AEGIS-06 authorization → TUSKER-04 task contract → normal local execution/policy path.

## 4. Proposed protocol and API contract (P1 draft)

All routes are versioned under `/api/v1`. JSON requests/responses use explicit schemas and bounded sizes. Mutating requests require an idempotency key where retries could duplicate work.

### Pairing lifecycle

- `POST /api/v1/pairing/challenges` — local authenticated UI creates a short-lived, single-use challenge; display as QR/code.
- `POST /api/v1/pairing/complete` — remote device submits challenge proof and device public key; requires local confirmation on TuskerOS before enrollment.
- `GET /api/v1/devices` — list enrolled devices (owner-only).
- `DELETE /api/v1/devices/{device_id}` — revoke a device and all its sessions.
- `POST /api/v1/devices/{device_id}/rotate-key` — controlled re-enrollment/key rotation, requiring local confirmation.

Challenge properties: cryptographically random, one-use, short expiry (proposal: 5 minutes), scoped to one device enrollment, stored hashed where practical, rate-limited, invalidated after success/expiry/revocation. QR payload contains no reusable long-lived bearer secret.

### Sessions

- `POST /api/v1/sessions` — authenticate a paired device using proof of possession; issue opaque high-entropy session credential.
- `POST /api/v1/sessions/rotate` — rotate credential with replay detection.
- `DELETE /api/v1/sessions/current` — revoke current session.
- `GET /api/v1/session` — return scopes, expiry and device identity (never return secret material).

Session token is stored hashed server-side; bound to device, scopes, issued/expiry times and revocation state. Proposed initial maximum lifetime: 12 hours with idle expiry at 30 minutes, subject to AEGIS review. Session renewal requires fresh proof of possession. Revocation must invalidate both HTTP and WebSocket access.

### Device and task APIs

- `GET /api/v1/device/status` — health summary and remote-connectivity state; no secrets or sensitive inventory.
- `GET /api/v1/tasks` — authorized task summaries with pagination.
- `GET /api/v1/tasks/{task_id}` — authorized task detail projection.
- `POST /api/v1/tasks` — submit a task to TUSKER-04; include idempotency key and request correlation ID.
- `POST /api/v1/tasks/{task_id}/pause`, `/resume`, `/cancel` — requested lifecycle operations, subject to task support and fresh AEGIS authorization.
- `GET /api/v1/approvals` — list pending approvals visible to this user/device.
- `POST /api/v1/approvals/{approval_id}/decision` — approve/deny with explicit decision, approval nonce/version and idempotency key; AEGIS-06 validates policy, binding, expiry and replay.
- `GET /api/v1/audit/events` — only a deliberately limited owner-facing audit view if approved by AEGIS; no unrestricted log file download.

### WebSocket

- `GET /api/v1/events` — authenticated WebSocket upgrade. Authenticate during handshake; validate Origin against configured trusted origins; enforce message size, heartbeat and connection limits.
- Event envelope: `version`, `event_id`, `sequence`, `occurred_at`, `type`, `resource_id`, `correlation_id`, `payload`.
- Event types: `connection.state`, `device.health`, `task.created`, `task.updated`, `task.progress`, `approval.requested`, `approval.resolved`, `session.revoked`.
- Event payloads are minimal projections; client must refetch authorized resource state after gaps or reconnect.
- No approval or privileged action is authorized merely because an event was received.

## 5. Authentication and pairing proposal

- Pairing starts from a locally authenticated TuskerOS session and requires a clear local confirmation of device name and requested scopes.
- Use asymmetric device identity (Ed25519 or a platform-supported equivalent after cryptographic-library review); remote client proves possession of its private key.
- Avoid inventing cryptography: use maintained libraries and documented primitives; no custom protocol crypto.
- Bind enrollment challenge to server identity, device public key, nonce, expiry and one-time state.
- Keep private keys in OS keyring/secure storage; fail closed if secure storage is unavailable unless user explicitly accepts a documented reduced-security mode.
- Session credentials are high entropy, short-lived, scoped and revocable; never place them in URLs, logs, QR images after enrollment, browser local storage or analytics.
- Require re-pairing or locally confirmed key rotation after suspected device compromise.
- Local physical/desktop owner can disable remote access and revoke all devices.

## 6. Threat model and mitigations

| Threat | Primary mitigation | Required verification |
|---|---|---|
| Stolen remote device | Device key proof, short sessions, remote revoke, optional local re-pair | Revoke device; existing HTTP/WS sessions stop |
| Unauthorized pairing | Local authenticated initiation and explicit confirmation; short one-use challenge | Expired/replayed/wrong challenge rejected |
| MITM / hostile Wi-Fi | TLS with server identity verification; no plaintext fallback | Invalid cert and downgrade tests fail closed |
| Session theft/hijack | Secure storage, no URL tokens, bounded expiry, rotation, device binding | Stolen/replayed token and cross-device use rejected |
| Replay of requests/approvals | Nonces, expiry, idempotency, approval version and one-time decision | Duplicate/replayed mutations rejected or safely deduplicated |
| CSRF / hostile web origin | Origin allowlist, secure cookie strategy if cookies used, CSRF defense; prefer explicit authorization header for native clients | Cross-origin browser requests rejected |
| Brute force / denial of service | Pairing/auth rate limits, bounded payloads, connection caps, backoff | Rate and resource limit tests |
| Credential/log leakage | Secret redaction, hashed token storage, no secret query params | Log/trace inspection |
| Privilege escalation | AEGIS-06 authoritative policy on every operation; no direct shell/broker route | Denied policy requests never reach task execution |
| Compromised remote client | Per-device scopes, least privilege, audit attribution, fast revoke | Scope escalation and revoked-device tests |
| WebSocket stale authorization | Revalidate session/revocation on connection and during lifetime; close on revoke/expiry | Active WS closes immediately on revoke |
| LAN exposure | Loopback-only default; explicit private-interface enablement and firewall guidance | Default listener address/port inspection |
| Task/event data disclosure | Per-user authorization and minimal projections | Cross-user/resource access negative tests |
| Clock skew/network interruption | Server-authoritative expiry, reconnect with re-authentication and event resync | Sleep/resume, clock skew and disconnect tests |

## 7. Network and deployment defaults

- Default listener binds to loopback only; remote access is unavailable until the owner explicitly enables a private-network mode.
- Do not bind to `0.0.0.0` by default; do not create router port-forwarding or UPnP rules.
- Private connectivity options to evaluate: user-managed WireGuard, existing trusted LAN with verified TLS, and user-managed private overlay networking. Do not require or silently install a VPN.
- Public relay/cloud tunnel is out of initial scope; any future relay requires separate privacy, threat and architecture review.
- Never expose model-runtime, systemd, SSH, D-Bus, Polkit or privileged broker ports as a shortcut.
- If service restarts, invalidate in-memory sessions unless durable revocation/session storage has been reviewed; clients must reauthenticate.
- Fail closed when TLS identity, authorization service, audit requirements or credential storage is unavailable.

## 8. Cross-agent dependencies and coordination

- **AEGIS-06:** mandatory approval of device identity trust, session claims/scopes, policy decision API, remote approval rules, audit identity, secret storage, listener/TLS posture, emergency disable and security tests. No privileged remote implementation before this boundary is agreed.
- **TUSKER-04:** task submit/status/event schema, pagination, task ownership, cancellation/pause/resume semantics, idempotency and reconnect/resync contract.
- **NEXUS-07:** no direct integration for MVP; remote requests must enter via TUSKER-04. Consult only if device health/status needs a supported read-only system API.
- **NOVA-02:** desktop pairing surface, connection state, device management, remote-session indicator and local approval UI integration.
- **NEXUS-07 / AEGIS-06:** confirm that remote operations cannot invoke tools outside the ordinary policy path.
- **PHOENIX-10 / ATLAS-01:** service packaging, firewall defaults, system service identity, secure storage dependencies and lifecycle integration.

Contract changes follow project rules: issue → impacted-owner acknowledgement → decision record/shared contract update → contract tests → reviewed PR. This document is a proposal, not evidence of agreement.

## 9. Risks and open decisions

1. Authentication primitive and supported platform key storage need implementation-time review.
2. Browser clients and native clients may require different credential transport strategies; avoid weakening either for convenience.
3. TLS certificate provisioning/trust UX for private networks is unresolved.
4. AEGIS-06 must define which approval classes can be remotely approved; default is remote approval disabled until explicit policy allows it.
5. Task ownership and user identity mapping must be defined by TUSKER-04.
6. Remote audit retention and content redaction must follow AEGIS-06 privacy policy.
7. LAN discovery is not required for MVP; if later added, it must not itself establish trust.
8. Remote desktop introduces screen privacy, input injection, session locking and consent risks; defer pending separate threat review.
9. No implementation stack is selected until repository conventions and shared contracts exist.

## 10. Granular execution checklist

### P0 — Discovery and requirements
- [x] Read master execution blueprint and PILOT-08 scope.
- [x] Verify repository, default branch and dedicated branch.
- [x] Inspect current branch contents and confirm implementation baseline.
- [x] Define supported remote user journeys.
  - [x] Pair a trusted laptop/device.
  - [x] Inspect device and connection status.
  - [x] Submit a task and monitor progress.
  - [x] Request pause/resume/cancel where supported.
  - [x] Review and respond to approvals only under policy.
  - [x] Revoke a device and recover from device loss.
- [x] Enumerate remote threat scenarios and initial mitigations.
- [x] Separate local-only, remote-eligible and deferred capabilities.
- [x] Compare HTTPS/WebSocket and private-network deployment options at architecture level.
- [x] Document requirements, acceptance criteria, dependencies and risks.
- [ ] Obtain AEGIS-06 review of threat assumptions and security boundary.
- [x] Obtain TUSKER-04 review of task lifecycle and event needs (draft v0.1 received; final contract agreement remains pending).
- [ ] Obtain NOVA-02 review of local pairing/status UX.
- [ ] Record unresolved decisions and P0 sign-off.

**P0 exit:** requirements and acceptance criteria reviewed; assumptions and blockers recorded.

### P1 — Architecture and contracts
- [x] Draft component boundaries and trust boundaries.
- [x] Draft device identity and pairing lifecycle.
- [x] Draft session expiry, rotation and revocation behavior.
- [x] Draft HTTPS routes and WebSocket event envelope.
- [x] Draft TLS, secret storage, replay, rate-limit, origin and binding requirements.
- [x] Draft AEGIS/TUSKER/NOVA dependency contracts.
- [ ] Agree device identity and pairing contract with AEGIS-06.
- [ ] Agree authorization/approval/audit contract with AEGIS-06.
- [ ] Agree task/event/idempotency contract with TUSKER-04.
- [ ] Agree desktop pairing/status integration with NOVA-02.
- [ ] Record ADRs and versioned schemas after owner review.
- [ ] Complete P1 architecture review.

**P1 exit:** interfaces agreed by dependent agents; ADRs recorded.

### P2 — Foundation
- [ ] Confirm implementation language/framework and repository conventions.
- [ ] Add remote service skeleton under owned path.
- [ ] Implement loopback-only listener and explicit opt-in network config.
- [ ] Implement device registry and secure key storage adapter.
- [ ] Implement local-consent pairing challenge and proof-of-possession.
- [ ] Implement session issue, expiry, rotation and revocation.
- [ ] Implement TLS and authenticated WebSocket foundation.
- [ ] Add structured redacted security logs and diagnostics.
- [ ] Add schema, build and authentication-negative tests.
- [ ] Verify no unauthenticated administrative endpoint exists.

### P3 — Working MVP
- [ ] Complete end-to-end pairing from local desktop to a second device.
- [ ] Authenticate a paired device and establish a revocable session.
- [ ] Show device/connection status.
- [ ] Submit one safe task through TUSKER-04 contract.
- [ ] Stream task progress/status with reconnect/resync.
- [ ] Demonstrate denial when AEGIS-06 rejects a remote action.
- [ ] Demonstrate device/session revocation.
- [ ] Capture VM/test-environment evidence and user walkthrough.

### P4 — Complete feature set
- [ ] Add robust device management and key rotation.
- [ ] Add task history, filters and bounded pagination.
- [ ] Add supported pause/resume/cancel operations.
- [ ] Add policy-approved remote approval workflow, disabled by default until approved.
- [ ] Add rate limits, connection limits and abuse diagnostics.
- [ ] Add sleep/resume, service restart and offline recovery behavior.
- [ ] Evaluate remote desktop separately; keep disabled unless separately approved.

### P5 — Integration
- [ ] Integrate AEGIS-06 authorization for every remote mutation and retry.
- [ ] Bind task ownership and remote actor identity to TUSKER-04.
- [ ] Integrate approval request/decision routing with AEGIS-06 and TUSKER-04.
- [ ] Integrate NOVA-02 local pairing, device management and connection indicators.
- [ ] Integrate packaging/service configuration with ATLAS-01/PHOENIX-10.
- [ ] Verify no alternate path to NEXUS-07 tools or privileged broker exists.

### P6 — Verification and hardening
- [ ] Test pairing success, invalid code, expiry, replay and concurrent enrollment.
- [ ] Test authentication failure, session expiry, rotation and revocation.
- [ ] Test revoked active WebSocket closure and stale-event handling.
- [ ] Test disconnect/reconnect, sleep/resume, restart and clock skew.
- [ ] Test AEGIS allow/deny, expired approval, duplicate approval and policy outage.
- [ ] Test TLS failure, origin validation, CSRF strategy and rate limits.
- [ ] Test credential redaction and absence of secrets in logs/URLs.
- [ ] Test default loopback binding and explicit private-network configuration.
- [ ] Run dependency/security review and resolve critical/high findings.
- [ ] Document VM versus physical-device coverage and residual risks.

### P7 — Release and handover
- [ ] Document pairing, device trust, session lifecycle and revocation.
- [ ] Document supported clients, API/event versioning and compatibility.
- [ ] Document private-network setup, firewall behavior and TLS troubleshooting.
- [ ] Document lost-device response and emergency remote-access disable.
- [ ] Publish API schemas, examples and diagnostics.
- [ ] Publish security test report and known limitations.
- [ ] Complete release report and handover.

## 11. Phase 1 execution plan

1. Get AEGIS-06's threat-model, identity, policy, approval and audit requirements before privileged implementation.
2. Get TUSKER-04's task/event contract and lifecycle semantics.
3. Get NOVA-02's local pairing UX and connection-state integration requirements.
4. Convert agreed interfaces into versioned schemas and ADRs.
5. Only then implement the smallest vertical slice: local-consent pairing → authenticated session → task status → revocation.
6. Add automated negative tests before expanding mutating operations.

## 12. Current status

P0 documentation baseline is drafted and repository intake is complete. A TUSKER-04 draft v0.1 task-boundary response has been captured in `remote-control/contracts/v1/TUSKER-04-TASK-CONTRACT-REVIEW.md`; AEGIS-06 and NOVA-02 reviews remain outstanding, so P0 sign-off is open. P1 is a proposal only and task/event semantics still require owner agreement. No runtime code, tests, pairing flow or security approval is claimed complete.

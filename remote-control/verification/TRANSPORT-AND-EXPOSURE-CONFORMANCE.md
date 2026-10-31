# PILOT-08 Transport & Exposure-Boundary Conformance Specification

**Status:** Implementation-neutral conformance proposal; not a runtime implementation or release approval.
**Owner:** PILOT-08
**Branch:** `agent/08-remote-control`
**Task:** `PILOT-08-P08-04`
**Baseline:** `8bf66079f9e021244eda432fa8455e83b59e2165`
**Security source:** AEGIS-06 `security/REMOTE_DEVICE_SECURITY_CONTRACT.md`, branch `06-security-gatekeeper`, blob `d72feb9d78c81da769c8bca009b721b69bf8032c`
**Disposition:** NO-GO for listeners, routes, WSS, or deployment changes until repository reauthorization and dependent contracts close.

## 1. Purpose and scope

This document converts AEGIS-06 DEC-AEG-007 and the transport/deployment section of its accepted contract into conformance tests and evidence requirements for PILOT-08. It also records the exact bounds that are already fixed by AEGIS, and separates them from rate-limit tuning that remains unspecified.

This is not an OpenAPI contract, deployment guide, TLS library selection, port assignment, certificate-provisioning design, UI decision, or authorization to expose a listener. Loopback-only remains the default. Private-network binding remains an explicit local owner opt-in.

## 2. Binding transport profile

| Area | Accepted requirement |
|---|---|
| Non-loopback transport | TLS required; TLS 1.2 minimum, TLS 1.3 preferred |
| Server certificate | Validate configured certificate chain or explicit owner-pinned certificate fingerprint |
| Verification bypass | No skip-verification option and no plaintext fallback |
| Default bind | Loopback only |
| Private network | Requires explicit local owner opt-in and visible status indicator |
| Public exposure | No public listener, relay, UPnP, router port-forwarding, or cloud tunnel by default |
| Host | Validate Host against configured local endpoint |
| Browser Origin | Exact configured allowlist; no wildcard or suffix matching; missing Origin is not authentication |
| HTTP request body | Maximum 1 MiB |
| Task submission body | Maximum 16 KiB |
| WebSocket frame | Maximum 64 KiB |
| WebSocket connections | Maximum 5 per device |
| Event transport | WSS only; authenticated device-bound handshake; server-to-client only in MVP |
| Rate limiting | Per-device and per-source limits for pairing, authentication, and API routes; exact numeric rates/windows remain unspecified |
| Secret handling | No credentials in URLs; redact Authorization, Signature, cookies, pairing material and private task data |
| VPN/private overlay | Reachability only; never identity, authentication or authorization |

## 3. Exposure and transport invariants

1. Service startup without an explicit remote-network setting binds only to loopback addresses.
2. A private-network listener cannot be enabled by a remote request, environment inherited from an untrusted client, or silent auto-discovery.
3. Any private-network opt-in must be performed locally by an authenticated owner and produce visible status; disabling it returns the listener to loopback-only mode.
4. Any non-loopback connection uses TLS and validates the server identity. Invalid, expired, untrusted or mismatched certificates fail closed.
5. A pinned certificate is an explicit owner-established trust decision; the client must not silently accept a changed fingerprint.
6. Host validation is independent of Origin validation. Neither is a substitute for device proof or AEGIS authorization.
7. Browser Origin matching is exact and scheme/host/port sensitive. Wildcard, suffix, substring and implicit localhost trust are prohibited.
8. Request, frame and connection limits are enforced before expensive parsing, policy evaluation, or task dispatch.
9. WebSocket is an authenticated, server-to-client event channel only. Client task mutations and approval decisions use separately authorized HTTPS routes; approvals remain local-only for MVP.
10. Rate limiting must be applied per device and per source without using source IP as identity. Rate-limit responses must not enumerate registered owners/devices.
11. TLS termination, access logs, reverse proxies and diagnostics must not leak Authorization, Signature, cookies, pairing challenge material or private task data.
12. VPN reachability never bypasses TLS, device-key proof, session validation, exact Origin/Host checks, or AEGIS policy.

## 4. Conformance test matrix

The cases below are specified, not implemented or executed. Use isolated loopback and private-network test fixtures, synthetic certificates, synthetic devices, and instrumented handlers.

| Test ID | Condition / attack | Required result |
|---|---|---|
| NET-C01 | Start service with default configuration | Listener binds loopback only |
| NET-C02 | Attempt non-loopback bind without local owner opt-in | Startup/configuration rejects or remains loopback-only |
| NET-C03 | Remote client attempts to enable private-network exposure | Reject; no listener configuration change |
| NET-C04 | Owner explicitly enables private-network mode locally | Mode changes only after explicit local action and visible status is emitted |
| NET-C05 | Owner disables private-network mode | Non-loopback listener closes; loopback-only state restored |
| NET-C06 | Non-loopback HTTP/plaintext request | No plaintext service response; reject/connection failure |
| NET-C07 | TLS 1.0 or TLS 1.1 client negotiation | Reject |
| NET-C08 | TLS 1.2 valid certificate chain | Handshake permitted, subject to device authentication |
| NET-C09 | TLS 1.3 valid certificate chain | Handshake permitted, subject to device authentication |
| NET-C10 | Untrusted, expired, malformed or hostname-mismatched certificate | Reject before HTTP handler |
| NET-C11 | Owner-pinned certificate fingerprint matches | Handshake permitted |
| NET-C12 | Pinned certificate changes unexpectedly | Reject; no silent pin replacement |
| NET-C13 | Client requests insecure certificate-verification bypass | No such mode; reject/ignore configuration and preserve validation |
| NET-C14 | Host header differs from configured local endpoint | Reject before route handler |
| NET-C15 | Duplicate/ambiguous Host headers or malformed authority | Reject before route handler |
| NET-C16 | Exact configured browser Origin | Passes Origin gate only; device proof and policy remain mandatory |
| NET-C17 | Origin differs by scheme, hostname, port or trailing authority | Reject |
| NET-C18 | Origin is a suffix/substring lookalike or wildcard match | Reject |
| NET-C19 | Browser request omits Origin | Reject browser-origin request; missing Origin is not trusted |
| NET-C20 | Native client has no browser Origin | Native-client policy may omit browser Origin only under explicit client-type handling; still requires Host and device proof; never treat absence as identity |
| NET-C21 | HTTP body is exactly 1 MiB | Accepted by size gate if route schema permits |
| NET-C22 | HTTP body exceeds 1 MiB | Reject before expensive parsing/policy/dispatch |
| NET-C23 | Task submission body is exactly 16 KiB | Accepted by size gate if schema permits |
| NET-C24 | Task submission body exceeds 16 KiB but is below 1 MiB | Reject specifically at task submission limit |
| NET-C25 | WebSocket frame is exactly 64 KiB | Accepted by frame-size gate if message schema permits |
| NET-C26 | WebSocket frame exceeds 64 KiB | Reject/close; no event handler side effect |
| NET-C27 | Sixth concurrent WSS connection for one device | Reject or close excess connection; maximum remains 5 |
| NET-C28 | Multiple devices each open up to 5 WSS connections | Per-device bound enforced independently; global resource cap remains separately bounded |
| NET-C29 | Pairing/auth/API flood from one source | Per-source limiter bounds work and returns bounded generic response |
| NET-C30 | One device floods pairing/auth/API routes across multiple source addresses | Per-device limiter remains effective |
| NET-C31 | Source address changes while device identity remains the same | Device-specific limits and authorization remain bound to device, not IP |
| NET-C32 | VPN peer is present but device proof is absent/invalid | Reject; VPN membership grants no identity |
| NET-C33 | VPN peer and valid device proof exist but AEGIS denies action | No protected handler/Core dispatch |
| NET-C34 | Client submits task mutation over WSS | Reject; no task mutation |
| NET-C35 | Client submits approval decision over WSS or HTTPS remote API | No remote approval capability; no grant or state transition |
| NET-C36 | Credential appears in URL path/query or redirect Location | Reject unsafe route/redirect behavior; no credential reflected |
| NET-C37 | Authorization/Signature/cookie headers are captured in access logs | Fail redaction test; secret values must be absent |
| NET-C38 | Pairing challenge, QR payload or private task body appears in diagnostics | Fail redaction test; sensitive payload must be absent |
| NET-C39 | Reverse proxy forwards untrusted Host/Origin or downgrades TLS | Gateway rejects; trusted endpoint metadata is not inferred from client-controlled forwarding headers |
| NET-C40 | Connection flood / slow handshake / oversized headers | Bounded resource use; service remains responsive to local owner controls |
| NET-C41 | Service restarts after private-network opt-in | Exposure state follows the explicitly approved persistence policy; no silent exposure expansion |
| NET-C42 | Rate-limit store or policy dependency unavailable | Fail closed for protected operations; no unbounded fallback or bypass |

### Rate-limit tuning is deliberately not invented

AEGIS requires per-device and per-source rate limits for pairing, authentication and API routes, but does not specify requests-per-second, burst size, penalty duration, or shared-bucket persistence. PILOT must not choose production numeric values unilaterally. The implementation design must propose route-class-specific limits with measured resource budgets and obtain AEGIS review before code or tests assert exact numeric thresholds.

Likewise, test cases NET-C28, NET-C40 and NET-C41 require global resource bounds and restart behavior to be specified by the implementation/deployment design; this document does not invent those values or persistence semantics.

## 5. Test evidence requirements

For each test capture:
- build/commit and test-run identifier;
- configured bind address and observed listening sockets;
- negotiated TLS version, certificate-chain result or pin match (never private key material);
- normalized Host and Origin validation outcome;
- observed body/frame size and enforcement point;
- per-device/per-source rate-limit bucket outcome using synthetic identifiers;
- concurrent connection counts and close/reject timestamps;
- protected route, Core dispatch and executor counters;
- audit event IDs and redaction scan results.

For negative tests, assert zero protected-handler/Core/executor calls where rejection is required. A unit test of a parser alone is not end-to-end evidence of listener exposure or TLS behavior.

## 6. Cross-agent ownership and blockers

| Area | Owner | Current state | Closure needed |
|---|---|---|---|
| Security transport profile | AEGIS-06 | DEC-AEG-007 ACCEPT | Requirements frozen; implementation conformance still unproven |
| Listener status and opt-in UX | NOVA-02 | DEC-NOV-003 unresolved | Owner-approved local opt-in, visible status, disable/re-enable behavior |
| TLS deployment, service account, permissions, SELinux | ATLAS-01 | Not verified in this task | Deployment design and host-hardening review |
| API/session/authentication implementation | PILOT-08 | Runtime blocked | Reauthorization gate and test harness |
| Task route and event projection | TUSKER-04 | DEC-TUS-001..004,006..007 remain REVISE/draft | Final versioned Core contract |
| Final broker consume and authorization context | NEXUS-07 / AEGIS-06 / Chief Architect | Unresolved | Approved trusted context and atomic consume/dispatch contract |
| Repository authorization | Admin/coordinator | PR #49 gate not independently verified | Verify required checks and branch-protection state; coordinator authorization |

## 7. Explicit exclusions

This document does not authorize:
- adding or exposing an HTTP/WSS listener;
- private-network binding, firewall changes, UPnP, port-forwarding, public relay or cloud tunnel;
- selecting production rate-limit numbers without AEGIS review;
- changing the stale architecture draft's bearer/session model;
- direct task execution, direct NEXUS or broker calls;
- remote approvals, remote pause/resume, remote shell or remote desktop;
- weakening certificate validation, Origin/Host validation, request limits or redaction.

## 8. Acceptance status

**Specified:** 42 transport/exposure conformance cases.
**Executed:** 0 PILOT-08 runtime tests.
**Runtime features established:** 0.
**Release disposition:** NO-GO.

Before implementation, require repository reauthorization, NOVA-02 local exposure/status UX decisions, ATLAS-01 deployment review, final TUSKER Core contract, and the Chief Architect-approved AEGIS/NEXUS consume boundary. AEGIS acceptance of the transport profile is not evidence that the transport service exists or has passed conformance.

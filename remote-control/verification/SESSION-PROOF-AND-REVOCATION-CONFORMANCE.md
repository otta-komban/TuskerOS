# PILOT-08 Session Proof & Revocation Conformance Specification

**Status:** Implementation-neutral conformance proposal; not a frozen wire schema, implementation, or security acceptance.
**Owner:** PILOT-08
**Branch:** `agent/08-remote-control`
**Task:** `PILOT-08-P08-03`
**Baseline:** `8bf66079f9e021244eda432fa8455e83b59e2165`
**Security source:** AEGIS-06 `security/REMOTE_DEVICE_SECURITY_CONTRACT.md`, branch `06-security-gatekeeper`, blob `d72feb9d78c81da769c8bca009b721b69bf8032c`
**Disposition:** NO-GO for session runtime, HTTP middleware, WSS, or protected routes until repository and cross-agent gates close.

## 1. Purpose and boundary

This document translates AEGIS-06 DEC-AEG-003..005 and the relevant WSS requirements into observable conformance cases. It assumes a device has already been enrolled under the separately reviewed pairing ceremony. It does not define a new token format, signature library, database, HTTP framework, endpoint path, or broker API.

Authentication proves possession of a registered device key and a currently valid session. It does not itself authorize access. Every protected read and mutation must still pass AEGIS policy using trusted server-derived context. Task operations continue through TUSKER Core; PILOT must not call NEXUS providers or a privileged broker directly.

## 2. Binding session requirements

| Control | Accepted AEGIS requirement |
|---|---|
| Session secret | Opaque 32-byte / 256-bit random secret |
| Server persistence | Store only a cryptographic hash of the session secret |
| Binding | Device, registered public-key thumbprint, local owner principal, creation time, last activity, absolute expiry, revocation state |
| Absolute expiry | 8 hours from creation |
| Idle expiry | 15 minutes without activity; whichever expiry occurs first |
| Renewal | No refresh token. Renewal requires a fresh signed device-authentication challenge and a new session record |
| Request proof | RFC 9421 HTTP Message Signature made by registered Ed25519 key on every HTTP request |
| Covered components | `@method`, `@target-uri`, `authorization`, and `content-digest` (RFC 9530) |
| Signature parameters | `created`, `expires`, `nonce`, `keyid`, `alg=ed25519` |
| Signature lifetime | No more than 60 seconds |
| Timestamp skew | Server rejects request timestamps outside ±60 seconds |
| Nonce | Fresh unpredictable nonce of at least 128 bits per request |
| Replay cache | Unique per device; retain nonce for at least 2 minutes |
| WebSocket | WSS, server-to-client only for MVP; handshake uses same device-bound proof |
| Revocation | Durable state commit before success; new requests fail immediately; active WSS closes within 1 second |
| In-flight mutation | Revalidate before broker consume/dispatch; if already dispatched and uncertain, reconcile UNKNOWN; never blindly retry |

A bearer secret, source IP, VPN peer, cookie, user-agent, or public device identifier alone is never sufficient authentication.

## 3. Request verification order

This is a security ordering requirement, not a prescribed internal class design:

1. Parse request under strict size/header limits; reject ambiguous or malformed signature metadata.
2. Resolve the key ID only against the server-side enrolled-device registry.
3. Verify Ed25519 signature over the exact RFC 9421 covered components.
4. Verify `Content-Digest` against the received body, including the digest of the empty body when there is no body.
5. Validate signature creation/expiry bounds and ±60-second server timestamp skew.
6. Atomically reserve the nonce in the per-device replay cache; duplicate nonce fails before routing.
7. Resolve the opaque session secret by constant-time-safe hash comparison; validate device/key/owner binding, absolute expiry, idle expiry, and revocation/global-disable state.
8. Derive trusted principal, origin, device/session bindings and resource context from server-side records.
9. Invoke AEGIS for the protected read or mutation. Authentication success is not an ALLOW decision.
10. For a mutation, require a fresh policy decision and revalidation at the authoritative broker consume boundary. If consume semantics are unavailable or unresolved, do not dispatch.

A request rejected at steps 1–7 must not reach a protected handler or Core. A request rejected by AEGIS must not cause a Core mutation or executor/handler call. The exact atomic nonce/session lookup transaction and cache-failure behavior require implementation design review; any inability to prove uniqueness or current revocation state fails closed.

## 4. Conformance test matrix

These cases are specified, not implemented or executed. Tests use synthetic devices, secrets, timestamps, requests, and task fixtures.

| Test ID | Condition / attack | Required result |
|---|---|---|
| SESS-C01 | Valid enrolled device, valid opaque session, correct signature | Authentication succeeds; protected route still invokes AEGIS |
| SESS-C02 | Session secret has incorrect length/entropy or is not opaque random | Session issuance rejects; no usable session |
| SESS-C03 | Inspect session persistence | Only cryptographic hash stored; raw session secret absent |
| SESS-C04 | Session secret presented with another device key | Reject binding mismatch before route |
| SESS-C05 | Unknown key ID | Reject before route; no key enumeration detail |
| SESS-C06 | Valid key ID with invalid Ed25519 signature | Reject before route |
| SESS-C07 | Signature omits `@method` coverage | Reject |
| SESS-C08 | Signature omits `@target-uri` coverage or is replayed to another URI | Reject |
| SESS-C09 | Signature omits Authorization coverage or is paired with a different session secret | Reject |
| SESS-C10 | Signature omits Content-Digest coverage | Reject |
| SESS-C11 | Body modified after digest/signature generation | Reject digest/signature mismatch |
| SESS-C12 | Empty-body request lacks the required empty-body digest | Reject |
| SESS-C13 | Signature expiry exceeds 60 seconds | Reject |
| SESS-C14 | Signature timestamp is more than 60 seconds ahead/behind server time | Reject |
| SESS-C15 | Nonce is shorter than 128 bits or not freshly generated | Reject |
| SESS-C16 | Same nonce reused by same device on concurrent requests | At most one request reserves it; all duplicates reject before routing |
| SESS-C17 | Nonce replay attempted inside the 2-minute retention period | Reject |
| SESS-C18 | Replay cache unavailable, loses atomicity, or evicts before 2 minutes | Fail closed; no protected handler call |
| SESS-C19 | Request arrives at exactly absolute expiry boundary | Expired according to server-authoritative boundary rule; no protected data |
| SESS-C20 | Request arrives at exactly 15-minute idle boundary | Expired according to server-authoritative boundary rule; no protected data |
| SESS-C21 | Activity occurs near idle expiry but absolute expiry has passed | Absolute expiry wins; no extension |
| SESS-C22 | Client requests refresh-token or generic token rotation endpoint | No refresh token/rotation path; renewal requires fresh device-auth challenge and new session |
| SESS-C23 | Session is revoked before request validation | Reject immediately |
| SESS-C24 | Device revoked while multiple sessions exist | All sessions for that device become invalid |
| SESS-C25 | Global disable commits while request is starting | After durable commit, new request fails; no stale positive cache |
| SESS-C26 | Revocation store unavailable or stale state cannot be checked | Fail closed |
| SESS-C27 | Active WSS socket exists during session/device revocation | Socket closes within 1 second of durable commit |
| SESS-C28 | WSS handshake lacks valid request proof or exact allowed Origin | Upgrade rejected |
| SESS-C29 | Client sends task mutation or approval decision over WSS | No such client-to-server mutation channel; reject/close |
| SESS-C30 | WSS session expires or global disable occurs | Socket closes within 1 second; reconnect denied until valid new session |
| SESS-C31 | Revocation races with mutation before atomic broker consume | Final consume/revalidation fails; zero new handler dispatch |
| SESS-C32 | Revocation races after operation was already consumed/dispatched | Do not claim rollback; return/reconcile UNKNOWN and preserve execution identity |
| SESS-C33 | AEGIS returns DENY or REQUIRE_APPROVAL | No Core mutation and zero executor/handler calls |
| SESS-C34 | AEGIS timeout, malformed result, or unavailable dependency | Fail closed; zero Core mutation and zero executor/handler calls |
| SESS-C35 | Previously ALLOWed decision is replayed after session/device/resource/precondition change | Re-evaluate; stale decision cannot authorize |
| SESS-C36 | Retry uses same idempotency key after authorization-relevant state changes | Fresh policy evaluation; idempotency does not bypass authorization |
| SESS-C37 | Client submits principal, role, origin, device/session ID, policy result, or resource authority | Reject/ignore as untrusted; trusted context is server-derived |
| SESS-C38 | Logs/traces/crash reports inspected after success and failure | No raw session secret, private key, signature, nonce, Authorization header, or private task body |
| SESS-C39 | Service restarts with active sessions | Durable revocation/session policy is honored; if safe state cannot be established, reauthentication required |
| SESS-C40 | Disconnect occurs after consume/dispatch but before response | Explicit UNKNOWN and reconciliation reference; no blind retry |

### Test evidence required

For each test, retain:
- build/commit and test-run identity;
- synthetic device thumbprint and non-secret session binding digest;
- request method/target and covered-component validation result, with Authorization and secret material redacted;
- server-side expiry/revocation state and nonce-reservation outcome;
- AEGIS decision reference and policy/registry versions where applicable;
- Core dispatch, broker-consume, and executor counters;
- WSS close timestamp relative to durable revocation commit;
- audit event IDs and redaction assertions.

Negative authentication tests must assert zero protected-handler calls. Negative authorization tests must assert zero Core mutations and zero executor/handler calls. Do not treat a mocked policy result or schema-only validation as end-to-end evidence.

## 5. Cross-agent dependencies and unresolved semantics

| Dependency | Owner | Current disposition | PILOT action |
|---|---|---|---|
| Session lifetime, request signatures, nonce replay, WSS, revocation | AEGIS-06 | Accepted in security contract | Preserve exact values; obtain implementation/test evidence |
| Trusted principal and authorization decision | AEGIS-06 | Policy contract accepted; broker consume details need integration closure | Do not accept caller-provided authority |
| Task lifecycle and unknown-outcome reconciliation | TUSKER-04 | DEC-TUS-001..004,006..007 REVISE in draft v0.1 | No task mutation implementation until final contract |
| Atomic broker consume and dispatch identity | NEXUS-07 / AEGIS-06 / Chief Architect | Unresolved; shared schema change requires approval | No remote privileged invocation or consume API assumptions |
| Global disable/re-enable UX and visible state | NOVA-02 | DEC-NOV-003 unanswered | No UI/API behavior invented by PILOT |
| Repository implementation authorization | Admin/coordinator | PR #49 reauthorization evidence not independently verified | No runtime implementation |

## 6. Explicit exclusions

This proposal does not authorize:
- session/authentication middleware, session storage, nonce-cache, HTTP signature verifier, WSS server, or network listener implementation;
- refresh-token, session-rotation, or bearer-only fallback;
- remote approval (disabled for MVP);
- direct NEXUS provider or privileged broker access;
- bypassing AEGIS policy or TUSKER Core lifecycle;
- weakening TLS, Origin/Host checks, replay protections, revocation, or expiry.

## 7. Acceptance status

**Specified:** 40 session/request-proof/revocation conformance cases.
**Executed:** 0 PILOT-08 runtime tests.
**Runtime features established:** 0.
**Release disposition:** NO-GO.

Before implementation, require the repository reauthorization gate, finalized TUSKER Core contract, Chief Architect-approved NEXUS/AEGIS consume boundary, approved implementation design, and a reproducible test harness with zero-dispatch instrumentation. Security acceptance of AEGIS requirements is not evidence that PILOT runtime behavior exists.

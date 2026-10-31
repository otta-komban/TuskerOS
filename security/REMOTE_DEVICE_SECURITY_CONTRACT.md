# Remote Device and Session Security Contract

**Owner:** AEGIS-06  
**Version:** 0.1.0  
**Status:** AEGIS security-owner decision for PILOT-08 DEC-AEG-001 through DEC-AEG-008. This freezes the security requirements, not a runtime implementation or release approval.  
**Applies to:** PILOT-08 remote pairing, device authentication, sessions, HTTPS/WSS transport, AEGIS policy handoff and remote security audit.

## Decision summary

| PILOT decision | AEGIS disposition | Binding decision |
|---|---|---|
| DEC-AEG-001 — device identity | ACCEPT | Per-device Ed25519 key pair; private key generated on client and held only in OS-protected secure storage; server stores public key and SHA-256 thumbprint. No plaintext-file fallback. |
| DEC-AEG-002 — pairing ceremony | ACCEPT | Local authenticated owner initiates; 256-bit CSPRNG challenge, 5-minute expiry, one successful atomic consume, maximum 5 proof attempts; local owner verifies device label and a 10-hex-character transcript fingerprint before explicit confirmation. |
| DEC-AEG-003 — session credential | ACCEPT | Opaque 256-bit session secret, hash-only server storage, device-key proof on every HTTP request using RFC 9421 HTTP Message Signatures and RFC 9530 Content-Digest; 8-hour absolute lifetime, 15-minute idle timeout, no refresh token. |
| DEC-AEG-004 — authorization | ACCEPT | Every remote read and mutation is checked by the AEGIS policy authority; identity and origin are server-derived; deny/approval-required/service-unavailable never dispatches. |
| DEC-AEG-005 — revocation | ACCEPT | Durable revocation blocks new requests synchronously; active WSS sockets close within 1 second; in-flight operations are revalidated before consume/dispatch and uncertain post-dispatch outcomes are reconciled, never blindly retried. |
| DEC-AEG-006 — audit | ACCEPT | Remote policy events include device and session binding digests. Transport/pairing lifecycle events are separately typed and correlated; credentials and task content are not logged. |
| DEC-AEG-007 — transport | ACCEPT | TLS 1.2 minimum (TLS 1.3 preferred), validated certificate chain/pin, loopback-only default, explicit private-network opt-in, exact browser Origin allowlist, Host validation, bounded requests and no public relay/UPnP/port-forwarding by default. |
| DEC-AEG-008 — remote approval | DEFER / DISABLED FOR MVP | No remote approve/deny endpoint or remote approval UI action. All approval classes requiring a user decision remain local-only. |

## 1. Device identity and key lifecycle (DEC-AEG-001)

1. Each paired device MUST generate its own Ed25519 key pair. Keys MUST NOT be shared between devices or derived from a pairing code.
2. The private key MUST be non-exportable where the platform supports it and stored in the platform's OS-protected credential/key store. If secure storage is unavailable, remote pairing MUST remain disabled; plaintext file storage is not an accepted fallback.
3. The registry stores the public key, a stable device identifier, the SHA-256 public-key thumbprint, owner binding, display label, creation/last-seen metadata and revocation state. Device identity is the registered public-key thumbprint, not a caller-supplied device label, IP address, VPN peer name or user-agent.
4. A device proves possession by signing the fresh pairing transcript and, after enrollment, each authenticated HTTP request (Section 3). A public key or device identifier alone never authenticates a request.
5. Planned key rotation requires proof from the currently registered key plus fresh local owner confirmation. If the old key is lost, revoke the device and perform a new pairing ceremony; remote-only recovery is prohibited.
6. A device key is scoped to one local owner account. A remote device cannot select another local principal by submitting a principal/user identifier.

## 2. Pairing ceremony (DEC-AEG-002)

1. Pairing MUST be initiated from a locally authenticated owner session. An unpaired remote client cannot create a challenge or enroll itself.
2. The server generates a 32-byte CSPRNG challenge secret, stores only its cryptographic hash, binds it to the local owner and pairing transaction, and sets a 5-minute expiry. The QR/deep-link payload carries only this one-time enrollment challenge and the endpoint/certificate identity; it is not a reusable session credential.
3. The remote client generates its Ed25519 key locally and signs a domain-separated transcript containing the challenge identifier/secret, server identity and public-key thumbprint.
4. The client and local UI display the same 10-hex-character short authentication fingerprint derived from the transcript. The local UI shows the remote device label and fingerprint and requires an explicit owner confirmation. A mismatch means cancel; the user must not approve based on a device label alone.
5. The challenge is consumed with an atomic compare-and-set after valid proof and local confirmation. Expired, replayed, already-consumed or mismatched challenges fail. At most 5 proof attempts are accepted per challenge; on exhaustion, invalidate it and require a new local ceremony.
6. Rate-limit challenge creation and proof failures per owner and source. Do not reveal whether a device identifier or owner account exists in error responses.
7. Enrollment and cancellation are durable audit events. A failed, expired or cancelled challenge creates no device/session.

## 3. Session credential and request proof (DEC-AEG-003)

1. Following successful device proof, issue an opaque 32-byte (256-bit) session secret. Store only a cryptographic hash server-side. The session record binds the secret to device ID/public-key thumbprint, local owner principal, creation time, last activity, absolute expiry and revocation state.
2. A session expires after **8 hours absolute** or **15 minutes idle**, whichever occurs first. There is no refresh token. Renewal requires a new signed device-authentication challenge and a new session record. Server time is authoritative; request signature timestamps outside a ±60-second window are rejected.
3. Each HTTP request MUST carry the opaque session secret in the Authorization header and an RFC 9421 HTTP Message Signature made by the registered Ed25519 device key. The signature MUST cover `@method`, `@target-uri`, `authorization`, and `content-digest` (RFC 9530; include the digest of the empty body when there is no body). Signature parameters MUST include `created`, `expires`, `nonce`, `keyid` and `alg=ed25519`.
4. The signature lifetime MUST NOT exceed 60 seconds. The client generates a fresh unpredictable nonce of at least 128 bits per request; the server enforces uniqueness per device in a replay cache retained for at least 2 minutes. Reuse, stale timestamps, unknown key IDs, mismatched body digest, invalid signature, revoked device or invalid session is rejected before routing.
5. The server MUST validate the device signature and session binding on every request; a VPN peer, source IP, cookie alone or bearer token alone is insufficient. Credentials MUST NOT appear in URLs, query strings, QR codes after enrollment, logs or diagnostics.
6. The WebSocket event stream is server-to-client only for MVP. Its WSS handshake is authenticated with the same device-bound request proof. Clients cannot submit task mutations or approval decisions over WebSocket; those use separately authorized HTTPS routes. Browser handshakes require an exact configured Origin allowlist. A missing Origin is never treated as authentication.
7. WebSocket connections are bound to the authenticated session and device; expiry, device revocation, session revocation or global disable closes the socket within 1 second. The server rechecks authorization for each subscription and sensitive event projection.

## 4. Authoritative policy boundary (DEC-AEG-004)

Every remote route that reads owner/task/system information and every remote mutation MUST invoke the AEGIS policy authority. Authentication establishes who is calling; it does not grant access.

The trusted adapter supplies the following context out-of-band (not from client JSON):

- local owner `principal_ref` resolved from the paired-device record;
- `origin=remote`;
- registered `device_id` and `device_binding` digest;
- server-side `session_id` and `session_binding` digest;
- registered `action_id`, validated canonical arguments and resolved resource scope;
- task/step/proposal/correlation identifiers and idempotency key where applicable;
- trusted server timestamp, policy version, registry version and precondition snapshot.

The client MUST NOT set or override principal, origin, role, risk class, policy decision, resource authority, approval status, operation registry metadata or executor identity. A client-supplied task identifier is a correlation/reference value only and must be checked for owner visibility.

The AEGIS policy authority evaluates DENY / REQUIRE_APPROVAL / ALLOW. DENY is terminal for the request. REQUIRE_APPROVAL does not dispatch and cannot be converted to ALLOW by the remote adapter. ALLOW is short-lived (maximum 30 seconds for remote-origin operations), bound to the exact action digest, principal/device/session, operation, resources, policy/registry versions and preconditions, and must be revalidated at broker consume. Each retry is a new policy evaluation; idempotency reconciliation is not permission to reuse stale authorization.

The remote gateway MUST route task submissions and task controls through TUSKER-04's ordinary task lifecycle. It MUST NOT call NEXUS tools, Polkit, D-Bus, shell or a privileged broker directly. If policy, identity, registry, clock, Core or required audit is unavailable, return a typed fail-closed error and make zero new handler calls. If dispatch may already have occurred, return/reconcile UNKNOWN; never blindly retry a non-idempotent mutation.

Minimum HTTP mapping:
- 401: missing/invalid session or device proof;
- 403: policy DENY or local approval required (no execution);
- 409: replay or conflicting idempotency key;
- 503: policy/identity/registry/Core/audit dependency unavailable before dispatch;
- unknown post-dispatch result: explicit `unknown_outcome`, with reconciliation reference; not a retry instruction.

## 5. Revocation and race semantics (DEC-AEG-005)

1. Device revocation, current-session logout and global remote-access disable MUST commit to durable authoritative state before success is returned.
2. Revoking a device invalidates every session for that device. Global disable invalidates all remote sessions and prevents new pairing/session issuance until locally re-enabled. Re-enable never silently re-pairs a device.
3. New HTTP requests fail immediately after the revocation transaction commits. The server MUST NOT rely on a stale positive cache; if authoritative revocation state cannot be checked, fail closed.
4. Active WSS connections are terminated within 1 second of committed revocation/disable. Reconnect with a revoked device/session is rejected.
5. A mutation not yet atomically consumed by the broker MUST fail its final consume/revalidation after revocation. A mutation already consumed or dispatched is not assumed rolled back: record its execution/consumption identity, report UNKNOWN if the result cannot be confirmed, and reconcile against the idempotency key. No blind retry.
6. In-flight read responses must not disclose new data after revocation is observed. Cancellation/connection close does not claim rollback of already completed side effects.

## 6. Audit, redaction and retention (DEC-AEG-006)

For every AEGIS policy evaluation originating remotely, the security audit event MUST carry:
- existing AEGIS fields: event ID/time/type, principal binding, `origin=remote`, task/step/proposal/decision/operation IDs, risk class, policy and registry versions/status, action digest, result status, reason code and correlation ID;
- `device_binding`: SHA-256 thumbprint/digest of the registered device public key;
- `session_binding`: SHA-256 digest of the random server-side session identifier.

Raw device/session IDs MAY remain in the access-controlled remote-device registry for operational lookup, but MUST NOT be copied into general audit events. Session secrets, private keys, signatures, pairing challenge secrets, authorization references, request bodies containing private task data and full event payloads MUST NOT be logged. Use stable reason codes and minimal metadata.

The candidate AEGIS audit-event v0.2.0 schema is extended by this decision to require both binding digests when `origin=remote`; local/extension/system events do not supply these fields. Active audit-event v0.1.0 remains unchanged. Transport-only pairing/session lifecycle events that do not have an AEGIS policy decision (for example, challenge created, device enrolled/revoked, session issued/expired, WSS closed) MUST use a separately typed, append-only security event contract owned by PILOT-08 and reviewed by AEGIS-06; they must include event ID/time, actor/owner binding, device/session binding where available, correlation ID, outcome and stable reason code. They must never be misrepresented as policy decisions.

Audit writes for security-sensitive mutations MUST be durable before returning success; required pre-dispatch authorization/consume audit MUST commit before a grant or handler dispatch. Audit-store unavailability fails closed for those operations. Retention duration and deletion/legal-hold policy are a project privacy decision and remain a release gate; access is restricted and audit integrity must be verifiable.

## 7. Transport and deployment profile (DEC-AEG-007)

1. TLS is mandatory for every non-loopback connection. TLS 1.2 is the minimum; TLS 1.3 is preferred. Validate the configured certificate chain or explicit owner-pinned certificate fingerprint. Never offer a “skip certificate verification” mode or plaintext fallback.
2. Remote service binds to loopback only by default. Private-network/LAN binding requires explicit local owner opt-in and a visible status indicator. No automatic public listener, UPnP, router port-forwarding, public relay or cloud tunnel.
3. Validate Host against the configured local endpoint. Browser HTTP and WebSocket requests MUST validate Origin against an exact allowlist; wildcard and suffix matching are prohibited. Origin is a CSRF boundary, not identity.
4. WSS is required for events. Bound HTTP request bodies to 1 MiB (task submission body to 16 KiB), WebSocket frames to 64 KiB, and concurrent WebSocket connections to 5 per device. Enforce per-device and per-source rate limits for pairing, authentication and API routes; return bounded generic errors.
5. Do not put credentials in URL query strings. Redact Authorization, Signature, cookies, pairing material and private task data from logs. Disable verbose request-body logging in production.
6. VPN/private-overlay membership is transport reachability only; it never substitutes for device proof, session validation or AEGIS policy authorization.

## 8. Remote approval is disabled for MVP (DEC-AEG-008)

No remote approve/deny endpoint, remote approval button or remote approval relay is permitted in MVP. A remote client MAY receive a redacted notification that local approval is pending, but it cannot approve, deny, dismiss or extend the request. The approval decision must be made through the trusted local approval surface by an eligible local principal. Any future remote approval capability requires a separate contract version, explicit risk review, trusted UX and negative test suite; it is not implied by this document.

## 9. Required PILOT-08 acceptance tests

- Pairing challenge is rejected after 5 minutes, after one consume, after 5 failed proofs, and on transcript/key mismatch.
- A second device cannot enroll without local confirmation; remote-only challenge creation is rejected.
- A device without OS-protected key storage cannot enable pairing; no plaintext private key is written.
- Missing/invalid/replayed HTTP signature, reused nonce, stale timestamp, wrong body digest, wrong session/device key and revoked device each return denial before route handler invocation.
- A bearer token copied to another device is unusable without the registered device private key.
- Session is rejected at 8-hour absolute expiry and 15-minute idle expiry; clock skew outside ±60 seconds is rejected.
- Every protected read and mutation invokes AEGIS policy; DENY, REQUIRE_APPROVAL, unavailable policy/identity/registry/Core/audit all produce zero new executor calls.
- Client-supplied principal, origin, role, risk, resource scope, decision or approval fields are rejected or ignored and never enter trusted context.
- Device revoke/global disable blocks new requests immediately and closes active WSS within 1 second; revoke racing broker consume yields exactly one safe outcome.
- WebSocket mutation messages are rejected; browser Origin mismatch and Host mismatch are rejected.
- Oversized body/frame, connection flood and rate-limit tests are bounded.
- Remote approval attempt is unavailable and cannot create an authorization grant.
- Remote audit events contain device/session binding digests but no credentials, private keys, challenge secrets or private task content.

## 10. Ownership and implementation gate

- **AEGIS-06:** policy context, decision/error semantics, remote approval prohibition, audit binding requirements and security acceptance.
- **PILOT-08:** device key/pairing/session services, HTTP signature verification, TLS/Origin/Host handling, listener/rate/size limits, WSS revocation and transport lifecycle audit.
- **TUSKER-04:** trusted principal/origin context propagation, task lifecycle adapter, owner-scoped projections, idempotency and unknown-outcome reconciliation.
- **NEXUS-07:** broker-side final authorization consume, peer identity, durable atomicity and dispatch reconciliation; no remote direct broker endpoint.
- **NOVA-02:** local pairing confirmation, device/revoke/global-disable UX and local-only approval UX.
- **ATLAS-01:** OS secure storage dependencies, service user/permissions, TLS deployment and systemd/SELinux hardening.

This is an owner-authored security contract decision. It does not prove any of the above services, schemas, UX, broker behavior or tests are implemented. PILOT-08 may update its decision register to ACCEPT DEC-AEG-001 through DEC-AEG-008 with this document as the durable decision reference, but implementation remains blocked until the relevant owner implementation and negative tests pass.

## References

- RFC 9421 — HTTP Message Signatures: https://www.rfc-editor.org/rfc/rfc9421
- RFC 9530 — Digest Fields: https://www.rfc-editor.org/rfc/rfc9530
- OWASP WebSocket Security Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html

# PILOT-08 Transport and Security Research

**Status:** research note for P0/P1; not an approved project contract  
**Date checked:** 2026-10-31  
**Owner:** PILOT-08

## 1. Decision summary

- Keep the remote service disabled by default and bound to loopback until the owner explicitly enables remote connectivity.
- Use HTTPS for request/response APIs and WSS (WebSocket over TLS) for live task/connection events. WebSocket is a transport for events, not a separate authorization system.
- Prefer a user-managed private network (WireGuard or another owner-managed overlay) for remote reachability. Do not silently configure router port forwarding, UPnP, a public relay, or a cloud tunnel.
- Retain application-layer device authentication, per-request authorization and revocation even when traffic is carried over a VPN. A VPN peer is not automatically an authorized TuskerOS user/device.
- For browser clients, validate WebSocket Origin against an exact allowlist and avoid putting credentials in URLs. Authenticate the handshake and revalidate session expiry/revocation for the lifetime of the socket.
- Do not select OAuth/OIDC, DPoP, mTLS, a particular cryptographic library, or a session lifetime until AEGIS-06 reviews the threat model and supported client types.

## 2. HTTPS and WebSocket

OWASP's WebSocket guidance notes that WebSockets do not provide authentication by themselves and browser cookies can create Cross-Site WebSocket Hijacking risk. It recommends explicit Origin allowlisting, authentication/authorization checks, connection and message limits, security-event logging, and avoiding sensitive values in logs.

PILOT implications:
- WSS only; no plaintext fallback.
- Browser WebSocket handshake requires an exact configured Origin allowlist; reject absent/unexpected origins for browser-facing endpoints.
- Native clients use a separately specified authentication mechanism; do not treat a missing Origin as trusted identity.
- Authenticate before accepting the upgrade. Authorize subscriptions and every client message independently.
- Apply message-size, connection, idle and rate limits; heartbeat and close stale sessions.
- Close active sockets on session expiry, device revocation, global disable, or authorization invalidation.
- Never put bearer credentials, pairing codes, or session tokens in URL query strings.
- Log connection/auth/authorization/abnormal-close metadata without logging tokens, full messages or unnecessary personal/task content.

Source: OWASP WebSocket Security Cheat Sheet, https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html

## 3. Device-bound credentials and session handling

IETF RFC 9700 (OAuth 2.0 Security Best Current Practice, January 2025) recommends restricting token privileges and audience, and describes sender-constrained access tokens (for example, mTLS or DPoP) to mitigate replay of stolen tokens. It also requires public-client refresh tokens to be sender-constrained or rotated if refresh tokens are used.

PILOT implications:
- Prefer a device-bound proof-of-possession design over a reusable bearer credential alone, subject to AEGIS-06 and platform support.
- Keep access credentials short-lived and scoped to the remote API audience.
- If refresh tokens are introduced for a public/native client, follow RFC 9700's sender-constraint or rotation requirements; otherwise choose a simpler re-pair/re-authentication design.
- Store device private keys and session material in platform secure storage; document behavior where unavailable.
- Server-side revocation must invalidate HTTP and WebSocket access. Device revocation must revoke all sessions for that device.
- OAuth is not automatically required. RFC 9700 is relevant if the project adopts OAuth token patterns; the project may choose a smaller first-party pairing/session protocol after security review.

Source: IETF RFC 9700, https://www.rfc-editor.org/rfc/rfc9700.html

## 4. Private network connectivity

WireGuard's official documentation describes peer keys, interface configuration, AllowedIPs and optional PersistentKeepalive for NAT/firewall situations. Its official installation page lists `wireguard-tools` for Fedora. This makes WireGuard a plausible optional private-network transport for a Fedora-based OS, but not a turnkey remote-access product: peer provisioning, endpoint reachability, routing, key rotation, firewall policy and support UX remain product responsibilities.

PILOT implications:
- Evaluate user-managed Wireguard as an optional transport path, not a mandatory dependency.
- Never generate or distribute peer private keys through the pairing QR code.
- Pairing and app-level authorization remain mandatory after a VPN tunnel is established.
- Do not enable PersistentKeepalive globally; use it only when a documented NAT/firewall scenario requires it.
- No public listener or inbound router port-forwarding is created automatically. The user/operator owns the private network and firewall configuration.

Sources:
- WireGuard Quick Start: https://www.wireguard.com/quickstart/
- WireGuard Installation: https://www.wireguard.com/install/

## 5. Options comparison

| Option | Strengths | Risks / cost | PILOT position |
|---|---|---|---|
| HTTPS/WSS on trusted LAN | Simple client support; standard web tooling | LAN is not a trust boundary; certificate provisioning and discovery are unresolved | MVP transport, loopback default and explicit LAN enablement |
| User-managed WireGuard | Encrypted private overlay; peer-based reachability; no need to expose application admin API publicly | User must manage peers/endpoints/keys; NAT and roaming complexity; not app authorization | Optional preferred remote-network path |
| Other private overlay/VPN | Can simplify NAT traversal and device reachability | External provider dependency, account/privacy considerations and differing trust model | Evaluate later; no vendor assumption |
| Public reverse proxy/relay/tunnel | Convenient reachability across arbitrary networks | Public attack surface, operational cost, metadata exposure and relay trust | Out of initial scope; separate security review required |
| Direct public HTTPS listener | Broad reachability | Requires public hardening, exposure, TLS lifecycle, abuse controls and operational response | Not default; not needed for MVP |

## 6. Research-derived acceptance checks

- [ ] WSS handshake rejects missing/invalid credentials.
- [ ] Browser handshake rejects unexpected Origin values.
- [ ] Tokens/pairing codes never appear in URLs or logs.
- [ ] Oversized messages, floods and excess connections are bounded.
- [ ] Session expiry and device revocation close existing sockets.
- [ ] Access scopes and resource audience are narrow.
- [ ] If OAuth refresh tokens are used, sender constraint or rotation is implemented and replay-tested.
- [ ] VPN membership alone cannot authorize a task or approval.
- [ ] Default listener is loopback-only; no automatic UPnP/port-forwarding.
- [ ] Private-network setup is explicit, documented and reversible.

## 7. Open decisions for AEGIS-06

1. Device proof-of-possession algorithm and supported client key storage.
2. First-party session protocol versus OAuth/OIDC; if OAuth is selected, required RFC 9700 profile.
3. Session lifetime/idle expiry and renewal strategy.
4. Browser vs native credential transport.
5. Required audit retention/redaction and fail-closed conditions.
6. TLS certificate trust and renewal UX for LAN/private-network mode.

This note is research input, not security approval. No implementation should infer authorization from transport reachability.

# Theme Preview Rendering Contract (Draft 1.0)

**Status:** PIXEL-03 proposal for NOVA-02 review. Not approved, not implemented by a desktop adapter, and not an apply contract.

## Scope and ownership

PIXEL-03 owns the resolved theme snapshot, preview-session lifecycle, request validation and safe asset identity. NOVA-02 owns desktop adapters and all KDE/Qt rendering. This contract defines the boundary only; it does not select Plasma APIs, Qt versions, IPC transport or concrete settings keys.

## Preview request

The engine sends a JSON document conforming to `schema/preview-render-request.schema.json`. Required properties:

- Protocol version `1.0`, opaque request ID, opaque preview session ID and non-negative revision.
- `preview_only: true` is mandatory. Unknown fields are rejected; there is no apply, commit, activate, persist, or shell-reload operation in this request.
- `expires_in_ms` is a bounded remaining lifetime (1–300000 ms), derived from the engine's monotonic preview-session deadline. It is a duration, not a timestamp.
- `surfaces` contains only the fixed surface allowlist. The engine intersects requested surfaces with adapter-supported surfaces before dispatch.
- Snapshot contains theme identity/version, semantic token namespaces, inert asset IDs/kinds and enforced accessibility flags. No arbitrary file paths, URLs, executable references, QML, JavaScript, CSS, shell snippets, plugin identifiers or commands cross this interface.

Asset IDs are opaque references resolved by the engine. An adapter must request bytes only through a future separately approved asset broker; it must not construct filesystem paths from IDs or load arbitrary URLs. Preview assets are read-only and bounded by the existing asset inspection policy.

## Capability negotiation

Before rendering, the adapter advertises a document conforming to `schema/preview-adapter-capabilities.schema.json`: adapter ID, supported protocol versions, surfaces, token namespaces and explicit capability booleans. The engine selects the highest mutually supported protocol version (currently only 1.0), intersects surfaces/namespaces, and sends only that subset. If no protocol version or no requested surface is mutually supported, rendering is not dispatched.

Capability booleans are descriptive, not permission grants. An unsupported optional effect (blur, transparency, animation, dynamic wallpaper or lock-screen theming) must be omitted and reported as unsupported; it must never be emulated by executing pack content.

## Response and failure semantics

The adapter returns a JSON document conforming to `schema/preview-render-response.schema.json`. The response echoes protocol version, request ID, session ID and revision. Status-specific requirements are enforced by schema: `rendered` requires at least one rendered surface and no omissions; `partial` requires both rendered and omitted surfaces with a stable omission reason per surface; `rejected` requires a stable failure code and reports no rendered surfaces. Unknown fields, including apply-like claims, are rejected. The adapter returns a typed result at the transport layer:

- `rendered`: preview rendered in an isolated, non-active preview target; includes request ID, session ID, revision and the exact rendered surface list.
- `partial`: only explicitly accepted surfaces rendered; each omitted surface has a stable reason code.
- `rejected`: no surface rendered; includes a stable reason code such as `unsupported_protocol`, `unsupported_surface`, `unsupported_namespace`, `invalid_payload`, `expired_session`, `resource_limit` or `adapter_unavailable`.

A response must echo request/session/revision identifiers. The engine discards stale, mismatched, late or post-expiry responses. Adapter errors must not expose filesystem paths, user data or implementation secrets. No fallback may silently claim a surface was previewed when it was not; diagnostics identify every unsupported or omitted surface.

## Isolation and security invariants

1. Preview is visually isolated from the active desktop; it may use a dedicated preview window/mock surface, but must not mutate the visible active shell configuration.
2. Preview must not write Plasma/KDE settings, profile state, caches used by the active shell, startup configuration or persistent theme selection.
3. Adapter receives only authenticated, owner-authorized sessions. Owner identity remains at the engine/transport boundary and is not trusted from fields inside the payload.
4. Session ID is opaque and short-lived; adapter enforces the supplied remaining lifetime and engine expiry remains authoritative.
5. All payloads are data-only, bounded and schema-validated. No dynamic evaluation, plugin loading, shell command, script execution, or arbitrary resource fetch is permitted.
6. Accessibility/security policy is engine-enforced. Adapters must not suppress focus indicators or bypass reduced-motion/high-contrast policy.
7. Preview cancellation/expiry tears down the isolated preview target and releases temporary resources. It never restores settings because preview never changed them.
8. Preview and apply are separate APIs and separate authorization paths. This contract deliberately defines no apply/rollback semantics.

## Compatibility and open decisions for NOVA-02

- Confirm target Plasma/Qt versions and the initial required surfaces.
- Select IPC mechanism and authentication/peer-credential strategy.
- Define adapter process lifecycle, timeout budgets and response envelope serialization.
- Confirm whether the MVP preview is a TuskerOS-owned preview window/mock surface or isolated staging instance.
- Define how asset bytes are brokered without exposing arbitrary paths.
- Agree capability semantics and stable failure reason codes.

Until those decisions are reviewed, this document and schemas are proposals only. No KDE integration or production adapter may claim conformance.

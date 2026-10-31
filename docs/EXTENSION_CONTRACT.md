# TuskerOS Extension Contract — v0.1 proposal

**Status:** Draft for review; not a production trust or sandbox specification.

## Package layout

An extension package contains:
- `manifest.json`: required declarative metadata.
- `README.md`: user-facing purpose, permissions and support information.
- `payload/`: optional runtime-specific content. The host/runtime format is not yet standardized; this initial example has no executable payload.

## Manifest fields

| Field | Requirement | Meaning |
|---|---|---|
| `manifest_version` | required, integer | Manifest schema major version; currently 1 |
| `id` | required | Reverse-DNS publisher namespace plus package name |
| `name` | required | Human-readable display name |
| `version` | required | Semantic version |
| `description` | required | Short plain-text description |
| `publisher` | required | Stable publisher identifier |
| `license` | required | SPDX identifier or `LicenseRef-...` |
| `kind` | required | `extension`, `theme`, `layout`, or `workflow` |
| `api` | required | Minimum and maximum supported host API |
| `os` | required | Minimum and maximum supported TuskerOS release |
| `permissions` | required | Explicit list; empty list means no privileged capability |
| `dependencies` | required | Explicit package IDs and version ranges; may be empty |
| `artifacts` | optional | Immutable artifact URI, digest and signature metadata |

## Initial permission design

Permission strings in examples are illustrative and not approved capability identifiers. Before runtime implementation, AEGIS-06 must define the canonical vocabulary, risk classes, user-consent rules, revocation behavior and sandbox mapping. Unknown permission strings must be rejected, not silently granted.

Extensions receive no system-level permission by default. No wildcard permissions. No implicit privilege inheritance from dependencies. A dependency's permissions are independently reviewed and granted.

## Security requirements

1. Validate manifest and artifact metadata before download/install.
2. Verify artifact digest and trusted signature before activation.
3. Stage extraction in a private directory; reject absolute paths, traversal, unsafe symlinks, duplicate normalized paths and resource-exhaustion archives.
4. Do not execute install scripts or arbitrary package hooks.
5. Run extension payloads only inside the AEGIS-approved isolated host with declared, user-approved capabilities.
6. Route OS operations through typed NEXUS-07 APIs; never expose a general shell or root process.
7. Record install, update, enable, disable, permission grant/revoke and uninstall events.
8. Removal affects only files owned by the package manager; preserve user data and explain orphaned dependencies.
9. Quarantine/revoke compromised packages and stop loading them on next safe opportunity.
10. Treat manifest descriptions, README text and remote catalog content as untrusted data, never as policy instructions.

## Compatibility and lifecycle

The host checks schema version, OS range, host API range, dependency constraints and package conflicts before presenting an install plan. An extension may declare optional capabilities but cannot silently require them at runtime. API breaking changes require a major version increase and migration notes.

## Open decisions

- Canonical permission names and risk tiers: AEGIS-06.
- Sandbox technology, host ABI and payload format: AEGIS-06 + NEXUS-07.
- Theme/layout package manifest mapping: PIXEL-03.
- Extension discovery and lifecycle hooks: TUSKER-04 + NOVA-02.
- Signing envelope, catalog root and revocation distribution: AEGIS-06 + PHOENIX-10.
- Package source and OS transaction adapter: ATLAS-01 + PHOENIX-10.

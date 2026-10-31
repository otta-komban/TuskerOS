# TuskerOS Developer Ecosystem Architecture

**Owner:** FORGE-09  
**Status:** Phase 1 proposal; cross-agent interfaces provisional  
**Branch:** `09-ecosystem`

## Goals and boundaries

The Developer Center is an optional user-space product surface. It discovers and manages developer bundles and community packages; it is not a privileged package manager, policy engine, sandbox implementation, or arbitrary-code host.

Owned areas:
- `developer-center/`: catalog and developer workflow UI/service.
- `marketplace/`: catalog metadata, publication and lifecycle workflows.
- `sdk/`: schemas, client libraries, templates and validation tools.
- `bundles/`: optional developer environment definitions.
- `docs/`: developer and publisher documentation.
- `examples/`: sample extension projects.

## Logical architecture

1. **Catalog client** reads signed catalog metadata and presents search, details, compatibility, publisher, license, ratings and review status.
2. **Manifest validator** checks schema, identifiers, versions, permissions, dependencies, compatibility and package references before any plan is shown.
3. **Planner** resolves declared dependencies and produces a deterministic install preview. It does not execute package scripts.
4. **Approval and policy boundary** sends requested capabilities and operation context to AEGIS-06. FORGE does not make allow/deny decisions or mint privileged grants.
5. **Installer adapter** delegates approved package operations to OS/package services owned by ATLAS-01/PHOENIX-10. It records a transaction and supports cancellation/rollback only where the underlying package system supports it.
6. **Extension host** is supplied by the agreed runtime/security implementation. Extensions receive only explicitly granted capabilities and typed APIs; they do not receive direct root, arbitrary shell, or unrestricted filesystem access.
7. **Audit adapter** emits package lifecycle and permission events through the shared audit contract; secrets and private payloads are excluded.

## Package classes

- **Theme/layout assets:** declarative data and media only. No executable code, scripts, hooks, macros, or embedded active content. PIXEL-03 owns the theme format.
- **Extensions:** versioned manifest plus a runtime-specific payload. The payload format and host ABI remain provisional pending AEGIS-06/NEXUS-07 agreement. No native executable support is implied by this initial contract.
- **Developer bundles:** declarative lists of package-manager dependencies and optional environment setup metadata. No implicit post-install shell execution.
- **Documentation/workflow packs:** declarative content/configuration subject to content and permission review.

## Lifecycle

`discover → inspect → validate → resolve → preview → authorize → acquire → verify → install → record`

Removal:
`inspect installed state → compute reverse-dependency impact → preview removal → authorize if needed → remove managed files/packages → verify → record`

Updates use the same pipeline as installation and must preserve rollback metadata where supported. Failed operations leave a recoverable transaction record and do not silently report success.

## Cross-agent interfaces

| Partner | Required agreement |
|---|---|
| AEGIS-06 | Permission vocabulary, policy evaluation, approval token format/lifetime, sandbox profile, signature trust roots, audit event requirements |
| NEXUS-07 | Typed capability API, extension-facing tool surface, input/output schemas, cancellation and postcondition semantics |
| PIXEL-03 | Theme/layout package schema, asset allowlist, compatibility and preview metadata; theme payloads remain non-executable |
| NOVA-02 | Extension points, UI contribution model, lifecycle and failure isolation |
| ATLAS-01 | Supported package sources, package IDs, OS dependency metadata and package transaction integration |
| PHOENIX-10 | Component version metadata, signed artifact conventions, update/rollback and release compatibility |
| TUSKER-04 | Discovery metadata and invocation lifecycle; no direct access to private orchestration internals |

## Compatibility policy

Every published item declares a manifest schema version, package version and supported TuskerOS/API range. Semantic versioning is recommended for public SDK APIs. Unknown required fields, unsupported schema versions, incompatible OS ranges and unresolved dependencies fail closed. Optional unknown metadata may be preserved but never interpreted as executable instructions.

## Trust and supply chain

A production marketplace should require publisher identity, immutable artifact digest, signature verification against configured trust roots, provenance, license metadata, review state and revocation status. A valid signature proves artifact origin/integrity under a key; it does not prove the artifact is safe. Review and sandboxing remain necessary.

## Risks and mitigations

- **Permission drift:** centrally version the permission vocabulary with AEGIS-06; reject unknown permissions.
- **Dependency confusion:** use canonical source identities, namespace ownership and explicit source pinning.
- **Malicious archive:** safe extraction, path normalization, symlink policy, size/count limits and no writes outside staging.
- **Compromised publisher:** revocation, quarantine, signed updates and incident response.
- **Uninstall damage:** maintain a file/package ownership ledger; never delete user-owned data implicitly.
- **API instability:** schema/API versioning, compatibility tests and deprecation windows.
- **Resource bloat:** optional bundles, explicit size estimates and low/standard/powerful profile guidance.

## Phase 1 exit criteria

- [x] Initial architecture and ownership boundaries documented.
- [x] Initial declarative extension manifest contract drafted.
- [x] Minimal example package created.
- [ ] AEGIS-06 permission/sandbox contract acknowledged.
- [ ] NEXUS-07 extension-facing API contract acknowledged.
- [ ] PIXEL-03 theme package boundary acknowledged.
- [ ] Schema and validator automated tests added and run.
- [ ] Marketplace signature/catalog format accepted by security and release owners.

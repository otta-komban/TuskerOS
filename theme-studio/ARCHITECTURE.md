

## 16. Persistent profile store reference implementation

`theme-studio/runtime/profile_store.py` persists declarative profile selections and token overrides as versioned JSON. It rejects unknown fields, malformed IDs, duplicate mixins, invalid mixin-winner references, duplicate JSON keys, symlink/non-regular store files and oversized documents (including a bounded read). Writes use a same-directory temporary file, mode 0600, file fsync, atomic replace and parent-directory fsync. Active-profile deletion requires an explicit existing fallback. The store is thread-safe within one process, not a cross-process transaction manager. Its parent directory must be private to the user; it does not itself verify package availability or token semantics. Profile activation here changes the persisted active-profile pointer only; preview/apply and desktop acknowledgement/rollback remain separate work.


## 17. Profile composition service

`theme-studio/runtime/profile_composer.py` joins the persisted profile format to an already validated, caller-supplied inert catalog and the deterministic token resolver. The catalog is keyed by pack ID and supplies `kind`, `version`, and declarative `tokens`; the base theme must match the exact version pinned by the profile. Selected mixins are resolved by ID from the catalog. Profile format v1 does not pin mixin versions, so reproducibility of mixin selection is bounded by the catalog snapshot supplied to composition; a future profile-format revision should pin mixin versions before marketplace updates can silently change them.

Composition rejects absent or wrong-kind packs, invalid catalog records, stale base-theme versions, invalid mixin winners and unresolved token conflicts. Precedence remains defaults < base theme < mixins < profile overrides < user overrides < enforced policy. It returns a detached token/provenance snapshot and does not mutate the profile store or catalog, read pack files, execute pack content, or apply desktop settings. The catalog provider remains responsible for manifest and asset validation before exposing records to this service.


## 18. Isolated preview-session lifecycle

`theme-studio/runtime/preview_sessions.py` holds resolved composition snapshots in a bounded, process-local in-memory session manager. Each session is scoped to an owner, has an opaque identifier, expires using a monotonic clock (five-minute default), and is returned only as detached copies. The manager supports explicit cancellation, expiry cleanup and a configurable concurrent-session ceiling (32 by default). Missing, expired and wrong-owner reads share the same not-found error to avoid disclosing session existence.

A preview session is presentation data only. Creating, reading, cancelling or expiring it does not activate a profile, modify the profile store, write persistent preview state, or call KDE/Qt adapters. It is intentionally volatile: process restart drops all previews. The caller must bind owner IDs to authenticated application identities and invoke cleanup periodically or on session operations. This component does not yet implement desktop rendering, apply, adapter acknowledgement or rollback; those require the NOVA-02 adapter contract and a separate transactional apply coordinator.


## 19. Preview rendering boundary (draft contract)

The preview-session manager remains presentation-data storage only. A separate proposed rendering boundary is specified in `contracts/preview-rendering-contract.md`, with strict request and adapter-capability schemas in `schema/preview-render-request.schema.json` and `schema/preview-adapter-capabilities.schema.json`. The request is data-only, bounded, owner-authorized outside the payload, and explicitly `preview_only: true`; it contains semantic token values and opaque asset IDs rather than paths or executable content. Capability negotiation intersects protocol version, surfaces and token namespaces before dispatch. Unsupported effects/surfaces are reported rather than silently claimed. The draft requires isolated rendering, no persistent desktop/profile mutation, expiry/cancellation cleanup and stale-response rejection. This is an interface proposal only: NOVA-02 must agree the IPC/authentication, supported Plasma/Qt stack, initial surfaces and asset broker before any adapter implementation. Preview remains separate from apply/rollback.

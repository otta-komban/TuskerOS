# Theme Engine Architecture

**Status:** Phase 1 proposal, 2026-10-31. This is a design baseline, not an implemented or integrated engine.

## 1. Goals and non-goals

The Theme Engine is the single authority for resolving TuskerOS visual preferences into a normalized theme snapshot. It must support consistent theming without making KDE Plasma internals a second theme database.

Goals:
- One versioned declarative theme-pack format for all theme families.
- Deterministic token resolution, inheritance/mixing, profiles, preview, apply, rollback and reset.
- Asset validation and provenance checks before use.
- Accessibility and security overrides that themes cannot weaken.
- Stable integration boundaries for NOVA-02 desktop surfaces and FORGE-09 marketplace delivery.
- Graceful operation when a pack, asset, renderer, or optional desktop surface fails.

Non-goals:
- Replacing KDE's native settings or patching unsupported Plasma internals.
- Executing theme-provided code, scripts, hooks, commands, plugins, or arbitrary QML.
- Owning the desktop shell, notification implementation, lock screen implementation, or marketplace UI.
- Guaranteeing every third-party Qt/KDE application can be fully themed.

## 2. Logical components

1. **Pack Registry** — indexes installed pack metadata and immutable versioned pack directories.
2. **Manifest Validator** — validates schema version, strict keys, compatibility, token values, references, and declared capabilities.
3. **Asset Inspector** — resolves paths beneath the pack root; rejects traversal, symlinks escaping the root, unsupported formats, oversized assets, mismatched MIME types, and digest failures.
4. **Token Resolver** — resolves defaults, selected base theme, optional mixins, profile overrides, user overrides, and enforced accessibility/system overrides into one immutable snapshot.
5. **Profile Manager** — stores named selections such as Work, Study, Gaming, Night; profile changes are declarative references, not executable workflows.
6. **Preview Session** — creates a temporary snapshot and preview namespace; it never mutates the active theme until explicit Apply.
7. **Apply Coordinator** — stages the resolved snapshot, asks desktop adapters to prepare, commits only after required adapters acknowledge, and restores the previous snapshot on failure.
8. **Persistence Store** — stores active pack/version, mixins, user overrides, profiles, and last-known-good snapshot using atomic writes and schema migrations.
9. **Surface Adapters** — narrow adapters for supported desktop surfaces. They consume normalized tokens and safe asset references; they do not parse arbitrary pack content independently.
10. **Diagnostics** — records pack ID/version, validation outcome, adapter acknowledgements, fallback reason and rollback result without logging private file contents.

## 3. Resolution precedence

Lowest to highest precedence:

1. Built-in system defaults.
2. Selected base theme.
3. Explicitly selected compatible mixins (disjoint keys preferred; conflicts require an explicit user choice).
4. Active profile overrides.
5. User-level per-token overrides.
6. Enforced system/accessibility policy overrides.

Themes cannot override the final layer. Examples include high contrast, minimum text scale, reduced motion, focus visibility, and security-sensitive dialog readability.

Mixing must be deterministic. Each mixin declares the token namespaces it provides. Conflicting values are rejected unless the user explicitly selects a winner; there is no implicit “last pack wins” behavior. Asset namespaces are isolated by pack ID to prevent collisions.

## 4. Declarative package format

The canonical manifest is `theme.json`, validated against `schema/theme-pack.schema.json`. It contains:
- Stable ID, semantic version, display metadata and license/provenance.
- Minimum/maximum Theme Engine API compatibility.
- Typed design tokens for colors, typography, spacing, shape, shadows and motion.
- Explicit semantic asset-role references for desktop/lock-screen wallpapers, icon sets, fonts and system sounds.
- Surface-specific references to shared tokens and inert assets.
- Accessibility declarations and resource hints.

The schema uses `additionalProperties: false` at each defined object boundary. Asset paths are relative, contained paths. There are no extension points for executable content. New capabilities require a schema/API version change and review.

## 5. Lifecycle

**Discover → Stage → Validate → Preview → Apply → Verify → Persist**

- Discover reads metadata only; no asset is activated.
- Stage copies/downloads a pack into a temporary location and verifies package integrity.
- Validate checks schema, version compatibility, path containment, asset type/size/digest, license metadata and policy.
- Preview resolves a temporary snapshot and renders it in a non-persistent preview session.
- Apply prepares each available adapter against the staged snapshot.
- Verify collects adapter acknowledgements and checks required surfaces.
- Persist atomically writes the new selection and last-known-good snapshot only after successful verification.

On failure, restore the previous snapshot and tell the user which surface failed. A failed optional adapter may use the declared fallback policy; a failure on a required surface aborts the transaction.

## 6. Persistence and rollback

- User theme state is user-scoped; system defaults are read-only to ordinary users.
- Pack contents are immutable after validation. Updates install as a new version.
- Active state references exact pack IDs and versions, never floating “latest”.
- Writes use temp-file + fsync + atomic rename where supported.
- Keep at least one last-known-good snapshot.
- Import never auto-applies. Restore and reset are explicit user actions.
- Removing an active pack first switches to the built-in default or another confirmed pack.

## 7. Desktop integration boundary

The engine exports a normalized, versioned token snapshot and lifecycle events. Desktop adapters expose capabilities and report prepare/apply/fallback status. NOVA-02 owns rendering, shell components, Plasma-specific configuration and surface-specific implementation. See `contracts/desktop-contract.md`.

The engine must not directly patch Plasma config files owned by NOVA-02 without an agreed API. Unsupported surfaces are reported as unsupported rather than silently approximated.

## 8. Marketplace integration boundary

FORGE-09 owns catalog, discovery, publishing, download UX and marketplace install orchestration. The Theme Engine owns validation, compatibility evaluation, activation, removal and rollback. See `contracts/marketplace-contract.md`. Marketplace metadata is untrusted input.

## 9. Security and trust model

Threats include path traversal, archive bombs, malformed manifests, malicious media/font files, deceptive license metadata, stale/incompatible packages, resource exhaustion, spoofed IDs, and hostile content in descriptions.

Controls:
- Strict allowlist schema; reject unknown keys and versions.
- No executable files or executable manifest fields.
- Resolve all asset paths beneath a canonical pack root; reject symlink escapes.
- Enforce per-file and total unpacked size limits, MIME allowlists and content sniffing. SVG is excluded from v1 because it can contain active content; a future vector-asset profile would require a separately reviewed sanitizer and strict external-reference policy.
- Enforce semantic asset-role references against the declared asset IDs and kinds; reject dangling references and kind mismatches.
- Restrict surface overrides to the schema's enumerated surface IDs; adapters must still confirm runtime support.
- Verify SHA-256 digests and package provenance/signature when supplied by package policy.
- Do not trust marketplace descriptions, filenames or claimed publisher identity.
- Install as user data; never request root privileges to apply a theme.
- Render untrusted image/font/media assets through platform decoders with normal sandbox/process boundaries.
- Never let a theme override security prompts, privileged dialogs or accessibility policy.
- Make activation reversible and preserve the previous working configuration.

A valid signature establishes package origin/integrity under a trust policy; it does not make a theme's assets harmless.

## 10. Performance and accessibility

- Prefer static wallpaper and vector/raster assets within declared limits.
- Blur, transparency and animation are hints; surface adapters may reduce or disable them based on hardware or compositor capability.
- Reduced-motion policy forces motion durations to zero/near-zero and disables animated assets.
- High-contrast policy, text scaling, focus indicators and keyboard visibility override pack values.
- Validate contrast for semantic foreground/background pairs; report failures before apply.
- Avoid full-resolution duplicate previews; cache decoded assets with bounded memory and release preview resources on close.

## 11. Main risks and mitigations

| Risk | Mitigation |
|---|---|
| Plasma/KDE APIs differ by version | Capability discovery, adapter versioning, compatibility matrix, no unsupported config patching |
| Theme breaks desktop readability | Preview, semantic contrast checks, accessibility override layer, last-known-good rollback |
| Malicious or malformed pack | Strict schema, asset inspection, size/path limits, no code execution |
| Theme mixing creates conflicts | Explicit conflict resolution and deterministic precedence |
| Expensive blur/animation harms low-end systems | Resource hints, capability-aware fallback, reduced-effects mode |
| Marketplace and engine duplicate install logic | Explicit FORGE-09/PIXEL-03 ownership boundary |
| Theme update changes active appearance unexpectedly | Immutable version pinning and explicit update/apply |
| Surface partially applies | Prepare/commit protocol, acknowledgements, rollback and per-surface fallback |

## 12. Phase 1 exit criteria

- [x] Master execution blueprint and PIXEL-03 ownership/phase checklist reviewed.
- [x] Repository and owned branch inspected; branch confirmed to exist.
- [x] Initial architecture and safety model documented.
- [x] One versioned declarative manifest schema established.
- [x] Desktop and marketplace contracts drafted for owner review.
- [ ] NOVA-02 acknowledges desktop token/API contract.
- [ ] FORGE-09 acknowledges marketplace package boundary.
- [ ] KDE/Qt surface compatibility research completed against selected Fedora/KDE versions.
- [x] Schema validation tests and malicious-package fixtures added (Draft 2020-12 validator, starter-pack checks, and negative cases committed; CI execution is currently failing and requires diagnosis).
- [ ] Initial architecture reviewed and accepted as G1 contract baseline.

Only the checked items above have evidence in this commit. Remaining items are open.


## 13. Schema hardening note

Theme Pack v1 excludes SVG assets rather than attempting to sanitize a complex active-content format. V1 allows PNG, JPEG and WebP images, TTF/OTF/WOFF2 fonts, and OGG/WAV audio, all subject to runtime content sniffing, decoder isolation, size limits and digest verification. Asset-role references must resolve to declared asset IDs with matching kinds. Surface override IDs are restricted to the v1 allowlist in the JSON Schema. Path validation rejects absolute paths, backslashes, duplicate separators and dot-segment traversal; runtime canonical-path and symlink checks remain mandatory.


## 14. Runtime asset inspection implementation note

The initial Python reference inspector lives at `theme-studio/runtime/asset_inspector.py`. It validates declared kind/media-type compatibility, strict relative paths, canonical containment, symlink-free path components, regular-file status, per-kind and cumulative byte limits, file signatures, SHA-256 and unique asset IDs. It streams files rather than loading them whole. This is a reference validation layer, not yet wired into an installer or desktop activation path. The staged pack root must be private and non-writable; a production implementation should use directory-descriptor-relative traversal (openat-style) to eliminate parent-directory replacement races.

# PIXEL-03 Theme Studio — Task Plan and Contract Audit

**Status:** Investigation/proposal only; implementation gate remains closed.
**Agent / branch:** PIXEL-03 / `03-PIXEL`
**Task ID:** Pending Chief Architect assignment.
**Branch HEAD / live main at inspection:** `345fc5a3d0f831fc714bae0cc88fa842cd9bed79` (branch compares identical to main).
**Launch base:** `5162de364a2f0b7dcf8aa14251a4c5ce5cf57e6d`; live main is 19 commits ahead, 0 behind this launch base.
**Blocking issue:** [#50](https://github.com/otta-komban/TuskerOS/issues/50) remains open.

## First deliverable: bounded audit and dependency plan

This document records the current evidence and an implementation sequence. It does not amend a shared schema, freeze an API, or authorize desktop mutation.

### Current baseline

- `theme-studio/schema/theme-pack.schema.json` declares pack `schema_version: 1.0.0`; `compatibility.theme_engine_api` is a major.minor string. The schema does not define a compatibility acceptance/rejection algorithm.
- The pack token model is stored as `tokens.colors`, `tokens.typography`, `tokens.spacing`, `tokens.shape`, optional `tokens.shadow`, and `tokens.motion`. Surface-specific values live in `surface_overrides`; accessibility constraints live in `accessibility`; icon/font/wallpaper/sound references live in `assets` and `asset_roles`.
- `theme-studio/contracts/desktop-contract.md` is explicitly a draft and proposes consumer namespaces `color`, `typography`, `spacing`, `shape`, `shadow`, `motion`, `surface`, and `asset`.
- `theme-studio/contracts/preview-rendering-contract.md` is explicitly a proposal, separate from apply/rollback. It requires data-only bounded requests, opaque asset IDs, authenticated owner-scoped sessions, preview isolation, stale-response rejection and exact surface accounting.
- `theme-studio/ARCHITECTURE.md` says profile composition and preview sessions are side-effect-free; no desktop adapter, apply path, persistent desktop mutation or rollback coordinator is implemented.
- The marketplace contract is also a draft; package install must not imply activation.

### Reconciliation findings for reviewers

1. **Manifest-to-consumer projection:** manifest field names and desktop token namespace names are not identical. Define a versioned normalized snapshot mapping rather than exposing raw manifest layout to adapters.
2. **Icon semantics:** the current manifest models `icon_set` as an asset role referencing an asset of kind `icon`; it does not define a general icon-token namespace. Decide whether the consumer contract preserves that role or introduces a separately versioned namespace.
3. **Surface semantics:** `surface_overrides` is a surface-keyed override map, not currently a generic `surface` token namespace. Define whether consumers negotiate surface IDs separately from token namespaces.
4. **Optional shadow support:** `shadow` is optional in the manifest. Define whether an adapter lacking shadow capability omits the effect with diagnostics or rejects a pack that requires it.
5. **Accessibility ownership:** accessibility is a required manifest policy block, with focus and reduced-motion constraints enforced by schema. Confirm that the engine remains authoritative and adapters cannot weaken those constraints.
6. **Compatibility:** define separate rules for pack schema version and engine API version, including older/newer minor handling, migration policy and fail-closed behavior. The present schema alone does not settle this.

These are evidence-backed review questions, not unilateral contract changes.

## Work plan and acceptance criteria

| Work item | Dependency / gate | Acceptance evidence |
|---|---|---|
| P0 — Reconcile pack schema, samples, runtime and tests | Read-only audit allowed | Field mapping and mismatch list with exact source paths; no schema mutation |
| P1 — Freeze pack/engine compatibility and consumer snapshot policy | Chief Architect approval; NOVA-02 review; ATLAS-01 platform baseline | Approved versioned decision; compatibility matrix; migration and rejection examples |
| P2 — Implement validation and path/asset safety gaps | Approved task ID and contract | Positive, malformed, boundary, traversal, symlink, size, content-type and digest tests |
| P3 — Implement apply/reload transaction, backup and rollback | NOVA shell/session API and approved lifecycle contract | Prepare/commit/abort tests; failed-adapter rollback; last-known-good retained; exact diagnostics |
| P4 — Accessibility and runtime integration | Approved desktop surfaces and platform baseline | Contrast/reduced-motion/focus checks; desktop-session apply/reload and rollback evidence |
| P5 — Delivery | All prior acceptance evidence | Focused PR to main; exact base/head SHA; tests, security, rollback and limitations documented; integrator merges |

### Explicit non-goals while blocked

- Do not change `theme-pack.schema.json`, desktop/preview/marketplace contracts, or shared token semantics.
- Do not implement KDE/Qt adapters, apply/reload, persistent desktop mutation or rollback coordinator.
- Do not claim runtime, accessibility, or rollback acceptance without reproducible tests in the target desktop session.

## Blockers and decisions required

- **B-PIXEL-01 — Issue #50:** required-check enforcement and the activation gate are not demonstrated as satisfied; the coordinator/administrator must verify repository protection through an authorized context.
- **B-PIXEL-02 — Task authorization:** Chief Architect must publish the PIXEL-03 task ID and approve the shared theme-pack compatibility/version policy.
- **B-PIXEL-03 — Desktop boundary:** NOVA-02 must approve the consumer token projection, target Plasma/Qt baseline, IPC/authentication, initial surfaces and apply/reload ownership.
- **B-PIXEL-04 — Cross-agent baseline:** ATLAS-01 must confirm supported platform versions; coordinator must confirm the shared-contract baseline.

Issue #50 remains open. NOVA-02's preview-only review on Issue #30 is not approval of apply/reload. The token proposal on Issue #8 has not yet been accepted as a frozen API.

## Branch and historical-work inspection

- Verified `03-PIXEL` exists and compared identical to live `main` at `345fc5a3d0f831fc714bae0cc88fa842cd9bed79`.
- Live `main` is 19 commits ahead of the cohort launch base and has no divergence behind it.
- Read the current branch's role guide, repository rules, task scope, launch mapping and logging policy.
- Read the current desktop contract, preview contract, theme-pack schema, architecture and marketplace contract.
- A legacy `03-theme-studio` branch is substantially behind current main; no unreviewed changes are to be ported. Any later port requires a file-level review against the current baseline.
- No local working-tree status is available through the connected GitHub interface; branch/ref verification is via GitHub's branch and compare APIs.

## Validation record

- Static repository inspection only.
- Tests: NOT RUN (no implementation change; no local checkout/test runner exposed in this session).
- Desktop runtime/apply/reload/rollback: NOT RUN.
- Shared-contract approval: NOT GRANTED.


## Iteration 2 — isolated accessibility diagnostics

**Deliverable:** `ACCESSIBILITY-AUDIT.md`, `tests/support/accessibility_audit.py`, and `tests/test_accessibility_audit.py`.

- Added a test-only diagnostic helper for semantic text, accent, focus and border color pairs. It lives under `tests/support/`, is not imported by product runtime code, does not gate pack validation or activation, and does not modify the shared theme schema.
- Text and accent pairs use a 4.5:1 static threshold; focus pairs use 3:1. Alpha colors return `not_evaluated` because the effective result depends on compositing.
- Border contrast returns `review`, not pass/fail, because the manifest alone cannot tell whether a border is decorative or communicates a meaningful UI component boundary.
- Test coverage: known black/white 21:1 reference, all three starter theme color sets, a low-contrast negative case, alpha handling, missing roles, malformed color values and non-mapping input.
- Local scratch-fixture test result: **7 tests passed** after moving the helper into the isolated test support directory. The fixture used the semantic color values copied from the three branch starter packs; this was not a full repository checkout or full Theme Studio test-suite run.
- No desktop rendering, Plasma runtime, apply/reload, or rollback behavior was tested. This diagnostic is not a WCAG conformance certification.
- Issue #50 remains open; no shared contract or schema changes were made.

- Scope correction: the helper was moved out of `runtime/` and into `tests/support/` to keep this iteration strictly within the role guide's isolated-test allowance while Issue #50 remains open. The runtime helper was deleted from this branch.


## Iteration 3 — compatibility/version-policy evidence audit (read-only)

**Status:** Evidence and decision options only; no compatibility behavior or shared contract is frozen.

### Observed schema constraints

- `schema_version` is a required top-level field constrained to the exact constant `1.0.0`. Under this schema, a pack declaring any other schema version is structurally invalid; the schema does not itself express a range of supported schema versions or a migration route.
- `compatibility.theme_engine_api` is required and constrained only by the lexical pattern `^[0-9]+\\.[0-9]+$`. This establishes a two-component numeric spelling, but does not define whether compatibility means exact match, same-major acceptance, minimum version, or negotiated capabilities.
- `compatibility.desktop` and `required_surfaces` are optional arrays of unique strings. The schema constrains item length but does not define supported identifier registries, whether unknown identifiers reject the pack, or how optional versus required surfaces affect acceptance.
- The desktop contract remains a draft and its namespace list does not define version negotiation. NOVA-02's Issue #30 response accepts preview isolation invariants but labels its MVP rendering and apply/reload lifecycle as proposals pending Chief Architect decisions. Issue #8 has PIXEL-03's reconciliation proposal but no NOVA-02 approval comment.

### Compatibility decisions that remain open

| Dimension | What current evidence guarantees | Decision required before implementation |
|---|---|---|
| Pack schema | Exactly `1.0.0` validates against this schema | Whether future schema versions coexist, require migration, or reject until engine support is installed |
| Engine API | Required major.minor numeric string | Exact-match vs same-major/minimum-version policy; treatment of leading zeros and unsupported future minors |
| Desktop/surfaces | Optional unique string lists | Canonical ID registry, required/optional semantics, and whether unsupported required surfaces reject or degrade |
| Consumer namespaces | Draft names differ from manifest storage layout | Canonical versioned snapshot projection and negotiation behavior |
| Migration | No migration behavior is specified by the reviewed schema/contract material | Whether migrations are explicit, deterministic, bounded, and performed before validation or rejected entirely |

### Safe review recommendation (not an approved policy)

Keep parsing/validation separate from compatibility acceptance. First validate the manifest against a known schema version; then evaluate the declared engine API and required desktop/surface capabilities against an explicit engine support table. Unknown schema versions and unsupported required capabilities should not be guessed or silently downgraded. Optional capability omission should produce structured diagnostics only if the Chief Architect and NOVA-02 explicitly approve that behavior. Do not infer same-major compatibility merely from the version string shape.

No implementation or compatibility tests were added: expected acceptance outcomes are not yet authorized by an approved policy, so tests would prematurely encode a shared decision. Issue #50 remains open. This iteration is static repository/issue inspection only; no runtime or test result is claimed.


## Iteration 4 — proposed compatibility decision packet (review-only)

**Status:** Recommended defaults for Chief Architect / NOVA-02 / ATLAS-01 review. These are not approved policy, are not encoded in schemas or runtime code, and do not lift Issue #50.

### Proposed decision matrix

| Area | Recommended default for review | Compatibility consequence | Required approver(s) |
|---|---|---|---|
| Pack schema version | Accept only an explicitly supported exact schema version. Unknown versions reject with `unsupported_schema_version`; do not auto-migrate on load. | A pack authored for a newer schema cannot be guessed into the current shape. Future migration must be a separately versioned, deterministic, bounded operation. | Chief Architect + PIXEL-03 |
| Engine API version | Treat the pack's major.minor declaration as a minimum required engine API. Accept only when major matches and runtime minor is greater than or equal to the declared minor. | A newer runtime minor may load an older-minor pack only if the project guarantees additive, backward-compatible minor releases. Major mismatch or runtime minor below requirement rejects. | Chief Architect + PIXEL-03 + NOVA-02 |
| Version spelling | Parse numeric components as integers and require canonical decimal spelling (no signs, whitespace or leading zeroes except `0`). | Prevents ambiguous string comparisons such as `1.10` versus `1.9`. Existing schema regex may need a future approved tightening; do not change it now. | Chief Architect + PIXEL-03 |
| Desktop compatibility IDs | Treat declared desktop IDs as an allowlist/target constraint, not as an optional feature request. Unknown or non-matching required desktop targets reject. | Avoids activating a pack on an unclaimed desktop environment. Exact semantics need confirmation against sample packs and ATLAS platform IDs. | Chief Architect + ATLAS-01 |
| Required surfaces | Require every declared `required_surfaces` ID to be supported by the selected adapter set; otherwise reject before prepare/apply. | No silent partial activation for a surface the pack explicitly requires. | Chief Architect + NOVA-02 |
| Optional effects/namespaces | Omit only capabilities explicitly classified as optional by the frozen contract; return structured per-capability diagnostics. Never infer optionality from an unknown identifier. | Allows graceful degradation without hiding missing required functionality. The current manifest does not encode a general required/optional flag for every namespace. | Chief Architect + NOVA-02 + PIXEL-03 |
| Consumer projection | Define a versioned normalized snapshot; keep manifest storage paths private. Preserve `icon_set` as an asset role unless reviewers explicitly approve a separate icon namespace. | Adapter contracts can evolve independently of manifest JSON layout. Surface IDs are negotiated separately from token namespaces. | Chief Architect + NOVA-02 + PIXEL-03 |
| Accessibility | Keep accessibility policy engine-enforced and outside optional namespace negotiation. User/system high-contrast and reduced-motion overrides take precedence over pack values. | An adapter cannot downgrade accessibility requirements by omitting a capability. | Chief Architect + NOVA-02 |
| Migration | No implicit migration in the activation path. If later approved, migrations must be explicit, deterministic, bounded, version-to-version steps and validated again after transformation. | Unknown source/target paths reject rather than best-effort mutate. | Chief Architect + PIXEL-03 |

### Acceptance examples reviewers should confirm

Assuming the recommended engine API rule is approved:

- Runtime `1.4` with pack requirement `1.2`: accept the API-version check.
- Runtime `1.2` with pack requirement `1.4`: reject as engine API too old.
- Runtime `2.0` with pack requirement `1.4`: reject major mismatch; no implicit cross-major compatibility.
- Runtime `1.10` with pack requirement `1.9`: accept numeric minor comparison, not lexicographic comparison.
- Pack schema `1.0.0`: validate only through the explicitly supported v1 schema.
- Pack schema `1.1.0` or `2.0.0`: reject until a corresponding schema and migration/compatibility policy is explicitly supported.
- A missing required surface: reject before any adapter mutation; retain the last-known-good active snapshot.
- An unsupported optional effect: omit with a diagnostic only after the contract classifies that effect as optional.

### Approval checklist

1. Chief Architect: approve/reject the schema-version rule, engine API comparison rule, migration stance, and task ID.
2. NOVA-02: approve/revise required-surface behavior, normalized namespace projection, optional-effect reporting, and adapter capability semantics.
3. ATLAS-01: publish canonical desktop/platform IDs and supported Fedora/Plasma/Qt baseline.
4. Coordinator/repository administrator: verify required checks are enforced and confirm the shared-contract baseline, then resolve Issue #50.

Until those approvals are recorded, all examples above remain proposals. No compatibility implementation, schema edits, activation/apply/reload code, or contract conformance claim is authorized by this document.

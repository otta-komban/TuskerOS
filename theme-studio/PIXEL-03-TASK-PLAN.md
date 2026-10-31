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

**Deliverable:** `ACCESSIBILITY-AUDIT.md`, `runtime/accessibility_audit.py`, and `tests/test_accessibility_audit.py`.

- Added an opt-in diagnostic for semantic text, accent, focus and border color pairs. It does not gate pack validation or activation and does not modify the shared theme schema.
- Text and accent pairs use a 4.5:1 static threshold; focus pairs use 3:1. Alpha colors return `not_evaluated` because the effective result depends on compositing.
- Border contrast returns `review`, not pass/fail, because the manifest alone cannot tell whether a border is decorative or communicates a meaningful UI component boundary.
- Test coverage: known black/white 21:1 reference, all three starter theme color sets, a low-contrast negative case, alpha handling, missing roles, malformed color values and non-mapping input.
- Local scratch-fixture test result: **7 tests passed**. The fixture used the semantic color values copied from the three branch starter packs; this was not a full repository checkout or full Theme Studio test-suite run.
- No desktop rendering, Plasma runtime, apply/reload, or rollback behavior was tested. This diagnostic is not a WCAG conformance certification.
- Issue #50 remains open; no shared contract or schema changes were made.

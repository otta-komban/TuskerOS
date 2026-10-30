# TuskerOS Theme Studio

Status: Phase 1 architecture baseline (draft; desktop and marketplace contracts require owner review).

This directory owns the declarative theme format, Theme Engine architecture, theme validation rules, visual tokens, and Theme Studio design. KDE shell implementation and desktop surfaces remain NOVA-02-owned; marketplace catalog/install workflows remain FORGE-09-owned.

## Phase 1 deliverables

- `ARCHITECTURE.md`: engine boundaries, lifecycle, persistence, failure behavior, risks.
- `schema/theme-pack.schema.json`: versioned, strict JSON Schema for declarative theme packs.
- `contracts/desktop-contract.md`: proposed integration contract for NOVA-02.
- `contracts/marketplace-contract.md`: proposed package handoff for FORGE-09.
- `../themes/*/theme.json`: starter examples exercising the same format.

## Safety invariants

1. A theme is data plus inert assets, never a program.
2. No shell snippets, scripts, hooks, commands, QML/JS/Python, plugins, binaries, or executable payloads are accepted.
3. The loader validates the complete manifest and every referenced asset before activation.
4. Preview is isolated from the active theme; apply is transactional and rollback-capable.
5. Accessibility/system safety overrides always win over theme preferences.
6. Unknown schema versions and unsupported surfaces fail closed to the built-in default.

## Validation

The schema is normative for manifest shape. Runtime validation must additionally check asset existence, size limits, content type, digest, path containment, license/provenance metadata, and platform compatibility. Schema-valid does not mean trusted or safe to install.

## Theme Pack v1 asset policy

V1 accepts PNG/JPEG/WebP images, TTF/OTF/WOFF2 fonts, and OGG/WAV sounds. SVG is deliberately excluded because it may carry active content. Asset references use semantic roles and must resolve to declared asset IDs of the expected kind. The schema allowlists known desktop surface IDs. Runtime validation must still sniff actual file content, enforce size budgets, verify SHA-256, reject symlink escapes and use safe decoders; JSON Schema alone cannot establish file safety.

## Developer validation

From the repository root:

```sh
python -m pip install -r theme-studio/requirements-dev.txt
python -m unittest discover -s theme-studio/tests -v
```

The tests validate the Draft 2020-12 schema and starter manifests, and include negative cases for executable extension fields, SVG assets, path traversal, unknown surfaces and invalid asset-role references. Asset-role and duplicate-ID checks are runtime semantic checks; JSON Schema alone does not enforce cross-field references or uniqueness by an object property.

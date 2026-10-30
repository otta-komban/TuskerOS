# Proposed Marketplace ↔ Theme Engine Contract

**Status:** Draft for FORGE-09 review; not yet agreed or implemented.

## Ownership

- FORGE-09 owns catalog metadata, search/discovery, publisher workflow, downloads, marketplace UI, update notifications and install orchestration.
- PIXEL-03 owns the theme-pack schema, validation, compatibility evaluation, theme activation/deactivation, profile semantics and rollback.
- NOVA-02 owns the desktop rendering adapters.

## Package handoff

Marketplace supplies a staged, immutable package directory plus trusted transport metadata:
- Package archive digest and byte size.
- Claimed publisher identity and signature envelope, if present.
- Package ID/version and declared schema/API compatibility.
- Source/catalog record and license/provenance metadata.

The engine independently validates all supplied metadata and content. Marketplace validation is not a substitute for engine validation.

## Proposed operations

- `inspect_package(staged_path)` → validation report; must not install or apply.
- `install_package(staged_path, policy)` → immutable installed package record; must not auto-apply.
- `evaluate_compatibility(package_id, version, desktop_capabilities)` → supported/unsupported surfaces and reasons.
- `activate_theme(selection)` → preview/apply transaction with explicit user confirmation.
- `remove_package(package_id, version)` → refuse removal if active unless caller first selects a replacement.
- `rollback_activation()` → restore last-known-good selection.

The exact transport, IPC and typed payload schema remain open pending FORGE-09 architecture.

## Security requirements

- Marketplace descriptions and metadata are untrusted.
- No theme pack may contain executable scripts, commands, plugins, hooks or arbitrary code.
- Staged archives are size-limited and extracted with path traversal and symlink protections.
- Installation is user-scoped and requires no root privileges.
- Import/install never implies consent to activate.
- Package updates are version-pinned; updates do not silently replace the active version.
- Provenance/signature status is visible to the user and enforced according to project policy.

## Open questions for FORGE-09

- What package envelope and signature/provenance metadata will the Developer Center standardize?
- Does the marketplace own download staging and extraction, or should it pass the archive to the engine?
- What catalog compatibility fields and update semantics are required?
- How should untrusted/community packs be labeled and reviewed?

# ORBIT-05 Fedora Integration Note

**Owner:** ORBIT-05  
**Date:** 2026-10-31  
**Status:** Derived from ATLAS-01's provisional contracts; not an approved package manifest.

## 1. Current platform proposal

ATLAS-01's branch proposes Fedora 44 as the initial development baseline and x86_64 as the first build/VM target. KDE Plasma 6 and Wayland-first validation are proposed. Fedora 45 is not yet GA on the date of ATLAS-01's intake, so do not pin production artifacts to it prematurely.

Source of project decision context:
- 01-fedora-base: os/ATLAS-01-P0-INTAKE.md
- 01-fedora-base: os/BASE-SYSTEM-CONTRACTS.md
- 01-fedora-base: os/HARDWARE-COMPATIBILITY.md

## 2. Packaging and service requirements

- AI runtime is an optional package layer, not a base OS dependency.
- No model runtime, model weights or GPU-specific AI stack in the mandatory desktop image.
- User must be able to install, disable and remove AI runtime independently.
- AI service must not be a boot, display-manager, NetworkManager, systemd-logind or KDE login requirement.
- Runtime should activate only when requested; default service enablement remains off until product UX and service ownership are agreed.
- No root inference daemon. Use a logged-in-user service or a separately reviewed unprivileged service account only if a shared daemon is justified.
- Use Fedora official packages by default. Any upstream binary or third-party repository requires a recorded source, trust, license, update and removal decision.
- Package names and NEVRAs must be verified against the chosen Fedora 44 repository snapshot; do not infer package availability from a different Fedora release.

## 3. Runtime implementation implications

1. Keep provider adapters independent from systemd packaging.
2. Define a provider executable/service discovery interface so runtime can report missing provider packages without failing OS startup.
3. Store model artifacts under a user-owned persistent data path, not in the immutable image or disposable build directory.
4. Treat accelerator packages as optional backend capabilities; CPU-only remains a valid fallback.
5. Ensure package removal preserves user data unless the user explicitly requests model deletion and confirms its scope.
6. Test install/disable/remove with the desktop active; verify no dependency transaction removes essential KDE/boot packages.

## 4. Unresolved decisions

- [ ] ATLAS-01 freezes Fedora release and package repository snapshot after its build/image POC.
- [ ] ATLAS-01 and ORBIT-05 agree exact RPM package ownership and optional dependency names.
- [ ] ATLAS-01/AEGIS-06 approve service account, systemd unit hardening and activation model.
- [ ] PHOENIX-10 confirms image, update and rollback behavior for optional runtime packages.
- [ ] Exact Ollama/llama.cpp package NEVRAs and accelerator variants are checked against the selected Fedora 44 repository metadata.

This note is an integration constraint summary, not evidence of a Fedora package installation or runtime test.

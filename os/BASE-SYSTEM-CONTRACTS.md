# ATLAS-01 Base System Contracts (Provisional)

**Phase:** P1.2–P1.3 — package, service and OS integration boundaries  
**Date:** 2026-10-31  
**Status:** Provisional contract proposal for NOVA-02, NEXUS-07, AEGIS-06 and PHOENIX-10 review. No interface is frozen until its owning agent confirms it.

## 1. Base-system invariants

- Fedora remains bootable and usable without any Tusker service, model, remote-control agent, extension host or optional developer package.
- KDE Plasma/Wayland login must not require Tusker orchestration or local AI inference.
- Tusker services are optional system/user services and must be disableable without leaving the desktop in a failed state.
- No Tusker process receives unrestricted root privileges.
- Do not add new D-Bus names, Polkit action IDs, service users, filesystem paths or package names on behalf of another agent; request the owning agent's decision.
- User data and configuration must not be stored in disposable image/build paths.
- Core OS updates and recovery must remain possible when network access, Tusker runtime, model registry or extension ecosystem is unavailable.

## 2. Base installation profiles and hardware tiers\n\nThe product hardware tiers are 4 GB low-end, 8 GB standard and 16 GB+ powerful systems. These are capability-planning tiers, not performance certifications. Keep the base desktop lean; local model runtimes, developer toolchains and remote-control remain optional. See [HARDWARE-COMPATIBILITY.md](HARDWARE-COMPATIBILITY.md) for the required hardware matrix, test classes and support-claim rules.\n\nBase package profiles:\n- **Minimal desktop:** Fedora core, KDE Plasma/Wayland, network/storage/firmware/audio essentials and diagnostics; no model runtime or developer SDK.\n- **Recommended desktop:** minimal desktop plus curated common desktop applications and utilities.\n- **Optional bundles:** AI runtime, developer tools, remote control and additional applications, each independently installable/disableable/removable.\n\n## 3. Package layers

Package composition is separated into logical layers. The exact RPM list is deferred until NOVA-02 and NEXUS-07 confirm dependencies and the image POC validates package names in Fedora 44.

| Layer | Contents | Required in base? | Owner |
|---|---|---:|---|
| base-core | systemd, DNF, NetworkManager, storage, boot, SELinux, firmware, diagnostics and essential system utilities | Yes | ATLAS-01 |
| desktop-kde | KDE Plasma desktop, Wayland session, display manager, portals, audio/session integration and core desktop utilities | Yes for desktop image | NOVA-02 proposes; ATLAS packages |
| tusker-integration | OS-facing Tusker entry points, service units, desktop integration and package metadata | No; independently installable | TUSKER-04/NEXUS-07 with ATLAS packaging |
| security-integration | Polkit policy, privilege broker client/policy metadata, service hardening and audit integration | Minimal OS controls yes; Tusker-specific integration optional | AEGIS-06 owns policy; ATLAS packages |
| diagnostics | Hardware/system inspection, logs, recovery diagnostics and support tools | Small baseline subset | NEXUS-07 proposes |
| developer-tools | Compilers, SDKs, containers and build tools | No | FORGE-09 proposes |
| ai-runtime | model runners, accelerators, model storage and optional GPU-specific AI components | No | ORBIT-05 proposes |
| remote-control | remote endpoint and supporting components | No; off by default | PILOT-08/AEGIS-06 |

Package layer requirements:
- Each layer has an explicit package manifest, owner, reason for inclusion, license/source, optionality and test.
- Base packages must not pull in large model weights, optional developer SDKs, or network-exposed remote-control services.
- Avoid broad package groups when they obscure dependency ownership or create unwanted optional packages; use groups only when stable and audited.
- Package removal must not remove essential boot, login, networking, recovery, or security components.
- Tusker package removal/disable must not remove shared system dependencies still required by KDE or Fedora.

## 4. Package and repository policy

- Fedora official repositories are the default source.
- No third-party repository is enabled by default until an ADR records its maintainer, signing key trust, package scope, update policy, licensing and failure/disable procedure.
- RPM signature verification remains enabled; never use --nogpgcheck in production build or update workflows.
- Release builds must record repository IDs, repository metadata timestamps or snapshot identifiers, package NEVRAs, architecture, Fedora release, and build tool version.
- Avoid floating latest tags and unpinned external artifacts in release builds.
- Security updates are not delayed solely to preserve a frozen image; release inputs are refreshed through reviewed updates and tested before promotion.
- Separate runtime package dependencies from build-only dependencies; do not include compilers/toolchains in the final base unless justified.
- Produce an SBOM and package/license inventory for release artifacts where tooling permits.

## 5. Filesystem and state boundaries

Provisional mutable Fedora layout:
- /usr: vendor/system packages and read-only-by-convention files managed by RPM.
- /etc: administrator/system configuration; configuration changes require documented ownership and migration behavior.
- /var: persistent mutable system state, caches, logs and service state.
- /var/lib/<service>: persistent service state for system services, owned by the corresponding service account.
- /var/cache/<service>: regenerable service cache.
- /home: user data; never overwritten by routine image upgrades.
- /run: transient runtime state only.
- /opt and /usr/local: avoid for RPM-managed Tusker components unless a specific packaging reason exists.

If bootc is selected later, re-evaluate the contract for read-only deployment content, /etc merge/rollback, /var persistence and system service update semantics before implementation. Do not silently apply mutable-DNF assumptions to an image-based deployment.

## 6. systemd service conventions

Proposed requirements for all Tusker-owned system services:
- Separate service accounts; no shared root-owned daemon account unless a reviewed exception exists.
- Explicit User, Group, StateDirectory, CacheDirectory and RuntimeDirectory where applicable.
- NoNewPrivileges, PrivateTmp, restrictive filesystem/device/network controls and syscall filters where compatible; AEGIS-06 owns final hardening profiles.
- Restart policy must avoid crash loops; use rate limiting and clear failure state.
- Do not add Tusker units to multi-user.target or graphical login as hard requirements unless an explicit required system function is approved.
- AI/runtime and remote-control services must be disabled/off by default unless the user opts in.
- Avoid Before, Requires or BindsTo edges from core OS boot/login targets to Tusker services.
- A Tusker service failure must not make display-manager, NetworkManager, systemd-logind, or the default KDE session fail.
- All units must be tested with service disabled, unavailable dependency, crash/restart and package removal.

No actual service unit or service account name is defined here; the owning agent must supply exact identifiers.

## 7. D-Bus and desktop-session boundaries\n\nFedora KDE 44 is the provisional desktop baseline. Fedora's KDE 44 release notes report Plasma 6.6.4 and introduce Plasma Setup plus Plasma Login Manager for fresh installs. Use a Wayland-first validation target. Do not assume SDDM or an X11 session fallback without confirming the actual Fedora 44 package/service availability. Resolve Qt 6 and KDE Frameworks 6 package NEVRAs from the selected Fedora 44 repository metadata at build time and record them in the build manifest. NOVA-02 owns session UX and exact desktop dependency requests; ATLAS-01 owns the resolved Fedora package composition. Source: https://fedoramagazine.org/whats-new-in-fedora-kde-plasma-desktop-44/

- NOVA-02 owns Plasma shell, desktop UI and user-session integration.
- NEXUS-07 owns system capability discovery and typed system service APIs.
- TUSKER-04 owns task/orchestration interfaces.
- ATLAS-01 owns Fedora package dependencies and system-level enablement conventions only.
- Use the system bus for privileged/system-wide capability interfaces and the session bus for per-user desktop integration, subject to the owning agent's security review.
- D-Bus service activation must not create an implicit requirement for Tusker to start during login.
- Do not expose privileged methods directly over a session bus without AEGIS-06 authorization and identity review.

## 8. Polkit and privileged operations

- AEGIS-06 owns the policy model, action identifiers, authorization decisions, approval semantics and audit requirements.
- ATLAS-01 packages the approved policy/service files and validates Fedora integration after receiving the contract.
- NEXUS-07 owns system tool implementations and must call the approved authorization path before privileged mutations.
- No general-purpose run-arbitrary-command-as-root API.
- Fail closed for unknown actions, missing policy service, malformed caller identity or authorization backend failure.
- Destructive install, disk, network, firmware and system settings changes require explicit, scoped authorization appropriate to the action.
- Never encode an allow-all default rule to simplify development.

## 9. Logging, diagnostics and recovery

- System services log to journald with useful unit names and structured metadata where practical.
- Secrets, access tokens, model prompts, private file contents and personal data must not be written to routine system logs.
- Diagnostics must distinguish OS boot/service health from Tusker application health.
- Recovery must be callable without the Tusker daemon, local model, remote service or extension runtime.
- Recovery/installer must not select destructive storage targets by enumeration order; PHOENIX-10 and NEXUS-07 own the exact identity contract.
- Package/update failures must leave the prior bootable OS or a documented recovery path; the exact mechanism depends on the update model decision.

## 10. Cross-agent questions

### NOVA-02
- Confirm KDE Plasma version/session package requirements for Fedora 44.
- Confirm Wayland-first and X11 fallback expectations.
- Identify required portals, display manager, audio, input and session startup dependencies.
- Confirm no Tusker service is a hard requirement for desktop login.

### NEXUS-07
- Confirm service/D-Bus names, hardware capability interface and minimum OS tools.
- Confirm systemd service conventions, diagnostic and recovery dependencies.
- Identify required kernel interfaces, udev rules, firmware and optional hardware support packages.

### AEGIS-06
- Confirm Polkit action and broker packaging contract.
- Confirm service account, systemd hardening profile and audit/logging requirements.
- Confirm fail-closed behavior and package lifecycle for policy files.

### PHOENIX-10
- Confirm install artifact target, filesystem/update model and recovery constraints.
- Confirm Secure Boot, UEFI, partition and first-boot requirements.
- Confirm image metadata, signing, checksums, SBOM and release-channel expectations.

## 11. Review status

- [ ] NOVA-02 reviewed and confirmed.
- [ ] NEXUS-07 reviewed and confirmed.
- [ ] AEGIS-06 reviewed and confirmed.
- [ ] PHOENIX-10 reviewed and confirmed.
- [ ] Cross-agent contracts reconciled with Tusker master plan.
- [ ] Fedora 44 package manifests validated by an actual image build.
- [ ] Service failure/disable tests implemented.

Until these are checked, this file is a proposal, not an approved shared API.

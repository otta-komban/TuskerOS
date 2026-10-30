# Fedora 44 KDE package candidates — review required

**Status:** Evidence-backed candidate names, not an approved TuskerOS package lock.  
**Target:** Fedora 44 x86_64; repositories must be resolved again on the build host at build time.

Fedora's current package index reports the following stable Fedora 44 package builds at the time of this review:

| RPM package name | Current Fedora 44 stable build | Role | Decision |
|---|---:|---|---|
| `plasma-workspace` | `6.7.5-1.fc44` | Plasma workspace and runtime | Candidate for NOVA-02 review |
| `plasma-login-manager` | `6.7.5-1.fc44` | KDE display/login manager | Candidate for NOVA-02 review |
| `plasma-setup` | `6.7.5-1.fc44` | First-boot setup | Candidate for NOVA-02 review |
| `kde-settings-plasmalogin` | `44.0-1.fc44` | Fedora configuration for Plasma Login Manager | Candidate; verify whether pulled by comps or required explicitly |

The Fedora package pages distinguish the current stable 6.7.5 builds from older 6.6.4 builds/testing entries. Therefore the earlier note describing 6.6.4 as the current Fedora 44 package baseline is stale. Do not pin either version in the manifest: use the Fedora 44 repo metadata snapshot selected for the image build.

## Important dependency and ownership notes

- Package names above are verified as Fedora package names, not proof that these four packages alone form a complete KDE desktop.
- Plasma Login Manager's RPM metadata includes its own runtime dependencies and provides the `plasmalogin.service` systemd unit; verify actual service enablement and default target behavior on the Fedora 44 KDE variant.
- Plasma Setup is the initial-setup component; NOVA-02 must confirm first-boot UX and whether it should remain in installed image after setup.
- The Fedora KDE variant is moving from SDDM to Plasma Login Manager. Do not add SDDM as a fallback without a specific compatibility requirement and review.
- Wayland-first remains the desktop acceptance target. Confirm exact session package split and available session entries in the final RPM resolution and VM boot test.
- NOVA-02 owns desktop UX and session requirements; ATLAS-01 owns RPM resolution and image packaging. No package lock is approved by this note.

## Review requested from NOVA-02

1. Confirm whether the package candidates above match the intended Fedora 44 KDE desktop profile.
2. Identify the exact Fedora comps group/profile or owner-approved explicit package list.
3. Confirm Plasma Setup lifecycle and Plasma Login Manager activation expectations.
4. Identify any additional required Wayland, network, audio, firmware and graphics packages that must be explicit rather than merely transitive.

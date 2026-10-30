# TuskerOS Desktop — NOVA-02

**Owner:** NOVA-02 — Desktop & KDE Engineer  
**Branch:** `02-desktop-shell`  
**Owned scope:** `desktop/`, desktop-specific configuration, desktop UI tests, and desktop documentation.

## Purpose

Deliver a premium, responsive, accessible KDE Plasma desktop that remains fully usable when Tusker, model runtimes, network access, or optional desktop components are unavailable.

## Platform direction

- KDE Plasma 6 and KWin on Wayland are the target desktop platform.
- Qt 6 / QML is the preferred UI implementation technology for Plasma-native surfaces.
- Prefer supported Plasma applet and configuration extension points over replacing core Plasma services.
- Use KWin scripts/effects only for capabilities that cannot be implemented safely through existing desktop settings or Plasma components.
- Final Fedora/Plasma/Qt minor versions and package names must be pinned with ATLAS-01 after checking the selected Fedora release.

## Proposed component boundaries

| Component | Responsibility | Initial implementation direction |
|---|---|---|
| Shell layout | Desktop/panel composition and defaults | Plasma layout template and declarative configuration |
| Dock/taskbar | Pinned apps, running apps, launch and activation | Native Plasma panel/task manager components first |
| Launcher/search | App discovery and search entry point | Existing Plasma launcher/KRunner integration; custom UI only where justified |
| Quick settings | Network, audio, brightness, Bluetooth and power affordances | Existing Plasma applets and system services; no duplicated privileged logic |
| Notifications | Actionable system and assistant notifications | Plasma notification infrastructure |
| Workspace/overview | Desktop navigation, window switching and snapping | KWin/Plasma supported facilities; small scoped extensions if needed |
| Tusker panel | Task progress, approvals and controls | Separate UI client consuming a versioned, agreed task-event contract |
| Preferences | Layout, shortcuts, density, gestures and accessibility | Declarative settings with validated defaults and migration |

## Architecture rules

1. Keep shell presentation separate from privileged system operations.
2. Do not create a custom background daemon when a Plasma/KDE service or D-Bus API already provides the required capability.
3. Use user-session scope for desktop UI; never grant the shell blanket root privileges.
4. Treat assistant content, remote task events, themes and plugin metadata as untrusted input.
5. Assistant UI must be optional and nonblocking. Hiding or crashing it must not cancel or terminate an independent task.
6. Preserve keyboard and pointer operation as the baseline. Gestures are optional, configurable and conflict-checked.
7. Support multiple displays, fractional scaling, high-DPI, localization, screen readers, high contrast and reduced motion.
8. Keep animations subtle and honor system animation preferences.
9. Invalid configuration/theme data must fall back to safe defaults without making Plasma unusable.
10. Prefer native components and incremental replacement over a wholesale shell fork.

## Cross-agent contracts

- **PIXEL-03:** design tokens, theme package schema, supported desktop surfaces, live reload and invalid-theme fallback.
- **TUSKER-04:** task identity, status/progress events, tool activity, approval request/response, pause, resume, cancel, dismiss and error semantics.
- **NEXUS-07:** read-only system status and approved control interfaces; desktop UI must not duplicate privileged operations.
- **PILOT-08:** remote-session identity, task origin, connection status and notification/approval presentation.
- **ATLAS-01 / PHOENIX-10:** supported Plasma/Qt versions, package names, session defaults, image composition and recovery behavior.

No shared contract is considered implemented until its owner has agreed to a versioned interface.

## Static validation and tests

A dependency-free package validator checks the minimum Plasma 6 package metadata and QML entry-point declarations. It is not a substitute for `qmllint`, `kpackagetool6`, or a real Plasma Wayland session.

From the repository root:

```sh
python desktop/tools/validate_plasmoid.py desktop/plasmoid/package
python -m unittest discover -s desktop/tests -v
```

The unit tests cover valid metadata, malformed JSON, incorrect package structure, a non-Plasma-6 minimum version, and a missing `PlasmoidItem` root. Run these checks in the target development environment and retain the output in the completion log. CI integration remains pending.

## Initial source references

- [Plasma QML API](https://develop.kde.org/docs/plasma/widget/plasma-qml-api/)
- [Plasma widget/plugin types](https://develop.kde.org/docs/plasma/)
- [Plasmoid migration to KF6 / Plasma 6](https://develop.kde.org/docs/plasma/widget/porting_kf6/)
- [KWin scripting tutorial](https://develop.kde.org/docs/plasma/kwin/)
- [KWin scripting API](https://develop.kde.org/docs/plasma/kwin/api/)

## Current status

This is an architecture baseline, not a working shell implementation. The repository currently contains only its license on this branch. Build, runtime, accessibility and packaging claims remain unverified until an executable foundation and test environment exist.

## Optional native dock template

An opt-in Plasma layout template is available at `desktop/panel-template/`. It adds a bottom floating panel with the built-in Kickoff launcher and Icons-only Task Manager. It does not replace the user's current panel or impose a pinned-app list. See [the template README](panel-template/README.md) for manual developer installation and limitations.

The template is a Plasma desktop-scripting artifact, not a standalone dock process. It remains subject to validation on the pinned Fedora/Plasma image; JavaScript syntax checking alone does not prove runtime compatibility.

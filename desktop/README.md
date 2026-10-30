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

Dependency-free validators check the applet package metadata/QML entry point and the optional dock template metadata/layout invariants. They do not replace `qmllint`, `kpackagetool6`, or a real Plasma Wayland session.

From the repository root:

```sh
python desktop/tools/validate_plasmoid.py desktop/plasmoid/package
python desktop/tools/validate_panel_template.py desktop/panel-template
python -m unittest discover -s desktop/tests -v
node --check desktop/panel-template/contents/layout.js
```

The panel-template validator checks the layout-template service metadata, required native launcher/task-manager widgets, bottom-panel intent and absence of selected destructive panel operations. These are static checks only: they do not establish that the installed Plasma build accepts the metadata or widget IDs. CI integration and runtime validation remain pending.

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

The template is a Plasma desktop-scripting artifact, not a standalone dock process. JavaScript syntax and static structure checks do not prove runtime compatibility on the pinned Fedora/Plasma image.

## Dock template installation and recovery

The optional native dock template can be installed for the current user without sudo:

```sh
python desktop/tools/install_panel_template.py
```

The installer uses `$XDG_DATA_HOME` (or `~/.local/share`), refuses existing or symlink destinations, stages the copy before publishing it, and writes an ownership marker. It never overwrites existing user data. To remove only its own marked installation:

```sh
python desktop/tools/install_panel_template.py --remove
```

There is no force-overwrite option. Inspect an existing destination manually. Installing the template only makes it available to Plasma; the user explicitly selects it from Add Panel if supported. Existing panels and their configuration are not modified. See [the dock template README](panel-template/README.md).

Installer unit tests cover installation, no-overwrite, symlink refusal, marked removal and refusal to remove unmanaged directories. Static tests do not validate Plasma runtime compatibility.


## Automated desktop CI

The `.github/workflows/desktop-validation.yml` workflow runs on desktop-related pushes to `02-desktop-shell`, pull requests targeting `main`, and manual dispatch. It runs the full desktop unittest discovery suite, both static package/template validators, and `node --check` for the panel layout script.

The workflow uses GitHub-hosted Ubuntu with Python 3.12 and Node.js 22, requests read-only repository contents permission, and does not start a Plasma session or claim runtime validation. Check the Actions run for the actual result; workflow creation alone is not a passing CI result.

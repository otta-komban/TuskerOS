# TuskerOS Desktop — NOVA-02

**Owner:** NOVA-02 — Desktop & KDE Engineer  
**Branch:** `agent/02-desktop-shell`  
**Owned scope:** `desktop/`, desktop-specific configuration, desktop UI tests, and desktop documentation.

## Settings UX and persistence

The Qt Quick Controls preferences surface is in `desktop/settings/main.qml`.
It covers panel layout, assistant visibility and accessibility preferences.
The host injects a narrow adapter around `SettingsController`; QML never writes
configuration files directly. Updates are validated and atomically persisted
before being published to the UI. Restore defaults requires explicit
confirmation. See [settings UI](settings/README.md) and
[settings persistence contract](config/README.md).

Schema-v0 and unversioned preferences migrate to v1 through the same atomic
mode-0600 writer. Invalid, symlinked, duplicate-key and future-version input
fails closed and is not overwritten. Backend and source-level accessibility
tests are included. Qt/Plasma runtime and screen-reader checks remain pending;
this source-level work is not a graphical runtime acceptance claim.

# TuskerOS Desktop — NOVA-02

**Owner:** NOVA-02 — Desktop & KDE Engineer  
**Branch:** `agent/02-desktop-shell`  
**Owned scope:** `desktop/`, desktop-specific configuration, desktop UI tests, and desktop documentation.

## Settings UX and persistence

The runnable Qt Quick preferences application is launched by
`/usr/libexec/tuskeros/settings` and appears as **TuskerOS Desktop Settings**
in the desktop settings application menu. Package the complete `desktop/`
Python package under `/usr/lib/tuskeros/desktop/`, the executable launcher
under `/usr/libexec/tuskeros/settings` (0755), and its desktop entry under
`/usr/share/applications/tuskeros-settings.desktop` (0644). The package
requires Python 3, PySide6 Qt 6 and Qt Quick Controls 2.

The Qt host injects a narrow `SettingsBackend` around `SettingsController`;
QML never writes configuration files directly. Updates are validated and
atomically persisted before being published to the UI. Restore defaults
requires explicit confirmation. The branch CI now installs PySide6 and loads
the actual QML window with Qt's offscreen platform; this is a real Qt/QML
runtime smoke test, not just a source-string check. See [settings UI](settings/README.md)
and [settings persistence contract](config/README.md).

Schema-v0 and unversioned preferences migrate to v1 through the same atomic
mode-0600 writer. Migration reads only bounded regular files and rejects
symlinks, duplicate keys and unsupported future versions without rewriting
them. Invalid settings cannot be overwritten by ordinary UI edits; the user
must explicitly confirm restoring defaults. Fedora Plasma session startup,
graphical settings interaction, keyboard navigation and screen-reader checks
remain separate runtime acceptance items.

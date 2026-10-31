# TuskerOS desktop settings UI

`main.qml` is the Qt Quick Controls preferences surface. `app.py` is its
working Qt host: it creates a `SettingsController`, injects the narrow
`SettingsBackend` QObject into the QML context, then loads the UI. The backend
exposes only detached `read()`, `status()`, validated `update(patch)`, and
`reset()` operations. QML has no direct filesystem or privileged-operation
access.

## Package layout

| Source | Installed path | Mode |
|---|---|---:|
| Complete `desktop/` Python package | `/usr/lib/tuskeros/desktop/` | files 0644 |
| `desktop/settings/tuskeros-settings` | `/usr/libexec/tuskeros/settings` | 0755 |
| `desktop/settings/tuskeros-settings.desktop` | `/usr/share/applications/tuskeros-settings.desktop` | 0644 |

The package requires Python 3, PySide6 Qt 6, and Qt Quick Controls 2. The
launcher inserts `/usr/lib/tuskeros` as the private module root. Package
dependencies must include the PySide6 and Qt Quick Controls runtime packages
for the target Fedora release.

Controls have accessible names, keyboard operation and system palette colors.
Save failures preserve the last persisted settings and are announced in an
assertive accessibility live region. If existing settings are invalid,
ordinary edits are blocked until the user explicitly confirms Restore defaults.

Run backend and host-contract tests with:
`python -m unittest desktop.tests.test_settings_controller desktop.tests.test_settings_migration desktop.tests.test_settings_ui desktop.tests.test_settings_app -v`.

The Qt host requires PySide6. Graphical QML runtime, keyboard navigation and
screen-reader validation still require the supported Plasma/Qt environment.

# TuskerOS desktop settings UI

`main.qml` is the Qt Quick Controls preferences surface. `app.py` is its
runnable Qt host: it creates a `SettingsController`, injects the narrow
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

## Validation

The GitHub desktop-validation workflow installs PySide6 and runs the entire
desktop unittest suite with Qt's offscreen platform. The runtime test launches
the actual `desktop.settings.app` module, loads the real QML file and checks
that Qt creates its window; this catches missing QML imports and QML load
errors that source-string tests cannot detect. Run locally with:

```sh
python -m pip install "PySide6>=6.8,<7"
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
  python -m unittest desktop.tests.test_settings_qt_runtime -v
```

Controls have accessible names, keyboard operation and system palette colors.
Save failures preserve the last persisted settings and are announced in an
assertive accessibility live region. If existing settings are invalid,
ordinary edits are blocked until the user explicitly confirms Restore defaults.
If that reset write fails, the UI reports failure, the source file remains
unchanged and the recovery lock stays active; a successful reset is required
before preferences can be edited again.

The offscreen test is not a replacement for real Plasma session, keyboard
navigation or screen-reader acceptance. Those checks still require the
supported Fedora KDE/Plasma environment.

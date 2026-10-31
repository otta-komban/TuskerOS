# Desktop settings contract (schema v1)

The dependency-free settings module owns presentation preferences only. It does
not store credentials, privileged system state, task history, or remote-session
secrets. Defaults and validation rules remain defined by
`desktop/config/settings.py`.

## UI integration

The Qt Quick Controls surface is in `desktop/settings/main.qml`; the runnable
host is `desktop/settings/app.py`. The host injects a narrow QObject adapter
backed by `desktop/config/controller.py` before loading QML. The adapter
exposes only detached `read()`, validated transactional `update(patch)`,
and `reset()`. A new candidate is published only after the atomic disk write
succeeds. Failed writes leave the last valid state active. The installed
desktop entry is `tuskeros-settings.desktop`.

## Migration and persistence

`desktop/config/migrations.py` upgrades unversioned and explicit schema-v0
preferences to schema v1. Migration reads at most 64 KiB from a regular file,
rejects final-component symlinks and duplicate JSON keys, validates the full
candidate and uses the same mode-0600 atomic writer as normal updates.
Malformed, duplicate-key, symlinked, oversized, excessively nested and unsupported future-version
files are not rewritten. When settings are invalid, normal UI updates remain
blocked; only the separately confirmed Restore defaults action can replace
them. A failed migration write preserves the original file for recovery.
Future schema changes require a new migration and regression tests; unknown
future versions must never be silently downgraded.

## Validation

Run:
`python -m unittest desktop.tests.test_settings_controller desktop.tests.test_settings_migration desktop.tests.test_settings_ui desktop.tests.test_settings_app -v`.

These tests exercise restart persistence, invalid update rejection, write
failure recovery, reset, detached reads, bounded migration and source-level
host/accessibility contracts. Qt runtime, keyboard navigation and screen-reader
testing still require the supported Plasma/Qt environment.

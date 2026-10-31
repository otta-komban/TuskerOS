# Desktop settings contract (schema v1)

The dependency-free settings module owns presentation preferences only. It does
not store credentials, privileged system state, task history, or remote-session
secrets. Defaults and validation rules remain defined by
`desktop/config/settings.py`.

## UI integration

The Qt Quick Controls surface is in `desktop/settings/main.qml`. The host
injects a narrow adapter backed by `desktop.config.controller.SettingsController`.
The controller exposes detached `read()`, validated transactional
`update(patch)`, and `reset()`; it publishes an in-memory candidate only after
the atomic disk write succeeds. Failed writes leave the last valid state active.

## Migration and persistence

`desktop/config/migrations.py` upgrades unversioned and explicit schema-v0
preferences to schema v1. Migration validates the complete candidate and uses
the same mode-0600 atomic writer as normal updates. Malformed, duplicate-key,
symlinked, oversized and unsupported future-version files are not rewritten;
the UI receives safe defaults and a non-sensitive error. A failed migration
write preserves the original file for recovery. Future schema changes require
a new migration and regression tests; unknown future versions must never be
silently downgraded.

## Validation

Run:
`python -m unittest desktop.tests.test_settings_controller desktop.tests.test_settings_migration desktop.tests.test_settings_ui -v`.

These tests exercise restart persistence, invalid update rejection, write
failure recovery, reset, detached reads, migration and source-level accessibility
contracts. Qt runtime, keyboard navigation and screen-reader testing still
require the supported Plasma/Qt environment.

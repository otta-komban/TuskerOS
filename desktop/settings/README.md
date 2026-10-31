# TuskerOS desktop settings UI

`main.qml` is the Qt Quick Controls settings surface. The desktop host injects
a `SettingsBackend` adapter around `desktop.config.controller.SettingsController`;
QML does not open files or bypass validation. Controls have accessible names,
keyboard operation and system palette colors. Save failures preserve the last
persisted settings and are announced in an assertive accessibility live region.
Restore defaults requires confirmation.

The controller is UI-toolkit independent so persistence can be tested without
starting Qt. The host adapter exposes only `read()`, `update(patch)` and
`reset()`; it must not expose privileged operations.

Run backend tests with:
`python -m unittest desktop.tests.test_settings_controller desktop.tests.test_settings_migration desktop.tests.test_settings_ui -v`.

QML runtime and screen-reader validation require the packaged Qt 6 / Plasma
runtime; source-level accessibility checks do not replace those tests.

# Desktop settings contract (schema v1)

The first desktop settings module is dependency-free Python. It deliberately owns only presentation preferences; it does not store credentials, privileged system state, task history, or remote-session secrets.

## Effective defaults

```json
{
  "schema_version": 1,
  "panel": { "enabled": true, "edge": "bottom", "icon_size": 48, "auto_hide": false },
  "assistant": { "enabled": false, "show_task_progress": true },
  "accessibility": { "reduced_motion": false, "high_contrast": false }
}
```

The assistant panel is disabled by default. Supported panel edges are `bottom`, `top`, `left`, and `right`; supported icon sizes are 24 through 96 in 8-pixel increments. Booleans are type-checked explicitly (Python booleans are not accepted as integer values). Unknown keys and unsupported schema versions are rejected rather than silently persisted.

## API

Import `load_settings`, `validate_settings`, `save_settings` from `desktop.config.settings`.

- `validate_settings(value)` returns a list of validation errors. Partial nested objects are accepted and merged with defaults.
- `load_settings(path)` returns `(effective_settings, errors)`. A missing file returns defaults without error; malformed, oversized, symlinked, or invalid input returns defaults with an error list.
- `save_settings(path, value)` validates before writing, creates parent directories, writes a complete effective config to a temporary file with mode `0600`, fsyncs it, and atomically replaces the destination. It refuses symlink destinations and raises `ValueError` for invalid input.

The caller chooses the user config path (recommended: `$XDG_CONFIG_HOME/tuskeros/desktop.json`, falling back to `~/.config/tuskeros/desktop.json`). This module does not read environment variables or perform any privileged operation. Integrate with the UI only after settings migration and desktop component contracts are agreed.

## Validation

Run `python -m unittest discover -s desktop/tests -v`. The CI workflow runs this suite on every desktop-related branch push and pull request. The tests cover defaults, partial merges, strict keys/types, malformed and oversized files, atomic round-trip persistence, file permissions and symlink refusal.

Schema v1 is an initial desktop-owned contract, not yet a cross-agent integration contract. Future additions require a schema version/migration decision and tests. Do not persist transient task state or security/approval decisions here.


Regression coverage includes malformed root values, unsupported schema versions, and dangling symlinks; dangling links are checked before missing-file handling so they cannot silently appear absent.

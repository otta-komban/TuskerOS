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
- `load_settings(path)` returns `(effective_settings, errors)`. A missing file returns defaults without error; malformed, oversized, symlinked, duplicate-key, or invalid input returns defaults with an error list. Duplicate keys at any JSON object depth are rejected to avoid ambiguous last-key-wins parsing.
- `save_settings(path, value)` validates before writing, creates parent directories, writes a complete effective config to a temporary file with mode `0600`, fsyncs the file, atomically replaces the destination, and fsyncs the parent directory so the rename is durable. The temporary file descriptor is managed by a context manager, including on write/fsync failures. atomically replaces the destination. It refuses symlink destinations and raises `ValueError` for invalid input.

The caller chooses the user config path (recommended: `$XDG_CONFIG_HOME/tuskeros/desktop.json`, falling back to `~/.config/tuskeros/desktop.json`). This module does not read environment variables or perform any privileged operation. Integrate with the UI only after settings migration and desktop component contracts are agreed.

## Validation

Run `python -m unittest discover -s desktop/tests -v`. The CI workflow runs this suite on every desktop-related branch push and pull request. The tests cover defaults, partial merges, strict keys/types, malformed and oversized files, atomic round-trip persistence, file permissions and symlink refusal. The recovery CLI has separate tests for safe status output, explicit reset confirmation, XDG path resolution and symlink refusal.

## User recovery commands

Run a privacy-conscious validation check (it reports status/errors but does not print settings values):

```sh
python -m desktop.tools.settings_recovery check
```

Restore schema-v1 defaults only after explicit confirmation:

```sh
python -m desktop.tools.settings_recovery reset --yes
```

Both commands accept `--config /path/to/desktop.json` for a non-default file. The default path is `$XDG_CONFIG_HOME/tuskeros/desktop.json`, or `~/.config/tuskeros/desktop.json` when `XDG_CONFIG_HOME` is unset or relative. Reset uses the existing atomic mode-0600 writer and refuses symlink destinations. It replaces the settings file; copy it first if you may need its current values.

Schema v1 is an initial desktop-owned contract, not yet a cross-agent integration contract. Future additions require a schema version/migration decision and tests. Do not persist transient task state or security/approval decisions here.


Regression coverage includes malformed root values, unsupported schema versions, and dangling symlinks; dangling links are checked before missing-file handling so they cannot silently appear absent.


## Machine-readable schema

`settings.schema.json` publishes the same schema-v1 shape as a JSON Schema Draft 2020-12 artifact for editor completion and external tooling. The runtime Python validator remains authoritative for application loading and persistence; the JSON Schema does not replace it. Partial objects are valid by design, omitted values use runtime defaults, and unknown keys are rejected. The standard-library regression tests compare the schema's defaults, keys, version and enum constraints with `DEFAULT_SETTINGS`.

Run the consistency tests with:

```sh
python -m unittest desktop.tests.test_settings_schema -v
```

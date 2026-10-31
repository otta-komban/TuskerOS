# TuskerOS Dock panel template

Optional KDE Plasma layout template; not a replacement shell.

## Safe user-level installation

From the repository root:

```sh
python desktop/tools/install_panel_template.py
```

Default destination: `$XDG_DATA_HOME/plasma/layout-templates/com.tuskeros.desktop.dock`, or `~/.local/share/plasma/layout-templates/com.tuskeros.desktop.dock`.

The installer copies the template into a staging directory and publishes it by rename. It refuses existing or symlink destinations, does not use sudo, and never overwrites existing user data. It writes a management marker.

Remove only this installer's marked directory:

```sh
python desktop/tools/install_panel_template.py --remove
```

There is intentionally no force-overwrite option. Inspect any existing destination manually. Installation only makes the template available; the user still selects Add Panel / TuskerOS Dock from Plasma if supported. Existing panels are not modified.

## Static validation

```sh
python desktop/tools/validate_panel_template.py desktop/panel-template
python -m unittest discover -s desktop/tests -v
node --check desktop/panel-template/contents/layout.js
```

The validator checks template metadata and required native widget IDs. Installer tests check installation, no-overwrite, symlink refusal, marked removal and preservation of unmanaged directories. These are not Plasma runtime tests.

The installer tests passed in an isolated Python harness. The full desktop suite is expected to contain 15 static tests. The template has not been loaded by a Plasma 6 session; verify Add Panel discovery and widget plugin availability on the selected Fedora/Plasma build before shipping.

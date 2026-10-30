# TuskerOS Dock panel template

This is an optional KDE Plasma layout template, not a replacement shell.

## What it creates

- One bottom, centered, floating panel.
- The built-in Kickoff application launcher.
- The built-in Icons-only Task Manager for launching and switching running windows.

Plasma remains authoritative for application launching, search, window activation, and desktop-file handling. This template adds no custom process launcher, privileged helper, daemon, or AI dependency.

## Installation (manual developer test)

Copy this directory to the user's Plasma layout-template directory:

```sh
mkdir -p ~/.local/share/plasma/layout-templates
cp -a desktop/panel-template ~/.local/share/plasma/layout-templates/com.tuskeros.desktop.dock
```

Then open the Plasma desktop/panel context menu and choose Add Panel / TuskerOS Dock if the installed Plasma version exposes the template in its panel-template picker. If it does not appear, inspect Plasma logs and installed template metadata; do not overwrite the existing panel configuration as a workaround.

## Safety and behavior

- Selecting the template adds a panel; it does not remove existing panels.
- Existing panel configuration is not migrated or deleted.
- No pinned application list is imposed. Users can pin applications using the native task manager UI.
- Assistant/runtime/network outages do not affect this panel.
- The script uses Plasma desktop scripting and native widget plugin IDs.

## Static validation

From the repository root:

```sh
python desktop/tools/validate_panel_template.py desktop/panel-template
node --check desktop/panel-template/contents/layout.js
```

The validator checks required metadata and script invariants, including the native launcher/task-manager widget IDs and selected destructive operations. It is not a Plasma runtime test.

## Validation status

Static source review, five validator unit tests and JavaScript syntax checking have passed in an isolated harness. This template has not yet been loaded by a Plasma 6 session. Confirm the template metadata and panel API against the exact Fedora/Plasma build before shipping. Verify the template appears in Add Panel and that the installed task-manager plugin ID is available.

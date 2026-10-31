# TuskerOS Desktop Plasma 6 applet foundation

This is the first runnable UI component in the NOVA-02 desktop work. It is intentionally a small Plasma 6 applet package, not a replacement Plasma shell. It provides a real, installable surface while preserving the standard Plasma panel, launcher, task manager, notifications and system settings.

## Requirements

- KDE Plasma 6
- Qt 6 QML runtime
- Plasma SDK / `kpackagetool6`

The exact Fedora package names and supported minor versions must be confirmed with ATLAS-01 against the selected Fedora release.

## Install for the current user

From the repository root:

```sh
kpackagetool6 --type=Plasma/Applet --install desktop/plasmoid/package
```

Then open Plasma's Add Widgets interface and add **TuskerOS Desktop** to a panel or desktop. If Plasma already has an instance loaded, remove/re-add it or restart the Plasma shell using the platform-supported session procedure.

## Validate package metadata and QML

```sh
python3 -m json.tool desktop/plasmoid/package/metadata.json >/dev/null
qmllint desktop/plasmoid/package/contents/ui/main.qml
kpackagetool6 --type=Plasma/Applet --list
```

These are validation commands, not evidence of tests already run. Run them on a Plasma 6 development session and record the exact output before marking the P2 foundation checklist complete.

## Design constraints

- Plasma 6 applet root is `PlasmoidItem`.
- Plasma 6 package metadata declares `X-Plasma-API-Minimum-Version: 6.0` and `KPackageStructure: Plasma/Applet`.
- The applet contains no privileged operations, network calls, AI calls or background daemon.
- It does not modify or replace the user's desktop layout.
- It uses Plasma components so its controls follow the active Plasma style.

## Source references

- [Plasma widget setup](https://develop.kde.org/docs/plasma/widget/setup/)
- [Porting plasmoids to KF6 / Plasma 6](https://develop.kde.org/docs/plasma/widget/porting_kf6/)
- [Plasma QML API](https://develop.kde.org/docs/plasma/widget/plasma-qml-api/)

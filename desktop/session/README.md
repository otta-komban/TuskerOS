# TuskerOS Plasma Wayland session entry point

TuskerOS uses the stock KDE Plasma 6 Wayland session. This entry point is a thin
session descriptor and launcher wrapper; it does not fork Plasma, replace KWin,
start a private session daemon, or request elevated privileges.

## Package layout

Install these source files with the following package paths:

| Source | Installed path | Mode |
|---|---|---:|
| `desktop/session/launch.py` | `/usr/libexec/tuskeros/session-launcher` | `0755` |
| `desktop/session/tuskeros-wayland.desktop` | `/usr/share/wayland-sessions/tuskeros-wayland.desktop` | `0644` |

The descriptor is discoverable by SDDM. Selecting **TuskerOS (Plasma Wayland)**
executes the wrapper, which directly `execve`s `/usr/bin/startplasma-wayland`.
The wrapper preserves the login-manager environment and explicitly sets the
Wayland / KDE Plasma 6 session identifiers. It does not invoke a shell or
interpolate arguments.

The package must depend on the Fedora package that provides
`/usr/bin/startplasma-wayland`; ATLAS-01 must confirm the exact package NEVRA for
the selected Fedora repository snapshot before packaging. Do not bundle a
second Plasma session implementation.

## Validation

```sh
python -m unittest desktop.tests.test_session_launch -v
/usr/libexec/tuskeros/session-launcher --check
```

`--check` verifies only that the packaged Plasma executable exists and is
executable. It does not start a graphical session. The unit tests verify
session-environment construction, direct exec semantics, argument forwarding,
missing-binary behavior, launch failure handling, and the SDDM descriptor.

For runtime acceptance, use a disposable Fedora KDE VM, select the TuskerOS
session from SDDM, confirm a Plasma Wayland desktop is reached, log out and log
back in, and retain the VM/package/version metadata plus journal/session logs.
The unit suite is not a substitute for that VM smoke test.

## Rollback

From a TTY or a different working session, select the standard **Plasma
(Wayland)** session at SDDM. Package rollback removes only the TuskerOS session
descriptor and `/usr/libexec/tuskeros/session-launcher`; it must not remove or
modify Plasma packages, user configuration, panels, or the standard Plasma
session descriptor. No user settings are migrated or deleted by this wrapper.

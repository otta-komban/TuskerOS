# TuskerOS Plasma Wayland session entry point

TuskerOS uses the stock KDE Plasma 6 Wayland session. This entry point is a thin
freedesktop Wayland session descriptor and launcher wrapper; it does not fork
Plasma, replace KWin, start a private session daemon, or request elevated
privileges.

## Package layout

Install these source files with the following package paths:

| Source | Installed path | Mode |
|---|---|---:|
| `desktop/session/launch.py` | `/usr/libexec/tuskeros/session-launcher` | `0755` |
| `desktop/session/tuskeros-wayland.desktop` | `/usr/share/wayland-sessions/tuskeros-wayland.desktop` | `0644` |

The descriptor follows the standard Wayland session-file location and invokes
`/usr/libexec/tuskeros/session-launcher`. The wrapper directly `execve`s
`/usr/bin/startplasma-wayland`, preserves the login-manager environment, and
explicitly sets the Wayland / KDE Plasma 6 session identifiers. It does not
invoke a shell or interpolate arguments.

**Fedora 44 login-manager compatibility is a release gate.** Fedora's KDE
variants are transitioning from SDDM to Plasma Login Manager (PLM). The
standard session descriptor is intended to be display-manager-neutral, but
this branch has not yet verified that the selected Fedora 44 PLM build lists
and launches this custom entry. Do not add an SDDM dependency or claim PLM
support based only on the unit tests. Verify session discovery and launch on
the exact Fedora 44 image. If PLM does not expose the descriptor, pause
packaging and agree on its supported integration mechanism with ATLAS-01.

The package must depend on the Fedora package that provides
`/usr/bin/startplasma-wayland`; ATLAS-01 must confirm the exact package NEVRA
for the selected Fedora repository snapshot before packaging. Do not bundle a
second Plasma session implementation.

## Validation

```sh
python -m unittest desktop.tests.test_session_launch -v
/usr/libexec/tuskeros/session-launcher --check
```

`--check` verifies only that the packaged Plasma executable exists and is
executable. It does not start a graphical session. The unit tests verify
session-environment construction, direct exec semantics, argument forwarding,
missing-binary behavior, launch failure handling, and the session descriptor.

For runtime acceptance, use a disposable Fedora 44 KDE VM with its selected
default login manager (PLM for the Fedora 44 KDE profile). Confirm that the
TuskerOS entry is actually listed before selecting it, then verify a Plasma
Wayland desktop is reached, log out and log back in, and retain the
VM/package/version metadata plus journal/session logs. If the entry is absent
or launch fails, capture the evidence and stop; do not silently substitute
SDDM. The unit suite is not a substitute for this VM smoke test.

## Rollback

From a TTY or a different working session, select the standard **Plasma
(Wayland)** session using the installed login manager. Package rollback removes
only the TuskerOS session descriptor and
`/usr/libexec/tuskeros/session-launcher`; it must not remove or modify Plasma
packages, user configuration, panels, or the standard Plasma session
descriptor. No user settings are migrated or deleted by this wrapper.

# Fedora 44 / Plasma 6 runtime validation runbook

**Status:** reproducible test plan; not yet executed on a Fedora KDE host or VM.  
**Platform target:** Fedora 44 KDE, Plasma 6, Qt 6 / KF6, Wayland-first. Fedora's
Fedora 44 KDE package candidates now identify Plasma Login Manager (PLM) as the
default login manager instead of SDDM. Resolve exact package NEVRAs from the
chosen repository snapshot at test time; do not pin a stale minor version.

## 1. Preconditions and evidence capture

Use a disposable Fedora 44 KDE VM with UEFI firmware, a fresh user account, and
a snapshot taken before testing. Boot an actual Plasma Wayland session; a
container or headless Ubuntu runner is not a substitute for shell integration.

Record:

```sh
cat /etc/fedora-release
uname -m
echo "$XDG_SESSION_TYPE"
plasmashell --version
kwin_wayland --version
qtpaths6 --query QT_VERSION 2>/dev/null || true
systemctl status plasmalogin.service --no-pager || true
rpm -qa --qf '%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}\\n' | sort > fedora-rpm-manifest.txt
```

Keep the manifest, command output, VM image/build identifier, repository
metadata and screenshots/logs with the test report. Do not claim a version is
pinned merely because it was observed once.

## 2. Resolve tool packages before installing

Fedora's package index lists `qt6-qtdeclarative-devel` for Fedora 44 and its
file list includes Qt 6 `qmllint`. Confirm the executable path and package
ownership on the selected repository snapshot rather than assuming a command
alias:

```sh
sudo dnf repoquery --latest-limit=1 qt6-qtdeclarative-devel
sudo dnf repoquery --whatprovides '*/qmllint'
sudo dnf repoquery --whatprovides '*/plasmoidviewer'
sudo dnf repoquery --whatprovides '*/kpackagetool6'
rpm -ql qt6-qtdeclarative-devel | grep -E '/(qmllint|qmlformat)$' || true
```

Install only the resolved package(s) needed for the test. Do not assume
`plasmoidviewer` or `kpackagetool6` belongs to a particular RPM until
`repoquery` confirms it. Save the package NEVRAs and executable paths.

## 3. Static QML lint

Run the discovered Qt 6 linter against the applet QML entry point. On current
Fedora package layouts the binary may be under a Qt 6 libexec/bin directory;
use the path returned by `rpm -ql` / `command -v`.

```sh
qmllint --version
qmllint desktop/plasmoid/package/contents/ui/main.qml
```

If the executable is not on PATH, invoke its verified absolute path. Record
warnings and errors. A clean Qt lint is only a source-level signal: it does not
prove that Plasma imports, runtime context properties, package metadata, or
the applet lifecycle work.

## 4. Package validation and isolated applet launch

From the repository root, run the existing dependency-free checks first:

```sh
python -m unittest discover -s desktop/tests -v
python desktop/tools/validate_plasmoid.py desktop/plasmoid/package
python desktop/tools/validate_panel_template.py desktop/panel-template
node --check desktop/panel-template/contents/layout.js
```

Use the verified Plasma package tool to validate/list/install the package only
in the disposable VM. If `plasmoidviewer` is available, launch the applet in
its isolated test host and save stdout/stderr. Use the command's own `--help`
output to select supported flags for the installed Plasma release; do not copy
flags from another major version.

## 5. Real Wayland session and login-manager checks

Fedora 44 KDE is expected to use Plasma Login Manager (PLM). The session
descriptor in `/usr/share/wayland-sessions/` is designed as a standard
Wayland session entry, but custom-entry discovery under the selected PLM
package must be demonstrated, not assumed. In the disposable VM:

- record the installed login manager package and service, and confirm which
  login manager is active;
- confirm the TuskerOS session entry is listed; if it is absent, stop and
  investigate PLM's supported session integration rather than installing
  SDDM as an undocumented workaround;
- if listed, select it and verify the wrapper starts stock Plasma Wayland;
- confirm standard Plasma Wayland remains selectable as a recovery option;
- verify logout/login and a Plasma shell restart do not leave a broken session;
- applet can be installed, loaded, rendered and removed without shell errors;
- optional dock template is discoverable through Plasma's supported Add
  Panel/template UI;
- selecting the template creates the intended panel and native
  launcher/task-manager widgets;
- pre-existing panels and user configuration remain unchanged before explicit
  selection;
- panel can be removed and the normal Plasma panel/session remains usable;
- keyboard focus, launcher activation, task switching, high-DPI scaling and a
  second display are checked where VM support permits.

Capture exact steps, expected/actual outcomes, logs and screenshots. A
successful isolated applet viewer test is not a substitute for real Wayland
session checks.

## 6. Rollback and safety

Take a VM snapshot before package or panel changes. Prefer a disposable user
account. The dock-template installer is user-scoped and refuses to overwrite
existing destinations; test its install/remove behavior separately from
selecting a panel template. Never test destructive recovery against a user's
daily desktop profile. Keep the stock Plasma session and its login manager
intact as the recovery path.

## 7. Completion gate

Do not mark Fedora build/runtime checklist items complete until the evidence
bundle includes:

1. Fedora release, architecture, repository snapshot and RPM NEVRA manifest;
2. exact resolved package names and executable paths;
3. active login manager and evidence of custom-session discovery/launch;
4. QML lint output and all static test output;
5. applet package-tool / isolated-host output, if supported;
6. actual Plasma Wayland session test record, including dock discovery and
   rollback;
7. known limitations and any failures.

**Current result:** this runbook is documented only. No Fedora VM, Plasma
session, login-manager integration, QML lint, package installation, or applet
runtime test was executed as part of this change.

# NOVA-02 Desktop Engineering Plan

All checkboxes remain open until the task has been implemented or researched and its evidence has been recorded. Planning alone is not test evidence.

## P0 — Discovery and requirements

- [ ] Map core user journeys.
  - [ ] First boot and initial desktop orientation.
  - [ ] Launch, search, pin, switch and close applications.
  - [ ] Manage windows, virtual desktops and multiple displays.
  - [ ] Open quick settings and connect/disconnect common devices.
  - [ ] Receive, inspect and act on notifications.
  - [ ] Customize layout, appearance, shortcuts and accessibility.
  - [ ] Open, monitor and dismiss Tusker without interrupting tasks.
- [ ] Define desktop visual and interaction requirements.
  - [ ] Calm, consistent visual hierarchy and spacing.
  - [ ] Responsive behavior across screen sizes and scaling factors.
  - [ ] Keyboard-first and pointer-first workflows.
  - [ ] Touchpad/touchscreen gestures as optional enhancements.
  - [ ] Reduced-motion and high-contrast behavior.
- [ ] Inventory Plasma 6, KWin/Wayland, QML, accessibility and extension points.
  - [ ] Confirm Plasma 6 applet root and KF6 compatibility requirements.
  - [ ] Confirm supported panel/layout customization mechanisms.
  - [ ] Confirm launcher/KRunner integration options.
  - [ ] Confirm KWin scripting/effect capabilities and limitations.
  - [ ] Confirm multi-monitor and fractional-scaling constraints.
- [ ] Define acceptance criteria and known risks.
  - [ ] Desktop remains useful with network disconnected.
  - [ ] Desktop remains useful when Tusker/model services are stopped.
  - [ ] Standard keyboard and pointer operation is always available.
  - [ ] Shell customization failure has a safe recovery path.
- [ ] Record Fedora/KDE version decision with ATLAS-01.

## P1 — Architecture and contracts

- [ ] Finalize shell composition and component boundaries.
- [ ] Define desktop settings schema, defaults, validation and migration.
- [ ] Define keyboard shortcuts and conflict-resolution behavior.
- [ ] Define multi-monitor, scaling and per-output layout behavior.
- [ ] Agree theme token and reload contracts with PIXEL-03.
- [ ] Agree task/progress/approval/control event contract with TUSKER-04.
- [ ] Agree system status/control interface with NEXUS-07.
- [ ] Agree remote-session and task-origin presentation with PILOT-08.
- [ ] Record decisions, compatibility matrix and threat/performance considerations.

## P2 — Foundation

- [ ] Create a minimal Plasma 6 / Qt 6 desktop component skeleton.
- [ ] Add reproducible build and development instructions.
- [x] Document a reproducible Fedora/Plasma runtime-validation procedure.
  - Evidence: `desktop/validation/FEDORA-PLASMA-RUNTIME.md` records package discovery, Qt 6 QML lint, isolated applet validation, real Wayland-session checks, rollback and evidence requirements. This is a runbook, not an executed runtime test.
- [x] Add configuration parsing, validation and persistence.
  - Evidence: `desktop/config/settings.py` implements schema-v1 defaults, strict validation, safe fallback, partial merges, and atomic mode-0600 persistence with symlink refusal. The original eight tests in `desktop/tests/test_settings.py` passed in hosted CI run 41124464540 (23 total desktop tests). C0010 adds regression tests for invalid root values, unsupported schema versions and dangling symlinks; hosted CI run 41125249406 passed all 26 desktop unit tests, both static validators and the dock-template JavaScript syntax check. UI integration and future schema migration remain open.
- [x] Add desktop test harness.
  - [x] Add CI checks for the desktop validator and unit tests.
    - Evidence: `.github/workflows/desktop-validation.yml` runs Python unit tests, both static validators and Node.js syntax validation on pushes to `02-desktop-shell`, pull requests to `main`, and manual dispatch. Hosted run 41116394507 passed all 15 tests and all four validation steps; Plasma runtime is not covered.
- [ ] Add diagnostics and privacy-conscious crash logging.
- [ ] Add safe defaults and reset/recovery path.
- [ ] Verify clean build in the selected Fedora development environment.

## P3 — Working MVP

- [ ] Implement usable launcher/search entry point.
- [ ] Implement app launching and dock/taskbar behavior.
- [ ] Integrate system tray and notification display.
- [ ] Implement basic workspace/window navigation.
- [ ] Implement common quick-settings entry points.
- [ ] Add unobtrusive Tusker entry point, hidden by default.
- [ ] Verify ordinary desktop workflows without AI or network access.
- [ ] Verify opening/closing assistant UI does not cancel a running task.

## P4 — Complete feature set

- [ ] Add workspace overview and configurable window layouts.
- [ ] Add app folders and useful desktop widgets.
- [ ] Add optional configurable gestures with conflict detection.
- [ ] Add panel/dock placement, sizing and behavior settings.
- [ ] Add lock-screen/window-decoration integration where supported.
- [ ] Add keyboard-only, screen-reader, contrast and reduced-motion support.
- [ ] Add localization and high-DPI/fractional-scaling validation.

## P5 — Integration

- [ ] Integrate PIXEL-03 theme tokens and live theme switching.
- [ ] Integrate TUSKER-04 task cards, progress, approvals and controls.
- [ ] Integrate NEXUS-07 status/control interfaces without duplicating privilege logic.
- [ ] Integrate PILOT-08 remote-session status and task origin indicators.
- [ ] Coordinate packaging and first-boot defaults with ATLAS-01/PHOENIX-10.
- [ ] Run desktop contract and integration tests.

## P6 — Verification and hardening

- [ ] Test Wayland session behavior and supported Plasma versions.
- [ ] Test multiple monitors, hotplug, fractional scaling and screen rotation.
- [ ] Test keyboard layouts, touchpad variants and degraded hardware.
- [ ] Test accessibility and reduced-motion behavior.
- [ ] Stress-test launcher, panel, notifications and long-running assistant tasks.
- [ ] Test theme switching, invalid themes and shell restart/recovery.
- [ ] Measure startup, idle CPU/RAM, animation smoothness and memory growth.
- [ ] Triage and fix blocking defects; document residual risks.

## P7 — Release and handover

- [ ] Package desktop components and document exact dependencies.
- [ ] Document configuration migration and rollback behavior.
- [ ] Write user guides for launcher, dock, shortcuts, gestures and workspaces.
- [ ] Produce reproducible demo and test evidence.
- [ ] Verify recovery to a standard Plasma session if custom shell components fail.
- [ ] Publish known issues, maintenance notes and handover report.

## Evidence policy

Each completed item must link to a commit/PR, test output, reproducible manual test record, reviewed contract, or source-backed research note. A checkbox is not complete merely because the design is written.

# NEXUS-07 Phase 1 Checklist
**Phase:** P1 — Architecture and contracts (10 effort points) · **Status:** In progress

## P0 — Discovery and requirements
- [x] Locate and read master execution blueprint and NEXUS-07 P0–P7 checklist.
- [x] Verify repository identity, default branch, permissions and current branch.
- [ ] Read repository copies of MASTER_SPEC.md, ARCHITECTURE.md, SHARED_CONTRACTS.md, AGENT_REGISTRY.md, BRANCH_OWNERSHIP.md, COMMUNICATION_PROTOCOL.md, DECISIONS.md, PROGRESS.md and NEXUS handover notes (not present at intake).
- [ ] Inventory candidate file/app/process/settings/device/storage/battery/performance/network/clipboard/screenshot/maintenance operations.
  - [ ] Separate read-only, low/moderate mutation, privileged and destructive operations.
  - [ ] Define per-operation preconditions, postconditions and side effects.
  - [ ] Record idempotency, timeout, cancellation and rollback support.
- [ ] Research and validate Fedora/KDE/systemd/D-Bus/Polkit/portal/NetworkManager/UPower/BlueZ interfaces with ATLAS-01 and AEGIS-06.
- [x] Record initial architecture, dependency direction and high-level failure risks.
- [x] Receive ATLAS-01 ownership/base-system boundary review; record reply in Issue #5.\n- [ ] Obtain AEGIS-06, TUSKER-04 and remaining impacted-agent reviews of proposed architecture and interface drafts.

## P1 — Architecture and contracts
- [x] Draft common typed tool invocation and result envelopes.
- [x] Draft error taxonomy and operation metadata requirements.
- [x] Draft D-Bus naming, method, event and health conventions.
- [x] Receive TUSKER-04 provisional lifecycle review and incorporate task/step/correlation IDs, cancellation semantics, evidence refs and idempotency scope.\n- [ ] Obtain focused TUSKER-04 approval of revised schemas.
- [ ] Agree caller identity, authorization, approval, privilege and audit contract with AEGIS-06; TUSKER-04 confirms this ownership split.
- [ ] Agree OS service activation, packaging and supported API choices with ATLAS-01.
- [ ] Agree desktop telemetry/status contract with NOVA-02.
- [ ] Agree remote-origin identity propagation with PILOT-08.
- [ ] Agree extension capability facade with FORGE-09.
- [x] Add provisional machine-readable JSON schemas, valid fixtures and an executable Python unittest harness (pending cross-agent approval).\n- [ ] Run schema tests in the repository environment and record actual results.\n- [ ] Freeze schema/API version 1.0 only after TUSKER-04 and AEGIS-06 approval.

## P2 — Foundation (future)
- [ ] Create tool-provider/module skeleton in owned paths.
- [ ] Implement schema validation.
- [ ] Implement read-only system information, app discovery, device inventory and file metadata.
- [ ] Add OS API adapters and deterministic mock adapters.
- [ ] Add structured logs, diagnostics, capability discovery and health reporting.

## P3 — Working MVP (future)
- [ ] Implement confined file operations with previews and overwrite protection.
- [ ] Implement safe app launch and process status/management with process identity checks.
- [ ] Implement selected user-level settings APIs.
- [ ] Add postcondition verification tests.

## P4 — Complete feature set (future)
- [ ] Add device/peripheral, storage, battery/power and performance telemetry.
- [ ] Add network status and user-authorized configuration with disruption confirmation.
- [ ] Add maintenance helpers without bypassing package managers.
- [ ] Add clipboard/screenshot tools only behind explicit privacy permissions.

## P5 — Integration (future)
- [ ] Integrate catalogue and metadata into TUSKER-04.
- [ ] Route all mutations/elevated calls through AEGIS-06.
- [ ] Publish telemetry/status to NOVA-02 and model suitability signals to ORBIT-05.
- [ ] Coordinate package/service operations with ATLAS-01 and FORGE-09.
- [ ] Run end-to-end local safe-control scenarios.

## P6 — Verification and hardening (future)
- [ ] Test malformed input, Unicode, unusual filenames, symlinks, permission changes and races.
- [ ] Test stale process IDs, missing devices, timeouts and service restarts.
- [ ] Test destructive operations only in disposable VMs, including cancellation and rollback.
- [ ] Test non-admin users, denied permissions, sleep/resume and offline operation.
- [ ] Verify declared side effects against observed system state.

## P7 — Release and handover (future)
- [ ] Publish stable schemas, versioning policy, capability catalogue and examples.
- [ ] Document each tool's permission, side effects, preconditions, postconditions, rollback and limits.
- [ ] Create Fedora/KDE compatibility tests.
- [ ] Publish release report, known issues and maintenance handover.


## C0002 review findings
- [x] Read ATLAS-01 `os/BASE-SYSTEM-CONTRACTS.md` on `01-fedora-base`.
- [x] Record no-Tusker-boot/login dependency and optional/off-by-default AI/remote constraints.
- [x] Publish candidate NEXUS read-only system-bus identifiers for review; reverse-DNS ownership and AEGIS approval remain open.
- [x] Reply to Issue #5 with the proposal and explicit review requests.

- [x] Record TUSKER-04 review and ownership split in Issue #5; exact AEGIS identity/decision schema remains pending.

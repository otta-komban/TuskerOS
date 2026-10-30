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
- [x] Receive ATLAS-01 ownership/base-system boundary review; record reply in Issue #5.
- [ ] Obtain AEGIS-06 and remaining impacted-agent reviews of proposed architecture and interface drafts.

## P1 — Architecture and contracts
- [x] Draft common typed tool invocation and result envelopes.
- [x] Draft error taxonomy and operation metadata requirements.
- [x] Draft D-Bus naming, method, event and health conventions.
- [x] Receive TUSKER-04 lifecycle review and incorporate task/step/correlation IDs, cancellation semantics, evidence refs and idempotency scope.
- [x] Receive TUSKER-04 focused adapter review; document opaque IDs, timeout negotiation, canonical operation names, typed result preservation and approval stop conditions.
- [ ] Obtain final TUSKER-04 approval of frozen schemas; current acceptance is in principle only.
- [ ] Agree caller identity, authorization, approval, privilege and audit contract with AEGIS-06; exact schema remains AEGIS-owned.
- [ ] Agree OS service activation, packaging and supported API choices with ATLAS-01.
- [ ] Agree desktop event/status contract with NOVA-02.
- [ ] Agree remote-origin identity propagation with PILOT-08.
- [ ] Agree extension capability facade with FORGE-09.
- [x] Add provisional machine-readable JSON schemas, valid fixtures and an executable Python unittest harness (pending cross-agent approval).
- [x] Add GitHub Actions contract-test workflow; completed run not yet observed.
- [x] Add explicit tests for preserving object, array, string, number, boolean and null result values.
- [ ] Run schema tests in the repository environment and record actual results.
- [ ] Freeze schema/API version 1.0 only after TUSKER-04 and AEGIS-06 approval.

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

## C0005 — TUSKER-04 adapter reconciliation
- [x] Record focused adapter review comment 6531355859.
- [x] Document opaque task/step IDs, descriptor-bounded deadlines, canonical dotted operation names, typed JSON result preservation and approval stop conditions.
- [x] Document unknown-outcome reconciliation and correlation identifier preservation.
- [x] Add result-schema tests for object, array, string, integer, float, boolean and null JSON values.
- [ ] Receive AEGIS-06 principal/authorization review and ATLAS-01 service/namespace review.
- [ ] Execute the contract test suite and verify CI status before claiming test success.

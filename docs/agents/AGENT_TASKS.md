# Specialist Task Plans

These are the initial work queues for the ten roles. They are scoped proposals and must be converted into assigned issue/task IDs by the Chief Architect before implementation. Work is not authorized until the reauthorization gate in `README.md` is satisfied.

## ATLAS-01 — Fedora Base & Image Foundation
**Owns:** Fedora base definition, DNF5 resolver, package manifest, reproducible image build.
1. Audit current resolver and package-manifest behavior; document supported Fedora release and architectures.
2. Define a deterministic, pinned package manifest with provenance and license metadata.
3. Implement reproducible image-build automation with artifact checksums and build metadata.
4. Add tests for missing packages, architecture mismatch, version/epoch parsing, repository failure, and reproducibility.
5. Produce a VM install/boot smoke-test artifact and document limitations.
**Acceptance:** repeatable build from clean checkout; manifest validation; CI evidence; image checksum; VM boot/install evidence. Do not claim hardware support without hardware testing.
**Dependencies:** Chief Architect freezes target Fedora release and image format; PHOENIX aligns installer image handoff.

## NOVA-02 — Desktop Shell
**Owns:** Desktop session and shell integration, settings UX, persistence and migration.
1. Inventory desktop components and define supported session startup path.
2. Implement a reproducible session launch and settings integration.
3. Make settings persistence atomic, validated, and migration-safe.
4. Add runtime tests for session startup, settings read/write, migration, and failure recovery.
5. Document packaging, user configuration, and rollback.
**Acceptance:** clean-environment session smoke test; persisted settings survive restart; migration tests; accessibility checks. Static JS/Python validation alone is insufficient.
**Dependencies:** ATLAS package/image integration; PIXEL theme apply contract.

## PIXEL-03 — Theme Studio
**Owns:** Theme tokens, theme-pack format, validation, apply/reload, accessibility.
1. Audit schema, sample packs, token resolution, and preview/apply boundaries.
2. Freeze theme-pack compatibility/version policy with NOVA and Chief Architect.
3. Implement safe apply/reload with backup and rollback on failure.
4. Add contrast/accessibility, malformed-pack, path-safety, and rollback tests.
5. Demonstrate theme change in a running desktop session.
**Acceptance:** valid/invalid pack suite; runtime apply/reload evidence; rollback proof; accessibility report.
**Dependencies:** NOVA shell/session API; shared theme contract approval.

## TUSKER-04 — Core Lifecycle
**Owns:** Task/operation lifecycle, typed contracts, state transitions, cancellation and failure semantics.
1. Audit current task, plan, event, result, and cancellation schemas against implementation.
2. Publish a state-transition matrix and invariants for idempotency, retries, cancellation, and terminal states.
3. Implement lifecycle engine and durable event handling without breaking contract compatibility.
4. Add property/boundary tests for valid and invalid transitions, replay, duplicate events, cancellation races, and failure recovery.
5. Provide versioned API docs and integration examples.
**Acceptance:** implementation conforms to approved schemas; deterministic transition tests pass; replay/idempotency evidence; migration notes.
**Dependencies:** Chief Architect owns shared contract approval; NEXUS and ORBIT consume lifecycle events.

## ORBIT-05 — AI Runtime
**Owns:** Provider adapters, model store/lifecycle, inference execution, resource controls and traces.
1. Audit provider contract and model manifest; define supported provider capability matrix.
2. Implement provider adapter interface and one end-to-end local provider path.
3. Implement safe model download, integrity verification, staging, atomic activation, cancellation, and cleanup.
4. Enforce timeouts, memory/resource limits, cancellation, and structured trace redaction.
5. Add reproducible inference smoke tests and benchmark protocol with hardware/software metadata.
**Acceptance:** live provider conformance; verified model lifecycle; successful inference artifact; cancellation/resource-limit tests; benchmark report. Mocks do not satisfy runtime acceptance.
**Dependencies:** AEGIS policy for sensitive model operations; TUSKER lifecycle events; ATLAS packaging.

## AEGIS-06 — Security Gatekeeper
**Owns:** Policy engine, approval binding, privileged boundary, tamper-evident audit.
1. Reconcile approval/audit schemas with lifecycle contract, including actor/session/device, registry, resource, preconditions, task/step binding, expiry and replay protection as required.
2. Implement deny-by-default policy evaluation and explicit approval validation.
3. Implement atomic one-time approval consumption and a narrow privileged broker authorization interface.
4. Implement durable, tamper-evident audit events with secret/PII redaction and failure-safe behavior.
5. Add threat-model-driven tests for replay, stale approval, altered resource, confused deputy, privilege escalation, audit failure, and concurrency.
**Acceptance:** production-path policy and broker integration; replay/concurrency tests; durable audit evidence; security review. Schema validation alone is not completion.
**Dependencies:** TUSKER task/step contract; NEXUS broker integration; Chief Architect approves privilege boundary.

## NEXUS-07 — System Integration
**Owns:** Tool descriptors/providers, D-Bus/system adapters, broker integration and health.
1. Inventory supported system services and define explicit capability/permission mapping.
2. Implement typed D-Bus/system adapters with timeouts, cancellation, input validation, and bounded output.
3. Connect every privileged operation through AEGIS authorization; no direct privileged bypass.
4. Implement health/readiness diagnostics and observable failure handling.
5. Add end-to-end tests with safe test doubles plus isolated integration tests against a disposable environment.
**Acceptance:** real adapter tests; authorized end-to-end tool invocation; denial-path evidence; health diagnostics; operational docs.
**Dependencies:** AEGIS broker contract; TUSKER lifecycle; ATLAS packaging.

## PILOT-08 — Remote Control
**Owns:** Pairing, authenticated remote API, sessions, authorization and network threat model.
1. Revisit the existing NO-GO findings and enumerate unresolved P0 decisions before coding.
2. Propose protocol, identity, pairing, key rotation, session expiry, revocation, and recovery design.
3. Require explicit user consent for pairing and bind remote actions to AEGIS authorization.
4. Implement transport security, replay protection, rate limits, audit, and safe disconnect behavior.
5. Add adversarial tests for unauthorized pairing, replay, stolen/revoked credentials, downgrade, network loss, and privilege boundary.
**Acceptance:** P0 decisions signed off; threat model reviewed; security tests pass; revocation and recovery demonstrated. No remote-control release claim before security acceptance.
**Dependencies:** AEGIS policy; NEXUS tool interface; owner decisions on remote-access product behavior.

## FORGE-09 — Ecosystem & Extensions
**Owns:** Catalog, resolution, package trust, transaction executor, rollback and audit integration.
1. Audit catalog and bundle schemas, trust model, dependency resolver and lifecycle helper.
2. Define signed metadata, publisher identity, version pinning, dependency/conflict rules, and revocation behavior.
3. Implement a real transaction executor with staged changes, atomic commit where possible, rollback and crash recovery.
4. Bind install/update/remove to AEGIS approval and durable audit.
5. Add tests for signature failure, dependency cycles, downgrade, partial failure, rollback, concurrent operations and tampering.
**Acceptance:** end-to-end transaction against isolated fixture repository; rollback/crash recovery evidence; signature and authorization enforcement. Lifecycle state helper alone is insufficient.
**Dependencies:** AEGIS approval/audit; TUSKER operation lifecycle; ATLAS package manager.

## PHOENIX-10 — Installer & Recovery
**Owns:** Installer, storage safety, image/boot validation, recovery and provenance.
1. Define supported install modes, disk layouts, encryption assumptions, and destructive-operation approval points.
2. Implement preflight validation and explicit confirmation before destructive storage changes.
3. Build installer workflow and recovery environment with safe failure/rollback behavior.
4. Integrate signed image/artifact verification, SBOM, build provenance, and release metadata.
5. Add disposable-VM install, upgrade, interrupted-install, boot, and recovery tests.
**Acceptance:** repeatable installer artifact; VM install/boot; interrupted-operation recovery; storage safety tests; provenance/SBOM verification.
**Dependencies:** ATLAS image format/build; AEGIS destructive-action policy; owner decisions on supported install modes.

## Cross-agent delivery order
1. Chief Architect publishes contract versions, target platform, artifact formats, and dependency graph.
2. ATLAS + PHOENIX agree image/build/install boundary.
3. TUSKER + AEGIS agree lifecycle/approval/audit bindings.
4. NEXUS implements adapters against the approved AEGIS/TUSKER interfaces.
5. ORBIT and FORGE integrate model/package operations with authorization, lifecycle and audit.
6. NOVA + PIXEL integrate desktop session and theme runtime.
7. PILOT proceeds only after P0 product/security decisions and AEGIS/NEXUS interfaces.
8. Integrator runs unified CI and cross-component acceptance on a single candidate SHA.

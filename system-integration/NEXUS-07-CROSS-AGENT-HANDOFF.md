# NEXUS-07 Cross-Agent Integration Decisions

**Owner:** NEXUS-07  
**Branch:** `07-NEXUS`  
**Task:** NEXUS-07-SI-003 — integration handoffs and broker blocker clarification  
**Status:** Review decisions and recommendations; shared contracts remain unmodified  
**Baseline:** `main` at `345fc5a3d0f831fc714bae0cc88fa842cd9bed79`

This note responds to the open ATLAS-01, TUSKER-04 and AEGIS-06 integration questions using the current NEXUS-owned schemas and adapter code. It does not freeze cross-agent APIs or authorize privileged dispatch.

## 1. ATLAS-01 — Fedora 44 direct package handoff

### Required for minimal Fedora base

| RPM | Decision | Reason / owner |
|---|---|---|
| `systemd` | **Existing base dependency; do not add a second NEXUS package row.** | The current read-only prototype invokes `/usr/bin/busctl`, which is shipped by Fedora's `systemd` RPM. ATLAS owns the base systemd package selection. |

NEXUS does not require a separate D-Bus client library for this prototype: it invokes the fixed systemd `busctl` executable and uses Python standard-library modules only. The production runtime language has not been selected, so this is not a production Python runtime dependency declaration.

### Required only when Tusker system integration is installed

**No additional RPM is requested at this time.** The current adapter is a prototype, is not registered as a public tool, and has no production service/activation unit. If ATLAS later packages this exact prototype, it must verify that the host's existing `systemd` package supplies `/usr/bin/busctl`; it must not add a duplicate `systemd` package row to a layer already depending on the base system.

The adapter's `jsonschema` requirement is test-only (from `system-integration/requirements-test.txt`), not a runtime RPM request.

### Optional diagnostics / hardware-specific additions

**None requested.** NEXUS currently has no implemented hardware probe that justifies adding `dbus-tools`, `dbus-broker-tests`, vendor utilities, or a hardware-specific package.

### Explicit non-dependencies

- Do not add `dbus-broker` as a NEXUS dependency. It is a system-bus implementation owned by the Fedora base/system integration, not a client library or NEXUS adapter runtime requirement.
- Do not add `dbus-libs` for the current subprocess-based adapter.
- Do not add a Tusker D-Bus daemon, policy, activation unit, service account, or Polkit action. The `org.tuskeros.SystemTools1` namespace and activation shape remain provisional and require owner approval.
- Do not make any NEXUS component a boot, graphical-login, networking, logind, or Plasma hard dependency.

**ATLAS action:** no rows are to be added to `os/package-manifest.csv` from this NEXUS review. ATLAS should resolve any future package addition against its selected immutable Fedora 44 repository snapshot and obtain a separate owner review. The current ATLAS snapshot lock is empty, so no NEVRA, repository ID, RPM digest or provenance pin can be asserted by NEXUS.

**External package evidence:** Fedora's [Fedora 44 systemd package file list](https://packages.fedoraproject.org/pkgs/systemd/systemd/fedora-44.html) includes `/usr/bin/busctl`; the [Fedora 44 dbus-broker package page](https://packages.fedoraproject.org/pkgs/dbus-broker/dbus-broker/fedora-44.html) identifies it as the Linux D-Bus message-bus implementation. These facts identify package ownership, not a validated package lock.

## 2. TUSKER-04 — result status and side-effect guarantees

NEXUS confirms the seven status vocabulary already present in `tool-result.schema.json`: `succeeded`, `rejected`, `needs_approval`, `running`, `cancelled`, `failed`, and `unknown_outcome`.

The following is NEXUS's proposed producer contract for Core review:

| Status | Dispatch guarantee | Side-effect interpretation |
|---|---|---|
| `rejected` | **No handler dispatch for this request.** | The broker/provider rejected the request before dispatch (for example invalid arguments, unavailable authorization, policy denial, precondition mismatch, or unknown operation). Report an empty `side_effects` list. |
| `failed` | Handler dispatch may have begun. | **Does not guarantee zero side effects.** Report known side effects and postcondition evidence; Core must preserve uncertainty and inspect prior steps. |
| `unknown_outcome` | Dispatch may or may not have occurred. | Side-effect state is indeterminate. Reconcile the same operation/idempotency identity; never blindly retry. |
| `needs_approval` | No protected handler dispatch. | Return to the approval flow. This status is not an AEGIS decision or authorization grant. |
| `cancelled` | Terminal only when operation stop is confirmed. | `cancellation.operation_state` must be `stopped`; acceptance of a cancellation request is not proof of stop. |
| `succeeded` | Dispatch completed. | Core may complete only after the postcondition is `verified` or `not_applicable`; otherwise verify/reconcile. |
| `running` | Operation is active. | Preserve the operation identity and monitor/cancel/reconcile it. |

A handler-level business refusal after dispatch is **not** `rejected`; it is `failed` with accurate side-effect/postcondition evidence, or `unknown_outcome` if the result cannot be established. This distinction is essential: `rejected` is the only status that promises no handler invocation, while `failed` does not promise no side effects.

This proposal is consistent with the AEGIS broker draft's rule that a failed or indeterminate authorization check returns a typed rejection with zero privileged side effects. It does not claim that the current schema enforces the dispatch-phase distinction; the result schema has no explicit dispatch-phase field. Before freezing this semantic as a shared contract, add cross-field schema/adapter tests or an explicit typed dispatch-state field under Chief Architect review.

### Cancellation and correlation

- A cancellation request's `accepted` state means the request was accepted for processing, not that the operation stopped.
- NEXUS may report `cancelled` only after the provider confirms the operation is stopped and cannot dispatch further work.
- A timeout/disconnect after possible side effects is `unknown_outcome`; reconcile the same operation and idempotency identity.
- Preserve `request_id`, `operation_id`, `task_id`, `step_id`, and `correlation_id` byte-for-byte. TUSKER-04 remains authoritative for aggregate task/step state.

## 3. AEGIS-06 — broker integration decisions

### Security invariants: ACCEPT

NEXUS accepts these as mandatory semantic requirements, not as an API/transport approval:

1. Use a fresh opaque `authorization_ref` issued only after AEGIS has re-evaluated the exact approved proposal. `approval_request_id` is correlation only and is never a consume credential.
2. Consume authorization once through a durable atomic compare-and-set or equivalent linearizable transaction. Return a unique `consumption_id`; no handler dispatch on any non-`CONSUMED` result.
3. Commit required pre-dispatch authorization audit evidence durably before returning `CONSUMED`. If audit cannot be committed, no grant is returned.
4. AEGIS owns policy semantics and authority; NEXUS owns verified runtime registry loading and fixed broker-operation-ID-to-handler mapping.
5. Authenticate the local IPC peer independently using kernel/platform credentials. Caller-supplied identity, policy decision, approval state or authorization reference is never authoritative.
6. Persist operation/idempotency/dispatch intent before side effects. A lost or ambiguous response is reconciled against the same execution identity; never blind-retry a possible mutation.
7. Fail closed on missing/invalid identity, authority, registry, clock, audit, preconditions, or an indeterminate consume result.

### Registry status and version: ACCEPT WITH SOURCE REQUIREMENT

- NEXUS can report `registry_status=resolved` only after loading and integrity/version-verifying an immutable trusted registry artifact.
- `registry_version` must identify that exact verified artifact and must come from the trusted loader, never the invocation or caller.
- If the artifact is absent, stale, malformed, revoked, or unverifiable, report unavailable and block authorization/dispatch.
- `POLICY_REGISTRY_UNAVAILABLE` is acceptable as the stable fail-closed reason code, subject to AEGIS's ownership of the reason-code registry.
- The signing/trust root, artifact distribution channel, version/revocation source and packaging handoff are not yet defined. NEXUS therefore cannot claim a resolved production registry or provide a real version value today.

### Audit event producer ownership

- **AEGIS** owns and emits authorization lifecycle events: request created/presented, approval/denial/dismissal, expiry, invalidation, revocation, consume accepted/rejected, and authorization reconciliation.
- **NEXUS** owns and emits broker dispatch intent/start, provider operation progress/terminal result, and execution reconciliation events. It supplies the trusted registry version/status and operation correlation it actually observed.
- **TUSKER-04** owns task/step/task-event semantics and aggregate task lifecycle. NEXUS preserves the opaque task/step identifiers but does not redefine them.
- Do not attribute approval presentation, user approval, expiry, revocation, or authorization consume to NEXUS unless the event is a separately identified broker observation of the AEGIS result.

For the missing lifecycle coverage identified in SEC-SCHEMA-006, NEXUS supports explicit event types for presentation, dismissal, invalidation, revocation, consume accepted/rejected, and reconciliation rather than overloading execution events. A single `authorization_reconciliation_completed` event with a required typed outcome is preferable to ambiguous generic success/failure events; AEGIS must define the final event names and outcome vocabulary. The candidate v0.2.0 schema remains AEGIS-owned and is not approved for migration by this note.

### Transport and runtime: RECOMMENDATION ONLY; APPROVAL REQUIRED

NEXUS recommends evaluating a local Linux `AF_UNIX` `SOCK_SEQPACKET` endpoint with kernel-provided `SO_PEERCRED`, a protected socket path, bounded message framing, and explicit versioned request/response messages. Message-boundary preservation and kernel peer credentials are a better fit for this narrow local broker boundary than accepting caller-supplied identity in a public JSON envelope.

This is a recommendation, **not a frozen decision**. Chief Architect and AEGIS approval are required before committing a socket path, wire fields, service identity, systemd activation, SELinux policy, runtime language or API. The existing Python adapter is a testable read-only prototype and does not establish the production broker language. No concrete durable store/transaction primitive or authority service is selected.

### JCS canonicalization

No production NEXUS canonicalizer is currently identified or wired into the read-only adapter. The RFC 8785 vectors must be run against the actual selected broker canonicalizer, including invalid-surrogate rejection and exact code-point preservation, before any privileged operation can be enabled. Do not treat Python's generic JSON serialization as proof of JCS conformance.

### Additional AEGIS schema consistency findings from the security review

The NEXUS-07 review of the uploaded `6-Security.txt` report records two further AEGIS-owned contract gaps. These are findings from the security agent's review, not changes made on the NEXUS branch:

1. **Approval binding completeness:** the approval schema does not fully represent the session/device, registry, resource and precondition bindings required by the authorization lifecycle contract. Until AEGIS reconciles the schema with those lifecycle bindings, NEXUS cannot claim that an approval record is a complete binding of the authorized operation context.
2. **Audit correlation minimums:** the audit schema does not require `task_id` and `step_id`, although the lifecycle contract lists them among its minimum fields. AEGIS should decide whether these are universally required or conditionally required for task-scoped events, then encode that rule and add valid/invalid schema examples and tests.

**Owner / disposition:** AEGIS-06 owns both schemas and the lifecycle-to-schema reconciliation; Chief Architect approval is required for shared contract changes. NEXUS will preserve task/step identifiers when supplied and will not independently edit, migrate or version AEGIS schemas. These gaps join the existing broker release blockers; they do not authorize a permissive fallback or privileged dispatch.

## 4. Blockers and next acceptance evidence

| Blocker | Owner(s) | Evidence/decision needed |
|---|---|---|
| Public caller envelope still permits arbitrary `authorization_context` on this branch | Chief Architect + NEXUS | Approve public/internal boundary; then remove caller field, define separate internal trust binding, and add direct smuggling-negative tests. |
| Broker transport/API and runtime not frozen | Chief Architect + AEGIS + NEXUS | Approve versioned transport, peer-credential source, runtime owner/language, typed consume request/response. |
| Authority/store and atomic consume implementation absent | AEGIS | Name authority service and durable linearizable transaction primitive; demonstrate race and lost-response reconciliation. |
| Registry artifact provenance/revocation absent | AEGIS + NEXUS + ATLAS | Define trust root, artifact format/distribution, immutable version, revocation and packaging. |
| TUSKER status phase distinction not machine-enforced | TUSKER + NEXUS + Chief Architect | Approve `rejected`/pre-dispatch and `failed`/post-dispatch semantics; add schema/adapter tests or a typed dispatch phase. |
| Real system-bus interoperability absent | NEXUS + ATLAS | Disposable D-Bus environment and exact runtime evidence; current fake-process tests are not enough. |

Until these blockers are closed, the D-Bus adapter remains an isolated read-only prototype, not a public tool; mutating handlers remain disabled/fail-closed.

## 5. Rollback

This is a review/decision document only. Revert its single commit to remove the handoff note. No shared schema, runtime, package manifest, service activation, or privileged behavior is changed.

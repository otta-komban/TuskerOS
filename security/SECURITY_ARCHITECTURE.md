# TuskerOS Security Architecture

**Owner:** AEGIS-06  
**Status:** Initial P1 proposal — contracts require cross-agent review  
**Implementation status:** Design only; no runtime enforcement is claimed

## 1. Architectural rule

The AI planner is an untrusted request producer. It may describe intent and propose typed actions, but it cannot authorize, elevate, or directly execute privileged operations.

The enforcement path is:

`Request → Typed proposal → Identity + schema validation → Deterministic policy → Approval (if required) → Short-lived authorization → Narrow executor/broker → Independent verification → Audit`

The policy decision is external to model output and UI presentation.

## 2. Components and responsibilities

| Component | Responsibility | Must not do |
|---|---|---|
| Tusker planner (TUSKER-04) | Produce typed action proposal and explain intent | Grant permissions or invoke privileged operations directly |
| Identity adapter | Establish local process or authenticated remote principal | Treat network reachability as identity |
| Policy service (AEGIS) | Classify operation, validate scope, decide allow/deny/approval | Execute arbitrary commands |
| Approval presenter (NOVA) | Display exact action, target, impact and choice | Make authorization decisions |
| Approval store | Bind one-time approval to immutable action digest and expiry | Accept approval for modified arguments |
| Tool executor (NEXUS) | Execute approved typed operation and verify postconditions | Skip policy checks on retries/background work |
| Privileged broker (AEGIS) | Expose a minimal allowlisted privileged API | Offer generic root shell or arbitrary executable path |
| Remote gateway (PILOT) | Authenticate, bind device/session identity, forward requests | Bypass local policy or approve silently |
| Extension host (FORGE) | Run extensions with declared capabilities | Provide ambient host access |
| Audit sink (AEGIS) | Record decisions and outcomes with redaction | Store raw secrets or silently discard required events |

## 3. Decision semantics

Policy evaluation returns exactly one of:

- `DENY`: do not execute; return a stable reason code.
- `ALLOW`: execute only the exact canonical action and resource scope evaluated.
- `REQUIRE_APPROVAL`: create an approval request; do not execute until a valid approval is received.

Unknown action IDs, unknown risk classes, invalid schemas, missing identity, unresolved targets, policy version mismatch, expired grants, or policy evaluation errors return `DENY`.

The policy engine owns operation risk. Model-provided risk labels are ignored.

## 4. Risk policy defaults

| Class | Examples | Decision |
|---|---|---|
| R0 read-only | Query system status; read a user-selected file | Allow only within explicit read scope |
| R1 low-risk reversible | Launch installed app; create a draft in an allowed workspace | Auto-allow from narrow allowlist |
| R2 sensitive | Read broad personal data; change privacy setting | Require approval |
| R3 privileged | Install package; alter service or firewall | Require approval and broker validation |
| R4 destructive | Bulk delete; format or repartition storage | Strong confirmation and preflight; deny if target/impact ambiguous |
| R5 security-critical | Disable protections; modify policy/broker/audit controls | Deny to AI; separate administrator maintenance workflow |

The default is deny. Risk may only be escalated by policy; callers cannot downgrade it.

## 5. Action and approval binding

A proposal should contain a stable action identifier, schema version, typed arguments, declared resource references, caller identity, task/step identifiers, and idempotency key. The policy service canonicalizes and validates the arguments, resolves resources, determines risk, and creates an immutable action digest.

An approval record should bind at minimum:

- approval ID and action digest;
- requesting principal and originating local/remote session identity;
- exact operation and canonical target/resource scope;
- human-readable impact summary and reason approval is required;
- policy version and relevant precondition snapshot;
- creation and expiry timestamps;
- one-time-use state and approving principal;
- decision (approve/deny) and timestamp.

Any changed argument, target, resource scope, principal, policy version, or expired precondition requires a new policy evaluation and approval. Approval is not a reusable capability.

## 6. Privileged broker boundary

- Run ordinary planner, policy, UI, and tool services unprivileged.
- Prefer existing OS mechanisms (Polkit actions, system D-Bus services, package-manager APIs) over a custom always-root daemon.
- If a helper is necessary, it exposes fixed typed operations only, validates every argument independently, authenticates the IPC peer using OS-provided credentials, and runs with only the capabilities required for that operation.
- Never accept a shell string, arbitrary executable path, caller-supplied environment, arbitrary file path outside the operation's declared scope, or a model-supplied privilege flag.
- Apply timeouts, bounded request sizes, concurrency limits, rate limits, and structured audit events.
- Recheck policy immediately before the privileged side effect; reject stale authorization.

## 7. Sandboxing strategy

Use defense in depth; no single sandbox is treated as a complete security boundary.

- **bubblewrap:** candidate for untrusted user-space tool/extension processes requiring filesystem, mount, namespace, and network restrictions. Evaluate actual kernel/user-namespace availability and operational limitations on supported Fedora builds.
- **Podman:** candidate for OCI workloads and extension/developer workloads needing container lifecycle, resource limits, image provenance, and rootless operation. Prefer rootless containers; avoid privileged containers and host socket mounts.
- **Polkit:** candidate for user-authenticated authorization of narrowly defined system actions. Polkit prompts do not replace Tusker's action-bound approval contract; broker operations must still validate exact inputs.
- **systemd hardening:** use service users, filesystem protections, capability bounding, syscall filters, private tmp, and resource limits where compatible.
- **SELinux:** preserve enforcing defaults; do not disable SELinux to make a feature work. Define and review narrowly scoped policy if integration requires it.

Sandbox profile is selected by workload and risk. Host access, devices, network, secrets, and writable paths are denied unless explicitly required and scoped. Sandbox limitations are documented and tested.

## 8. Audit contract

Every security-sensitive request should produce correlated events for proposal receipt, policy decision, approval lifecycle, execution start/result, cancellation, verification, and rollback/compensation where applicable.

Events should include event ID, UTC timestamp, actor/principal, local or remote origin, task/step/action IDs, operation ID, risk class, canonical resource identifiers (redacted as needed), policy version, decision/reason code, approval reference, executor/broker identity, result status, and correlation ID.

Do not log passwords, tokens, private keys, raw secret environment variables, or unrestricted file contents. Define retention, access control, export, rotation, and integrity protection. If a required audit event cannot be persisted, high-risk operations fail closed; low-risk behavior must be explicitly specified and cannot silently claim an audit record exists.

Append-only is an application-level contract; tamper resistance requires OS permissions, ownership separation, integrity chaining or signed checkpoints, and protected backup/forwarding where appropriate. No storage design is claimed tamper-proof.

## 9. Cancellation, recovery, and quarantine

- Cancellation blocks new steps immediately and requests supported interruption of the active operation.
- An operation is `cancelled` only when executor evidence confirms it stopped; otherwise report `cancellation_requested` or `outcome_unknown`.
- Rollback is a distinct compensating action, separately authorized where required, and must be verified.
- Package/extension quarantine disables activation and isolates artifacts without silently deleting user data.
- Recovery paths must not depend on model availability and must preserve administrator access.

## 10. Cross-agent contract questions

- **TUSKER-04:** proposal envelope, task/step correlation, preflight call, denial/error states, retries and background-task policy.
- **NEXUS-07:** typed operation registry, caller identity, preconditions, resource canonicalization, execution handoff, postcondition verification and cancellation semantics.
- **PILOT-08:** authenticated principal/session claims, device revocation, replay resistance, remote approval response binding.
- **FORGE-09:** extension manifest capabilities, signature/provenance metadata, sandbox profile, permission prompt and revocation lifecycle.
- **NOVA-02:** trusted approval presentation, accessibility, theming boundaries, denial and timeout UX.
- **ATLAS-01:** service users/groups, Polkit action installation, SELinux integration, systemd hardening and package ownership.

## 11. Phase 1 architecture checklist

- [ ] Agree proposal, decision, approval, audit, and broker schemas with dependent agents.
- [ ] Select local IPC and caller authentication mechanism.
- [ ] Specify operation registry and deterministic risk mapping.
- [ ] Specify token/approval expiry, one-time use, revocation and replay protection.
- [ ] Validate bubblewrap, Podman, Polkit, systemd and SELinux assumptions on target Fedora base.
- [ ] Record ADRs for privileged execution and sandbox profiles.
- [ ] Create policy test matrix with positive and negative cases.

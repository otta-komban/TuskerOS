# TuskerOS Security Threat Model

**Owner:** AEGIS-06 — Security & Permission Engineer  
**Status:** Initial P0 baseline; living document  
**Scope:** Local AI, system tools, privileged operations, extensions, packages, and remote control

## 1. Security objectives

- Keep user data, credentials, system integrity, and availability protected.
- Ensure model output is never an authorization source.
- Permit only explicitly classified and scoped operations.
- Require informed, fresh user approval for sensitive, privileged, destructive, and security-critical actions.
- Preserve local authorization when requests originate remotely.
- Make security decisions and execution outcomes auditable without logging secrets.
- Fail closed when policy, identity, approval, broker, or audit prerequisites cannot be established.

## 2. Assets

| Asset | Security property | Examples |
|---|---|---|
| User data | Confidentiality, integrity, availability | Home files, documents, browser profiles |
| Credentials and keys | Confidentiality, integrity | Tokens, SSH keys, Wi-Fi secrets, session credentials |
| System integrity | Integrity, availability | OS packages, boot configuration, services, firewall |
| Security policy | Integrity | Rules, trusted identities, permission grants |
| Privileged broker | Integrity, availability | Narrow system-changing operations |
| AI runtime and models | Integrity, provenance | Model files, adapters, prompts, tool proposals |
| Extensions and packages | Integrity, isolation | Marketplace bundles, plugins, dependencies |
| Remote sessions | Authentication, authorization, freshness | Paired devices, session tokens, approval responses |
| Audit records | Integrity, confidentiality, availability | Decisions, approvals, execution results |

## 3. Trust boundaries

1. **Untrusted content → planner:** prompts, files, webpages, model responses, tool output, extension metadata and downloaded content are data, never policy.
2. **Planner → policy service:** the planner submits a typed action proposal. The policy service independently validates identity, action, arguments, target resources, risk and preconditions.
3. **Policy service → approval UI:** the service creates an immutable approval summary. The UI displays it; the UI cannot grant permission by itself.
4. **Policy service → broker/tool executor:** only a signed or otherwise integrity-protected, short-lived authorization decision for an exact action may cross this boundary.
5. **Unprivileged service → privileged broker:** the broker authenticates the local caller and revalidates the narrow operation; it does not accept arbitrary shell text.
6. **Remote client → local service:** remote authentication establishes identity, not privilege. Local policy and approval rules still apply.
7. **Extension → host capabilities:** extensions receive no ambient system authority; each declared capability is mediated and scoped.
8. **Audit producer → audit store:** audit writes are structured, append-only by interface, redacted, and failure-aware.

## 4. Adversaries and threat scenarios

| Threat actor / source | Threat | Required control |
|---|---|---|
| Malicious prompt or document | Prompt injection asks Tusker to exfiltrate data or bypass approval | Treat content as untrusted; deterministic policy outside model |
| Compromised/buggy model | Fabricated intent, unsafe command, repeated calls | Typed allowlisted actions, schema validation, quotas, policy checks |
| Malicious extension | Reads private files, invokes tools, persists or escalates | Isolation, explicit capabilities, provenance checks, revocation |
| Malicious package/archive | Dependency confusion, traversal, post-install execution | Trusted sources, signature/checksum verification, safe extraction, install preview |
| Local unprivileged process | Spoofs caller or talks directly to broker | OS peer credentials, narrow IPC ACLs, broker-side validation |
| Remote attacker / stolen device | Session hijack, replay, unauthorized approval | Strong pairing/authentication, expiry, anti-replay, revocation, local approval |
| Compromised user-space service | Attempts privilege escalation | Separate broker, minimal API, Polkit/root helper boundaries, no inherited root |
| Malicious or compromised administrator | Alters policy or logs | Explicit admin boundary, protected policy ownership, tamper-evident audit where feasible |
| Resource exhaustion | Floods planner, broker, logs or sandbox | Rate limits, bounded inputs/outputs, timeouts, quotas, backpressure |

## 5. Action risk taxonomy

Risk is assigned by the policy engine from the registered operation and validated arguments, not from model-provided labels.

| Class | Examples | Default decision |
|---|---|---|
| R0 Read-only | Read a user-selected file; query battery state | Allow only within granted read scope |
| R1 Low-risk reversible | Open an installed application; create a draft in an approved workspace | Auto-allow only from a narrow allowlist and after precondition checks |
| R2 Sensitive | Read broad personal directories; change user privacy settings; access credentials | Explicit approval; narrow resource scope |
| R3 Privileged | Install packages; change system services; alter firewall/network settings | Explicit approval plus broker allowlist and operation-specific validation |
| R4 Destructive / irreversible | Delete data recursively; repartition disks; overwrite system state | Strong confirmation, exact target preview, backup/recovery preflight; deny if safe preview cannot be produced |
| R5 Security-critical | Disable protections; change authorization policy; modify broker or audit controls | Deny to AI by default; administrator-only maintenance path outside normal agent execution |

An operation may be escalated to a higher class based on target, scope, uncertainty, reversibility, or blast radius. Unknown operations and malformed arguments are denied.

## 6. Security invariants

- No model text, tool output, extension metadata, remote message, or UI event can grant itself permission.
- Every mutation is authorized immediately before execution against the exact validated operation and target.
- Approval is bound to action ID, canonical arguments, resource scope, requesting identity, policy version, and expiry; any material change invalidates it.
- Approval is one-time by default; no blanket “approve all future actions” grant for privileged or destructive operations.
- A denial, timeout, expired approval, missing identity, policy error, broker error, or required audit failure prevents execution.
- No arbitrary shell, unrestricted root session, or general-purpose privileged command endpoint is exposed to Tusker.
- Remote origin does not reduce local approval requirements.
- Cancellation stops future steps and attempts supported safe interruption; it is not represented as rollback unless rollback is independently verified.
- Logs redact secrets and minimize personal content.
- Recovery and emergency-disable paths remain available without depending on the AI runtime.

## 7. Initial risk register

| ID | Risk | Initial severity | Planned mitigation | Status |
|---|---|---:|---|---|
| AEGIS-R01 | Model output treated as authority | Critical | Independent deterministic policy service | Open |
| AEGIS-R02 | Broker exposes generic root/shell capability | Critical | Narrow operation allowlist; no shell passthrough | Open |
| AEGIS-R03 | Approval replay or argument substitution | High | One-time, expiring, action-bound approval token | Open |
| AEGIS-R04 | Remote request bypasses local policy | Critical | Same local policy path for local and remote callers | Open |
| AEGIS-R05 | Extension escapes sandbox | High | Capability isolation, syscall/filesystem/network limits, review | Open |
| AEGIS-R06 | Path traversal or symlink race | High | Canonical path policy plus descriptor-relative safe operations | Open |
| AEGIS-R07 | Audit records leak secrets or are silently dropped | High | Redaction, restricted access, integrity checks, fail-closed rules | Open |
| AEGIS-R08 | Cancellation falsely reported as rollback | High | Separate cancel/compensation/verified rollback states | Open |
| AEGIS-R09 | Package provenance or dependency is malicious | High | Source policy, signature/checksum, dependency review | Open |
| AEGIS-R10 | Policy/approval UI confused by custom theme | Medium | Security service owns decision; accessible trusted UI treatment | Open |

Severity is provisional pending implementation context and attack-surface review.

## 8. Phase 1 evidence still required

- [ ] Validate threat actors and assets with TUSKER-04, NEXUS-07, PILOT-08 and FORGE-09.
- [ ] Map every planned tool to a risk class and resource boundary.
- [ ] Decide local caller identity and IPC authentication mechanism.
- [ ] Define policy, approval, broker, and audit schemas.
- [ ] Verify Fedora/Polkit/bubblewrap/Podman capabilities against supported versions.
- [ ] Record unresolved assumptions and accepted residual risks.

## 9. Out of scope / explicit limitations

This baseline is a design artifact, not proof that TuskerOS currently enforces these controls. No implementation, penetration test, sandbox escape test, or runtime security result is claimed here.

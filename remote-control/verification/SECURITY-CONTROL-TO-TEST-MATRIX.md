# PILOT-08 Security Control-to-Test Traceability Matrix

**Status:** Draft v0.1 — design-time test specification; not executable evidence or security approval  
**Owner:** PILOT-08 | **Branch:** `08-remote-control`  
**Threat baseline:** `remote-control/security/THREAT-MODEL-AND-ABUSE-CASE-REGISTER.md` (AB-01..AB-20; CTRL-01..CTRL-12)  
**Protocol baseline:** 72 scenarios in `PROTOCOL-ACCEPTANCE-AND-NEGATIVE-TESTS.md`; specified, not executed  
**Decision:** **NO-GO**. AEGIS-06 and NOVA-02 sign-offs are absent; TUSKER-04 dispositions remain draft REVISE/DEFER.

## 1. Purpose and evidence rules

This matrix turns every registered abuse case into concrete negative/security test cases, expected observable results, audit assertions, traceability links and accountable reviewers. It is implementation-neutral: no test framework, language, cryptographic primitive, persistence engine or runtime interface is selected here.

- **Specified** means a reproducible test intent and expected result are written down.
- **Executable** means implemented against an identified build/commit and runnable in the selected test harness.
- **Passed** means the executable test ran and its evidence was reviewed. Nothing in this document is executable or passed evidence.
- Use synthetic principals, devices, keys, tasks and secrets. Never commit live credentials or production task content.
- Every protected mutation must pass fresh AEGIS authorization. **DENY, REQUIRE_APPROVAL, stale policy, timeout, malformed response or unavailable policy must result in zero Core/executor dispatches.**
- A test must record build/commit, fixture version, environment, exact request/action, result, audit correlation and reviewer. Redact secrets from evidence.
- Existing scenario IDs are linked below; new IDs are additive and do not inflate the existing 72-scenario count.

## 2. Abuse-case to test matrix

| Abuse case / control | Test ID(s) | Attack setup and exact action | Expected result / security assertion | Audit expectation | Existing links / requirement | Owners / sign-off |
|---|---|---|---|---|---|---|
| **AB-01 Pairing brute force** / CTRL-01, CTRL-09 | SCT-01A, 01B | Start a pending challenge; submit invalid proofs at and beyond the configured threshold, including concurrent requests; separately attempt reuse after expiry. | Rate limit/backoff applies at the approved threshold; challenge expires and is single-use; no device/session is enrolled; resource use stays within approved budget; response does not reveal secret-dependent detail. | Record challenge reference, outcome, throttle decision and correlation; never record code, private key or proof. | PAIR-002..008, NET-007; RC-PAIR-01, RC-DEVICE-01 | AEGIS-06 sets parameters; PILOT-08 tests; NOVA-02 reviews owner feedback. |
| **AB-02 Pairing relay / wrong-device confirmation** / CTRL-01 | SCT-02A, 02B | Obtain a valid pending challenge for device A; relay its proof to device B or alter key/fingerprint/label/scope between initiation and local confirmation; race confirm against cancel. | Proof bound to challenge, server and exact device key; local confirmation displays stable identity and scope; mismatched/relayed proof and cancelled challenge fail; at most one atomic completion. | Audit initiator, confirmed fingerprint/device reference, scope, confirmation/cancel outcome and time; no reusable QR/code. | PAIR-001, 003..010; RC-PAIR-02, RC-DEVICE-01 | AEGIS-06 + NOVA-02 approve ceremony; PILOT-08 supplies tests. |
| **AB-03 Stolen device credential** / CTRL-02 | SCT-03A, 03B | Copy a session credential to another device lacking the registered private key; replay a superseded rotation credential; authenticate after device revoke. | Proof-of-possession/device binding rejects clone; superseded/revoked credentials fail; no protected response or mutation. | Record device/session reference, replay/revoke result and correlation; credential material absent. | SESS-001..010, 012..014; RC-SESSION-01, RC-REVOKE-01 | AEGIS-06 owns key/session contract and sign-off. |
| **AB-04 Client-supplied principal / role** / CTRL-03, CTRL-04 | SCT-04A, 04B | Send task/read/cancel requests with forged principal_ref, role, admin, scopes, origin, device_ref or policy decision; repeat with unknown JSON fields. | Reject unknown authority-bearing fields or ignore them only if schema explicitly requires; server-derived identity is used; every operation independently authorized; forged identity never reaches Core. | Audit authenticated principal/device/session and rejected-field category, not attacker-supplied identity as trusted actor. | AUTH-001..009, TASK-016; RC-AUTH-01, RC-AUDIT-01 | AEGIS-06 + TUSKER-04 approve authoritative context and policy. |
| **AB-05 Direct tool / executor injection** / CTRL-04, CTRL-12 | SCT-05A, 05B | Submit tool/provider/command/risk/executor selectors; probe shell, SSH, D-Bus, Polkit, privileged broker and NEXUS provider routes using method/path variants. | Strict task schema rejects or discards prohibited selectors without changing Core plan; no prohibited route exists; no subprocess, provider or privileged call occurs. | Record route/probe category and denial; do not log command payloads or sensitive input. | AUTH-010, TASK-006; RC-PRIV-01, RC-TASK-01 | TUSKER-04 + AEGIS-06; PILOT-08 route inventory and integration test. |
| **AB-06 Idempotency collision / replay** / CTRL-05 | SCT-06A, 06B, 06C | Submit same principal/key/payload concurrently; reuse key with changed canonical payload; crash/restart after Core dispatch but before response, then retry. | One logical task for same payload; conflicting payload returns conflict; durable record/reconciliation returns original outcome after restart; never duplicate side effect on uncertain dispatch. | Stable idempotency correlation and task reference; audit one dispatch and subsequent replay/reconciliation; no raw secret. | TASK-002..005, 012..014; RC-TASK-02 | TUSKER-04 must approve canonicalization, retention and crash consistency; PILOT-08 verifies. |
| **AB-07 Context-reference substitution** / CTRL-04, CTRL-06 | SCT-07A | Replace an authorized context reference with another principal's file/task/context ID; mix valid and invalid references in one bounded request. | Core independently checks every reference against trusted principal/device scope; unauthorized reference causes documented safe rejection/redaction; no partial privilege expansion. | Record opaque reference outcome and authenticated actor; do not expose referenced resource names/content. | TASK-007..008; RC-TASK-01, RC-TASK-03 | TUSKER-04 + AEGIS-06. |
| **AB-08 Unauthorized task read / enumeration** / CTRL-03, CTRL-06 | SCT-08A, 08B | Guess another principal's task ID; enumerate list pages/cursors and request snapshot fields containing prompt, path, output or evidence. | Deny or non-disclosing not-found per approved contract; no cross-resource metadata leak; projection contains only explicitly allowed fields; pagination is bounded. | Audit denied resource access and rate-limit pattern without logging private content. | AUTH-004, EVT-001..002, EVT-008; RC-TASK-03 | AEGIS-06 + TUSKER-04 approve resource and field policy. |
| **AB-09 Event subscription / cursor theft** / CTRL-06, CTRL-07 | SCT-09A, 09B | Use another principal/device's cursor; subscribe to a guessed task; replay a cursor after permission change or revoke. | Cursor is not bearer authority; authorize resource at subscribe and replay; cross-scope events withheld; revoked session stream closes and reconnect fails. | Record authorized subscription scope, denied replay and close reason; no event payload secrets. | EVT-003..012, SESS-010..014; RC-EVENT-01/02, RC-REVOKE-01 | AEGIS-06 + TUSKER-04. |
| **AB-10 Event gap / sequence manipulation** / CTRL-06 | SCT-10A, 10B | Drop, duplicate and reorder event frames; submit stale, future, malformed and expired cursors; force snapshot/replay boundary race. | Client detects gaps/duplicates; sequence is monotonic under approved semantics; expired cursor triggers explicit authoritative snapshot reset; no silent false-complete stream. | Record cursor reset, gap and replay range; avoid recording private event body. | EVT-003..007; RC-EVENT-02 | TUSKER-04 owns event registry, ordering, cursor and snapshot consistency. |
| **AB-11 Revoked session persists** / CTRL-02, CTRL-07 | SCT-11A, 11B, 11C | Revoke device/session while WSS is open; race revoke against protected mutation; restart service with stale session cache or persisted credential state. | Active WSS closes within AEGIS-approved bound; next frame/request and reconnect fail; mutation outcome follows documented linearization point and never proceeds on stale authorization; restart cannot resurrect revoked access. | Audit revoke commit, active-stream termination, in-flight outcome and subsequent denial with shared correlation. | SESS-008..014, EVT-009, NET-009; RC-REVOKE-01 | AEGIS-06 defines atomicity/bounds; TUSKER-04 defines mutation boundary; PILOT-08 tests. |
| **AB-12 Host / Origin / DNS rebinding** / CTRL-08 | SCT-12A, 12B | Send hostile Origin, mismatched Host, spoofed forwarded headers and DNS-rebinding-style requests to loopback; test absent Origin and untrusted proxy paths. | Reject untrusted Host/Origin and untrusted proxy metadata before upgrade/credential use; no wildcard CORS or cookie-CSRF bypass; native-client exceptions must be explicitly specified. | Record normalized host/origin decision and rejection reason; never log cookies/tokens. | NET-001..006; RC-TRANSPORT-01/02 | AEGIS-06 approves browser/native and proxy profile; PILOT-08 verifies. |
| **AB-13 LAN / public exposure** / CTRL-08 | SCT-13A, 13B | Start clean install with defaults and inspect listening sockets/firewall/router behavior; then enable private-network mode explicitly and inspect exact interface. | Default binds loopback only; no UPnP, port-forwarding, public tunnel or plaintext; explicit opt-in exposes only approved interface with TLS and visible status; disable returns to closed/loopback profile. | Record effective bind/interface, TLS identity and opt-in state; no private key contents. | NET-001..005, NET-009; RC-TRANSPORT-01/02 | AEGIS-06 + PHOENIX-10 + ATLAS-01; PILOT-08 integration. |
| **AB-14 Resource exhaustion** / CTRL-09 | SCT-14A, 14B, 14C | Flood handshakes/connections; send oversized HTTP body, headers and WS frames; request unbounded replay/pagination; churn connections to bypass per-connection rate limits. | Numerical limits and backpressure enforced; replay/page work bounded; service remains responsive for local owner; overload fails safely without unbounded memory/CPU or auth amplification. | Aggregate counters/throttle events only; no payloads or credentials; alert thresholds documented. | NET-006..008, EVT-011; TASK-007; RC-TRANSPORT-02 | AEGIS-06 sets policy thresholds; PILOT-08 measures; PHOENIX-10 validates deployment capacity. |
| **AB-15 Audit / diagnostic leakage** / CTRL-10 | SCT-15A, 15B | Trigger success, denial, malformed input, exception, crash and support-bundle paths with synthetic canary secrets/private prompts; scan logs, traces, URLs, metrics and bundle. | No token, private key, proof, pairing code, prompt, raw tool output or unauthorized path appears; audit retains approved actor/action/outcome/correlation fields. | Expected security audit fields present and integrity/retention policy applied; redaction scan has zero canary matches. | SESS-014, TASK-016, NET-010; RC-AUDIT-01 | AEGIS-06 owns audit/redaction/retention; TUSKER-04 context propagation; PILOT-08 test. |
| **AB-16 Approval bypass** / CTRL-03, CTRL-11 | SCT-16A, 16B | Probe route inventory for approval endpoints and hidden aliases; cause AEGIS to return DENY, REQUIRE_APPROVAL, stale ALLOW, timeout, malformed or unavailable; inspect Core/executor call counters. | Remote approval route absent/disabled in MVP; every non-ALLOW outcome produces **zero Core dispatches and zero executor calls**; no fallback converts approval-required to allow. Fresh authorization occurs on retry. | Audit policy outcome and no-dispatch result; never record approval secret or imply user approved. | AUTH-006..009, AUTH-010; conditional approval suite; RC-APPROVAL-01, RC-AUTH-01 | AEGIS-06 must explicitly sign off disabled MVP policy; TUSKER-04 verifies zero executor call invariant. |
| **AB-17 Global disable bypass** / CTRL-07 | SCT-17A, 17B | While device/session and WSS are active, use local global-disable control; concurrently attempt new pairing, new session, HTTP read/mutation and WS frame; restart service while disabled. | Disable is authoritative, not cosmetic: blocks new pairing/auth and protected operations, invalidates sessions and closes streams; disabled state persists according to approved policy; re-enable requires explicit local action. | Audit local actor, disable generation/time, invalidated sessions/streams and any in-flight mutation disposition. | PAIR-010, SESS-013, NET-010; RC-DEVICE-02 | AEGIS-06 + NOVA-02; PILOT-08 integration; PHOENIX-10 lifecycle. |
| **AB-18 Local account / process abuse** / CTRL-01, CTRL-10 | SCT-18A | Under a second unprivileged local process/account, attempt pairing initiation, local confirmation and registry access; race pending enrollment state. | OS/user boundary and local-auth contract prevent unauthorized account from confirming or reading owner device secrets; UI shows stable identity/scope; no silent pairing. | Attribute local account/session and attempted action; no key/code in logs. | PAIR-001, 008..010; RC-PAIR-01/02, RC-DEVICE-01 | AEGIS-06 + NOVA-02; ATLAS-01 reviews OS boundary. |
| **AB-19 Uncertain cancel / dispatch race** / CTRL-03, CTRL-05 | SCT-19A, 19B | Drop transport before dispatch, during dispatch, after Core acceptance and during cancellation; retry same idempotency key and cancel concurrently. | Return known-not-dispatched only with proof; otherwise `unknown_outcome`; same key reconciles original operation; cancel reports accepted vs confirmed stop and side effects; no blind duplicate dispatch or false stop claim. | Correlate submit/cancel/reconcile events; record Core state and linearization evidence, not private task body. | TASK-009..015; RC-TASK-02/04 | TUSKER-04 final cancellation/idempotency contract; AEGIS-06 fresh authorization; PILOT-08 fault tests. |
| **AB-20 Compromised paired endpoint** / CTRL-06, CTRL-07 | SCT-20A | Paired client requests all allowed projections/events and attempts to widen scope; revoke device while it retains cached data and active stream. | Server discloses only approved per-device projection; revoke blocks future access/streaming; explicitly acknowledge already copied/displayed data cannot be recalled. | Audit data scope and revoke; do not claim deletion of client-side copies. | AUTH-004, EVT-002, SESS-008; RC-TASK-03, RC-REVOKE-01 | AEGIS-06 + NOVA-02; product owner accepts residual risk. |

## 3. Additional cross-cutting tests (gaps beyond the 72 scenarios)

These additive cases close concurrency, persistence, failure-injection and deployment gaps. They are **new specifications**, not part of the existing 72 count.

| Test ID | Gap / setup | Exact action | Expected result | Audit / evidence | Owners |
|---|---|---|---|---|---|
| SCT-X01 | Pairing/revocation transaction race | Race challenge completion, cancel, expiry and device revoke against the same registry record. | Single linearizable terminal outcome; no resurrected enrollment/session. | Transaction trace and state history. | AEGIS-06, PILOT-08 |
| SCT-X02 | Idempotency store crash consistency | Crash at each boundary: before Core call, after Core acceptance, before idempotency write, after write/before response; restart and retry. | Exactly one logical side effect; unresolved cases stay unknown until reconciliation. | Fault-injection schedule, persistence snapshots, Core call counter. | TUSKER-04, PILOT-08 |
| SCT-X03 | Policy timeout/unavailable/invalid response | Inject timeout, connection refusal, malformed schema and unknown policy result for read and mutation. | Fail closed; protected data not returned where policy is required; zero Core/executor calls for mutations. | Policy trace and zero-dispatch counters. | AEGIS-06, TUSKER-04 |
| SCT-X04 | Stale policy under concurrency | Obtain ALLOW, change principal/session/device/policy version, then race request/retry. | Old ALLOW cannot authorize changed context; fresh policy check per attempt. | Decision version/context hash and request correlation. | AEGIS-06 |
| SCT-X05 | Snapshot/event watermark race | Mutate task while snapshot is produced and event cursor is issued; reconnect from returned cursor. | Snapshot watermark and replay form a consistent recoverable view; no silent missing transition. | Snapshot version, sequence range and replay trace. | TUSKER-04 |
| SCT-X06 | Restart/reinstall/upgrade revocation | Revoke device, restart/upgrade/rollback service, replay old session and refresh material. | Revocation epoch cannot roll back or resurrect credentials; migration failure fails closed. | Before/after registry state and release artifact. | AEGIS-06, PHOENIX-10, ATLAS-01 |
| SCT-X07 | Clock rollback/sleep-resume | Roll server wall clock backward/forward and resume host after sleep with active sessions/challenges. | Server-authoritative monotonic expiry policy; no extension/resurrection; safe reauthentication where uncertain. | Clock fixture, expiry decision trace. | AEGIS-06, TUSKER-04 |
| SCT-X08 | Rate-limit evasion | Distribute guesses across connections, source ports, devices and restart boundaries. | Approved aggregate/device/IP/local quotas remain effective; restart does not reset security budget unexpectedly. | Aggregated counters and throttle decisions. | AEGIS-06, PILOT-08 |
| SCT-X09 | Reverse-proxy trust confusion | Send spoofed forwarded host/proto/client-IP headers directly and through untrusted proxy. | Forwarded metadata accepted only from explicitly trusted proxy; direct client cannot override. | Effective peer/host decision and config evidence. | AEGIS-06, PHOENIX-10 |
| SCT-X10 | Emergency shutdown under load | Activate global disable during handshake flood and active mutation/event load. | Disable reaches authoritative state promptly; no new work admitted; in-flight result reconciled and streams closed. | Disable latency, admitted/rejected counts, state reconciliation. | AEGIS-06, NOVA-02, PILOT-08 |

## 4. Coverage crosswalk

| Abuse cases | Existing protocol coverage | Requirement IDs | Main control IDs |
|---|---|---|---|
| AB-01..02 | PAIR-001..010; NET-006..007 | RC-PAIR-01/02, RC-DEVICE-01 | CTRL-01, CTRL-09 |
| AB-03, AB-11 | SESS-001..014; EVT-009; NET-009 | RC-SESSION-01, RC-REVOKE-01 | CTRL-02, CTRL-07 |
| AB-04, AB-05, AB-16 | AUTH-001..010; TASK-006, TASK-016 | RC-AUTH-01, RC-PRIV-01, RC-APPROVAL-01, RC-AUDIT-01 | CTRL-03, CTRL-04, CTRL-11, CTRL-12 |
| AB-06, AB-19 | TASK-002..005, TASK-009..015 | RC-TASK-02, RC-TASK-04 | CTRL-03, CTRL-05 |
| AB-07..08, AB-20 | TASK-007..008; AUTH-004; EVT-001..002, EVT-008 | RC-TASK-01/03 | CTRL-04, CTRL-06 |
| AB-09..10 | EVT-003..012 | RC-EVENT-01/02 | CTRL-06 |
| AB-12..13 | NET-001..010 | RC-TRANSPORT-01/02 | CTRL-08 |
| AB-14 | NET-006..008; EVT-011; TASK-007 | RC-TRANSPORT-02 | CTRL-09 |
| AB-15 | SESS-014; TASK-016; NET-010 | RC-AUDIT-01 | CTRL-10 |
| AB-17..18 | PAIR-001, 008..010; SESS-013; NET-010 | RC-DEVICE-01/02 | CTRL-01, CTRL-07, CTRL-10 |

**Coverage statement:** all 20 abuse cases have at least one concrete test ID; ten additive cross-cutting tests address concurrency, crash/restart, policy failure, snapshot consistency, clock, rate-limit evasion and shutdown. This is static mapping only. It does not establish executable coverage or pass status.

## 5. Mandatory AEGIS zero-dispatch assertions

For each protected mutation and each retry, instrument the Core adapter and executor boundary with test-only counters/spies. The following outcomes must assert **Core dispatch count = 0 AND executor invocation count = 0**:

1. AEGIS returns DENY.
2. AEGIS returns REQUIRE_APPROVAL (remote approval disabled in MVP).
3. AEGIS times out or is unavailable.
4. AEGIS response is malformed, unverifiable or has an unknown decision.
5. Policy decision is stale or bound to a different principal, device, session, resource, action or context.
6. Session/device is expired or revoked, or global remote access is disabled.
7. Authorization is not repeated on a retry after policy-relevant state changes.

An ALLOW from an earlier request is never a reusable capability. A successful idempotency lookup may return an existing authorized result only after the current request has passed the contractually required authorization check; TUSKER-04 and AEGIS-06 must approve the exact read/replay semantics.

## 6. Required sign-off evidence

| Owner | Required approval/evidence | Required artifact / acceptance |
|---|---|---|
| **AEGIS-06** | ACCEPT/REVISE/DEFER for DEC-AEG-001..008; normative device proof, pairing parameters, session lifetime/rotation, per-request policy schema/error behavior, revocation linearization and WSS bound, audit/redaction/retention, TLS/Host/Origin/limits, explicit approval-disabled MVP statement. | Signed/linked security contract plus reviewed SCT-01..04, 09, 11..18, X01, X03..04, X06..10 evidence; zero-dispatch proof. |
| **TUSKER-04** | Final schemas/interfaces for task submit, trusted context, idempotency durability/reconciliation, snapshot projection/redaction, event registry/cursor/replay, cancellation accepted-vs-confirmed and side effects; confirm pause/resume excluded. | Approved Core contract replacing draft REVISE dispositions; reviewed SCT-04..10, 19 and X02, X05 evidence; Core/executor counters. |
| **NOVA-02** | Approved local pairing initiation/confirmation/cancel, fingerprint/scope display, device inventory/revoke, visible connection state, global disable/re-enable, lost-device recovery and private-network opt-in UX. | UX flow/state map and usability/security review for SCT-02, 17, 18 and X10; no misleading consent or disable state. |
| **PHOENIX-10** | Clean-install/upgrade/rollback service lifecycle, listener/firewall/TLS profile, private-network opt-in and emergency shutdown deployment review. | VM/deployment evidence for SCT-13, 14, 17 and X06, X09, X10. |
| **ATLAS-01** | Fedora service account/permissions, key storage availability/fallback, firewall defaults and process/account isolation review. | Platform evidence for SCT-03, 13, 18 and X06; unsupported secure-storage behavior fails closed as approved. |
| **PILOT-08** | Freeze traceable API/event contract only after owner decisions; implement tests after stack selection; report exact build/commit/environment, results, coverage and residuals. | Executable test suite and evidence bundle for all applicable SCT cases; OpenAPI + WebSocket validation; signed GO/NO-GO record. |

## 7. Execution and release gates

### Gate A — contract freeze (before implementation)
- [ ] AEGIS-06 decisions and exact parameters are approved.
- [ ] TUSKER-04 final Core schemas and lifecycle/recovery semantics are approved.
- [ ] NOVA-02 consent, revoke, global-disable and recovery UX is approved.
- [ ] PHOENIX-10 / ATLAS-01 deployment and platform boundaries are reviewed.
- [ ] OpenAPI and normative WebSocket/event schemas validate; API-01..API-24 findings are resolved or explicitly accepted by owners.
- [ ] Implementation stack and test harness are selected by project owners.

### Gate B — security validation (before release)
- [ ] All applicable SCT-01..SCT-20 and SCT-X01..X10 are executable and pass on identified build(s).
- [ ] AEGIS zero-dispatch assertions pass for every non-ALLOW/failure condition.
- [ ] Pairing, session rotation/revoke, active WSS closure and global disable survive race/restart tests.
- [ ] Idempotency crash/retry and cancellation unknown-outcome reconciliation are demonstrated.
- [ ] Cross-resource snapshots/events and redaction scans pass.
- [ ] Resource bounds, listener defaults, TLS/Host/Origin and deployment behavior are measured on clean supported VMs.
- [ ] No critical/high findings remain unresolved; residual risks are accepted by named owners.
- [ ] AEGIS-06, TUSKER-04, NOVA-02 and release/platform owners record explicit sign-off.
- [ ] PILOT-08 publishes a signed GO/NO-GO decision.

**Current gate state:** Gate A NOT MET; Gate B NOT STARTED. Existing 72 protocol scenarios and the tests in this matrix are specifications only. Tests run: **0**. OpenAPI validation: **not run**. Runtime features: **0**. No implementation or release authorization is implied.

# AEGIS-06 Runtime Approval Transition and Test Coverage Review

**Task:** AEGIS-06-P1.3 — read-only approval/authorization transition review  
**Branch:** `06-AEGIS`  
**Base:** `345fc5a3d0f831fc714bae0cc88fa842cd9bed79`  
**Reviewed head:** `ccd5358d6af72efc2670fa584791bfaaa8d8c627`  
**Disposition:** Source review complete; no runtime or shared-contract changes authorized by this review.

## Scope and method

Reviewed `security/runtime/store.py`, `security/runtime/policy.py`, `security/runtime/broker.py`, `security/tests/test_runtime.py`, the normative `security/AUTHORIZATION_LIFECYCLE.md`, and `security/PRIVILEGED_RELEASE_GATE.md`. This is a static source/test review. No test command was run in this task, and no runtime integration behavior is claimed.

## State transition model observed

| Operation | Current state / guard | Transition on success | Fail-closed behavior observed |
|---|---|---|---|
| `create_approval` | Future expiry; fixed action/broker IDs; required actor/action/task/step and session/device/registry/resource/precondition bindings; matching audit context | Inserts `PENDING` request and `requested/accepted` audit event in one SQLite transaction | Validation rejects incomplete or malformed bindings; insert/audit failure rolls back |
| `decide` | Strict boolean decision; authenticated approver; request `PENDING`; matching audit context and identity binding; unexpired; unchanged binding | `APPROVED` or `DENIED`; expiry -> `EXPIRED`; changed binding -> `INVALIDATED` | Unauthorized or mismatched requests do not transition; audit/transaction failure rolls back |
| `issue_authorization` | Request `APPROVED`; bounded TTL; matching audit context; current policy recheck; unchanged binding and policy version | Revokes earlier `ISSUED` references, inserts a new opaque reference hash, writes `authorized/success` | Missing/failed recheck or changed/expired binding invalidates; audit/transaction failure prevents a reference being returned |
| `consume` | Authenticated peer matches principal/session/device; reference exists and is `ISSUED`; approval `APPROVED`; audit context matches; unexpired; exact operation/action/policy/registry/resource/precondition binding and current policy recheck | Marks reference and approval `CONSUMED`, creates a consumption ID, writes audit event, commits, then returns a narrow grant | Replay, revoked/inactive, expired, mismatch, unavailable authority and audit failure return no grant; audit failure rolls back; ambiguous commit returns `CONSUME_OUTCOME_UNKNOWN` |
| `reconcile` | Authenticated peer matches original principal/session/device | Returns current reference state; consumed state includes the existing consumption ID | Wrong peer, unknown reference or authority failure returns no consumption identifier |
| Audit read/checkpoint | No caller-owned transaction; chain verifies in one SQLite snapshot | Returns events or authenticated checkpoint | Invalid chain or active transaction is rejected |

The implementation has no production IPC listener or privileged handler dispatch. The returned consume grant is a narrow authorization result, not evidence that a privileged OS action ran.

## Existing source-level test evidence

The reviewed test source includes coverage for:
- expired approval, stale resource and wrong operation denial;
- wrong peer and use of an approval-request ID in place of an authorization reference;
- approver authentication failure and policy-version mismatch;
- audit failure rolling back consume, plus payload redaction;
- audit-chain tampering, external checkpoint rollback detection and malformed checkpoints;
- two concurrent consumers yielding exactly one `CONSUMED` and one `ALREADY_CONSUMED`;
- reconciliation identity binding and replay disclosure restricted to the original peer;
- oversized and invalid-Unicode authorization references;
- consume audit-context mismatch without consuming the authorization;
- narrow broker grant contents after successful consume.

These are observations of test source, not executed results. In particular, the concurrency test exercises two SQLite connections against a shared temporary database; it does not exercise a production broker or cross-process IPC boundary.

## Follow-up test gaps / recommendations

The following are candidate additions to the runtime test suite, not claims that the behavior is currently broken:

1. **Authorization re-issuance:** issue two references for one approved request; prove the first is revoked, cannot consume, and the second is the only eligible reference.
2. **Issue-time policy callback failures:** cover callback returning false, raising, and audit append failure; prove the reference table remains unchanged and no grant can be consumed.
3. **Decision race:** race approve and deny attempts from separate connections; prove exactly one terminal decision is recorded and the audit sequence agrees with the committed state.
4. **Consume policy callback failures:** cover callback returning false and raising; prove no reference or approval is consumed and no grant is returned.
5. **Expiry boundaries:** test exact equality at both approval expiry and reference expiry, plus just-before expiry, using injected timestamps.
6. **Commit ambiguity:** inject a commit failure after the consume writes; prove the API returns `CONSUME_OUTCOME_UNKNOWN`, never a grant, and reconciliation distinguishes committed from rolled-back outcomes.
7. **Malformed typed arguments:** test non-list resource scopes, booleans/non-integers for TTL, oversized operation/policy/registry values, and malformed binding mappings without mutation.
8. **Audit-chain write failure outside consume:** inject audit failure for create, decide, issue and denial/replay paths; prove state and audit remain transactionally consistent.
9. **Cross-connection state observation:** after each failure injection, reopen the database and verify persisted approval/reference state rather than relying only on the current connection.

Prioritize 1–6 because they exercise authorization lifecycle transitions and ambiguity boundaries. Do not introduce new event names, schema fields, or producer semantics to address the audit-event lifecycle gaps documented in `security/AEGIS_AUDIT_LIFECYCLE_COVERAGE.md` without Chief Architect approval and owner agreement.

## Event semantics requiring owner resolution

The current store writes `authorized/success` both when a fresh reference is issued and when a reference is consumed. The lifecycle review already records that these are distinct security transitions: fresh authorization issuance is not proof of atomic broker consume. The active candidate audit vocabulary has no explicit consume-accepted/rejected event. Do not silently reinterpret `authorized` or migrate producers; obtain the required AEGIS/NEXUS/Chief Architect decision before changing the shared vocabulary.

## Release and rollback

- **Release:** privileged operations remain **BLOCKED** under `security/PRIVILEGED_RELEASE_GATE.md`. This review does not satisfy IPC peer-authentication, production authority, NEXUS dispatch, OS confinement, or end-to-end evidence.
- **Rollback:** documentation-only; revert this file to remove the review. No database migration or runtime behavior change.

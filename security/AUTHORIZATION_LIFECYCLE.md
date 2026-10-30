# Authorization and Approval Lifecycle

**Owner:** AEGIS-06  
**Version:** 0.1.0-draft  
**Status:** Normative design; persistence and concurrency implementation pending NEXUS-07

## State model

An approval request is bound to one immutable proposal digest, principal binding, authenticated session/device binding, operation ID, canonical resource set, policy version, registry version, precondition snapshot and expiry.

PENDING -> APPROVED -> CONSUMED

PENDING -> DENIED / EXPIRED / INVALIDATED
APPROVED -> EXPIRED / REVOKED / INVALIDATED
All terminal states are immutable. A new proposal or renewed approval creates a new request ID; terminal records are never reopened.

## Transitions

| From | Event | To | Required guard |
|---|---|---|---|
| PENDING | authenticated approver approves | APPROVED | Exact digest and scope displayed; approver eligible; request unexpired |
| PENDING | approver denies | DENIED | Authenticated explicit denial |
| PENDING | deadline reached | EXPIRED | Trusted clock; expiry is inclusive |
| PENDING / APPROVED | resource, principal, session, policy, registry or precondition changes | INVALIDATED | Re-evaluation detects mismatch |
| APPROVED | administrator or policy revokes | REVOKED | Authorized revocation event |
| APPROVED | executor/broker consumes | CONSUMED | Atomic compare-and-set; all bindings revalidated |

A user dismissal is not approval. It is a terminal denial/cancellation outcome with a distinct reason code, or an explicit dismissal state if supported; it never creates authorization.

## Atomic one-time consumption

1. Broker authenticates the IPC peer independently and obtains the expected principal/session binding from trusted OS credentials.
2. Broker submits the opaque authorization reference, fixed operation ID, canonical resource scope and request correlation ID to the authorization authority.
3. Authority atomically checks state == APPROVED, expiry, revocation, audience, principal/session, digest, policy/registry version and preconditions.
4. In the same transaction, authority changes state to CONSUMED and records a unique consumption ID before returning a narrowly scoped execution grant.
5. Repeated or concurrent consume attempts return ALREADY_CONSUMED/deny. Exactly one caller can win.
6. If the consume response is lost, the broker reconciles by consumption ID and operation idempotency key; it must not assume that the grant was not consumed.

The atomic primitive must be a database transaction with a conditional update or an equivalent linearizable compare-and-set. A read-then-write sequence without atomicity is prohibited. In-memory process-local flags are insufficient across restart or multiple broker instances.

## Expiry and time

- Use a trusted monotonic deadline for in-process enforcement and a trusted wall-clock timestamp for durable audit.
- Define a small configured clock-skew tolerance; uncertainty outside it fails closed.
- Expiry is checked both at policy evaluation and at broker consumption, immediately before dispatch.
- Short-lived authorization TTL is policy-configured per operation/risk class; no global long-lived bearer token.

## Invalidation rules

Invalidate on any change to proposal arguments, resources, resolved target identity, principal, session/device binding, origin trust, operation registration, policy version, preconditions, approval eligibility, or security posture relevant to the decision. A retry is a new evaluation. No approval is transferable between users, sessions, devices, operations or resources.

## Required audit events

Record request-created, presented, approved/denied/dismissed, expired, invalidated, revoked, consume-accepted/rejected, and reconciliation outcomes. Include IDs, digest, policy/registry version, principal binding, timestamps, reason codes and correlation IDs. Never record secrets, raw credentials, authorization bearer material or sensitive argument values.

## Required concurrency tests

- Two concurrent consume requests for one approval: exactly one succeeds.
- Replayed reference after success: rejected.
- Expired, revoked, invalidated and wrong-principal/session references: rejected.
- Changed arguments/resources or policy/registry version: rejected.
- Crash after consume commit but before response: reconciliation prevents unsafe duplicate execution.
- Storage/clock/identity service unavailable: no grant is issued.


## Approval handoff and fresh authorization (AEGIS-06 C0013 clarification)

The approval-request identifier is a correlation/lookup identifier, **not** a bearer capability and is never accepted by the broker's consume method.

1. Initial policy evaluation that requires user approval returns `REQUIRE_APPROVAL`, a non-null `approval_request_id`, and `authorization_ref: null`. This decision cannot execute.
2. The approval authority authenticates the approver, verifies eligibility, and atomically changes the request from `PENDING` to `APPROVED`. The approval action itself issues no broker grant.
3. After that transition, AEGIS re-evaluates the exact proposal against current principal/session, operation, canonical arguments/resources, policy version, registry version, preconditions, expiry and security posture. Any mismatch moves the request to `INVALIDATED`; no `ALLOW` is returned.
4. Only if re-evaluation succeeds does AEGIS return a **fresh** `ALLOW` decision with a new opaque `authorization_ref` and short expiry. The reference is bound to the approved request, exact action digest, principal/session, operation, canonical resources, policy/registry versions and precondition snapshot. The original `REQUIRE_APPROVAL` decision remains non-authorizing.
5. The broker consumes only this fresh `authorization_ref`, never `approval_request_id`. Consumption is a durable atomic compare-and-set from `APPROVED` to `CONSUMED`; it records a unique `consumption_id` and durable pre-dispatch audit evidence before returning the narrow grant.
6. Any earlier authorization reference associated with the same approval request is invalidated/revoked when a fresh reference is issued. A consumed reference is never reissued. If an approval is invalidated or expires, a changed/retried proposal requires a new evaluation and new approval request ID; terminal requests are not reopened.

### Canonical consume outcomes

The adapter returns a typed outcome, not a boolean:

| Outcome | Meaning | Grant / handler rule |
|---|---|---|
| `CONSUMED` | Atomic consume succeeded; includes unique `consumption_id` and narrow grant | Broker may proceed after its own checks and durable dispatch-start audit |
| `NOT_APPROVED` | Request is still pending or has no approved state | No grant; zero handler calls |
| `DENIED` | User explicitly denied/dismissed the request | No grant; zero handler calls |
| `EXPIRED` | Request or authorization TTL elapsed | No grant; zero handler calls |
| `REVOKED` | Approval/authorization was revoked | No grant; zero handler calls |
| `INVALIDATED` | Action, identity/session, operation, resource, policy/registry version or precondition changed | No grant; zero handler calls |
| `ALREADY_CONSUMED` | Reference was consumed previously or lost a consume race | No new grant or dispatch; reconcile existing consumption |
| `BINDING_MISMATCH` | Supplied peer, operation, digest or resource binding does not match | No grant; zero handler calls; security audit |
| `CALLER_UNAUTHORIZED` | Authenticated IPC peer is not eligible for this operation | No grant; zero handler calls |
| `AUTHORITY_UNAVAILABLE` | Authorization authority/store unavailable or transaction outcome cannot be confirmed | No grant; zero handler calls; if commit may have happened, reconcile |
| `IDENTITY_UNAVAILABLE` | Trusted principal/session evidence unavailable | No grant; zero handler calls |
| `CLOCK_UNCERTAIN` | Trusted time/expiry cannot be established within configured skew | No grant; zero handler calls |
| `AUDIT_UNAVAILABLE` | Required durable pre-dispatch audit cannot be committed | No grant; consume transaction must not commit; zero handler calls |
| `CONSUME_OUTCOME_UNKNOWN` | Caller lost the response and cannot yet determine whether consume committed | No new grant or dispatch; reconcile by request correlation/consumption ID and idempotency key |

The authority must atomically persist the consume state and its required pre-dispatch audit evidence before returning `CONSUMED`. If this cannot be guaranteed in one durable transaction or equivalent protocol, it must not return a grant. The broker separately persists its dispatch intent before invoking the handler. A post-dispatch disconnect remains `UNKNOWN` under the broker result contract; it is not a consume retry.

The approval-request ID remains stable for audit correlation through this handoff. It is not secret, not sufficient to authorize, and not interchangeable with `authorization_ref`.

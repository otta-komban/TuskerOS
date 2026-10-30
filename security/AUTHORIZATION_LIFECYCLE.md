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

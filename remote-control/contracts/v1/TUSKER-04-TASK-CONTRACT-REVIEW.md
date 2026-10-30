# TUSKER-04 Remote Task Boundary — Review Capture

**Status:** Owner-provided draft v0.1; incorporated as a proposal, not a jointly approved contract  
**Source:** TUSKER-04 response on [issue #14](https://github.com/otta-komban/TuskerOS/issues/14)  
**Captured by:** PILOT-08  
**Date:** 2026-10-31

## Ownership boundary

PILOT-08 is an authenticated remote adapter, not a second task engine. Every remote task submission must enter the same Tusker Core task creation, planning, authorization, execution and verification path used by local requests. PILOT-08 does not select tools, assign risk, inject policy outcomes or submit privileged tool calls.

## Submission contract proposal

The TUSKER-04 response proposes these logical fields:

- `schema_version`
- `request_id`
- `idempotency_key`
- `principal_ref`, derived from the validated session and never trusted from client JSON
- `origin={kind:"remote", device_ref}`, attached by the trusted gateway/Core adapter
- `user_request`
- Optional bounded context references

The remote HTTP adapter carries the idempotency key and correlation/request identifier in headers. It must derive principal and origin from authenticated server-side context, not accept them as client-controlled authority claims.

A successful acceptance response should identify `task_id`, `accepted`, current `state`, `created_at` and a safe status summary.

Idempotency is scoped to the authenticated principal plus idempotency key. A repeated identical request returns the original task/result. Reuse of the same key with a conflicting payload returns a conflict.

## Read and event projections

- Task list/detail responses are authorization-scoped projections.
- Private prompts, filesystem paths, outputs and evidence are redacted according to user settings and device scope.
- Events carry an ordered per-task sequence and cursor/last-sequence for resynchronization.
- Delivery may duplicate or lose events. On reconnect, the client obtains an authoritative snapshot and replays from a supported cursor.
- PILOT-08 must not treat event receipt as authorization to perform an action.

## Lifecycle operations

- Cancellation is accepted only for nonterminal tasks and routed to the Core scheduler. The API must distinguish an accepted cancellation request from a confirmed stop and communicate possible side effects.
- Pause/resume remain unsupported unless Core exposes a safe checkpoint for the specific task.
- Remote approval remains disabled by default. Any future approval must bind the exact action/resource/input digest, actor, device/session, expiry and audit reference, with AEGIS-06 as policy authority.

## Identity, retries and failure behavior

- Carry trusted principal, device/session reference and correlation ID into Core and AEGIS audit context.
- Never accept a client-supplied role or authorization result.
- Policy unavailable/invalid, expired session, unknown device or revoked credential fails closed before mutation.
- A timeout or transport loss after dispatch is `unknown_outcome` until Core reconciles actual state. Do not blindly retry non-idempotent actions.
- Expose no shell, D-Bus, Polkit, NEXUS provider or privileged-broker endpoint.

## PILOT-08 incorporation and open review

This response is incorporated into the draft OpenAPI contract and event/lifecycle requirements. It is not a final sign-off: the TUSKER-04 comment itself requests further AEGIS review of remote identity/approval semantics. AEGIS-06 has not yet responded on issue #13; NOVA-02 has not yet responded on issue #15.

Before implementation, owners still need to agree:
1. Canonical task-state enum and terminal-state definition.
2. Exact Core task submission and snapshot interfaces.
3. Cursor retention and replay guarantees.
4. Error codes and the point at which an operation becomes `unknown_outcome`.
5. Whether cancellation confirmation and side-effect reporting are available from Core.
6. Any task-specific safe checkpoint semantics.

No runtime implementation or tests are claimed by this document.

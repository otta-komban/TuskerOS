# Approval binding schema review

**Owner:** AEGIS-06  
**Status:** Draft review; runtime-owner acceptance pending  
**Current draft:** approval-request schema 0.2.0  
**Related finding:** SEC-SCHEMA-001

## Current branch state

The branch now contains `security/schemas/approval-request.schema.json` with `$id` and `schema_version` set to `0.2.0`. The required `binding` object contains:

- `session_binding`: SHA-256 binding for authenticated session context;
- `device_binding`: SHA-256 binding for authenticated device context;
- `registry_version`: exact operation-registry revision (non-empty, max 128);
- `resource_scope`: non-empty unique array of canonical resource identifier strings (max 512 each);
- `precondition_digest`: SHA-256 digest of the relevant precondition snapshot.

This document reviews that current draft; it does not claim that AEGIS-06 authored the schema change or that runtime owners have accepted it.

## Review findings

1. **Versioning:** Advancing from 0.1.0 to 0.2.0 is the correct compatibility posture for newly required binding fields. Do not accept 0.1.0 and 0.2.0 payloads under one validator or silently reinterpret an old message.
2. **Identity trust:** `session_binding` and `device_binding` must be derived by the trusted authentication/authorization boundary. A caller- or UI-supplied digest is not proof of identity. The authority must recompute/compare bindings at consume time.
3. **Registry trust:** `registry_version` must come from the exact immutable registry snapshot used for evaluation and be rechecked at consumption.
4. **Resource scope:** The schema currently models scope as canonical opaque strings. Producers/consumers must define the canonical grammar, stable ordering, semantic duplicate detection and resource-to-operation access mapping. JSON Schema `uniqueItems` does not prove that differently encoded identifiers refer to different resources.
5. **Preconditions:** `precondition_digest` must be derived from authoritative state, not accepted as a client assertion; the authority must recompute it immediately before consume.
6. **Action digest:** The existing `action_digest` must cover operation ID, canonical arguments, resolved resource scope, principal/session/device bindings, schema version, policy version, registry version and precondition digest. The nested fields do not replace RFC 8785 canonicalization or the digest.
7. **Fail-closed behavior:** Missing/null bindings, unknown registry version, empty resource scope, changed session/device/resource/precondition state, or unavailable identity/registry/precondition services must deny and invalidate the approval.

## Compatibility and migration

- Preserve approval-request 0.1.0 as a historical draft; do not mutate its meaning.
- Treat 0.2.0 as a distinct draft wire format.
- Producers unable to provide all binding values must not issue an approval request or authorization.
- Runtime owners must identify any existing 0.1.0 producers and provide an explicit migration plan.
- The current schema shape is not frozen until producer, UI and broker owners accept the representation and conformance tests pass.

## Required conformance tests

Positive:
- all binding values are derived from trusted services and present in a 0.2.0 envelope;
- canonical resource identifiers are stable across equivalent input ordering;
- unchanged bindings permit exactly one successful consume.

Negative:
- missing/null binding members, empty resource scope, duplicate semantic resources and malformed digests;
- client-supplied binding differs from trusted session/device/registry/resource/precondition state;
- session, device, registry, resource or precondition changes between approval and consume;
- 0.1.0 payload presented to a 0.2.0 validator and vice versa;
- identity, registry, precondition or authorization-store outage.

## Owner acceptance required

- **NEXUS-07:** authorization-service storage/lookup, atomic consume and runtime representation.
- **TUSKER-04:** action digest inputs and proposal/decision producer compatibility.
- **NOVA-02:** exact resource scope shown in the approval UI and trusted display source.
- **PILOT-08:** authoritative session/device binding source and lifecycle.
- **AEGIS-06:** security semantics, schema and negative-test review.

Until these owners accept the contract and tests run against the implementation, SEC-SCHEMA-001 remains an integration blocker. Privileged execution remains blocked.

# Approval binding schema proposal

**Owner:** AEGIS-06  
**Status:** Proposed; not an accepted runtime contract  
**Target schema:** approval-request 0.2.0-draft  
**Related finding:** SEC-SCHEMA-001

## Decision requested

Represent the complete approval binding in the approval-request envelope using explicit, non-null fields. Do not mutate the existing 0.1.0 draft in place: adding required fields is a compatibility break, so publish a new schema identifier/version only after NEXUS-07, TUSKER-04 and the approval-UI owner accept the shape.

## Proposed fields

| Field | Proposed type | Required | Purpose |
|---|---|---:|---|
| `session_device_binding` | string matching `^sha256:[a-f0-9]{64}$` | yes | Opaque digest binding the authenticated session and device context; never expose raw session/device identifiers |
| `registry_version` | non-empty string, max 64 | yes | Exact operation-registry revision used for policy evaluation |
| `resource_scope` | array of strict resource objects | yes | Canonical resource identifiers and permitted access modes covered by approval |
| `precondition_digest` | string matching `^sha256:[a-f0-9]{64}$` | yes | Digest of the authoritative precondition snapshot evaluated for this proposal |

Each `resource_scope` item should contain:
- `kind`: non-empty resource type identifier, max 64 characters;
- `resource_id`: canonical opaque identifier, max 512 characters;
- `access_modes`: non-empty unique array from `read`, `create`, `modify`, `delete`, `execute`, `administer`.

The resource array must be canonicalized before digesting: stable sort by kind and resource identifier, normalize access-mode ordering, and reject duplicate semantic resources. JSON Schema `uniqueItems` alone does not enforce semantic uniqueness when object property order or access-mode order differs; the producer/consumer must perform canonical validation.

## Trust and binding rules

1. The policy/authorization authority derives session/device binding from authenticated OS/session context. A caller-supplied digest is not proof of identity.
2. The registry version, resolved resource scope and precondition digest are produced by trusted policy/registry evaluation, not accepted as authoritative client assertions.
3. The approver sees the trusted operation summary, target/resource scope, impact, risk and reversibility. Internal digests and opaque bindings need not be displayed, but the exact human-readable scope must be derived from the same trusted resource set.
4. The action digest covers the operation ID, canonical arguments, resolved resources, principal binding, session/device binding, schema version, policy version, registry version and precondition snapshot digest.
5. At approval consumption, the authority independently re-derives and compares every binding. Any missing value, mismatch, changed resource, session/device change, registry update or precondition change fails closed and invalidates the approval.
6. Binding fields are non-null and mandatory. No default, wildcard or empty-scope interpretation is permitted.
7. The broker receives only the opaque authorization reference and independently authenticated peer identity; it does not trust UI-returned fields or a client-provided binding object.

## Compatibility and migration

- Keep the current 0.1.0 schema immutable as a historical draft artifact.
- Publish a separate 0.2.0-draft schema with the four required fields and strict nested resource schema after owner review.
- A producer that cannot supply any required binding must not issue an approval request or authorization.
- Do not accept mixed 0.1.0/0.2.0 envelopes under one schema identifier.
- Runtime owners must state whether any existing prototype emits 0.1.0 and provide a migration/test plan before freezing 0.2.0.

## Required conformance tests

Positive:
- all four binding dimensions present and derived by trusted services;
- multiple resources canonicalize deterministically;
- same approved proposal and unchanged bindings consume successfully once.

Negative:
- missing/null session/device binding, registry version, resource scope or precondition digest;
- empty or duplicate resource scope, unknown access mode, non-canonical resource identity;
- caller-supplied binding differs from trusted session/registry/resource/precondition state;
- session/device, registry, resource or precondition changes between approval and consume;
- 0.1.0 payload presented to a 0.2.0 validator and vice versa;
- authorization-store, registry, identity or precondition service unavailable.

## Owner acceptance required

- **NEXUS-07:** authorization-service storage/lookup, atomic consume and runtime representation.
- **TUSKER-04:** action digest inputs and proposal/decision producer compatibility.
- **NOVA-02:** which trusted scope fields are rendered in the approval UI.
- **PILOT-08:** authoritative session/device binding source and lifecycle.
- **AEGIS-06:** security semantics, schema and negative-test review.

Until these owners accept the contract and tests run against the implementation, this remains a proposal. Privileged execution remains blocked.

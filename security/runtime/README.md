# AEGIS runtime primitives — milestone 1

**Status: internal, non-production. Privileged handlers remain disabled.**

This package implements a deterministic policy evaluator, SQLite-backed approval and authorization state machine, HMAC-authenticated audit chain, and narrow broker authorization adapter. It does not implement a Linux IPC listener, OS peer-credential extraction, trusted registry loader, or NEXUS dispatch.

## Security properties

- DENY when identity, registry verification, argument-schema validation, resource resolution, precondition verification, or canonical data is missing or invalid.
- Trust dependencies are injected callbacks. Production adapters must source them from authenticated OS/session state and integrity-protected registry/schema artifacts.
- Complete operation-registration v0.1.0 entries are checked against the schema's required fields, property allowlist, identifier bounds, resource/precondition limits, rate-limit shape and approval/risk constraints before use. The injected registry verifier remains responsible for authenticity/signature trust; shape validation does not establish provenance.
- Registry scope is validated fail-closed: allowed origins must be unique members of the supported origin set; principal-class allowlists must contain unique non-empty strings of at most 64 characters; authenticated principal classes use the same bound. Resource declarations reject duplicate kinds and malformed/duplicate/unsupported access modes.
- R0/R1 registered actions may receive ALLOW; R2/R3/R4 require approval. R5 and unsupported risk-escalation rules are denied.
- Mutations require idempotency keys. Resource mutations are escalated to at least R3; execute/delete/administer to R4.
- The digest binds arguments, canonical resources, principal/session/device, origin, principal class, precondition digest, fixed broker operation, operation schema version, and policy/registry versions.
- Unicode is preserved without normalization. Lone surrogates, unsafe integers and floating-point values are rejected until a vetted full RFC 8785 implementation is selected. The repository's two Unicode reference vectors match exact bytes and digests.
- Approval binds proposal/action digest, principal, session/device, fixed broker operation, exact resources, policy/registry versions, precondition digest, task/step correlation and expiry. R5 cannot enter the approval path.
- Approver authentication and post-approval policy re-evaluation are mandatory callbacks. Missing callbacks fail closed.
- Opaque authorization references are random; only SHA-256 token hashes are stored. Approval request IDs are not consume credentials.
- BEGIN IMMEDIATE serializes transitions. Consume state, durable consumption ID and required audit evidence commit in one SQLite transaction. Replays return ALREADY_CONSUMED and the original consumption ID.
- Audit rows are projected onto the candidate v0.2.0 field allowlist, redacted, and chained with HMAC-SHA-256. Verification rejects sequence gaps/renumbering, invalid checkpoint sequence types, non-genesis hashes at sequence zero, and broken/truncated chains. The HMAC key is externally managed and never stored in this database. SQLite uses WAL and synchronous=FULL.

## Tests

Run from repository root:

    python -m pytest -q security/tests
    python -m compileall -q security/runtime security/tests

## Production blockers

1. NEXUS accepted security invariants in principle but has not accepted a transport/API, OS peer-identity injection, authorization-service owner, durable store owner, or consume request/response contract.
2. Full RFC 8785 canonicalization and conformance suite are not implemented; floating-point values are denied.
3. Trusted registry loading/signature verification, current precondition resolver and action-specific schema validator must be integrated.
4. NEXUS must implement durable dispatch intent, idempotency/reconciliation, fixed handler mapping, OS confinement, independent precondition checks, postcondition verification and zero-handler-call integration tests.
5. Audit key provisioning/rotation, access control, external checkpoints, backup/restore and tamper recovery need platform integration.

This milestone does not enable privileged execution and does not satisfy security/PRIVILEGED_RELEASE_GATE.md.

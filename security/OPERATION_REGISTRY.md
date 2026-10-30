# Operation Registry Governance

**Owner:** AEGIS-06 (policy semantics); implementation ownership pending NEXUS-07  
**Version:** 0.1.0-draft

## Purpose

The registry is the allowlist connecting stable Tusker action IDs to validated schemas, risk rules and fixed broker implementations. It is security policy, not plugin metadata and not model-generated configuration.

## Required registration fields

Every entry conforms to security/schemas/operation-registration.schema.json and supplies:

- Stable, namespaced action_id and schema/registry version.
- Strict argument schema reference and canonicalization version.
- Allowed principal classes and trusted origins.
- Resource kinds and permitted access modes.
- Minimum risk class and deterministic escalation predicates.
- Approval mode and eligible approver class.
- Fixed broker operation ID; never an executable path, shell fragment or caller-selected handler.
- Timeout, output and resource limits.
- Idempotency requirements and reconciliation behavior.
- Preconditions and independent postcondition verifier.
- Named owner, reviewer, rationale, test evidence and lifecycle status (proposed, approved, deprecated, revoked).

## Admission and change control

1. New registrations begin disabled/proposed and are denied by the runtime.
2. Owner supplies threat analysis, least-privilege scope, argument schema, resource model, failure semantics and positive/negative tests.
3. Security review checks risk classification, principal/origin scope, approval mode, broker mapping and audit coverage.
4. Runtime/broker owner verifies the implementation mapping and independent enforcement.
5. An authorized release process signs or otherwise integrity-protects the immutable registry artifact and records its digest.
6. Deployment activates a versioned snapshot; policy decisions bind that exact version.
7. Changes create a new version and invalidate approvals created against prior versions where semantics or scope change.
8. Revocation is immediate at authorization consumption, including for cached policy decisions.

No single plugin, extension, model, ordinary user process or UI component can add or widen registrations. Emergency changes use a separately authenticated administrator path and are audited.

## Default-deny and scope

- The initial registry is empty; all operations are denied until individually reviewed and enabled.
- Wildcards, arbitrary command execution, generic filesystem write, generic package install, unrestricted network access and caller-defined broker IDs are prohibited.
- Read operations are registered and policy-evaluated too; read-only does not mean unrestricted.
- Mutation registrations require idempotency semantics even if the generic proposal envelope makes idempotency_key optional for non-mutating actions.
- Resource identifiers are resolved to canonical objects before authorization; display paths/names alone are not authority.
- Every operation has a bounded timeout, output size and resource budget.

## Ownership and review

AEGIS owns the policy meaning and approval criteria. NEXUS-07 must confirm the runtime registry storage, loader, signature/integrity mechanism and fixed broker ID mapping. TUSKER-04 owns action proposal production and typed client integration, not authorization. FORGE-09 may propose extension capabilities but cannot self-register privileged actions.

Each registration has a named operational owner and security reviewer. Review is required on code change, schema change, dependency change, privilege expansion, new resource kind, changed risk/approval rule or material threat-model update.

## Registry failure

Missing, corrupt, unverifiable, stale beyond policy, unavailable or internally inconsistent registry => deny all affected operations. Never fall back to a permissive built-in registry or cached arbitrary mapping.

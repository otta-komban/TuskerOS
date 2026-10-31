

## 9. P1.2 audit lifecycle coverage review — 2026-10-31

Created `security/AEGIS_AUDIT_LIFECYCLE_COVERAGE.md` as a read-only comparison of the normative authorization lifecycle, security contract, active audit-event v0.1.0 schema and candidate v0.2.0 schema.

The event mapping confirms direct candidate coverage for request receipt, approval grant/denial/expiry, authorization decision, dispatch/execution, cancellation and compensation. It identifies missing or ambiguous candidate coverage for approval presentation, dismissal semantics, invalidation, revocation, atomic consume acceptance/rejection, and consume/execution reconciliation. In particular, `authorized` is not evidence of broker consume, and `outcome_unknown` is not a reconciliation result; neither should be overloaded to represent those transitions.

**Disposition:** event-lifecycle mapping subtask complete as a source review. Overall P1.2 remains **in progress** because the field-by-field required/nullable/conditional audit and owner acceptance are still pending. No shared schema, event vocabulary, producer, consumer or runtime behavior was changed. No tests were run for this documentation-only review. The candidate v0.2.0 schema remains unapproved for producer migration.

Owner decisions are requested from NEXUS-07 (trusted producer/timing and consume/reconciliation semantics), TUSKER-04 (correlation and event ordering), NOVA-02 (presentation/dismissal evidence), and the Chief Architect (any versioned wire-format changes). Privileged execution remains blocked by `security/PRIVILEGED_RELEASE_GATE.md`.

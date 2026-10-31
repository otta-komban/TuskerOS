# Release validation report contract

Owner: PHOENIX-10  
Status: proposed machine-readable evidence contract; no validator or promotion gate is implemented by this document.

## Purpose

`schemas/release-validation-report.schema.json` defines a durable report envelope for checks performed against one immutable release manifest. It complements, but does not replace, `schemas/release-manifest.schema.json` and `docs/RELEASE-MANIFEST-VALIDATION-PLAN.md`.

A report is evidence about a particular candidate, not an approval token. A schema-valid report does not prove that its evidence URIs are accessible, its hashes match retrieved bytes, the validator is trustworthy, or a release may be promoted.

## Required identity and provenance

- `subject.manifest_sha256` identifies the exact manifest bytes evaluated.
- `subject.release_id` is a human-readable cross-reference, not the integrity key.
- `subject.artifact_digests` records the artifact SHA-256 values covered by the report.
- `validator.name` and `validator.version` identify the implementation; `source_commit` pins its source when available.
- `started_at_utc` and `finished_at_utc` delimit the report run and must be RFC 3339 UTC timestamps ending in `Z`.
- Each check repeats `subject_digest` so detached check records cannot be silently reassigned to another candidate.

## Check outcomes

Each check has a stable `check_id`, category, status, subject digest and explanatory message. Status values are:

| Status | Meaning |
|---|---|
| `passed` | The named check ran and its acceptance condition was met. |
| `failed` | The check ran and found a violation. |
| `blocked` | The check could not safely or correctly run because a prerequisite was unavailable or unresolved. |
| `not_run` | The check was intentionally or operationally not executed. |

Evidence entries identify retained material by URI and SHA-256. A report consumer must fetch the referenced bytes and recompute their digest; trusting a URI string or a report-provided digest alone is insufficient. Findings should be concise, actionable diagnostics and must not contain secrets, credentials, private keys or unnecessary personal data.

## Summary and semantic validation

The JSON Schema checks field shape and allowed values. A semantic validator must additionally enforce all of the following:

1. `summary.total` equals the number of check records.
2. The four outcome counters equal the actual status distribution and sum to `summary.total`.
3. `overall_status` is derived deterministically: `failed` if any check failed; otherwise `blocked` if any check is blocked; otherwise `incomplete` if any check is not_run; otherwise `passed`.
4. The manifest digest and artifact digest set match the manifest bytes and its declared artifact inventory.
5. Every check's `subject_digest` equals the report subject manifest digest unless a future version explicitly defines another subject type.
6. Evidence is retrievable, its bytes match the declared SHA-256, and the evidence is attributable to this exact candidate and check.
7. The finish timestamp is not earlier than the start timestamp; per-check times, when present, fall within the report interval.
8. Duplicate `check_id` values are rejected unless a future schema version defines explicit attempt identifiers and aggregation rules.

The semantic validator also rejects duplicate JSON object member names at every nesting level and rejects non-standard numeric constants (`NaN`, `Infinity` and `-Infinity`). This prevents parser-dependent ambiguity where one consumer uses the first occurrence and another uses the last, and ensures inputs conform to JSON rather than Python's permissive decoder extensions. The overall-status derivation above is deliberately stricter than JSON Schema's structural constraints. Consumers must not treat a user-supplied `overall_status` or summary counter as authoritative without recomputing it.

## Promotion use

A promotion controller may consume a report only after validating the report schema, semantic invariants, evidence bytes, validator identity and the AEGIS-06 release trust policy. A report cannot override missing required tests, failed checks, unresolved trust policy, anti-rollback requirements or staged-artifact digest mismatches. Rebuilding or changing any artifact creates a new manifest subject and requires fresh validation.

## Privacy and retention

Do not include secrets, signing private keys, authorization tokens, raw disk identifiers or user data. Use opaque runner identifiers and access-controlled evidence locations. Retain the report and referenced evidence under the project's release-evidence retention policy once that policy is approved.

## Conformance cases

- Accept a structurally complete report with all checks passed.
- Reject malformed manifest/check digests, unsupported statuses and unknown fields.
- Reject empty check arrays and zero total counts.
- Semantic validator rejects mismatched summary counters and incorrect overall status.
- Semantic validator rejects any check bound to a different manifest digest.
- Strict JSON parsing rejects duplicate object keys and non-standard numeric constants.
- Evidence verifier rejects missing references and byte/hash mismatches.
- Semantic validator rejects reversed timestamps and duplicate check IDs.
- A blocked or not-run required check must prevent a passed overall status.

No report fixture suite, JSON Schema engine, evidence fetcher, semantic validator, signature verifier or promotion controller has been implemented or executed in this completion.

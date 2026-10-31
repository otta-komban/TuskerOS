# Release manifest validation plan

Owner: PHOENIX-10  
Status: proposed test plan; no production validator or promotion gate is implemented by this document.

## Scope

Validate manifests against `schemas/release-manifest.schema.json` using a JSON Schema Draft 2020-12 implementation with date-time format assertion enabled. Then run semantic and evidence checks that JSON Schema cannot express or cannot prove. Keep schema validation, evidence verification, test-gate evaluation and signing as separate stages.

## Structural test matrix

| ID | Fixture/change | Expected result |
|---|---|---|
| RM-S01 | Minimal complete manifest with all required top-level and artifact fields | Schema accepts |
| RM-S02 | Unsupported schema version | Reject |
| RM-S03 | Missing source commit, recipe commit, platform, SBOM or provenance | Reject |
| RM-S04 | Git commit is neither exactly 40 nor 64 lowercase hexadecimal characters | Reject |
| RM-S05 | Timestamp has a numeric offset instead of UTC `Z` | Reject |
| RM-S06 | Invalid RFC 3339 date-time with format assertion enabled | Reject |
| RM-S07 | Empty repositories, package inventory or artifact list | Reject |
| RM-S08 | Artifact has zero-byte size or malformed SHA-256 | Reject |
| RM-S09 | Empty firmware target list or unsupported firmware value | Reject |
| RM-S10 | Unknown property at a closed object boundary | Reject |
| RM-S11 | Test status outside passed/failed/blocked/not_tested | Reject |
| RM-S12 | Test result omits status | Reject |
| RM-S13 | Valid unsigned candidate omits optional artifact signature | Accept structurally; signing gate remains pending |
| RM-S14 | Duplicate object values in arrays | Schema behavior documented; semantic uniqueness checks still required |

## Semantic and evidence test matrix

| ID | Validation | Expected result |
|---|---|---|
| RM-E01 | Recompute each artifact byte length and SHA-256 from actual bytes | Exact match required |
| RM-E02 | Fetch SBOM/provenance references and verify their SHA-256 | Exact match and parseable supported format required |
| RM-E03 | Resolve source and recipe commits from their repositories | Exact immutable commits must exist and be readable |
| RM-E04 | Compare repository snapshot identifiers and resolved package NEVRAs to retained build evidence | Exact match required |
| RM-E05 | Compare artifact architecture with platform and package architectures | Mismatch rejects candidate |
| RM-E06 | Check artifact IDs and filenames for duplicates/path traversal | Reject duplicates and unsafe paths |
| RM-E07 | Compare signature verification result with AEGIS-06 trust policy | Do not accept until authoritative verifier and trust policy exist |
| RM-E08 | Re-download staged artifact and recompute size/digest | Must match pre-stage bytes |
| RM-E09 | Check required test statuses and linked reports | Every required gate must be passed with retained evidence |
| RM-E10 | Check report timestamps, runner identity, firmware mode and test target | Evidence must be attributable to this exact candidate |
| RM-E11 | Mutate artifact bytes after verification | Invalidate candidate verification and any prior signature |
| RM-E12 | Replay older release against approved security epoch/rollback policy | Defer decision to AEGIS-06's authoritative anti-rollback contract |

## Promotion gate

1. Parse JSON and validate Draft 2020-12 schema with format assertion enabled.
2. Run semantic checks, including uniqueness, architecture consistency, immutable source resolution and safe artifact names.
3. Fetch every evidence reference and verify its digest against downloaded bytes.
4. Evaluate test gates from retained reports; missing, blocked, failed or not-tested required evidence cannot pass.
5. Verify signatures and rollback metadata only through the AEGIS-06 approved trust implementation.
6. Re-verify staged bytes after upload and before publication.
7. Record validator version, policy version, candidate digest, each check result and evidence reference.
8. Any changed artifact bytes create a new candidate and require the full validation sequence again.

A JSON Schema pass is not a release verification pass. A successful build is not a boot/install pass. UEFI and Secure Boot remain independent tests.

## Implementation prerequisites

- Select and pin a JSON Schema Draft 2020-12 validator and its format-assertion behavior.
- Define a versioned validator CLI and machine-readable report only after repository tooling conventions are reviewed.
- ATLAS-01 must confirm package/repository snapshot evidence and pinned image-build inputs.
- AEGIS-06 must define signature format, trust roots, key lifecycle and anti-rollback policy.
- CI must run structural fixtures and semantic checks before any promotion job is enabled.

## Current execution status

No validator executable, CI job, fixture suite, artifact hash verification, signature verification, staged download or release promotion test has been run in this completion. The matrix above is a test specification, not execution evidence.

# Release manifest validation plan

Owner: PHOENIX-10  
Status: partially implemented; structural and local byte-integrity checks exist. Cryptographic trust, remote evidence, and promotion remain blocked pending owner decisions.

## Scope and stages

Keep these stages separate:

1. Parse JSON strictly and validate Draft 2020-12 structure with date-time format assertion.
2. Run semantic checks for unique IDs/filenames, safe local paths, and platform/artifact architecture consistency.
3. Recompute local artifact byte sizes and SHA-256 values; recompute local SBOM, provenance and optional signature-file digests.
4. Evaluate whether required per-artifact test statuses are passed and have report references.
5. Verify signatures and rollback metadata only through the AEGIS-06 approved trust implementation.
6. Re-verify staged bytes after upload and before publication.

A schema pass or byte-integrity pass is not a release verification or promotion pass. UEFI and Secure Boot remain independent tests.

## Structural test matrix

| ID | Fixture/change | Expected result |
|---|---|---|
| RM-S01 | Complete manifest with required top-level and artifact fields | Schema accepts |
| RM-S02 | Unsupported schema version | Reject |
| RM-S03 | Missing source/recipe/platform/SBOM/provenance | Reject |
| RM-S04 | Invalid immutable commit identifier | Reject |
| RM-S05 | Timestamp without UTC Z suffix | Reject |
| RM-S06 | Invalid RFC 3339 date-time with format assertion enabled | Reject |
| RM-S07 | Empty repository, package or artifact inventory | Reject |
| RM-S08 | Zero-byte artifact or malformed SHA-256 | Reject |
| RM-S09 | Empty/unsupported firmware target | Reject |
| RM-S10 | Unknown property at a closed object boundary | Reject |
| RM-S11 | Unsupported test status or missing status | Reject |
| RM-S12 | Optional signature omitted | Structurally valid; cryptographic gate remains blocked |

## Semantic and evidence test matrix

| ID | Validation | Expected result |
|---|---|---|
| RM-E01 | Recompute artifact size and SHA-256 from actual bytes | Exact match required |
| RM-E02 | Recompute local SBOM/provenance reference SHA-256 | Exact match required |
| RM-E03 | Duplicate artifact IDs or filenames | Reject |
| RM-E04 | Artifact architecture differs from platform | Reject |
| RM-E05 | Absolute path, parent traversal, remote URI or symlink escape | Reject |
| RM-E06 | Referenced signature file bytes | Digest match only; not cryptographic trust |
| RM-E07 | Required test status missing, blocked, failed or not tested | Promotion remains blocked |
| RM-E08 | Mutate artifact bytes after manifest creation | Reject digest/size mismatch |
| RM-E09 | Duplicate JSON object keys | Reject |
| RM-E10 | Resolve source/recipe commits, verify evidence formats and trust policy | Pending external/owner-controlled implementations |
| RM-E11 | Re-download staged artifact and recompute digest | Pending staging/publishing integration |
| RM-E12 | Anti-rollback / security epoch | Defer to AEGIS-06 authoritative policy |

## Current implementation

scripts/verify_release_manifest.py implements strict JSON parsing, Draft 2020-12 validation, local path/symlink confinement, artifact/SBOM/provenance byte-digest checks, optional signature-file digest checks, architecture and duplicate checks, and test-status reporting. tests/test_verify_release_manifest.py covers positive and negative paths. .github/workflows/phoenix-release-validation.yml runs the dedicated test suite.

The tool intentionally reports promotion_ready=false and returns exit code 3 after successful integrity checks because the AEGIS-owned cryptographic signature verifier/trust-root policy has not been selected or integrated. It does not claim Git ref resolution, SBOM/provenance semantic validation, remote evidence retrieval, image build, VM boot, installer execution or storage recovery. See docs/PHOENIX-10-RELEASE-VERIFIER.md.

## Owner dependencies

- ATLAS-01: exact package/repository snapshot inputs, immutable image recipe and build/SBOM/provenance production.
- AEGIS-06 / release maintainers: selected signature format, trusted root, key custody/rotation/revocation, anti-rollback policy and verifier integration.
- NEXUS-07: stable storage identity, typed inventory/preflight and destructive operation schemas; PHOENIX must not invent broker/action IDs.

Destructive storage implementation remains blocked until NEXUS-07 and AEGIS-06 accept compatible contracts and negative authorization tests.

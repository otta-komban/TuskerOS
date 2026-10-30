# TuskerOS Release Artifact Contract

Status: draft for ATLAS-01 and AEGIS-06 review; not a production signing specification.

## Required release identity
A release manifest records schema/version, channel, UTC creation time, immutable source and image-recipe commits, Fedora release, architecture, builder/version, immutable build environment, repository IDs/URLs/snapshot identifiers, exact RPM NEVRAs, SBOM and provenance references.

Each artifact records stable ID, filename, media type, architecture, firmware targets, byte length, SHA-256 digest, signature reference, test-report reference and explicit results for UEFI boot, Secure Boot, desktop smoke, install and recovery as applicable.

## Test vocabulary
Use only `passed`, `failed`, `blocked`, `not_tested`. Missing evidence is never a pass. UEFI boot and Secure Boot are separate gates. A successful build command does not prove bootability or installability.

## Promotion states
`DRAFT -> BUILT -> VERIFIED -> SIGNED -> STAGED -> PUBLISHED`; failed gates move a candidate to `REJECTED`. Changing artifact bytes creates a new candidate and invalidates earlier verification and signatures.

- DRAFT: reviewed source and declared inputs.
- BUILT: artifacts and raw build logs retained.
- VERIFIED: schema, hashes, package manifest, SBOM/provenance and required test gates pass.
- SIGNED: approved release identity signs the verified candidate.
- STAGED: uploaded artifacts are downloaded and independently re-verified.
- PUBLISHED: versioned metadata, artifacts and user instructions are available.

## Validation requirements
1. Require full immutable source and recipe commit IDs; branch names alone are insufficient.
2. Require architecture consistency across manifest, packages, artifacts and test runner.
3. Verify byte length and SHA-256 after build and after staging upload.
4. Preserve repository snapshot identity and exact RPM NEVRAs.
5. Reject promotion if required tests are not passed, provenance is incomplete or a critical defect remains open.
6. Verify signatures against a public key/fingerprint distributed independently of the artifact host.
7. Separate test and production signing keys.
8. Consume AEGIS-06's approved anti-rollback policy; do not invent a competing format.
9. Never log passwords, tokens, LUKS/recovery keys, private signing material or user data.

## Evidence report
Record run ID, UTC start/end, runner OS/architecture/firmware, source and recipe commits, repository snapshots, builder/dependency versions, commands and exit codes, raw log paths, artifact sizes/digests, test IDs/status/assertions/evidence, defect links and reviewer sign-off. Distinguish not-applicable from not-tested.

## Ownership
PHOENIX-10 owns manifest validation, artifact inventory, release state machine, test evidence and promotion gates. ATLAS-01 owns Fedora/repository policy, package manifest, image inputs and package provenance. AEGIS-06 owns signing format/identity, key custody/distribution/rotation/revocation, anti-rollback, authorization and audit. NEXUS-07 owns typed installer operations and health/postcondition evidence. FORGE-09 owns extension compatibility/signing metadata where it intersects release.

## Open decisions before production signing
Manifest schema review; SPDX vs CycloneDX; provenance and signature formats; key custody/rotation and public-key distribution; downgrade/security epoch rules; publication channel metadata.

## Acceptance checklist
- [ ] ATLAS-01 and AEGIS-06 review this contract.
- [ ] ATLAS-01 supplies exact package/repository manifest source.
- [ ] AEGIS-06 supplies signing/trust policy.
- [ ] Build emits manifest, exact RPM NEVRAs, SBOM and provenance.
- [ ] Validator rejects malformed manifests and digest mismatches.
- [ ] Test reports record explicit status and evidence.
- [ ] Staged artifact is independently verified after download.
- [ ] Production promotion is blocked until boot, install, Secure Boot and recovery gates pass.

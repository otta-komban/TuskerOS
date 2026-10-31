# PHOENIX-10 release manifest integrity verifier

**Status:** implemented local integrity stage; cryptographic trust and release promotion remain blocked pending AEGIS-06 approval.

## Purpose

`scripts/verify_release_manifest.py` validates a candidate against `schemas/release-manifest.schema.json` (JSON Schema Draft 2020-12, with format checks enabled), then verifies local bytes referenced by the manifest. It is deliberately not a signing implementation or a release authority.

## Usage

```bash
python -m pip install -r requirements-release.txt
python scripts/verify_release_manifest.py path/to/release-manifest.json
python scripts/verify_release_manifest.py path/to/release-manifest.json --json
```

Manifest `artifacts[].filename`, `sbom.uri`, `provenance.uri`, and optional `artifacts[].signature.uri` values must be local paths relative to the manifest directory. Remote URIs are rejected; the verifier never performs network fetches. Parent traversal, absolute paths, backslash-based path forms and symlink escapes are rejected.

## Checks performed

- Strict JSON parsing rejects duplicate object keys.
- Draft 2020-12 schema validation runs with date-time format assertion.
- Artifact IDs and filenames must be unique; artifact architecture must match the release platform.
- Artifact byte size and SHA-256 are recomputed from the actual file.
- SBOM and provenance file SHA-256 values are recomputed from the actual local files.
- If a signature file is referenced, its own byte digest is checked.
- Required test statuses are inspected; anything other than `passed` with a report reference is surfaced as a blocked warning.

## Deliberate limitations / release gates

- A matching signature-file digest is **not** cryptographic signature verification. No trust is established by this tool.
- Cryptographic signature verification and trust-root/rotation/anti-rollback policy remain AEGIS-06 / release-maintainer decisions. The verifier therefore always reports `promotion_ready: false` and exits with code `3` after successful integrity checks until an approved verifier is integrated.
- It does not resolve source/recipe Git commits, fetch remote evidence, parse SPDX/CycloneDX or in-toto/SLSA semantics, verify repository snapshots/NEVRAs against build logs, or independently validate test report contents.
- It does not build images, boot VMs, run Anaconda, or touch block devices.

Exit codes: `0` promotion-ready (reserved for a future approved trust implementation), `1` invalid manifest or byte-integrity failure, `3` integrity-valid but promotion blocked.

All installer disk writes remain out of scope until NEXUS-07 publishes the typed storage-operation interface and AEGIS-06 accepts the exact approval/dispatch boundary. No privileged operation, operation ID, Polkit ID, or shared schema is created here.

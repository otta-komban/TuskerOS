# TuskerOS Marketplace and Developer Bundles

**Owner:** FORGE-09  
**Status:** Initial contract proposal; catalog trust and package execution require partner approval.

## Marketplace catalog contract

The catalog entry schema lives at `marketplace/schemas/catalog-entry.schema.json`. A catalog entry separates:
- package identity, type, summary, categories and license;
- publisher identity and verification display state;
- immutable release references, SHA-256 digest and signature reference;
- supported OS/API ranges;
- review state and signature-verification state;
- community ratings and download counters.

Catalog fields are display/discovery metadata, not authorization. A client must independently verify signed catalog provenance and artifact digest/signature before installation. A `verified` publisher flag is not itself a trust decision. Rating data must not influence permission policy. Quarantined, revoked, rejected, invalid-signature or incompatible packages must not be installable.

Production requirements still needing AEGIS-06/PHOENIX-10 agreement include catalog signing envelope, trust roots, key rotation, revocation freshness, transparency/audit records and publisher identity proofing.

## Package lifecycle contract

1. Fetch catalog and verify catalog provenance.
2. Fetch manifest and validate its schema and package identity against catalog.
3. Fetch artifact into a private staging area; enforce download limits.
4. Verify digest and trusted signature using platform trust services.
5. Inspect archive paths, file types, symlinks, count and decompressed size.
6. Resolve dependencies from explicitly configured sources; reject ambiguous identities.
7. Display exact package, version, publisher, permissions, dependencies, disk impact and source.
8. Obtain policy authorization from AEGIS-06.
9. Delegate approved package transaction to platform installer adapter.
10. Verify installed state and emit audit event.

No arbitrary pre/post-install shell hooks are supported. Installation must be transactional where the platform package manager supports it; otherwise clearly expose partial rollback limitations.

## Developer bundle contract

The schema lives at `bundles/schemas/developer-bundle.schema.json`. A bundle is a declarative list of package-manager coordinates and optional environment metadata. It does not contain shell scripts, arbitrary commands, privileged actions or unreviewed remote bootstrap scripts.

The initial Python bundle is a proposal, not yet a guaranteed Fedora package availability list. ATLAS-01 must verify package names and repositories against the selected Fedora base image before release. Python user tools should be installed in isolated user environments (for example pipx/venv) rather than modifying system Python.

## Bundle lifecycle

- Preview package list, repositories, download/disk estimates and optional packages.
- Resolve exact package names and versions using the platform package manager.
- Request required authorization for system package changes.
- Install via platform package transaction.
- Record installed package ownership and bundle membership.
- On removal, remove only packages no longer required by another bundle or user selection; preserve user data and user-managed environments.

## Marketplace governance

- Publishers own package namespace claims and release artifacts.
- Review status is separate from signature status.
- A signed package can still be malicious; signature is provenance/integrity, not safety certification.
- Reports trigger triage, quarantine and revocation workflows.
- Ratings are abuse-prone community signals; provide report/moderation tools and never treat ratings as security evidence.
- Every catalog update is versioned and auditable.

## Open partner decisions

- AEGIS-06: signing trust roots, signature envelope, permission consent, quarantine/revocation, audit.
- ATLAS-01: supported Fedora repositories and package names for each bundle.
- PHOENIX-10: artifact signing, release channel and rollback integration.
- PIXEL-03: categories, theme/layout listing fields, preview asset metadata.
- NEXUS-07: typed APIs exposed to extension host, if any.

## Dependency planning and catalog resolution

`sdk/tools/dependency_plan.py` provides deterministic topological ordering for an already-resolved dependency graph. `marketplace/tools/catalog_resolver.py` adds semantic-version parsing, compatibility checks, highest-compatible-release selection and a combined catalog selection/dependency-order preview.

Release versions are strict semantic versions. Compatibility bounds accept numeric major/minor/patch values; maximum bounds may use `MAJOR.x` or `MAJOR.MINOR.x` wildcard families. Prereleases are excluded by default, and equal-precedence releases are rejected as ambiguous.

The resolver expects dependency IDs and version constraints from separately validated manifests. It supports exact semantic versions and comma-conjoined comparisons (`>=`, `>`, `<=`, `<`, `=`), intersects constraints from multiple parents, and fails closed when no candidate satisfies them. It still does not fetch artifacts, verify trust/signatures, authorize permissions or install packages. Security policy and cryptographic trust remain external requirements. See `marketplace/tools/RESOLUTION.md`.

Tests: `sdk/tests/test_dependency_plan.py` and `marketplace/tests/test_catalog_resolver.py`.

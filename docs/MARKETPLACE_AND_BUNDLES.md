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
- On removal, create a dry-run plan from the installed ownership snapshot. Remove only packages attributed to the requested bundle/extension that have no remaining owner and are not required by any retained package. Preserve user/system-owned packages and their transitive dependencies. Execute only after the plan is reviewed, separately authorized and passed to the platform package transaction adapter; the planner itself never deletes or installs anything.

## Installed package ownership and removal planning

`marketplace/schemas/installed-package-state.schema.json` defines the local ownership snapshot. Each installed package records its exact package ID/version, a set of owner identities (`bundle`, `extension`, `user`, `system`) and installed dependency IDs. The same bundle/extension owner must be recorded on every package acquired for that owner, including dependencies. Existing user/system ownership and other bundle/extension owners are retained when a shared package is reused.

`marketplace/tools/package_ownership.py` validates the snapshot and produces a dry-run removal plan for one bundle or extension owner. Only packages attributed to that owner and left without another owner are removal candidates. Any candidate required by a retained package is protected, together with its transitive dependencies. User/system owners cannot be selected for removal. Duplicate records, missing dependency references and malformed state fail closed. The output includes explicit remove/keep reasons and `execution: not_performed`; it does not invoke DNF/Flatpak/pipx, mutate state, delete user data or authorize a transaction. A future adapter must revalidate current installed state, obtain policy approval and execute the reviewed plan transactionally where supported.

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

Tests: `sdk/tests/test_dependency_plan.py`, `marketplace/tests/test_catalog_resolver.py` and `marketplace/tests/test_package_ownership.py`.


## Package transaction preview and authorization boundary

`marketplace/tools/transaction_contract.py` now specifies the non-executing
adapter boundary. A preview binds the exact package actions and versions to a
deterministic digest of the installed-state snapshot. An external authorization
service must issue and cryptographically verify a short-lived approval token;
the local helper only checks its declared scope, expiry and digest claims and
labels the result `claims_valid_unverified`. A fresh installed-state snapshot
must match the preview immediately before any future execution. Changed state
invalidates the preview and requires a new review/approval cycle.

Rollback reporting is a data contract, not a rollback implementation. Audit
events use a strict allow-list and are described by
`marketplace/schemas/package-transaction-audit-event.schema.json`; a future
adapter must provide append-only durable storage, access control, retention
and tamper-evidence. Approval tokens, credentials and arbitrary exception
text must never be written to audit details.

No package manager is invoked by this contract. Transaction execution,
cryptographic token verification, policy authorization, audit persistence and
rollback remain external integration work requiring AEGIS-06 and PHOENIX-10
agreement. A prepared preview is not executable authorization.


## Transaction lifecycle state machine

`marketplace/tools/transaction_state.py` formalizes legal adapter states:
`prepared → approval_verified → revalidated → execution_started`, followed
by `committed`, `rolled_back` or `rollback_failed`. Rejection,
cancellation and stale-snapshot detection are terminal pre-execution outcomes.
Execution cannot start directly from a prepared preview; the lifecycle
validator requires approval-verification correlation fields, an exact
revalidated snapshot digest and a package-manager lock reference before
execution-started. Terminal records cannot advance.

These checks validate transition structure only. The trusted adapter must
perform actual cryptographic verification, acquire and enforce locks, execute
the transaction and independently record real outcomes. The state machine is
not an executor or source of authorization. The state record schema is
`marketplace/schemas/package-transaction-state.schema.json`.


Lifecycle records now validate lowercase SHA-256 plan/snapshot digests, terminal-flag consistency, history structure and event/evidence shape. Evidence fields are allow-listed per transition to prevent arbitrary strings (including secret-like payloads) from being copied into the lifecycle history. This remains structural validation, not authentication or proof of adapter behavior.


The validator also verifies history continuity from the initial `prepared` state, checks required evidence on historical transitions, and requires a valid differing observed snapshot digest for a `stale` event. A malformed or discontinuous lifecycle history is rejected rather than repaired silently.

The lifecycle validator also rejects history-free records unless their initial state is `prepared`; persisted non-initial states must carry a continuous transition history.


## Trusted package transaction adapter boundary

The draft contract in `docs/PACKAGE_TRANSACTION_ADAPTER_CONTRACT.md` defines the required sequence from immutable preview through external approval authentication, fresh state revalidation, native package-manager lock, bounded execution, read-back verification, recovery and durable audit. It assigns trust/policy to AEGIS-06 and package execution/recovery to PHOENIX-10. It also defines failure handling, idempotency and conformance tests. This is a design contract only: no executor is implemented, and implementation remains blocked pending the named partner decisions.

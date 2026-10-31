# Marketplace catalog resolution

The `marketplace/tools/catalog_resolver.py` module selects one release candidate
for a package ID against the running TuskerOS and extension API versions, then
uses the SDK dependency planner to produce dependency-before-dependent order.

## Supported version rules

- Release versions use strict `MAJOR.MINOR.PATCH` semantic versions, with
  optional prerelease and build metadata.
- Compatibility targets and minimums accept `MAJOR`, `MAJOR.MINOR`, or
  `MAJOR.MINOR.PATCH` (missing components normalize to zero).
- Maximums accept those same numeric forms inclusively, or `MAJOR.x` /
  `MAJOR.MINOR.x` as inclusive wildcard families.
- Stable releases are preferred by default; prereleases are excluded unless
  the caller explicitly opts in.
- Semantic precedence ignores build metadata. Two compatible catalog entries
  with equal precedence are ambiguous and rejected rather than selected by
  input order.
- Unknown range syntax and malformed matching catalog entries fail closed.

## Dependency version constraints

Manifest dependency entries carry a required version constraint. The resolver
accepts an exact semantic version (for example `1.4.2`) or a comma-conjoined
set of comparisons using `>=`, `>`, `<=`, `<` and `=` (for example
`>=1.2.0,<2.0.0`). Each comparison uses semantic-version precedence; build
metadata does not affect comparison. Every comparison in one expression must
match.

Pass the validated dependency graph and an edge-constraint mapping to
`resolve_catalog_plan`. The mapping shape is
`{parent_package_id: {dependency_package_id: constraint}}`. When supplied,
each graph edge must have exactly one constraint. Constraints from multiple
parents are intersected before a single release is selected for a shared
dependency. Missing edge constraints, malformed expressions and an empty
candidate intersection fail closed. Root packages have no incoming edge
constraint unless another selected package depends on them.

The resolver does not rewrite or infer constraints from catalog metadata; the
caller must construct this mapping from validated manifests and preserve the
manifest-to-package identity binding.

## Resolver boundaries

`select_catalog_release` is a metadata selector, not a trust engine. It
excludes entries whose catalog claims say the review status is `rejected`,
`quarantined` or `revoked`, or whose signature status is `invalid` or
`revoked`. These fields are untrusted claims: an exclusion is a conservative
metadata filter, while `approved`/`valid` is never proof of publisher trust,
signature validity or authorization. The caller must independently verify
signed catalog provenance, signatures, revocation freshness and publisher
trust through AEGIS-06 services before presenting an install approval.

`resolve_catalog_plan` accepts a dependency graph extracted from separately
validated manifests, selects a compatible catalog release for every package
in the dependency closure, and returns the existing deterministic topological
order plus the selected metadata. When `dependency_constraints` is supplied,
it validates that the constraint mapping exactly covers the declared edges,
parses each exact/comparison expression, and intersects constraints from all
parents before selecting a shared dependency release. Omitting the mapping
retains compatibility with callers that have no edge constraints; it does not
mean constraints were checked. The resolver does not fetch artifacts, verify
provenance or signatures, authorize, or install packages.

Run tests from the repository root with:

```sh
python3 -m unittest marketplace.tests.test_catalog_resolver
```

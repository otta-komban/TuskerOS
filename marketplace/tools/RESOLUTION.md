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

## Resolver boundaries

`select_catalog_release` is a metadata selector, not a trust engine. It does
not filter candidates by review/signature status because those fields are
untrusted catalog claims. The caller must independently verify signed catalog
provenance, signatures, revocation state and publisher trust through AEGIS-06
services before presenting an install approval.

`resolve_catalog_plan` accepts a dependency graph extracted from separately
validated manifests, selects a compatible catalog release for every package
in the dependency closure, and returns the existing deterministic topological
order plus the selected metadata. It does not interpret dependency version
ranges. The manifest/dependency resolver must enforce those constraints before
calling it. It does not fetch, verify, authorize, or install packages.

Run tests from the repository root with:

```sh
python3 -m unittest marketplace.tests.test_catalog_resolver
```

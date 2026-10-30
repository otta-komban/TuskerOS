# Marketplace metadata tools

Run the catalog metadata validator from the repository root:

```sh
python3 marketplace/tools/validate_catalog_entry.py marketplace/examples/hello-catalog-entry.json
```

The validator uses only the Python standard library. It rejects unknown fields, non-HTTPS external references, malformed package identifiers, non-semantic release versions, malformed SHA-256 digests, invalid timestamps, duplicate tags/categories and unknown trust-state values.

Use `marketplace/tools/catalog_resolver.py` to select a compatible release and produce an ordered dependency plan from a separately validated manifest dependency graph. Dependency edge constraints are enforced when the validated manifest graph and edge-constraint mapping are supplied. See `marketplace/tools/RESOLUTION.md` for supported syntax and limitations. Use `marketplace/tools/package_ownership.py` to validate an installed-state snapshot and create a dry-run owner-removal plan.

**Security boundary:** a successful metadata validation or version-selection result means only that the metadata is structurally acceptable and compatible with the supplied version inputs. Neither tool fetches URLs, verifies catalog provenance, cryptographically verifies signatures, establishes publisher identity, checks revocation freshness, or authorizes installation. In particular, an entry claiming `approved`/`valid` is not thereby trusted.


## Package ownership and safe removal

Validate an installed-state JSON document against
`marketplace/schemas/installed-package-state.schema.json`, then call
`plan_owner_removal(state, "bundle", bundle_id)` or
`plan_owner_removal(state, "extension", extension_id)`. The planner returns
explicit remove/keep lists and always reports `execution: not_performed`.
It never calls a package manager or mutates the supplied state.

Record the owning bundle/extension on every package acquired for that owner,
including dependencies. Preserve all other owner records when a package is
shared. Packages with user/system ownership cannot be selected as the removal
owner, and packages required by any retained package (including transitive
dependencies) remain in the keep list. Missing package references and
ambiguous ownership state fail closed.

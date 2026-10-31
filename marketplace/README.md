# TuskerOS Marketplace contract

The initial catalog schema and example are proposals for discovery metadata only.

- Schema: `schemas/catalog-entry.schema.json`
- Fixture: `examples/hello-catalog-entry.json`

Optional `package.conflicts` metadata lists package IDs that cannot coexist in one resolved plan. The catalog validator rejects malformed, duplicate, and self-conflict declarations; the resolver rejects a plan when either selected package declares a conflict with another selected package. This is a metadata-resolution safeguard, not a substitute for checking the authoritative installed state at execution time.

Release versions are checked against the same Semantic Versioning 2.0.0 pattern by both the JSON Schema and Python validator. Prerelease/build identifiers cannot be empty; numeric prerelease identifiers cannot have leading zeroes; numeric build identifiers may have leading zeroes. Version digits are ASCII-only, as required by SemVer.

Do not treat catalog metadata, publisher display flags, ratings, or a schema-valid record as proof of trust. Verify signed catalog provenance and artifact integrity using platform trust services before installation. Trust and review policy must be supplied by AEGIS-06 and PHOENIX-10.

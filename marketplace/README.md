# TuskerOS Marketplace contract

The initial catalog schema and example are proposals for discovery metadata only.

- Schema: `schemas/catalog-entry.schema.json`
- Fixture: `examples/hello-catalog-entry.json`

Optional `package.conflicts` metadata lists package IDs that cannot coexist in one resolved plan. The catalog validator rejects malformed, duplicate, and self-conflict declarations; the resolver rejects a plan when either selected package declares a conflict with another selected package. This is a metadata-resolution safeguard, not a substitute for checking the authoritative installed state at execution time.

Release versions are checked against the same Semantic Versioning 2.0.0 pattern by both the JSON Schema and Python validator. The resolver's direct release parser reuses that strict ASCII SemVer grammar, and compatibility version parsing also uses ASCII digits. Resolver precedence tests cover the SemVer 2.0.0 prerelease ordering sequence; dependency-edge constraint tests cover inclusive/exclusive operators and malformed empty clauses. Prerelease/build identifiers cannot be empty; numeric prerelease identifiers cannot have leading zeroes; numeric build identifiers may have leading zeroes. Version digits are ASCII-only, as required by SemVer.

Do not treat catalog metadata, publisher display flags, ratings, or a schema-valid record as proof of trust. Verify signed catalog provenance and artifact integrity using platform trust services before installation. Trust and review policy must be supplied by AEGIS-06 and PHOENIX-10.
Catalog package and publisher identifiers use the same lowercase ASCII slug grammar in the JSON Schema and Python validator. Optional descriptive, homepage, manifest, signature, and changelog URLs are constrained to HTTPS (without URL user-info) in the validator and schema; artifact URLs follow the same rule.
The schema also mirrors validator text constraints for non-blank bounded names, summaries, licenses, publisher display names, and compatibility range endpoints. Compatibility range objects reject unknown fields and require non-blank `min`/`max` strings of at most 64 characters. Metadata URL fields are bounded to 512 characters.
Catalog publication and review timestamps use RFC 3339 syntax with an explicit UTC marker or numeric offset. The Python validator also checks calendar validity; the schema carries the matching syntax, timezone, and 64-character bound.
The Python URL validator also fails closed on malformed authorities/ports and rejects whitespace plus all Unicode `Cc` control characters (including DEL and C1 controls) before parsing; malformed untrusted URLs return validation errors rather than escaping as parser exceptions. The JSON Schema URL patterns also reject whitespace and C0/C1 control characters throughout the authority and path, while allowing percent-encoded spaces.
The JSON Schema also caps release version text at the same 128-character limit as the Python validator. The direct compatibility-version parser also enforces the schema's 64-character endpoint bound before numeric conversion, so oversized public inputs return `CatalogResolutionError` instead of reaching unbounded integer parsing. Wildcard maximum matching applies the same bound before its separate numeric conversion path.

The catalog plan resolver validates root IDs and the complete supplied dependency mapping before ordering or release selection. Text-valued dependency declarations, invalid IDs, non-iterable dependency values, and non-mapping graphs are rejected as `CatalogResolutionError` rather than leaking Python type errors. Candidate collections must be iterable catalog-entry sequences (not text or mappings), and optional dependency-constraint input must be a mapping with non-empty parent IDs; malformed inputs are normalized to `CatalogResolutionError`.


Catalog JSON Schema patterns use an explicit end-of-input guard after their anchors. This prevents regex engines that treat `$` as matching before a final line terminator from accepting identifiers, versions, digests, timestamps or URLs with a trailing newline; the Python validator continues to enforce full-string matches.

The transaction lifecycle state machine requires `history` as an array and `terminal` as a boolean, while validating only transaction identifiers, state names, and digests as non-empty strings; this keeps runtime type checks aligned with the transaction schema.

The public dependency-constraint predicate validates direct `Version` objects and constraint iterables before comparison. Invalid component values, malformed prerelease tuples, text passed as the constraint collection, and non-iterable inputs raise `CatalogResolutionError` rather than leaking attribute or type errors.

The direct release selector validates its public collection and flag inputs, checks target compatibility versions before scanning candidates, and snapshots candidate constraints once. This is important for generator callers: every release candidate is evaluated against the same complete constraint set rather than only the first candidate consuming it.

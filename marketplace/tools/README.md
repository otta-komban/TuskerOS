# Marketplace metadata tools

Run the catalog metadata validator from the repository root:

```sh
python3 marketplace/tools/validate_catalog_entry.py marketplace/examples/hello-catalog-entry.json
```

The validator uses only the Python standard library. It rejects unknown fields, non-HTTPS external references, malformed package identifiers, non-semantic release versions, malformed SHA-256 digests, invalid timestamps, duplicate tags/categories and unknown trust-state values.

Use `marketplace/tools/catalog_resolver.py` to select a compatible release and produce an ordered dependency plan from a separately validated manifest dependency graph. See `marketplace/tools/RESOLUTION.md` for supported version syntax and limitations.

**Security boundary:** a successful metadata validation or version-selection result means only that the metadata is structurally acceptable and compatible with the supplied version inputs. Neither tool fetches URLs, verifies catalog provenance, cryptographically verifies signatures, establishes publisher identity, checks revocation freshness, or authorizes installation. In particular, an entry claiming `approved`/`valid` is not thereby trusted.

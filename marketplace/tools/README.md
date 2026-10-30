# Marketplace metadata tools

Run the catalog metadata validator from the repository root:

```sh
python3 marketplace/tools/validate_catalog_entry.py marketplace/examples/hello-catalog-entry.json
```

The validator uses only the Python standard library. It rejects unknown fields, non-HTTPS external references, malformed package identifiers, non-semantic release versions, malformed SHA-256 digests, invalid timestamps, duplicate tags/categories and unknown trust-state values.

**Security boundary:** a successful result means only that the metadata is structurally acceptable to this implementation. It does not fetch URLs, verify catalog provenance, cryptographically verify signatures, establish publisher identity, check revocation freshness, compare compatibility against the running system, inspect artifacts, or authorize installation. In particular, a metadata entry whose trust state says `approved`/`valid` is not thereby trusted by this tool.

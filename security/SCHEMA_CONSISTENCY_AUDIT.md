[object Object]

## C0017 update — approval-request v0.2.0 schema regression coverage

- Extended `security/tests/test_security_schemas.py` with a valid v0.2.0 approval-request fixture and positive validation.
- Added negative cases for each missing binding member, malformed session/device/precondition digests, empty registry version, empty or duplicate resource scope, unexpected binding properties, and attempting to validate a v0.1.0 request as v0.2.0.
- The new tests exercise schema shape and format assertions only. They do not prove that identity digests, registry revisions, canonical resource identifiers or precondition digests originate from trusted services or are recomputed at consume time.
- GitHub Actions result for commit `824a0b943f2b223c2cf44e254a9aee7e7ee60ba5` was not yet available at this update; no pass is claimed.

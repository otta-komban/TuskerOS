# AEGIS-06 Authorization Audit Rollback Fix

**Branch:** `06-AEGIS`  
**Reviewed area:** `SecurityStore.issue_authorization()`  
**Disposition:** Focused runtime fix and regression added.

## Finding

`issue_authorization()` begins a SQLite transaction, revokes any prior issued reference, inserts a new reference hash, and appends the `authorized` audit event before committing. Its `except SecurityStoreError: raise` branch previously re-raised audit-write failures without rolling back an active transaction. A failed audit append could therefore leave uncommitted authorization state and an open transaction on the store connection.

## Fix

The `SecurityStoreError` handler now rolls back whenever the connection remains in a transaction before re-raising. Explicitly committed invalidation outcomes remain committed because the transaction is already closed at that point.

A regression injects an audit append failure during authorization issuance and asserts:
- no transaction remains open;
- approval remains `APPROVED`;
- no authorization reference was persisted;
- the existing audit chain remains readable and contains only the earlier request/approval events.

## Verification

GitHub Actions run `41221480288` passed the security job on exact branch head `16d58ce420ee06f34fa64604700d9405e25cb587`; it executed `python -m pytest -q security/tests`. Unified validation run `41221480289` also completed successfully at the same head. An earlier run on the immediately preceding commit failed test collection because a pytest parametrization decorator attached to the new test; that placement was corrected before the successful run.

This fix does not alter the shared audit schema or event vocabulary and does not certify a production broker or enable privileged handlers.

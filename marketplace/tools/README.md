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


## Package transaction contract (preview only)

`marketplace/tools/transaction_contract.py` defines a non-executing boundary
between reviewed package plans and a future platform installer adapter:

- `create_transaction_preview(snapshot, operations, transaction_id)` binds
  the exact action/package/version list to a deterministic SHA-256 fingerprint
  of the installed-state snapshot and emits `state: prepared` and
  `execution: not_performed`.
- `validate_approval_claims(token, preview, now)` checks expiry, action scope
  and digest binding. Its result is explicitly `claims_valid_unverified`.
  AEGIS-06/platform authorization services must authenticate the issuer and
  cryptographically verify the token before this function is called. A claim
  check is not an authorization decision.
- `revalidate_snapshot(preview, current_snapshot)` fails closed if installed
  state changed after review. The adapter must obtain a fresh snapshot
  immediately before execution and repeat authorization/revalidation as
  required by policy.
- `build_rollback_report(...)` describes a reported rollback outcome; it does
  not perform or independently verify rollback.
- `build_audit_event(...)` emits an allow-listed record. The adapter owns
  append-only durable JSONL persistence, access control, retention and
  tamper-evidence. Never put credentials, approval tokens or arbitrary
  exception text in audit details.

The audit event shape is defined in
`marketplace/schemas/package-transaction-audit-event.schema.json`.
This module has no DNF/Flatpak/pipx integration, no token-signature verifier,
no authorization authority, no transaction state store and no rollback
executor. Do not treat a preview or a claims-valid result as permission to
execute. The adapter remains blocked on AEGIS-06 and PHOENIX-10 agreement.


## Transaction lifecycle state machine

`marketplace/tools/transaction_state.py` provides a pure transition validator
for the future adapter. The permitted path is:

`prepared → approval_verified → revalidated → execution_started → committed`

A running transaction may instead end as `rolled_back` or
`rollback_failed`; stale snapshots, rejection and cancellation are terminal
before execution. Execution cannot begin directly from a prepared preview.
Approval verification requires an external verification reference, fresh
snapshot revalidation must match the reviewed digest, and execution start
requires a package-manager lock reference. Terminal states cannot transition
again.

This state machine validates declared evidence fields; it does not authenticate
them, acquire locks, execute package operations, or prove that a package
manager committed/rolled back. Only the trusted adapter may emit these events
after the corresponding external action has succeeded. State schema:
`marketplace/schemas/package-transaction-state.schema.json`.


Lifecycle records now validate lowercase SHA-256 plan/snapshot digests, terminal-flag consistency, history structure and event/evidence shape. Evidence fields are allow-listed per transition to prevent arbitrary strings (including secret-like payloads) from being copied into the lifecycle history. This remains structural validation, not authentication or proof of adapter behavior.


The validator also verifies history continuity from the initial `prepared` state, checks required evidence on historical transitions, and requires a valid differing observed snapshot digest for a `stale` event. A malformed or discontinuous lifecycle history is rejected rather than repaired silently.

The lifecycle validator also rejects history-free records unless their initial state is `prepared`; persisted non-initial states must carry a continuous transition history.

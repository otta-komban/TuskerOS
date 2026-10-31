# Marketplace metadata tools

Run the catalog metadata validator from the repository root:

```sh
python3 marketplace/tools/validate_catalog_entry.py marketplace/examples/hello-catalog-entry.json
```

The validator uses only the Python standard library. It rejects unknown fields, non-HTTPS external references, malformed package identifiers, non-semantic release versions, malformed SHA-256 digests, invalid timestamps, duplicate tags/categories and unknown trust-state values. It also rejects unsupported object keys deterministically instead of raising while sorting malformed Python mappings. Optional community metrics, when present, must be non-null numbers/integers within the catalog schema's bounds.

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
ambiguous ownership state fail closed. The installed-state validator also enforces
the schema's 128-character maximum for package IDs, versions, dependency IDs,
and owner IDs.


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


## Trusted package transaction adapter boundary

The proposed language-neutral adapter sequence and failure/conformance requirements are documented in `docs/PACKAGE_TRANSACTION_ADAPTER_CONTRACT.md`. It separates AEGIS-06 approval authentication and policy from PHOENIX-10 package-manager locking, execution, recovery and outcome verification. FORGE-09 preview/lifecycle helpers remain non-executing. Adapter implementation is blocked pending partner decisions; do not interpret evidence references as proof or authorization.


The transaction-state JSON Schema now constrains each history item to one of the eleven legal source/event pairs and requires the event-specific evidence keys with no additional properties. It also constrains empty history/terminal flags for prepared, active and terminal states. The Python lifecycle validator remains the authoritative continuity check across the full history and binds the final event to the current state; schema validation alone does not authenticate evidence or prove execution.


## Lifecycle conformance vectors

Data-driven transition vectors live in `marketplace/tests/fixtures/transaction-state-vectors.json`. They cover valid commit, successful rollback, stale-snapshot termination, cancellation and rejection paths, plus fail-closed cases for execution bypass, snapshot mismatch, unexpected evidence fields and transitions after terminal state. `marketplace/tests/test_transaction_state_vectors.py` runs those vectors against the pure Python validator with `unittest`.

The vectors are structural test inputs only. Their approval/lock/result references are placeholders and do not represent authenticated approvals, real locks or package-manager outcomes. Test files are committed; execution must be performed in a working checkout before release.


The Python `build_audit_event(...)` builder mirrors the audit-event schema's
field-level constraints: plan and snapshot digests must be lowercase SHA-256,
timestamps must be valid RFC 3339 date-times with explicit timezones, numeric
counters must be non-negative integers (booleans are rejected), reason/error
codes are bounded strings, and rollback status must use the schema enum. This
is structural consistency only; it does not authenticate the actor, verify
authorization, or persist a durable audit record.

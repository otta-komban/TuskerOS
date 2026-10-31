# Model Store Transaction and Recovery Contract

Owner: ORBIT-05  
Status: Design proposal; implementation language and filesystem layout remain unselected  
Related: `MODEL-CATALOG-POLICY.md`, `PROVIDER-CONTRACT.md`, `schemas/model-manifest.schema.json`

## 1. Scope and safety properties

This contract defines the state changes for importing, installing, verifying, activating, updating and removing locally managed model artifacts. It is intentionally independent of a specific runtime or programming language.

Required properties:

1. **No partial activation:** an incomplete, unverified or interrupted artifact is never visible as ready.
2. **Integrity before use:** every declared file size and digest is checked against the exact staged bytes before activation.
3. **No path escape:** untrusted archive names, links and filesystem races cannot write outside the transaction staging root or managed model root.
4. **Old revision survives failed update:** an update does not replace the active revision until the candidate is verified and its activation checks pass.
5. **Recoverable interruption:** after process or machine interruption, startup reconciliation can distinguish committed, incomplete and ambiguous transactions without guessing.
6. **Explicit consent:** download/install work begins only after the user confirms artifact, revision, expected size and destination.
7. **No execution of artifact content:** model files, metadata, tokenizer assets and templates are data; they are never installer scripts.

## 2. Transaction states

A transaction has a unique random transaction ID and immutable target artifact ID/revision. State transitions are persisted before the corresponding irreversible step.

| State | Meaning | Allowed next states |
|---|---|---|
| created | User-approved operation and destination recorded | staging, aborted |
| staging | Bytes are downloaded/copied into private staging | staged, failed, aborted |
| staged | All expected files are present; no activation permitted yet | verifying, aborted |
| verifying | Manifest, path policy, sizes, digests and required metadata are checked | verified, failed, aborted |
| verified | Candidate is immutable/read-only to the installer and ready for activation checks | activating, aborted |
| activating | Atomic pointer/metadata switch is in progress | committed, rollback_required |
| committed | New revision is the active managed revision | — |
| rollback_required | Activation failed or postcondition is uncertain | rolled_back, recovery_required |
| rolled_back | Prior active revision is restored and verified | — |
| failed | Operation failed before activation; staged data is quarantined or safely removed | — |
| aborted | User cancelled before commit; active revision unchanged | — |
| recovery_required | Startup cannot prove a safe active state | manual_recovery |

Terminal states are `committed`, `rolled_back`, `failed`, `aborted` and `manual_recovery`. A terminal transaction is immutable; a retry creates a new transaction ID.

## 3. Staging and archive validation

- Use a private, permission-restricted staging directory on the same filesystem as the final managed model root when atomic rename is required.
- Enforce configured maximum total bytes, per-file bytes, path depth, path length, file count and elapsed time before unbounded resource consumption.
- Normalize archive paths once using platform-independent rules before filesystem access. Reject absolute paths, drive prefixes, empty/dot/dot-dot components, NUL/control characters, alternate separators and duplicate normalized names.
- Reject symlinks, hardlinks, devices, FIFOs, sockets and sparse-file tricks unless a future reviewed format explicitly requires a safe subset. Initial policy: regular files and directories only.
- Resolve each destination under the canonical staging root and verify containment immediately before creation; do not rely only on string-prefix checks.
- Create files exclusively without following links. Do not overwrite an existing staged path.
- Reject case-folding or Unicode-normalization collisions that would alias on supported target filesystems.
- Do not trust archive-declared sizes, compression ratios or file counts; enforce limits while streaming actual bytes.
- On any violation, stop extraction, mark the transaction failed, and quarantine or delete only the transaction-owned staging tree.

## 4. Verification gate

Before state becomes `verified`, require:

- Manifest schema validation with the supported schema version.
- Artifact ID and immutable revision match the user-approved target.
- Exact set of expected files; no undeclared executable or unexpected payload files.
- Actual byte size and SHA-256 match each manifest entry.
- License and catalog policy gates pass for curated installs. User imports with incomplete license metadata remain visibly unverified and are not promoted into the curated catalog.
- Provenance fields are retained; digest verification does not imply publisher authenticity.
- Required runtime compatibility metadata is present or explicitly unknown.
- The staged tree is no longer writable by the download/extraction worker before activation.

A digest mismatch, missing declared file, unexpected file, invalid metadata or unresolved policy block fails closed. Never auto-correct a manifest to match downloaded bytes.

## 5. Activation and update protocol

- Keep immutable revision directories; do not overwrite model files in place.
- Maintain one small active-revision record/pointer per model ID. Its format and durability semantics must be selected for the target filesystem before implementation.
- Write the candidate active record to a temporary sibling file, flush file contents, atomically rename it over the active record, and flush the parent directory where the platform supports it.
- Record the previous active revision and transaction ID before switching.
- Run bounded post-activation checks: active pointer resolves within the managed root, required files exist and retain verified digests, and the selected provider can inspect/load the candidate without starting inference on user data.
- Only after checks pass mark the transaction committed. If checks fail, restore the prior active record atomically and verify the rollback.
- If crash recovery cannot establish which pointer is authoritative, do not select the newest directory by timestamp. Enter `recovery_required` and keep inference disabled for that model until reconciliation.

## 6. Cancellation and cleanup

- Before activation, cancellation stops network/file work, closes handles and removes or quarantines only files owned by the transaction.
- During activation, cancellation is deferred until the atomic switch and rollback decision reach a known state; do not abandon a half-written active record.
- After commit, cancellation cannot silently undo the committed revision. A separate explicit rollback transaction is required.
- Cleanup must never follow symlinks and must verify that the target is beneath the canonical transaction staging root.
- Disk-full, permission loss, checksum mismatch, provider failure and shutdown are distinct diagnostic reasons.

## 7. Startup reconciliation

At runtime startup, scan transaction metadata and active-revision records without loading model weights.

- Mark abandoned pre-activation transactions failed/aborted and quarantine their staging trees.
- For `activating` or `rollback_required`, compare recorded prior/candidate revisions and verify the active record; restore the prior revision only when the transaction journal proves it is safe.
- Never infer commit from directory existence or timestamps alone.
- Verify active pointer containment and metadata before advertising a model as ready.
- Keep recovery actions idempotent; repeated startup reconciliation must converge to the same safe result.
- Emit a redacted diagnostic event with transaction ID, artifact ID, state and reason; never include prompts or generated content.

## 8. Required future tests

| ID | Scenario | Expected result |
|---|---|---|
| MS-001 | Cancel during download | Active revision unchanged; staging cleaned/quarantined |
| MS-002 | Disk full during staging | Failed transaction; no active pointer change |
| MS-003 | Truncated or missing file | Verification fails; no activation |
| MS-004 | Digest or size mismatch | Verification fails closed |
| MS-005 | Absolute or traversal archive path | Extraction rejected before write |
| MS-006 | Symlink/hardlink/device archive member | Rejected under initial policy |
| MS-007 | Duplicate normalized/case-folded path | Archive rejected |
| MS-008 | Excessive file count/size/depth | Bounded rejection without unbounded allocation |
| MS-009 | Unexpected undeclared file | Verification fails |
| MS-010 | Crash before activation | Previous active revision remains selected |
| MS-011 | Crash during pointer switch | Startup reconciliation selects proven prior or candidate; otherwise recovery required |
| MS-012 | Post-activation provider check fails | Prior revision restored and verified |
| MS-013 | Cancel during activation | Operation reaches committed or rolled-back state; never indeterminate |
| MS-014 | Cleanup encounters symlink | Does not follow link or delete outside staging root |
| MS-015 | Repeated recovery run | Idempotent, convergent outcome |
| MS-016 | Active pointer escapes managed root | Model not advertised ready; recovery required |

## 9. Implementation gates

Before implementation, agree on the managed root, filesystem support matrix, atomic replacement/durability behavior, permission model and journal format with ATLAS-01 and AEGIS-06. Provider integration must expose a bounded post-activation inspection/health operation. Add tests for the actual target filesystem; a unit test of path strings alone is insufficient.

This document is a proposed contract, not evidence that an installer, transaction journal, archive extractor or recovery routine exists.

# Read-only installer recovery journal validator

**Status:** local PHOENIX-10 validation utility; not integrated with installer runtime.  
**Safety boundary:** this code reads in-memory JSONL supplied by its caller. It does not open block devices, write disks, invoke a broker, recover filesystems, or dispatch operations.

## Record envelope

Each line is one JSON object containing exactly:

- `sequence`: positive integer, contiguous from 1
- `operation_id`: non-empty operation identity, constant within one journal
- `state`: one of `planned`, `prepared`, `executing`, `interrupted`, `succeeded`, `failed`, `cancelled`
- `idempotent`: boolean declaration; not proof of idempotency
- `previous_checksum`: prior record checksum, or 64 zeroes for the first record
- `checksum`: SHA-256 of the other fields serialized with this module's deterministic JSON encoding

The checksum is an accidental-corruption/tamper-evidence chain only. It is not keyed, signed, authenticated, or equivalent to RFC 8785 JCS. A malicious writer able to rewrite the journal can recompute it. The journal must not be trusted as authorization evidence.

## State transitions

Allowed transitions are:

- `planned -> prepared | failed | cancelled`
- `prepared -> executing | failed | cancelled`
- `executing -> interrupted | succeeded | failed | cancelled`
- `interrupted -> failed | cancelled`
- `succeeded`, `failed`, and `cancelled` are terminal

An interrupted record remains unresolved. This validator does not infer that rollback occurred or that retry is safe.

## Replay advisory

`replay_eligibility` returns a candidate only when the latest record is `interrupted`, the operation is declared idempotent, and the caller asserts that external preconditions and fresh authorization have been verified. It does not verify those assertions, call NEXUS/AEGIS, or dispatch a replay. A production implementation must consume the accepted NEXUS operation contract and AEGIS authorization/approval contract; until then, no installer recovery execution is permitted.

## Validation scope and limitations

The validator checks required/extra fields, strict JSONL parsing, contiguous and unique sequence numbers, stable operation identity, allowed state transitions, previous-checksum linkage, and per-record checksums. It rejects blank/truncated JSONL records and non-standard JSON constants. It does not provide durable writes, locking, fsync, atomic append, concurrent-writer protection, signatures, anti-rollback, trusted timestamps, secret handling, or crash-consistent persistence. Those concerns require cross-agent contract review before integration.

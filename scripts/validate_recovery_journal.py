"""Read-only validation for installer recovery journals.

This module does not perform recovery, replay operations, access disks, or call a
privileged broker. Its checksum format is a local integrity envelope, not JCS
and not an authentication mechanism. Integration awaits NEXUS-07/AEGIS-06.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterable
from itertools import islice

GENESIS_CHECKSUM = "0" * 64
MAX_JOURNAL_BYTES = 4 * 1024 * 1024
MAX_RECORD_BYTES = 64 * 1024
MAX_RECORDS = 10_000
SHA256_HEX_LENGTH = 64
STATES = {"planned", "prepared", "executing", "interrupted",
          "succeeded", "failed", "cancelled"}
TERMINAL_STATES = {"succeeded", "failed", "cancelled"}
TRANSITIONS = {
    "planned": {"prepared", "failed", "cancelled"},
    "prepared": {"executing", "failed", "cancelled"},
    "executing": {"interrupted", "succeeded", "failed", "cancelled"},
    "interrupted": {"failed", "cancelled"},
    "succeeded": set(), "failed": set(), "cancelled": set(),
}
REQUIRED_FIELDS = {"sequence", "operation_id", "state", "idempotent",
                   "previous_checksum", "checksum"}


class JournalValidationError(ValueError):
    """Raised when a journal is malformed or violates its integrity contract."""


@dataclass(frozen=True)
class JournalReport:
    valid: bool
    record_count: int
    last_sequence: int
    last_state: str | None
    last_checksum: str
    errors: tuple[str, ...]


def _canonical_payload(record: dict[str, Any]) -> bytes:
    payload = {key: value for key, value in record.items() if key != "checksum"}
    try:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode(
                              "utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise JournalValidationError(f"record is not strict JSON data: {exc}") from exc


def record_checksum(record: dict[str, Any]) -> str:
    """Return the SHA-256 checksum for a record, excluding its checksum field."""
    return hashlib.sha256(_canonical_payload(record)).hexdigest()


def seal_record(*, sequence: int, operation_id: str, state: str,
                idempotent: bool, previous_checksum: str = GENESIS_CHECKSUM
                ) -> dict[str, Any]:
    """Build a local test/producer fixture; this does not authorize execution."""
    record = {
        "sequence": sequence,
        "operation_id": operation_id,
        "state": state,
        "idempotent": idempotent,
        "previous_checksum": previous_checksum,
    }
    record["checksum"] = record_checksum(record)
    return record


def validate_journal(records: Iterable[dict[str, Any]]) -> JournalReport:
    errors: list[str] = []
    try:
        iterator = iter(records)
        materialized = list(islice(iterator, MAX_RECORDS + 1))
    except TypeError:
        return JournalReport(False, 0, 0, None, "", ("journal records must be iterable",))
    except Exception as exc:
        return JournalReport(
            False, 0, 0, None, "",
            (f"journal iteration failed: {type(exc).__name__}: {exc}",))
    if len(materialized) > MAX_RECORDS:
        materialized = materialized[:MAX_RECORDS]
        errors.append(f"journal exceeds maximum record count ({MAX_RECORDS})")
    previous = GENESIS_CHECKSUM
    previous_state: str | None = None
    operation_id: str | None = None
    operation_idempotent: bool | None = None
    seen_sequences: set[int] = set()

    for index, record in enumerate(materialized, start=1):
        if not isinstance(record, dict):
            errors.append(f"record {index}: expected object")
            continue
        non_string_keys = [key for key in record if not isinstance(key, str)]
        if non_string_keys:
            errors.append(
                f"record {index}: object keys must be strings; found {non_string_keys!r}")
            continue
        missing = REQUIRED_FIELDS - record.keys()
        extra = record.keys() - REQUIRED_FIELDS
        if missing:
            errors.append(f"record {index}: missing fields {sorted(missing)}")
            continue
        if extra:
            errors.append(f"record {index}: unexpected fields {sorted(extra)}")
        sequence = record["sequence"]
        if type(sequence) is not int or sequence < 1:
            errors.append(f"record {index}: sequence must be a positive integer")
        elif sequence in seen_sequences:
            errors.append(f"record {index}: duplicate sequence {sequence}")
        else:
            seen_sequences.add(sequence)
        if sequence != index:
            errors.append(f"record {index}: expected sequence {index}, got {sequence}")
        if not isinstance(record["operation_id"], str) or not record["operation_id"]:
            errors.append(f"record {index}: operation_id must be non-empty")
        elif operation_id is None:
            operation_id = record["operation_id"]
        elif record["operation_id"] != operation_id:
            errors.append(f"record {index}: operation_id changed within journal")
        state = record["state"]
        if index == 1 and state != "planned":
            errors.append("record 1: initial state must be planned")
        if not isinstance(state, str) or state not in STATES:
            errors.append(f"record {index}: unknown state {state!r}")
        elif previous_state is not None and state not in TRANSITIONS[previous_state]:
            errors.append(f"record {index}: illegal transition {previous_state} -> {state}")
        if type(record["idempotent"]) is not bool:
            errors.append(f"record {index}: idempotent must be boolean")
        elif operation_idempotent is None:
            operation_idempotent = record["idempotent"]
        elif record["idempotent"] is not operation_idempotent:
            errors.append(f"record {index}: idempotent declaration changed within journal")
        previous_checksum = record["previous_checksum"]
        if (not isinstance(previous_checksum, str)
                or len(previous_checksum) != SHA256_HEX_LENGTH
                or any(char not in "0123456789abcdef" for char in previous_checksum)):
            errors.append(f"record {index}: previous_checksum must be 64 lowercase hexadecimal characters")
        if previous_checksum != previous:
            errors.append(f"record {index}: previous checksum does not match chain")
        try:
            actual = record_checksum(record)
        except JournalValidationError as exc:
            errors.append(f"record {index}: {exc}")
            actual = ""
        supplied = record["checksum"]
        if (not isinstance(supplied, str)
                or len(supplied) != SHA256_HEX_LENGTH
                or any(char not in "0123456789abcdef" for char in supplied)):
            errors.append(f"record {index}: checksum must be 64 lowercase hexadecimal characters")
        elif supplied != actual:
            errors.append(f"record {index}: checksum mismatch")
        previous = supplied if isinstance(supplied, str) else ""
        # Never index TRANSITIONS with an unrecognized state on the next record.
        previous_state = state if isinstance(state, str) and state in STATES else None

    last = materialized[-1] if materialized and isinstance(materialized[-1], dict) else {}
    return JournalReport(
        valid=not errors,
        record_count=len(materialized),
        last_sequence=last.get("sequence", 0) if type(last.get("sequence")) is int else 0,
        last_state=last.get("state") if isinstance(last.get("state"), str) else None,
        last_checksum=last.get("checksum") if isinstance(last.get("checksum"), str) else "",
        errors=tuple(errors),
    )


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise JournalValidationError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def parse_jsonl(text: str) -> list[dict[str, Any]]:
    """Parse complete JSONL records; blank, duplicate-key and truncated records fail."""
    if not isinstance(text, str) or not text:
        raise JournalValidationError("journal must be non-empty text")
    try:
        encoded_size = len(text.encode("utf-8", errors="strict"))
    except UnicodeEncodeError as exc:
        raise JournalValidationError("journal contains invalid Unicode") from exc
    if encoded_size > MAX_JOURNAL_BYTES:
        raise JournalValidationError(f"journal exceeds maximum size ({MAX_JOURNAL_BYTES} bytes)")
    # JSON Lines uses LF (optionally preceded by CR), not every Unicode
    # separator recognized by str.splitlines(); U+2028 is valid string data.
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()  # one final line terminator is permitted
    if len(lines) > MAX_RECORDS:
        raise JournalValidationError(f"journal exceeds maximum record count ({MAX_RECORDS})")
    records = []
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            raise JournalValidationError(f"line {number}: blank records are not allowed")
        if len(line.encode("utf-8")) > MAX_RECORD_BYTES:
            raise JournalValidationError(f"line {number}: record exceeds maximum size ({MAX_RECORD_BYTES} bytes)")
        try:
            item = json.loads(
                line, object_pairs_hook=_unique_object,
                parse_constant=lambda value: (_ for _ in ()).throw(
                    JournalValidationError(f"non-standard JSON constant {value}")))
        except (json.JSONDecodeError, JournalValidationError) as exc:
            raise JournalValidationError(f"line {number}: {exc}") from exc
        if not isinstance(item, dict):
            raise JournalValidationError(f"line {number}: expected JSON object")
        records.append(item)
    return records


def replay_eligibility(record: dict[str, Any], *,
                       preconditions_verified: bool,
                       authorization_current: bool) -> tuple[bool, str]:
    """Conservative advisory only; never dispatches or authorizes a replay."""
    if not isinstance(record, dict) or record.get("state") != "interrupted":
        return False, "latest state is not interrupted"
    if record.get("idempotent") is not True:
        return False, "operation is not declared idempotent"
    if not preconditions_verified:
        return False, "external preconditions have not been re-verified"
    if not authorization_current:
        return False, "fresh authorization has not been confirmed"
    return True, "candidate only: caller must use the approved broker contract"

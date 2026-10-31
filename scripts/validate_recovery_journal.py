"""Read-only validation for installer recovery journals.

This module does not perform recovery, replay operations, access disks, or call a
privileged broker. Its checksum format is a local integrity envelope, not JCS
and not an authentication mechanism. Integration awaits NEXUS-07/AEGIS-06.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any, Iterable
from itertools import islice

GENESIS_CHECKSUM = "0" * 64
MAX_JOURNAL_BYTES = 4 * 1024 * 1024
MAX_RECORD_BYTES = 64 * 1024
MAX_RECORDS = 10_000
SHA256_HEX_LENGTH = 64
MAX_JSON_DEPTH = 64
MAX_JSON_NODES = 10_000
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


def _validate_json_value(value: Any, *, depth: int = 0,
                         active: set[int] | None = None,
                         budget: list[int] | None = None,
                         byte_budget: list[int] | None = None) -> None:
    """Accept bounded JSON primitives/containers only; never call custom hooks."""
    if active is None:
        active = set()
    if budget is None:
        budget = [MAX_JSON_NODES]
    if byte_budget is None:
        byte_budget = [MAX_RECORD_BYTES]
    budget[0] -= 1
    if budget[0] < 0:
        raise JournalValidationError("record exceeds maximum JSON node count")
    if depth > MAX_JSON_DEPTH:
        raise JournalValidationError("record exceeds maximum JSON nesting depth")
    value_type = type(value)
    if value_type in (type(None), bool):
        return
    if value_type is str:
        try:
            byte_budget[0] -= len(value.encode("utf-8", errors="strict"))
        except UnicodeEncodeError as exc:
            raise JournalValidationError("record contains invalid Unicode") from exc
        if byte_budget[0] < 0:
            raise JournalValidationError("record exceeds maximum encoded input size")
        return
    if value_type is int:
        if value.bit_length() > MAX_RECORD_BYTES * 3:
            raise JournalValidationError("record contains an oversized integer")
        return
    if value_type is float:
        if not math.isfinite(value):
            raise JournalValidationError("record contains a non-finite number")
        return
    if value_type not in (list, dict):
        raise JournalValidationError("record contains a non-JSON value type")
    identity = id(value)
    if identity in active:
        raise JournalValidationError("record contains a circular reference")
    active.add(identity)
    try:
        if value_type is list:
            for item in value:
                _validate_json_value(item, depth=depth + 1,
                                     active=active, budget=budget,
                                     byte_budget=byte_budget)
        else:
            for key, item in value.items():
                if type(key) is not str:
                    raise JournalValidationError(
                        "nested object keys must be plain strings")
                try:
                    byte_budget[0] -= len(key.encode("utf-8", errors="strict"))
                except UnicodeEncodeError as exc:
                    raise JournalValidationError(
                        "record contains invalid Unicode") from exc
                if byte_budget[0] < 0:
                    raise JournalValidationError(
                        "record exceeds maximum encoded input size")
                _validate_json_value(item, depth=depth + 1,
                                     active=active, budget=budget,
                                     byte_budget=byte_budget)
    finally:
        active.remove(identity)


def _canonical_payload(record: dict[str, Any]) -> bytes:
    if type(record) is not dict:
        raise JournalValidationError("record must be a plain dictionary")
    if any(type(key) is not str for key in record):
        raise JournalValidationError("record object keys must be plain strings")
    payload = {key: value for key, value in record.items() if key != "checksum"}
    _validate_json_value(payload)
    try:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode(
                                 "utf-8", errors="strict")
        if len(encoded) > MAX_RECORD_BYTES:
            raise JournalValidationError(
                f"record exceeds maximum size ({MAX_RECORD_BYTES} bytes)")
        return encoded
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
            (f"journal iteration failed: {type(exc).__name__}",))
    if len(materialized) > MAX_RECORDS:
        materialized = materialized[:MAX_RECORDS]
        errors.append(f"journal exceeds maximum record count ({MAX_RECORDS})")
    previous = GENESIS_CHECKSUM
    previous_state: str | None = None
    operation_id: str | None = None
    operation_idempotent: bool | None = None
    seen_sequences: set[int] = set()

    for index, record in enumerate(materialized, start=1):
        if type(record) is not dict:
            errors.append(f"record {index}: expected a plain dictionary")
            continue
        if any(type(key) is not str for key in record):
            # Do not format attacker-controlled key objects: __repr__ may raise.
            errors.append(f"record {index}: object keys must be plain strings")
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
        else:
            if sequence in seen_sequences:
                errors.append(f"record {index}: duplicate sequence {sequence}")
            else:
                seen_sequences.add(sequence)
            if sequence != index:
                errors.append(f"record {index}: expected sequence {index}, got {sequence}")
        if type(record["operation_id"]) is not str or not record["operation_id"]:
            errors.append(f"record {index}: operation_id must be non-empty")
        elif operation_id is None:
            operation_id = record["operation_id"]
        elif record["operation_id"] != operation_id:
            errors.append(f"record {index}: operation_id changed within journal")
        state = record["state"]
        if type(state) is not str:
            errors.append(f"record {index}: unknown state (state must be a plain string)")
        else:
            if index == 1 and state != "planned":
                errors.append("record 1: initial state must be planned")
            if state not in STATES:
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
        if (type(previous_checksum) is not str
                or len(previous_checksum) != SHA256_HEX_LENGTH
                or any(char not in "0123456789abcdef" for char in previous_checksum)):
            errors.append(f"record {index}: previous_checksum must be 64 lowercase hexadecimal characters")
        elif previous_checksum != previous:
            errors.append(f"record {index}: previous checksum does not match chain")
        supplied = record["checksum"]
        if type(supplied) is not str:
            errors.append(f"record {index}: checksum must be a plain string")
        if (type(supplied) is not str
                or len(supplied) != SHA256_HEX_LENGTH
                or any(char not in "0123456789abcdef" for char in supplied)):
            errors.append(f"record {index}: checksum must be 64 lowercase hexadecimal characters")
        # Only serialize a record after its schema fields have exact built-in
        # primitive types. This avoids invoking custom object behavior while
        # constructing a checksum for malformed caller-supplied dictionaries.
        if (type(sequence) is int and type(record["operation_id"]) is str
                and type(state) is str and type(record["idempotent"]) is bool
                and type(previous_checksum) is str and type(supplied) is str):
            try:
                actual = record_checksum(record)
            except JournalValidationError as exc:
                errors.append(f"record {index}: {exc}")
                actual = ""
            if supplied != actual:
                errors.append(f"record {index}: checksum mismatch")
        previous = supplied if type(supplied) is str else ""
        # Never index TRANSITIONS with an unrecognized state on the next record.
        previous_state = state if type(state) is str and state in STATES else None

    last = materialized[-1] if materialized and type(materialized[-1]) is dict else {}
    return JournalReport(
        valid=not errors,
        record_count=len(materialized),
        last_sequence=last.get("sequence", 0) if type(last.get("sequence")) is int else 0,
        last_state=last.get("state") if type(last.get("state")) is str else None,
        last_checksum=last.get("checksum") if type(last.get("checksum")) is str else "",
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
    # Require an exact built-in string so subclasses cannot override encode()
    # or otherwise run caller-controlled methods during parser preflight.
    if type(text) is not str or not text:
        raise JournalValidationError("journal must be non-empty plain text")
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
        except (ValueError, RecursionError, JournalValidationError) as exc:
            # json.loads may raise RecursionError for deeply nested input and
            # ValueError for implementation limits such as oversized integers.
            raise JournalValidationError(f"line {number}: invalid JSON ({type(exc).__name__})") from exc
        if not isinstance(item, dict):
            raise JournalValidationError(f"line {number}: expected JSON object")
        records.append(item)
    return records


def replay_eligibility(record: dict[str, Any], *,
                       preconditions_verified: bool,
                       authorization_current: bool) -> tuple[bool, str]:
    """Conservative advisory only; never dispatches or authorizes a replay."""
    if type(record) is not dict or type(record.get("state")) is not str \
            or record["state"] != "interrupted":
        return False, "latest state is not interrupted"
    if record.get("idempotent") is not True:
        return False, "operation is not declared idempotent"
    if not preconditions_verified:
        return False, "external preconditions have not been re-verified"
    if not authorization_current:
        return False, "fresh authorization has not been confirmed"
    return True, "candidate only: caller must use the approved broker contract"

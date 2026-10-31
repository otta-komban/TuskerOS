#!/usr/bin/env python3
"""Non-executing package transaction contracts for TuskerOS.

This module creates reviewable transaction previews and validates approval
claims. Cryptographic token verification and all package execution remain
outside this module and must be supplied by trusted platform services.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Mapping


class TransactionContractError(ValueError):
    """Raised when a transaction contract is malformed or unsafe."""


ALLOWED_ACTIONS = {"install", "remove"}
AUDIT_DETAIL_KEYS = {
    "package_count", "reason_code", "error_code", "rollback_status", "duration_ms"
}
ROLLBACK_STATES = {"not_required", "rolled_back", "rollback_failed", "partial"}
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
AUDIT_TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-(0[1-9]|1[0-2])-([0-2][0-9]|3[01])[Tt]"
    r"([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(\.[0-9]+)?([Zz]|[+-]([01][0-9]|2[0-3]):[0-5][0-9])$"
)


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TransactionContractError(f"{field} must be a non-empty string")
    return value


def _audit_digest(value: object, field: str) -> str:
    value = _text(value, field)
    if not SHA256_RE.fullmatch(value):
        raise TransactionContractError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _audit_timestamp(value: object) -> str:
    value = _text(value, "timestamp")
    if not AUDIT_TIMESTAMP_RE.fullmatch(value):
        raise TransactionContractError("timestamp must be an RFC 3339 date-time with timezone")
    normalized = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise TransactionContractError(
            "timestamp must be an RFC 3339 date-time with timezone"
        ) from exc
    if parsed.tzinfo is None:
        raise TransactionContractError("timestamp must include a timezone")
    return value


def canonical_digest(value: object) -> str:
    """SHA-256 of deterministic JSON; this is integrity binding, not a signature."""
    try:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise TransactionContractError("value is not canonical-JSON serializable") from exc
    return hashlib.sha256(encoded).hexdigest()


def create_transaction_preview(
    snapshot: object, operations: object, transaction_id: str
) -> dict[str, Any]:
    """Bind an exact operation list to the installed-state snapshot fingerprint."""
    transaction_id = _text(transaction_id, "transaction_id")
    if not isinstance(snapshot, Mapping):
        raise TransactionContractError("snapshot must be an object")
    if not isinstance(operations, list) or not operations:
        raise TransactionContractError("operations must be a non-empty array")
    normalized: list[dict[str, str]] = []
    for index, operation in enumerate(operations):
        if not isinstance(operation, Mapping) or set(operation) != {
            "action", "package_id", "version"
        }:
            raise TransactionContractError(
                f"operations[{index}] must contain only action, package_id, version"
            )
        action = _text(operation.get("action"), f"operations[{index}].action")
        if action not in ALLOWED_ACTIONS:
            raise TransactionContractError(f"operations[{index}].action is unsupported")
        normalized.append({
            "action": action,
            "package_id": _text(operation.get("package_id"), f"operations[{index}].package_id"),
            "version": _text(operation.get("version"), f"operations[{index}].version"),
        })
    identities = [(item["action"], item["package_id"]) for item in normalized]
    if len(identities) != len(set(identities)):
        raise TransactionContractError("duplicate action/package operation")
    snapshot_digest = canonical_digest(snapshot)
    operations_digest = canonical_digest(normalized)
    plan_digest = canonical_digest({
        "transaction_id": transaction_id,
        "snapshot_digest": snapshot_digest,
        "operations": normalized,
    })
    return {
        "transaction_id": transaction_id,
        "snapshot_digest": snapshot_digest,
        "operations": normalized,
        "operations_digest": operations_digest,
        "plan_digest": plan_digest,
        "state": "prepared",
        "execution": "not_performed",
    }


def validate_approval_claims(
    token: object, preview: Mapping[str, Any], now: str
) -> dict[str, str]:
    """Validate approval claims only; caller must first verify token cryptography.

    The token is an opaque authorization-service assertion. This function does
    not authenticate its issuer, signature, actor or authority.
    """
    required = {
        "token_id", "actor", "authority", "plan_digest",
        "snapshot_digest", "operations_digest", "approved_actions", "expires_at",
    }
    if not isinstance(token, Mapping) or set(token) != required:
        raise TransactionContractError("approval token claims have an invalid shape")
    for key in ("token_id", "actor", "authority", "plan_digest",
                "snapshot_digest", "operations_digest", "expires_at"):
        _text(token.get(key), f"token.{key}")
    if not isinstance(token["approved_actions"], list) or not token["approved_actions"]:
        raise TransactionContractError("token.approved_actions must be a non-empty array")
    if any(not isinstance(action, str) or action not in ALLOWED_ACTIONS for action in token["approved_actions"]):
        raise TransactionContractError("token contains an unsupported approved action")
    try:
        current = datetime.fromisoformat(_text(now, "now").replace("Z", "+00:00"))
        expiry = datetime.fromisoformat(token["expires_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise TransactionContractError("now and expires_at must be ISO-8601 timestamps") from exc
    if current.tzinfo is None or expiry.tzinfo is None:
        raise TransactionContractError("now and expires_at must include a timezone")
    if expiry <= current:
        raise TransactionContractError("approval token has expired")
    expected = {
        "plan_digest": preview.get("plan_digest"),
        "snapshot_digest": preview.get("snapshot_digest"),
        "operations_digest": preview.get("operations_digest"),
    }
    for key, value in expected.items():
        if token[key] != value:
            raise TransactionContractError(f"approval token {key} does not match preview")
    required_actions = {item["action"] for item in preview.get("operations", [])}
    if not required_actions.issubset(set(token["approved_actions"])):
        raise TransactionContractError("approval token does not cover every operation")
    return {
        "token_id": token["token_id"],
        "actor": token["actor"],
        "authority": token["authority"],
        "status": "claims_valid_unverified",
    }


def revalidate_snapshot(preview: Mapping[str, Any], current_snapshot: object) -> bool:
    """Return true only when the live installed state matches the reviewed snapshot."""
    if not isinstance(current_snapshot, Mapping):
        raise TransactionContractError("current_snapshot must be an object")
    if canonical_digest(current_snapshot) != preview.get("snapshot_digest"):
        raise TransactionContractError("installed state changed after preview")
    return True


def build_rollback_report(
    transaction_id: str,
    status: str,
    restored_packages: list[str],
    failed_packages: list[str],
) -> dict[str, Any]:
    """Describe rollback outcome; it does not perform or verify rollback."""
    transaction_id = _text(transaction_id, "transaction_id")
    if not isinstance(status, str) or status not in ROLLBACK_STATES:
        raise TransactionContractError("unsupported rollback status")
    for field, values in (("restored_packages", restored_packages),
                          ("failed_packages", failed_packages)):
        if not isinstance(values, list) or any(
            not isinstance(item, str) or not item.strip() for item in values
        ):
            raise TransactionContractError(f"{field} must be an array of non-empty strings")
    if set(restored_packages) & set(failed_packages):
        raise TransactionContractError("a package cannot be both restored and failed")
    if status == "rolled_back" and failed_packages:
        raise TransactionContractError("rolled_back report cannot contain failed packages")
    if status == "rollback_failed" and not failed_packages:
        raise TransactionContractError("rollback_failed requires failed packages")
    return {
        "transaction_id": transaction_id,
        "status": status,
        "restored_packages": sorted(set(restored_packages)),
        "failed_packages": sorted(set(failed_packages)),
        "execution": "not_performed_by_contract",
    }


def build_audit_event(
    transaction_id: str,
    timestamp: str,
    actor: str,
    event: str,
    plan_digest: str,
    snapshot_digest: str,
    outcome: str,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a minimal allow-listed audit record; persistence is adapter-owned."""
    if details is None:
        details = {}
    if not isinstance(details, Mapping) or set(details) - AUDIT_DETAIL_KEYS:
        raise TransactionContractError("audit details contain unsupported or sensitive fields")
    for key, value in details.items():
        if key in {"package_count", "duration_ms"}:
            if isinstance(value, bool) or not isinstance(value, int):
                raise TransactionContractError(f"audit detail {key} must be a non-negative integer")
            if value < 0:
                raise TransactionContractError(f"audit detail {key} cannot be negative")
        elif key in {"reason_code", "error_code"}:
            if not isinstance(value, str):
                raise TransactionContractError(f"audit detail {key} must be a string")
            if len(value) > 128:
                raise TransactionContractError(f"audit detail {key} is too long")
        elif key == "rollback_status":
            if not isinstance(value, str) or value not in ROLLBACK_STATES:
                raise TransactionContractError(f"audit detail {key} has an unsupported value")
    return {
        "transaction_id": _text(transaction_id, "transaction_id"),
        "timestamp": _audit_timestamp(timestamp),
        "actor": _text(actor, "actor"),
        "event": _text(event, "event"),
        "plan_digest": _audit_digest(plan_digest, "plan_digest"),
        "snapshot_digest": _audit_digest(snapshot_digest, "snapshot_digest"),
        "outcome": _text(outcome, "outcome"),
        "details": dict(details),
    }


__all__ = [
    "TransactionContractError", "canonical_digest", "create_transaction_preview",
    "validate_approval_claims", "revalidate_snapshot", "build_rollback_report",
    "build_audit_event",
]

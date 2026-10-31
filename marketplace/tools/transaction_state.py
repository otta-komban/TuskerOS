"""Pure package transaction lifecycle state machine; never executes packages.

The trusted adapter is responsible for authenticating approval and invoking
these transitions only after the corresponding external operation succeeds.
"""
from __future__ import annotations

from typing import Any, Mapping


class TransactionStateError(ValueError):
    """Raised for invalid transaction lifecycle transitions."""


TRANSITIONS = {
    "prepared": {"approval_verified", "cancelled"},
    "approval_verified": {"revalidated", "rejected", "cancelled"},
    "revalidated": {"execution_started", "stale", "cancelled"},
    "execution_started": {"committed", "rolled_back", "rollback_failed"},
    "committed": set(),
    "rolled_back": set(),
    "rollback_failed": set(),
    "stale": set(),
    "rejected": set(),
    "cancelled": set(),
}
TERMINAL_STATES = {
    "committed", "rolled_back", "rollback_failed", "stale", "rejected", "cancelled"
}
EVIDENCE_KEYS = {
    "approval_verified": {"approval_id", "verification_ref", "authority"},
    "revalidated": {"snapshot_digest"},
    "stale": {"observed_snapshot_digest"},
    "execution_started": {"lock_ref"},
    "committed": {"result_ref"},
    "rolled_back": {"result_ref"},
    "rollback_failed": {"result_ref"},
    "rejected": {"reason_code"},
    "cancelled": {"reason_code"},
}


def transition_transaction(
    transaction: Mapping[str, Any],
    event: str,
    evidence: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Return a new lifecycle record after validating one legal transition.

    Evidence is correlation metadata, not cryptographic proof. The trusted
    adapter must verify external approval and perform each real operation.
    """
    if not isinstance(transaction, Mapping):
        raise TransactionStateError("transaction must be an object")
    required = {"transaction_id", "state", "plan_digest", "snapshot_digest"}
    optional = {"history", "terminal"}
    if not required.issubset(transaction) or set(transaction) - required - optional:
        raise TransactionStateError("transaction has an invalid shape")
    history_value = transaction.get("history", [])
    if not isinstance(history_value, list):
        raise TransactionStateError("transaction history must be an array")
    if "terminal" in transaction and not isinstance(transaction["terminal"], bool):
        raise TransactionStateError("transaction terminal must be a boolean")
    for field in required:
        if not isinstance(transaction[field], str) or not transaction[field].strip():
            raise TransactionStateError(f"{field} must be a non-empty string")
    current = transaction["state"]
    if not isinstance(current, str) or current not in TRANSITIONS:
        raise TransactionStateError("unknown current transaction state")
    for field in ("plan_digest", "snapshot_digest"):
        digest = transaction[field]
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise TransactionStateError(f"{field} must be a lowercase SHA-256 digest")
    if "terminal" in transaction and transaction["terminal"] != (current in TERMINAL_STATES):
        raise TransactionStateError("terminal flag does not match current state")
    if history_value and (
        not isinstance(history_value[-1], Mapping)
        or history_value[-1].get("event") != current
    ):
        raise TransactionStateError("history must end with the current transaction state")
    if not history_value and current != "prepared":
        raise TransactionStateError("a transaction without history must start in prepared state")
    expected_source = "prepared"
    for index, item in enumerate(history_value):
        if not isinstance(item, Mapping) or set(item) != {"from", "event", "evidence"}:
            raise TransactionStateError(f"history[{index}] has an invalid shape")
        source = item["from"]
        target = item["event"]
        if not isinstance(source, str) or source not in TRANSITIONS:
            raise TransactionStateError(f"history[{index}].from is invalid")
        if source != expected_source:
            raise TransactionStateError(f"history[{index}] breaks transition continuity")
        if not isinstance(target, str) or target not in TRANSITIONS[source]:
            raise TransactionStateError(f"history[{index}].event is invalid")
        item_evidence = item["evidence"]
        if not isinstance(item_evidence, Mapping) or any(
            not isinstance(k, str) or not isinstance(v, str) or not v.strip()
            for k, v in item_evidence.items()
        ):
            raise TransactionStateError(f"history[{index}].evidence is invalid")
        if set(item_evidence) - EVIDENCE_KEYS.get(target, set()):
            raise TransactionStateError(f"history[{index}] contains unsupported evidence")
        if target == "approval_verified" and not {"approval_id", "verification_ref", "authority"}.issubset(item_evidence):
            raise TransactionStateError(f"history[{index}] lacks approval verification evidence")
        if target == "revalidated" and item_evidence.get("snapshot_digest") != transaction["snapshot_digest"]:
            raise TransactionStateError(f"history[{index}] has mismatched snapshot evidence")
        if target == "stale":
            observed = item_evidence.get("observed_snapshot_digest", "")
            if len(observed) != 64 or any(ch not in "0123456789abcdef" for ch in observed) or observed == transaction["snapshot_digest"]:
                raise TransactionStateError(f"history[{index}] has invalid stale snapshot evidence")
        if target == "execution_started" and not item_evidence.get("lock_ref"):
            raise TransactionStateError(f"history[{index}] lacks lock evidence")
        if target in {"committed", "rolled_back", "rollback_failed"} and not item_evidence.get("result_ref"):
            raise TransactionStateError(f"history[{index}] lacks result evidence")
        expected_source = target
    if history_value and expected_source != current:
        raise TransactionStateError("history does not describe the current state")
    if not isinstance(event, str) or event not in TRANSITIONS[current]:
        raise TransactionStateError(f"transition {current} -> {event!r} is not allowed")
    if evidence is None:
        evidence = {}
    if not isinstance(evidence, Mapping) or any(
        not isinstance(k, str) or not isinstance(v, str) or not v.strip()
        for k, v in evidence.items()
    ):
        raise TransactionStateError("evidence must map text keys to non-empty text values")
    if set(evidence) - EVIDENCE_KEYS.get(event, set()):
        raise TransactionStateError("evidence contains unsupported or sensitive fields")
    if event == "approval_verified" and not {
        "approval_id", "verification_ref", "authority"
    }.issubset(evidence):
        raise TransactionStateError(
            "approval_verified requires approval_id, verification_ref and authority"
        )
    if event == "revalidated" and evidence.get("snapshot_digest") != transaction["snapshot_digest"]:
        raise TransactionStateError("revalidated evidence must match the reviewed snapshot digest")
    if event == "stale":
        observed = evidence.get("observed_snapshot_digest", "")
        if len(observed) != 64 or any(ch not in "0123456789abcdef" for ch in observed):
            raise TransactionStateError("stale transition requires a valid observed snapshot digest")
        if observed == transaction["snapshot_digest"]:
            raise TransactionStateError("stale transition requires a different observed snapshot digest")
    if event == "execution_started" and not evidence.get("lock_ref"):
        raise TransactionStateError("execution_started requires a package transaction lock reference")
    if event in {"committed", "rolled_back", "rollback_failed"} and not evidence.get("result_ref"):
        raise TransactionStateError(f"{event} requires a result_ref")
    updated = dict(transaction)
    updated["state"] = event
    history = list(history_value)
    history.append({"from": current, "event": event, "evidence": dict(evidence)})
    updated["history"] = history
    updated["terminal"] = event in TERMINAL_STATES
    return updated


__all__ = ["TransactionStateError", "transition_transaction", "TRANSITIONS"]

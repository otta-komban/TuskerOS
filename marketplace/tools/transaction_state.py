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


def transition_transaction(
    transaction: Mapping[str, Any],
    event: str,
    evidence: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Return a new lifecycle record after validating one legal transition.

    Evidence is descriptive correlation metadata, not cryptographic proof.
    In particular, approval_verified must only be emitted by an adapter after
    the trusted authorization service has verified the approval token.
    """
    if not isinstance(transaction, Mapping):
        raise TransactionStateError("transaction must be an object")
    required = {"transaction_id", "state", "plan_digest", "snapshot_digest"}
    optional = {"history", "terminal"}
    if not required.issubset(transaction) or set(transaction) - required - optional:
        raise TransactionStateError("transaction has an invalid shape")
    if "history" in transaction and not isinstance(transaction["history"], list):
        raise TransactionStateError("transaction history must be an array")
    if "terminal" in transaction and not isinstance(transaction["terminal"], bool):
        raise TransactionStateError("transaction terminal must be a boolean")
    for field in required:
        if not isinstance(transaction[field], str) or not transaction[field].strip():
            raise TransactionStateError(f"{field} must be a non-empty string")
    current = transaction["state"]
    if current not in TRANSITIONS:
        raise TransactionStateError("unknown current transaction state")
    if not isinstance(event, str) or event not in TRANSITIONS[current]:
        raise TransactionStateError(f"transition {current} -> {event!r} is not allowed")
    if evidence is None:
        evidence = {}
    if not isinstance(evidence, Mapping) or any(
        not isinstance(k, str) or not isinstance(v, str) or not v.strip()
        for k, v in evidence.items()
    ):
        raise TransactionStateError("evidence must map text keys to non-empty text values")
    if event == "approval_verified" and not {
        "approval_id", "verification_ref", "authority"
    }.issubset(evidence):
        raise TransactionStateError(
            "approval_verified requires approval_id, verification_ref and authority"
        )
    if event == "revalidated" and evidence.get("snapshot_digest") != transaction["snapshot_digest"]:
        raise TransactionStateError("revalidated evidence must match the reviewed snapshot digest")
    if event == "stale" and evidence.get("observed_snapshot_digest") == transaction["snapshot_digest"]:
        raise TransactionStateError("stale transition requires a different observed snapshot digest")
    if event == "execution_started" and evidence.get("lock_ref") is None:
        raise TransactionStateError("execution_started requires a package transaction lock reference")
    if event in {"committed", "rolled_back", "rollback_failed"} and not evidence.get("result_ref"):
        raise TransactionStateError(f"{event} requires a result_ref")
    updated = dict(transaction)
    updated["state"] = event
    history = list(transaction.get("history", []))
    history.append({"from": current, "event": event, "evidence": dict(evidence)})
    updated["history"] = history
    updated["terminal"] = event in TERMINAL_STATES
    return updated


__all__ = ["TransactionStateError", "transition_transaction", "TRANSITIONS"]

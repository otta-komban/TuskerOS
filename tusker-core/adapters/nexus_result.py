"""Fail-closed mapping of NEXUS tool results into Core lifecycle actions.

This is a pure adapter helper. It does not dispatch tools, authorize operations,
or persist state; callers must apply the returned action inside Core's
transactional task/step state machine.
"""
from typing import Any, Dict


def classify_tool_result(result: Dict[str, Any]) -> str:
    """Return a conservative Core action for a validated NEXUS result.

    Possible actions:
      completed, verification_required, failed_preserve_effects,
      reauthorization_required, running, cancelled, reconcile.

    Unknown/malformed statuses always reconcile rather than implying success,
    failure, cancellation, or permission.
    """
    if not isinstance(result, dict):
        return "reconcile"

    status = result.get("status")
    postcondition = result.get("postcondition")
    post_state = postcondition.get("state") if isinstance(postcondition, dict) else None
    cancellation = result.get("cancellation")
    operation_state = (
        cancellation.get("operation_state")
        if isinstance(cancellation, dict)
        else None
    )

    if status == "succeeded":
        if post_state in ("verified", "not_applicable"):
            return "completed"
        return "verification_required"

    if status == "needs_approval":
        # Provider/broker approval is not an AEGIS decision or a grant.
        return "reauthorization_required"

    if status == "running":
        return "running"

    if status == "cancelled":
        # A cancellation response is terminal only when the operation is
        # confirmed stopped. Otherwise preserve uncertainty and reconcile.
        if operation_state == "stopped":
            return "cancelled"
        return "reconcile"

    if status in ("rejected", "failed"):
        # Preserve reported side effects; task-level failed vs partial
        # completion is decided by Core after inspecting prior steps/evidence.
        return "failed_preserve_effects"

    if status == "unknown_outcome":
        return "reconcile"

    return "reconcile"

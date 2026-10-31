"""Narrow broker authorization adapter; deliberately contains no handlers."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping
from .store import ConsumeResult, SecurityStore

@dataclass(frozen=True)
class BrokerAuthorizationRequest:
    authorization_ref: str = field(repr=False)
    broker_operation_id: str
    action_digest: str
    policy_version: str
    canonical_resource_scope: tuple[str, ...]
    registry_version: str
    precondition_digest: str
    peer_credentials: Any = field(repr=False)

@dataclass(frozen=True)
class BrokerAuthorizationResponse:
    outcome: str
    consumption_id: str | None = None
    grant: Mapping[str, Any] | None = None

class BrokerAuthorizationGate:
    """Single-purpose consume gate; a missing trusted peer verifier denies."""
    def __init__(self, authority: SecurityStore):
        self._authority = authority

    def authorize(self, request: BrokerAuthorizationRequest, audit_context: Mapping[str, Any],
                  *, now: datetime | None = None) -> BrokerAuthorizationResponse:
        # This is the last adapter before a broker may dispatch an operation.
        # Treat malformed inputs and authority failures as denials; never let an
        # exception or an incomplete "consumed" response cross the gate.
        if not isinstance(request, BrokerAuthorizationRequest) or not isinstance(audit_context, Mapping):
            return BrokerAuthorizationResponse("BINDING_MISMATCH")
        try:
            result: ConsumeResult = self._authority.consume(
                request.authorization_ref, operation_id=request.broker_operation_id,
                resource_scope=list(request.canonical_resource_scope), action_digest=request.action_digest,
                policy_version=request.policy_version, registry_version=request.registry_version,
                precondition_digest=request.precondition_digest, peer_credentials=request.peer_credentials,
                audit_context=audit_context, now=now)
        except Exception:
            return BrokerAuthorizationResponse("AUTHORITY_UNAVAILABLE")
        if not isinstance(result, ConsumeResult):
            return BrokerAuthorizationResponse("AUTHORITY_UNAVAILABLE")
        if result.outcome != "CONSUMED":
            return BrokerAuthorizationResponse(result.outcome)
        required_grant_fields = {
            "consumption_id", "operation_id", "resource_scope", "principal_binding",
            "session_binding", "device_binding", "action_digest", "registry_version",
            "precondition_digest",
        }
        if (not isinstance(result.consumption_id, str) or not result.consumption_id
            or not isinstance(result.grant, Mapping)
            or set(result.grant) != required_grant_fields
            or result.grant.get("consumption_id") != result.consumption_id):
            return BrokerAuthorizationResponse("AUTHORITY_UNAVAILABLE")
        return BrokerAuthorizationResponse("CONSUMED", result.consumption_id, result.grant)

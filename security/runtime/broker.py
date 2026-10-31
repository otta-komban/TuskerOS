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
        result: ConsumeResult = self._authority.consume(
            request.authorization_ref, operation_id=request.broker_operation_id,
            resource_scope=list(request.canonical_resource_scope), action_digest=request.action_digest,
            policy_version=request.policy_version, registry_version=request.registry_version,
            precondition_digest=request.precondition_digest, peer_credentials=request.peer_credentials,
            audit_context=audit_context, now=now)
        if result.outcome != "CONSUMED":
            return BrokerAuthorizationResponse(result.outcome)
        return BrokerAuthorizationResponse("CONSUMED", result.consumption_id, result.grant)

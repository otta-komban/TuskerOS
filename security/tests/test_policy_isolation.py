"""Regression tests for policy adapter input isolation."""
import uuid
from datetime import datetime, timezone

from security.runtime.policy import PolicyEngine

D1 = "sha256:" + "1" * 64
D2 = "sha256:" + "2" * 64
D3 = "sha256:" + "3" * 64
D4 = "sha256:" + "4" * 64


def test_policy_adapter_mutations_cannot_change_authorized_inputs():
    proposal = {
        "schema_version": "0.1.0",
        "action_id": "system.info.read",
        "proposal_id": str(uuid.uuid4()),
        "task_id": "task-1",
        "step_id": "step-1",
        "arguments": {"payload": "original"},
        "resources": [{"kind": "system", "id": "host", "access": "read"}],
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }
    context = {
        "authenticated": True,
        "principal_binding": D1,
        "session_binding": D2,
        "device_binding": D3,
        "origin": "local",
        "principal_class": "user",
    }
    registry = [{
        "schema_version": "0.1.0",
        "action_id": "system.info.read",
        "operation_schema_version": "1.0.0",
        "arguments_schema_ref": "schemas/arguments/system-info.json",
        "preconditions": [],
        "postcondition_verifier": "verify.system.info",
        "allowed_origins": ["local"],
        "allowed_principal_classes": ["user"],
        "resources": [{"kind": "system", "access_modes": ["read"]}],
        "minimum_risk_class": "R0",
        "approval_mode": "never",
        "broker_operation_id": "broker.system.info.read",
        "timeout_ms": 1000,
        "idempotency": "optional_read_only",
    }]

    def verify_identity(value):
        value["principal_class"] = "administrator"
        return True

    def verify_registry(value, version):
        value[0]["action_id"] = "system.evil.execute"
        value[0]["allowed_origins"].clear()
        return version == "registry-1"

    def validate_arguments(action_id, arguments):
        arguments["payload"] = "validator-mutated"
        return action_id == "system.info.read"

    def resolve_resources(resources):
        # Canonicalizing the returned identifier is allowed, but mutation of
        # the resolver's input must not leak into the caller's proposal.
        resources[0]["id"] = "canonical-host"
        return resources

    def verify_preconditions(value, resources):
        value["arguments"]["payload"] = "precondition-mutated"
        resources[0]["id"] = "precondition-mutated"
        return D4

    engine = PolicyEngine(
        "policy-1",
        identity_verifier=verify_identity,
        registry_verifier=verify_registry,
        argument_validator=validate_arguments,
        resource_resolver=resolve_resources,
        precondition_verifier=verify_preconditions,
    )

    decision = engine.evaluate(proposal, context, registry, "registry-1")

    assert decision.status == "ALLOW"
    assert proposal["arguments"] == {"payload": "original"}
    assert proposal["resources"] == [{"kind": "system", "id": "host", "access": "read"}]
    assert context["principal_class"] == "user"
    assert registry[0]["action_id"] == "system.info.read"
    assert registry[0]["allowed_origins"] == ["local"]


def test_policy_rejects_malformed_optional_idempotency_keys():
    from copy import deepcopy
    import pytest

    valid_proposal = {
        "schema_version": "0.1.0",
        "action_id": "system.info.read",
        "proposal_id": str(uuid.uuid4()),
        "task_id": "task-1",
        "step_id": "step-1",
        "arguments": {},
        "resources": [{"kind": "system", "id": "host", "access": "read"}],
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }
    context = {
        "principal_binding": D1,
        "session_binding": D2,
        "device_binding": D3,
        "origin": "local",
        "principal_class": "user",
    }
    registry = [{
        "schema_version": "0.1.0",
        "action_id": "system.info.read",
        "operation_schema_version": "1.0.0",
        "arguments_schema_ref": "schemas/arguments/system-info.json",
        "preconditions": [],
        "postcondition_verifier": "verify.system.info",
        "allowed_origins": ["local"],
        "allowed_principal_classes": ["user"],
        "resources": [{"kind": "system", "access_modes": ["read"]}],
        "minimum_risk_class": "R0",
        "approval_mode": "never",
        "broker_operation_id": "broker.system.info.read",
        "timeout_ms": 1000,
        "idempotency": "optional_read_only",
    }]
    engine = PolicyEngine(
        "policy-1",
        identity_verifier=lambda value: True,
        registry_verifier=lambda value, version: True,
        argument_validator=lambda action_id, arguments: True,
        resource_resolver=lambda resources: resources,
        precondition_verifier=lambda proposal, resources: D4,
    )

    for invalid in (None, 1, "short", "x" * 129):
        proposal = deepcopy(valid_proposal)
        proposal["idempotency_key"] = invalid
        decision = engine.evaluate(proposal, context, registry, "registry-1")
        assert decision.status == "DENY"
        assert decision.reason_code == "POLICY_INVALID_ARGUMENTS"


def test_policy_rejects_non_rfc3339_requested_at_values():
    from copy import deepcopy

    valid_proposal = {
        "schema_version": "0.1.0",
        "action_id": "system.info.read",
        "proposal_id": str(uuid.uuid4()),
        "task_id": "task-1",
        "step_id": "step-1",
        "arguments": {},
        "resources": [{"kind": "system", "id": "host", "access": "read"}],
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }
    context = {
        "principal_binding": D1,
        "session_binding": D2,
        "device_binding": D3,
        "origin": "local",
        "principal_class": "user",
    }
    registry = [{
        "schema_version": "0.1.0",
        "action_id": "system.info.read",
        "operation_schema_version": "1.0.0",
        "arguments_schema_ref": "schemas/arguments/system-info.json",
        "preconditions": [],
        "postcondition_verifier": "verify.system.info",
        "allowed_origins": ["local"],
        "allowed_principal_classes": ["user"],
        "resources": [{"kind": "system", "access_modes": ["read"]}],
        "minimum_risk_class": "R0",
        "approval_mode": "never",
        "broker_operation_id": "broker.system.info.read",
        "timeout_ms": 1000,
        "idempotency": "optional_read_only",
    }]
    engine = PolicyEngine(
        "policy-1",
        identity_verifier=lambda value: True,
        registry_verifier=lambda value, version: True,
        argument_validator=lambda action_id, arguments: True,
        resource_resolver=lambda resources: resources,
        precondition_verifier=lambda proposal, resources: D4,
    )

    for invalid_timestamp in (
        "2026-10-31 06:00:00+00:00",
        "2026-10-31T06:00+00:00",
        "2026-10-31",
        "not-a-timestamp",
    ):
        proposal = deepcopy(valid_proposal)
        proposal["requested_at"] = invalid_timestamp
        decision = engine.evaluate(proposal, context, registry, "registry-1")
        assert decision.status == "DENY"
        assert decision.reason_code == "POLICY_INVALID_ARGUMENTS"

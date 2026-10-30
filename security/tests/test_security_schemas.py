import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
AUDIT_SCHEMA = json.loads((SCHEMA_DIR / "audit-event.schema.json").read_text())

VALID_EVENT = {
    "schema_version": "0.1.0",
    "event_id": "123e4567-e89b-12d3-a456-426614174000",
    "timestamp_utc": "2026-10-31T00:00:00Z",
    "event_type": "succeeded",
    "principal_binding": "sha256:" + "a" * 64,
    "origin": "local",
    "task_id": "task-123",
    "step_id": "step-456",
    "proposal_id": "123e4567-e89b-12d3-a456-426614174001",
    "decision_id": "123e4567-e89b-12d3-a456-426614174002",
    "operation_id": "system.settings.update",
    "risk_class": "R2",
    "policy_version": "0.1.0",
    "action_digest": "sha256:" + "b" * 64,
    "approval_request_id": None,
    "executor_id": "broker-01",
    "result_status": "success",
    "reason_code": None,
    "correlation_id": "corr-123",
}


APPROVAL_SCHEMA = json.loads(
    (SCHEMA_DIR / "approval-request.schema.json").read_text()
)

VALID_APPROVAL = {
    "schema_version": "0.2.0",
    "approval_request_id": "123e4567-e89b-12d3-a456-426614174010",
    "proposal_id": "123e4567-e89b-12d3-a456-426614174011",
    "action_id": "system.settings.update",
    "action_digest": "sha256:" + "c" * 64,
    "principal_binding": "sha256:" + "d" * 64,
    "binding": {
        "session_binding": "sha256:" + "e" * 64,
        "device_binding": "sha256:" + "f" * 64,
        "registry_version": "registry-2026-10-31.1",
        "resource_scope": ["settings:display"],
        "precondition_digest": "sha256:" + "a" * 64,
    },
    "policy_version": "0.1.0",
    "risk_class": "R2",
    "summary": "Update display settings",
    "target": "Display settings",
    "impact": "Changes the active display configuration",
    "reversible": True,
    "created_at": "2026-10-31T00:00:00Z",
    "expires_at": "2026-10-31T00:05:00Z",
}


def approval_validator():
    Draft202012Validator.check_schema(APPROVAL_SCHEMA)
    return Draft202012Validator(
        APPROVAL_SCHEMA,
        format_checker=FormatChecker(),
    )


def test_valid_approval_request_with_all_bindings_is_valid():
    assert list(approval_validator().iter_errors(VALID_APPROVAL)) == []


@pytest.mark.parametrize(
    "field",
    [
        "session_binding",
        "device_binding",
        "registry_version",
        "resource_scope",
        "precondition_digest",
    ],
)
def test_approval_binding_members_cannot_be_omitted(field):
    request = json.loads(json.dumps(VALID_APPROVAL))
    del request["binding"][field]
    assert list(approval_validator().iter_errors(request))


@pytest.mark.parametrize(
    "field,value",
    [
        ("session_binding", None),
        ("device_binding", None),
        ("registry_version", ""),
        ("resource_scope", []),
        ("precondition_digest", "sha256:bad"),
    ],
)
def test_invalid_approval_binding_values_are_rejected(field, value):
    request = json.loads(json.dumps(VALID_APPROVAL))
    request["binding"][field] = value
    assert list(approval_validator().iter_errors(request))


def test_duplicate_resource_scope_is_rejected():
    request = json.loads(json.dumps(VALID_APPROVAL))
    request["binding"]["resource_scope"] = [
        "settings:display",
        "settings:display",
    ]
    assert list(approval_validator().iter_errors(request))


def test_approval_request_rejects_unknown_fields():
    request = json.loads(json.dumps(VALID_APPROVAL))
    request["binding"]["untrusted_identity"] = "root"
    assert list(approval_validator().iter_errors(request))


def audit_validator():
    Draft202012Validator.check_schema(AUDIT_SCHEMA)
    return Draft202012Validator(
        AUDIT_SCHEMA,
        format_checker=FormatChecker(),
    )


def test_all_security_schemas_are_valid_draft_2020_12_schemas():
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = json.loads(path.read_text())
        Draft202012Validator.check_schema(schema)


def test_correlated_audit_event_is_valid():
    assert list(audit_validator().iter_errors(VALID_EVENT)) == []


def test_explicit_null_task_and_step_are_valid():
    event = dict(VALID_EVENT, task_id=None, step_id=None)
    assert list(audit_validator().iter_errors(event)) == []


@pytest.mark.parametrize("field", ["task_id", "step_id"])
def test_task_and_step_keys_cannot_be_omitted(field):
    event = dict(VALID_EVENT)
    del event[field]
    assert list(audit_validator().iter_errors(event))


@pytest.mark.parametrize("field", ["task_id", "step_id"])
@pytest.mark.parametrize("value", [42, {}, []])
def test_task_and_step_values_must_be_string_or_null(field, value):
    event = dict(VALID_EVENT, **{field: value})
    assert list(audit_validator().iter_errors(event))


@pytest.mark.parametrize(
    "mutation",
    [
        {"event_id": "not-a-uuid"},
        {"timestamp_utc": "not-a-date"},
        {"principal_binding": "sha256:bad"},
        {"risk_class": "R9"},
        {"result_status": "maybe"},
        {"unexpected": True},
    ],
)
def test_invalid_audit_event_fields_are_rejected(mutation):
    event = dict(VALID_EVENT)
    event.update(mutation)
    assert list(audit_validator().iter_errors(event))

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

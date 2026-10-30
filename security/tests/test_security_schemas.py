import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
AUDIT_SCHEMA = json.loads((SCHEMA_DIR / "audit-event.schema.json").read_text())
APPROVAL_SCHEMA = json.loads((SCHEMA_DIR / "approval-request.schema.json").read_text())
AUDIT_V020_SCHEMA = json.loads((SCHEMA_DIR / "audit-event-0.2.0.schema.json").read_text())

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

VALID_APPROVAL = {
    "schema_version": "0.2.0",
    "approval_request_id": "123e4567-e89b-12d3-a456-426614174010",
    "proposal_id": "123e4567-e89b-12d3-a456-426614174011",
    "action_id": "system.storage.install",
    "action_digest": "sha256:" + "c" * 64,
    "principal_binding": "sha256:" + "d" * 64,
    "binding": {
        "session_binding": "sha256:" + "e" * 64,
        "device_binding": "sha256:" + "f" * 64,
        "registry_version": "registry-2026-10-31.1",
        "resource_scope": ["disk:wwn-0x5000c500aabbccdd"],
        "precondition_digest": "sha256:" + "1" * 64,
    },
    "policy_version": "0.1.0",
    "risk_class": "R4",
    "summary": "Install TuskerOS",
    "target": "Selected system disk",
    "impact": "Partitions and data on the selected disk may be replaced",
    "reversible": False,
    "created_at": "2026-10-31T00:00:00Z",
    "expires_at": "2026-10-31T00:02:00Z",
}


def make_validator(schema):
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def audit_validator():
    return make_validator(AUDIT_SCHEMA)


def approval_validator():
    return make_validator(APPROVAL_SCHEMA)


def audit_v020_validator():
    return make_validator(AUDIT_V020_SCHEMA)


def valid_audit_v020_event():
    event = json.loads(json.dumps(VALID_EVENT))
    event["schema_version"] = "0.2.0"
    event["registry_version"] = "registry-2026-10-31.1"
    event["registry_status"] = "resolved"
    return event


def test_all_security_schemas_are_valid_draft_2020_12_schemas():
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        make_validator(json.loads(path.read_text()))


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


def test_approval_request_v020_with_complete_bindings_is_valid():
    assert list(approval_validator().iter_errors(VALID_APPROVAL)) == []


def test_approval_binding_object_is_required():
    request = dict(VALID_APPROVAL)
    del request["binding"]
    assert list(approval_validator().iter_errors(request))


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
        ("session_binding", "sha256:bad"),
        ("device_binding", "sha256:bad"),
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
    request["binding"]["resource_scope"] = ["disk:one", "disk:one"]
    assert list(approval_validator().iter_errors(request))


def test_approval_request_rejects_unknown_nested_binding_fields():
    request = json.loads(json.dumps(VALID_APPROVAL))
    request["binding"]["untrusted_identity"] = "root"
    assert list(approval_validator().iter_errors(request))


def test_approval_request_rejects_unknown_top_level_fields():
    request = json.loads(json.dumps(VALID_APPROVAL))
    request["caller_principal"] = "root"
    assert list(approval_validator().iter_errors(request))


def test_approval_request_v010_is_not_accepted_by_v020_schema():
    request = json.loads(json.dumps(VALID_APPROVAL))
    request["schema_version"] = "0.1.0"
    assert list(approval_validator().iter_errors(request))



def test_audit_event_v020_candidate_accepts_required_versioned_fields():
    event = valid_audit_v020_event()
    assert list(audit_v020_validator().iter_errors(event)) == []


def test_audit_event_v020_candidate_accepts_explicit_null_executor_and_reason():
    event = valid_audit_v020_event()
    event["executor_id"] = None
    event["reason_code"] = None
    assert list(audit_v020_validator().iter_errors(event)) == []


@pytest.mark.parametrize("field", ["registry_version", "executor_id", "reason_code"])
def test_audit_event_v020_candidate_requires_minimum_keys(field):
    event = valid_audit_v020_event()
    del event[field]
    assert list(audit_v020_validator().iter_errors(event))


@pytest.mark.parametrize(
    "field,value",
    [
        ("registry_version", None),
        ("registry_version", ""),
        ("registry_version", "r" * 129),
        ("executor_id", 42),
        ("reason_code", {}),
    ],
)
def test_audit_event_v020_candidate_rejects_invalid_minimum_values(field, value):
    event = valid_audit_v020_event()
    event[field] = value
    assert list(audit_v020_validator().iter_errors(event))


@pytest.mark.parametrize("status", ["denied", "failure"])
def test_audit_event_v020_candidate_requires_reason_for_denial_and_failure(status):
    event = valid_audit_v020_event()
    event["event_type"] = "policy_denied" if status == "denied" else "failed"
    event["result_status"] = status
    event["reason_code"] = None
    assert list(audit_v020_validator().iter_errors(event))
    event["reason_code"] = "POLICY_DENY_DEFAULT"
    assert list(audit_v020_validator().iter_errors(event)) == []


def test_audit_event_v020_candidate_rejects_v010_envelope():
    event = valid_audit_v020_event()
    event["schema_version"] = "0.1.0"
    assert list(audit_v020_validator().iter_errors(event))


def test_audit_event_v010_schema_rejects_v020_envelope():
    event = valid_audit_v020_event()
    assert list(audit_validator().iter_errors(event))



def test_audit_event_v020_candidate_accepts_unavailable_registry_request():
    event = valid_audit_v020_event()
    event["registry_status"] = "unavailable"
    event["registry_version"] = None
    event["event_type"] = "requested"
    event["result_status"] = "accepted"
    event["executor_id"] = None
    event["reason_code"] = None
    assert list(audit_v020_validator().iter_errors(event)) == []


def test_audit_event_v020_candidate_accepts_registry_unavailable_denial():
    event = valid_audit_v020_event()
    event["registry_status"] = "unavailable"
    event["registry_version"] = None
    event["event_type"] = "policy_denied"
    event["result_status"] = "denied"
    event["executor_id"] = None
    event["reason_code"] = "POLICY_REGISTRY_UNAVAILABLE"
    assert list(audit_v020_validator().iter_errors(event)) == []


def test_audit_event_v020_candidate_rejects_resolved_registry_without_version():
    event = valid_audit_v020_event()
    event["registry_version"] = None
    assert list(audit_v020_validator().iter_errors(event))


def test_audit_event_v020_candidate_rejects_unavailable_registry_with_version():
    event = valid_audit_v020_event()
    event["registry_status"] = "unavailable"
    event["event_type"] = "requested"
    event["result_status"] = "accepted"
    event["reason_code"] = None
    assert list(audit_v020_validator().iter_errors(event))


def test_audit_event_v020_candidate_rejects_unavailable_registry_authorization():
    event = valid_audit_v020_event()
    event["registry_status"] = "unavailable"
    event["registry_version"] = None
    event["event_type"] = "authorized"
    event["result_status"] = "success"
    event["reason_code"] = None
    assert list(audit_v020_validator().iter_errors(event))


def test_audit_event_v020_candidate_requires_registry_failure_reason():
    event = valid_audit_v020_event()
    event["registry_status"] = "unavailable"
    event["registry_version"] = None
    event["event_type"] = "policy_denied"
    event["result_status"] = "denied"
    event["reason_code"] = "POLICY_UNKNOWN_ACTION"
    assert list(audit_v020_validator().iter_errors(event))


def test_audit_event_v020_candidate_requires_registry_status():
    event = valid_audit_v020_event()
    del event["registry_status"]
    assert list(audit_v020_validator().iter_errors(event))

@pytest.mark.parametrize(
    "event_type,result_status,reason_code",
    [
        ("authorized", "success", None),
        ("started", "pending", None),
        ("succeeded", "success", None),
        ("failed", "failure", "EXECUTION_FAILED"),
        ("cancellation_requested", "pending", None),
        ("cancelled", "cancelled", None),
        ("outcome_unknown", "unknown", None),
        ("compensation_started", "pending", None),
        ("compensation_verified", "success", None),
        ("compensation_failed", "failure", "COMPENSATION_FAILED"),
        ("approval_granted", "success", None),
        ("approval_denied", "denied", "APPROVAL_DENIED"),
        ("approval_expired", "denied", "APPROVAL_EXPIRED"),
    ],
)
def test_audit_event_v020_candidate_rejects_all_post_request_events_without_registry(
    event_type, result_status, reason_code
):
    event = valid_audit_v020_event()
    event["registry_status"] = "unavailable"
    event["registry_version"] = None
    event["event_type"] = event_type
    event["result_status"] = result_status
    event["reason_code"] = reason_code
    assert list(audit_v020_validator().iter_errors(event))


AUDIT_V020_EVENT_STATUS_PAIRS = [
    ("requested", "accepted"),
    ("authorized", "success"),
    ("started", "pending"),
    ("succeeded", "success"),
    ("failed", "failure"),
    ("cancellation_requested", "accepted"),
    ("cancelled", "cancelled"),
    ("outcome_unknown", "unknown"),
    ("compensation_started", "pending"),
    ("compensation_verified", "success"),
    ("compensation_failed", "failure"),
    ("approval_granted", "accepted"),
    ("approval_denied", "denied"),
    ("approval_expired", "denied"),
    ("policy_denied", "denied"),
]


@pytest.mark.parametrize("event_type,result_status", AUDIT_V020_EVENT_STATUS_PAIRS)
def test_audit_event_v020_candidate_accepts_defined_lifecycle_status_pair(event_type, result_status):
    event = valid_audit_v020_event()
    event["event_type"] = event_type
    event["result_status"] = result_status
    if result_status in ("denied", "failure"):
        event["reason_code"] = "AUDIT_TEST_REASON"
    assert list(audit_v020_validator().iter_errors(event)) == []


@pytest.mark.parametrize("event_type,wrong_status", [
    ("requested", "success"),
    ("authorized", "denied"),
    ("started", "success"),
    ("succeeded", "failure"),
    ("failed", "success"),
    ("cancellation_requested", "cancelled"),
    ("cancelled", "success"),
    ("outcome_unknown", "failure"),
    ("compensation_started", "success"),
    ("compensation_verified", "failure"),
    ("compensation_failed", "success"),
    ("approval_granted", "denied"),
    ("approval_denied", "success"),
    ("approval_expired", "success"),
    ("policy_denied", "success"),
])
def test_audit_event_v020_candidate_rejects_inconsistent_lifecycle_status_pair(event_type, wrong_status):
    event = valid_audit_v020_event()
    event["event_type"] = event_type
    event["result_status"] = wrong_status
    event["reason_code"] = "AUDIT_TEST_REASON" if wrong_status in ("denied", "failure") else None
    assert list(audit_v020_validator().iter_errors(event))

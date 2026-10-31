import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
AUDIT_SCHEMA = json.loads((SCHEMA_DIR / "audit-event.schema.json").read_text())
APPROVAL_SCHEMA = json.loads((SCHEMA_DIR / "approval-request.schema.json").read_text())
POLICY_SCHEMA = json.loads((SCHEMA_DIR / "policy-decision.schema.json").read_text())
AUDIT_V020_SCHEMA = json.loads((SCHEMA_DIR / "audit-event-0.2.0.schema.json").read_text())
JCS_UNICODE_VECTORS = json.loads((ROOT / "JCS_UNICODE_TEST_VECTORS.json").read_text())

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


def policy_validator():
    return make_validator(POLICY_SCHEMA)


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


def test_audit_event_v020_package_transaction_correlation_pair_is_valid():
    event = valid_audit_v020_event()
    event["transaction_id"] = "pkg-txn-2026-00042"
    event["snapshot_digest"] = "sha256:" + "2" * 64
    assert list(audit_v020_validator().iter_errors(event)) == []


@pytest.mark.parametrize(
    "field,other",
    [("transaction_id", "snapshot_digest"), ("snapshot_digest", "transaction_id")],
)
def test_audit_event_v020_package_transaction_fields_must_be_paired(field, other):
    event = valid_audit_v020_event()
    event[field] = (
        "pkg-txn-2026-00042"
        if field == "transaction_id"
        else "sha256:" + "2" * 64
    )
    assert list(audit_v020_validator().iter_errors(event))


@pytest.mark.parametrize(
    "snapshot_digest",
    ["sha256:bad", "sha256:" + "G" * 64, "", None],
)
def test_audit_event_v020_package_snapshot_digest_must_be_sha256(snapshot_digest):
    event = valid_audit_v020_event()
    event["transaction_id"] = "pkg-txn-2026-00042"
    event["snapshot_digest"] = snapshot_digest
    assert list(audit_v020_validator().iter_errors(event))

def test_audit_event_v020_remote_origin_requires_device_and_session_bindings():
    event = valid_audit_v020_event()
    event["origin"] = "remote"
    assert list(audit_v020_validator().iter_errors(event))


def test_audit_event_v020_remote_origin_accepts_both_binding_digests():
    event = valid_audit_v020_event()
    event["origin"] = "remote"
    event["device_binding"] = "sha256:" + "a" * 64
    event["session_binding"] = "sha256:" + "b" * 64
    assert list(audit_v020_validator().iter_errors(event)) == []


@pytest.mark.parametrize("field", ["device_binding", "session_binding"])
def test_audit_event_v020_remote_origin_requires_each_binding(field):
    event = valid_audit_v020_event()
    event["origin"] = "remote"
    event["device_binding"] = "sha256:" + "a" * 64
    event["session_binding"] = "sha256:" + "b" * 64
    del event[field]
    assert list(audit_v020_validator().iter_errors(event))


@pytest.mark.parametrize(
    "value",
    [
        "",
        "sha256:" + "A" * 64,
        "sha256:" + "g" * 64,
        "sha256:" + "a" * 63,
        None,
        42,
        {},
    ],
)
@pytest.mark.parametrize("field", ["device_binding", "session_binding"])
def test_audit_event_v020_remote_binding_digest_format_is_strict(field, value):
    event = valid_audit_v020_event()
    event["origin"] = "remote"
    event["device_binding"] = "sha256:" + "a" * 64
    event["session_binding"] = "sha256:" + "b" * 64
    event[field] = value
    assert list(audit_v020_validator().iter_errors(event))


@pytest.mark.parametrize("field", ["device_binding", "session_binding"])
def test_audit_event_v020_non_remote_origin_rejects_remote_bindings(field):
    event = valid_audit_v020_event()
    event[field] = "sha256:" + "a" * 64
    assert list(audit_v020_validator().iter_errors(event))


@pytest.mark.parametrize(
    "field",
    [
        "device_id",
        "session_id",
        "device_public_key",
        "session_token",
        "authorization",
        "signature",
        "pairing_secret",
        "private_key",
        "task_payload",
        "prompt",
        "completion",
    ],
)
def test_audit_event_v020_rejects_raw_remote_identity_credentials_and_payloads(field):
    event = valid_audit_v020_event()
    event["origin"] = "remote"
    event["device_binding"] = "sha256:" + "a" * 64
    event["session_binding"] = "sha256:" + "b" * 64
    event[field] = "must-not-enter-general-audit"
    assert list(audit_v020_validator().iter_errors(event))


VALID_ALLOW_DECISION = {
    "schema_version": "0.1.0",
    "decision_id": "123e4567-e89b-12d3-a456-426614174020",
    "proposal_id": "123e4567-e89b-12d3-a456-426614174021",
    "decision": "ALLOW",
    "reason_code": "POLICY_ALLOWED",
    "risk_class": "R2",
    "policy_version": "0.1.0",
    "action_digest": "sha256:" + "2" * 64,
    "principal_binding": "sha256:" + "3" * 64,
    "evaluated_at": "2026-10-31T00:00:00Z",
    "constraints": {},
    "expires_at": "2026-10-31T00:02:00Z",
    "approval_request_id": None,
    "authorization_ref": "opaque-authorization-reference",
}


def test_policy_decision_constraints_schema_is_explicitly_closed_and_empty_only():
    constraint_schema = POLICY_SCHEMA["properties"]["constraints"]
    assert constraint_schema["type"] == "object"
    assert constraint_schema["maxProperties"] == 0
    assert constraint_schema["additionalProperties"] is False


def test_policy_decision_constraints_must_be_present_and_empty():
    decision = dict(VALID_ALLOW_DECISION)
    assert list(policy_validator().iter_errors(decision)) == []
    del decision["constraints"]
    assert list(policy_validator().iter_errors(decision))


@pytest.mark.parametrize("constraints", [None, [], "system:*", 0, {"unknown": True}, {"timeout_ms": 1000}, {"resource_scope": ["system:*"]}])
def test_policy_decision_rejects_non_empty_or_non_object_constraints(constraints):
    decision = dict(VALID_ALLOW_DECISION)
    decision["constraints"] = constraints
    assert list(policy_validator().iter_errors(decision))


def test_policy_decision_allow_requires_expiry_and_authorization_reference():
    assert list(policy_validator().iter_errors(VALID_ALLOW_DECISION)) == []
    for field in ("expires_at", "authorization_ref"):
        decision = dict(VALID_ALLOW_DECISION)
        decision[field] = None
        assert list(policy_validator().iter_errors(decision))


def test_policy_decision_allow_rejects_missing_authorization_reference():
    decision = dict(VALID_ALLOW_DECISION)
    del decision["authorization_ref"]
    assert list(policy_validator().iter_errors(decision))


def test_policy_decision_require_approval_requires_request_and_has_no_grant():
    decision = dict(VALID_ALLOW_DECISION)
    decision.update(
        decision="REQUIRE_APPROVAL",
        expires_at=None,
        approval_request_id="123e4567-e89b-12d3-a456-426614174022",
        authorization_ref=None,
    )
    assert list(policy_validator().iter_errors(decision)) == []


def test_policy_decision_require_approval_rejects_missing_request_id():
    decision = dict(VALID_ALLOW_DECISION)
    decision.update(
        decision="REQUIRE_APPROVAL",
        expires_at=None,
        approval_request_id=None,
        authorization_ref=None,
    )
    assert list(policy_validator().iter_errors(decision))


def test_policy_decision_require_approval_rejects_grant_reference():
    decision = dict(VALID_ALLOW_DECISION)
    decision.update(
        decision="REQUIRE_APPROVAL",
        expires_at=None,
        approval_request_id="123e4567-e89b-12d3-a456-426614174022",
    )
    assert list(policy_validator().iter_errors(decision))


def test_policy_decision_deny_has_no_expiry_approval_or_authorization():
    decision = dict(VALID_ALLOW_DECISION)
    decision.update(
        decision="DENY",
        expires_at=None,
        approval_request_id=None,
        authorization_ref=None,
    )
    assert list(policy_validator().iter_errors(decision)) == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("expires_at", "2026-10-31T00:02:00Z"),
        ("approval_request_id", "123e4567-e89b-12d3-a456-426614174022"),
        ("authorization_ref", "caller-supplied-grant"),
    ],
)
def test_policy_decision_deny_rejects_authority_bearing_fields(field, value):
    decision = dict(VALID_ALLOW_DECISION)
    decision.update(
        decision="DENY",
        expires_at=None,
        approval_request_id=None,
        authorization_ref=None,
    )
    decision[field] = value
    assert list(policy_validator().iter_errors(decision))


def test_policy_decision_rejects_unknown_top_level_authority_claims():
    decision = dict(VALID_ALLOW_DECISION, caller_principal="root")
    assert list(policy_validator().iter_errors(decision))

# Public proposal JSON is untrusted. Authentication, origin and authorization
# are injected by trusted adapters/services and cannot be caller assertions.
def action_proposal_validator():
    schema = json.loads((SCHEMA_DIR / "action-proposal.schema.json").read_text())
    return make_validator(schema)


def valid_action_proposal():
    return {
        "schema_version": "0.1.0",
        "action_id": "system.settings.update",
        "proposal_id": "123e4567-e89b-12d3-a456-426614174020",
        "task_id": "task-123",
        "step_id": "step-456",
        "arguments": {"setting": "theme", "value": "dark"},
        "resources": [{"kind": "setting", "id": "theme", "access": "modify"}],
        "idempotency_key": "0123456789abcdef",
        "requested_at": "2026-10-31T00:00:00Z",
    }


def test_action_proposal_with_minimum_typed_fields_is_valid():
    assert list(action_proposal_validator().iter_errors(valid_action_proposal())) == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("principal", "root"),
        ("origin", "system"),
        ("decision", "ALLOW"),
        ("authorization_ref", "caller-forged-grant"),
        ("authorization_context", {"principal": "root", "decision": "ALLOW"}),
        ("approval_granted", True),
        ("risk_class", "R0"),
    ],
)
def test_action_proposal_rejects_caller_supplied_authority_fields(field, value):
    proposal = valid_action_proposal()
    proposal[field] = value
    assert list(action_proposal_validator().iter_errors(proposal))


def test_action_proposal_rejects_unknown_resource_authority_fields():
    proposal = valid_action_proposal()
    proposal["resources"][0]["principal"] = "root"
    assert list(action_proposal_validator().iter_errors(proposal))



def test_jcs_unicode_reference_vectors_preserve_exact_code_points():
    # These string-only fixtures pin the RFC 8785 Unicode-preservation rule.
    # This checks fixture serialization, not a production runtime canonicalizer.
    encoded_vectors = []
    for vector in JCS_UNICODE_VECTORS["cases"]:
        canonical = json.dumps(
            vector["input"],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        canonical_bytes = canonical.encode("utf-8")
        assert canonical_bytes.hex() == vector["canonical_utf8_hex"]
        assert "sha256:" + hashlib.sha256(canonical_bytes).hexdigest() == vector["sha256"]
        encoded_vectors.append(canonical_bytes)

    # NFC- and NFD-equivalent text remains byte-distinct under JCS.
    assert encoded_vectors[0] != encoded_vectors[1]
    assert JCS_UNICODE_VECTORS["cases"][0]["sha256"] != JCS_UNICODE_VECTORS["cases"][1]["sha256"]

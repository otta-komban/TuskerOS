from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import uuid
import pytest
from security.runtime.canonical import CanonicalizationError, canonical_bytes, digest
from security.runtime.policy import PolicyEngine
from security.runtime.store import SecurityStore

NOW = datetime(2026, 10, 31, 6, 0, tzinfo=timezone.utc)
D1, D2, D3, D4 = ["sha256:" + c * 64 for c in "1234"]
KEY = b"test-only-audit-key-material-32-bytes!!"
BINDING = {"session_binding": D2, "device_binding": D3, "registry_version": "registry-1",
           "resource_scope": ["disk:wwn-123"], "precondition_digest": D4}

def audit():
    return {"timestamp_utc": NOW.isoformat().replace("+00:00", "Z"), "event_type": "requested",
            "principal_binding": D1, "origin": "local", "proposal_id": str(uuid.uuid4()),
            "decision_id": str(uuid.uuid4()), "operation_id": "broker.disk.erase", "risk_class": "R3",
            "policy_version": "policy-1", "action_digest": D4, "result_status": "accepted",
            "correlation_id": str(uuid.uuid4()), "task_id": "task-1", "step_id": "step-1",
            "registry_version": "registry-1", "executor_id": None, "reason_code": None,
            "registry_status": "resolved"}

def peer(credentials):
    if credentials != {"uid": 1000, "pid": 42}: raise PermissionError
    return {"authenticated": True, "principal_binding": D1, "session_binding": D2, "device_binding": D3}

def store(path=":memory:"):
    return SecurityStore(path, audit_key=KEY, peer_authenticator=peer,
        approver_authenticator=lambda c, r: c == {"uid": 1000},
        policy_rechecker=lambda r, b, v: b == BINDING and v == "policy-1")

def approval(db):
    return db.create_approval(action_id="system.disk.erase", broker_operation_id="broker.disk.erase",
        action_digest=D4, proposal_id=str(uuid.uuid4()), principal_binding=D1,
        policy_version="policy-1", risk_class="R3", task_id="task-1", step_id="step-1",
        binding=BINDING, expires_at=NOW + timedelta(minutes=2), audit_context=audit(), now=NOW)

def decide_and_issue(db):
    rid = approval(db)
    assert db.decide(rid, approve=True, current_binding=BINDING, approver_credentials={"uid": 1000},
                     audit_context=audit(), now=NOW) == "APPROVED"
    return db.issue_authorization(rid, current_binding=BINDING, current_policy_version="policy-1",
                                  audit_context=audit(), now=NOW)

def consume(db, ref, **changes):
    args = dict(operation_id="broker.disk.erase", resource_scope=["disk:wwn-123"], action_digest=D4,
        policy_version="policy-1", registry_version="registry-1", precondition_digest=D4,
        peer_credentials={"uid": 1000, "pid": 42}, audit_context=audit(), now=NOW)
    args.update(changes)
    return db.consume(ref, **args)

def test_jcs_unicode_vectors_and_reject_invalid_subset():
    assert canonical_bytes({"name": "é"}).hex() == "7b226e616d65223a22c3a9227d"
    assert digest({"name": "é"}) == "sha256:2f16b8477146a1b2ba7d6bb7cf7c9979c191cc2838a107dbf5f0d920b4cb3ba1"
    assert digest({"name": "é"}) == "sha256:6a547588c4055916e090ed61467326046dd52810679d03bfb84d862a7123522e"
    with pytest.raises(CanonicalizationError): canonical_bytes({"x": "\ud800"})
    with pytest.raises(CanonicalizationError): canonical_bytes({"x": 0.5})

def test_policy_deny_default_allow_read_require_approval_and_deny_r5():
    proposal = {"schema_version": "0.1.0", "action_id": "system.info.read", "proposal_id": str(uuid.uuid4()),
        "task_id": "t1", "step_id": "s1", "arguments": {},
        "resources": [{"kind": "system", "id": "host", "access": "read"}], "requested_at": NOW.isoformat()}
    context = {"authenticated": True, "principal_binding": D1, "session_binding": D2,
        "device_binding": D3, "origin": "local", "principal_class": "user"}
    engine = PolicyEngine("policy-1", identity_verifier=lambda c: c.get("authenticated") is True,
        registry_verifier=lambda r, v: bool(r) and v == "registry-1", argument_validator=lambda a, x: True,
        resource_resolver=lambda r: list(r), precondition_verifier=lambda p, r: D4)
    assert engine.evaluate(proposal, context, [], "registry-1").status == "DENY"
    reg = {"schema_version": "0.1.0", "action_id": "system.info.read", "operation_schema_version": "1.0.0",
        "allowed_origins": ["local"], "allowed_principal_classes": ["user"],
        "resources": [{"kind": "system", "access_modes": ["read"]}], "minimum_risk_class": "R0",
        "approval_mode": "never", "broker_operation_id": "broker.system.info.read", "timeout_ms": 1000,
        "idempotency": "optional_read_only"}
    assert engine.evaluate(proposal, context, [reg], "registry-1").status == "ALLOW"
    reg.update(minimum_risk_class="R3", approval_mode="always")
    assert engine.evaluate(proposal, context, [reg], "registry-1").status == "REQUIRE_APPROVAL"
    reg.update(minimum_risk_class="R5", approval_mode="out_of_band_admin")
    assert engine.evaluate(proposal, context, [reg], "registry-1").status == "DENY"
    reg.update(minimum_risk_class="R0", approval_mode="never", idempotency="required")
    proposal["idempotency_key"] = "i" * 16
    proposal["resources"][0]["access"] = "modify"
    reg["resources"][0]["access_modes"] = ["read", "modify"]
    assert engine.evaluate(proposal, context, [reg], "registry-1").risk_class == "R3"
    assert engine.evaluate(proposal, context, [reg], "registry-1").status == "REQUIRE_APPROVAL"

    # Executable resources are elevated to R4, not ordinary mutation R3.
    proposal["resources"][0]["access"] = "execute"
    reg["resources"][0]["access_modes"] = ["read", "modify", "execute"]
    decision = engine.evaluate(proposal, context, [reg], "registry-1")
    assert decision.status == "REQUIRE_APPROVAL"
    assert decision.risk_class == "R4"


@pytest.mark.parametrize("resource_declarations", [
    [{"kind": "system", "access_modes": ["read"]},
     {"kind": "system", "access_modes": ["read", "modify"]}],
    [{"kind": "system", "access_modes": ["read", "execute", "execute"]}],
    [{"kind": "system", "access_modes": ["read", "shell"]}],
    [{"kind": "system", "access_modes": []}],
    [{"kind": "system", "access_modes": ["read"], "unexpected": True}],
])
def test_malformed_or_ambiguous_registry_resource_policy_is_denied(resource_declarations):
    proposal = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "proposal_id": str(uuid.uuid4()), "task_id": "t1", "step_id": "s1",
        "arguments": {}, "resources": [{"kind": "system", "id": "host", "access": "read"}],
        "requested_at": NOW.isoformat()}
    context = {"authenticated": True, "principal_binding": D1, "session_binding": D2,
        "device_binding": D3, "origin": "local", "principal_class": "user"}
    registry = [{"schema_version": "0.1.0", "action_id": "system.info.read",
        "operation_schema_version": "1.0.0", "allowed_origins": ["local"],
        "allowed_principal_classes": ["user"], "resources": resource_declarations,
        "minimum_risk_class": "R0", "approval_mode": "never",
        "broker_operation_id": "broker.system.info.read", "timeout_ms": 1000,
        "idempotency": "optional_read_only"}]
    engine = PolicyEngine("policy-1", identity_verifier=lambda c: True,
        registry_verifier=lambda r, v: True, argument_validator=lambda a, x: True,
        resource_resolver=lambda resources: list(resources),
        precondition_verifier=lambda p, r: D4)
    decision = engine.evaluate(proposal, context, registry, "registry-1")
    assert decision.status == "DENY"
    assert decision.reason_code == "POLICY_REGISTRY_INVALID"


@pytest.mark.parametrize("field,value", [
    ("allowed_origins", []),
    ("allowed_origins", ["local", "local"]),
    ("allowed_origins", ["local", "untrusted"]),
    ("allowed_origins", ["local", 7]),
    ("allowed_principal_classes", []),
    ("allowed_principal_classes", ["user", "user"]),
    ("allowed_principal_classes", ["user", "x" * 65]),
    ("allowed_principal_classes", ["user", None]),
])
def test_malformed_registry_identity_scope_is_denied(field, value):
    proposal = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "proposal_id": str(uuid.uuid4()), "task_id": "t1", "step_id": "s1",
        "arguments": {}, "resources": [{"kind": "system", "id": "host", "access": "read"}],
        "requested_at": NOW.isoformat()}
    context = {"authenticated": True, "principal_binding": D1, "session_binding": D2,
        "device_binding": D3, "origin": "local", "principal_class": "user"}
    entry = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "operation_schema_version": "1.0.0", "allowed_origins": ["local"],
        "allowed_principal_classes": ["user"],
        "resources": [{"kind": "system", "access_modes": ["read"]}],
        "minimum_risk_class": "R0", "approval_mode": "never",
        "broker_operation_id": "broker.system.info.read", "timeout_ms": 1000,
        "idempotency": "optional_read_only"}
    entry[field] = value
    engine = PolicyEngine("policy-1", identity_verifier=lambda c: True,
        registry_verifier=lambda r, v: True, argument_validator=lambda a, x: True,
        resource_resolver=lambda resources: list(resources),
        precondition_verifier=lambda p, r: D4)
    decision = engine.evaluate(proposal, context, [entry], "registry-1")
    assert decision.status == "DENY"
    assert decision.reason_code == "POLICY_REGISTRY_INVALID"


@pytest.mark.parametrize("principal_class", ["", "x" * 65, None, 7])
def test_malformed_authenticated_principal_class_is_denied(principal_class):
    proposal = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "proposal_id": str(uuid.uuid4()), "task_id": "t1", "step_id": "s1",
        "arguments": {}, "resources": [{"kind": "system", "id": "host", "access": "read"}],
        "requested_at": NOW.isoformat()}
    context = {"authenticated": True, "principal_binding": D1, "session_binding": D2,
        "device_binding": D3, "origin": "local", "principal_class": principal_class}
    registry = [{"schema_version": "0.1.0", "action_id": "system.info.read",
        "operation_schema_version": "1.0.0", "allowed_origins": ["local"],
        "allowed_principal_classes": ["user"],
        "resources": [{"kind": "system", "access_modes": ["read"]}],
        "minimum_risk_class": "R0", "approval_mode": "never",
        "broker_operation_id": "broker.system.info.read", "timeout_ms": 1000,
        "idempotency": "optional_read_only"}]
    engine = PolicyEngine("policy-1", identity_verifier=lambda c: True,
        registry_verifier=lambda r, v: True, argument_validator=lambda a, x: True,
        resource_resolver=lambda resources: list(resources),
        precondition_verifier=lambda p, r: D4)
    decision = engine.evaluate(proposal, context, registry, "registry-1")
    assert decision.status == "DENY"
    assert decision.reason_code == "POLICY_UNKNOWN_PRINCIPAL"


def test_resource_resolver_cannot_drop_add_or_widen_resources():
    proposal = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "proposal_id": str(uuid.uuid4()), "task_id": "t1", "step_id": "s1",
        "arguments": {}, "resources": [{"kind": "system", "id": "host", "access": "read"}],
        "requested_at": NOW.isoformat()}
    context = {"authenticated": True, "principal_binding": D1, "session_binding": D2,
        "device_binding": D3, "origin": "local", "principal_class": "user"}
    registry = [{"schema_version": "0.1.0", "action_id": "system.info.read",
        "operation_schema_version": "1.0.0", "allowed_origins": ["local"],
        "allowed_principal_classes": ["user"],
        "resources": [{"kind": "system", "access_modes": ["read"]}],
        "minimum_risk_class": "R0", "approval_mode": "never",
        "broker_operation_id": "broker.system.info.read", "timeout_ms": 1000,
        "idempotency": "optional_read_only"}]
    def evaluate_with(resolver):
        engine = PolicyEngine("policy-1", identity_verifier=lambda c: c.get("authenticated") is True,
            registry_verifier=lambda r, v: bool(r) and v == "registry-1",
            argument_validator=lambda a, x: True, resource_resolver=resolver,
            precondition_verifier=lambda p, r: D4)
        return engine.evaluate(proposal, context, registry, "registry-1")
    assert evaluate_with(lambda resources: []).reason_code == "POLICY_RESOURCE_RESOLUTION_MISMATCH"
    assert evaluate_with(lambda resources: resources + [{"kind":"system","id":"other","access":"read"}]).reason_code == "POLICY_RESOURCE_RESOLUTION_MISMATCH"
    assert evaluate_with(lambda resources: [{"kind":"system","id":"host","access":"modify"}]).reason_code == "POLICY_RESOURCE_RESOLUTION_MISMATCH"


def test_action_digest_binds_original_and_resolved_resource_identifiers():
    proposal = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "proposal_id": str(uuid.uuid4()), "task_id": "t1", "step_id": "s1",
        "arguments": {}, "resources": [{"kind": "system", "id": "alias-a", "access": "read"}],
        "requested_at": NOW.isoformat()}
    context = {"authenticated": True, "principal_binding": D1, "session_binding": D2,
        "device_binding": D3, "origin": "local", "principal_class": "user"}
    registry = [{"schema_version": "0.1.0", "action_id": "system.info.read",
        "operation_schema_version": "1.0.0", "allowed_origins": ["local"],
        "allowed_principal_classes": ["user"],
        "resources": [{"kind": "system", "access_modes": ["read"]}],
        "minimum_risk_class": "R0", "approval_mode": "never",
        "broker_operation_id": "broker.system.info.read", "timeout_ms": 1000,
        "idempotency": "optional_read_only"}]
    engine = PolicyEngine("policy-1", identity_verifier=lambda c: c.get("authenticated") is True,
        registry_verifier=lambda r, v: bool(r) and v == "registry-1",
        argument_validator=lambda a, x: True,
        resource_resolver=lambda resources: [{"kind":"system","id":"canonical-host","access":"read"}],
        precondition_verifier=lambda p, r: D4)
    first = engine.evaluate(proposal, context, registry, "registry-1")
    proposal["resources"][0]["id"] = "alias-b"
    second = engine.evaluate(proposal, context, registry, "registry-1")
    assert first.status == second.status == "ALLOW"
    assert first.action_digest != second.action_digest

def test_atomic_consume_replay_and_authenticated_reconciliation():
    db = store()
    try:
        ref = decide_and_issue(db)
        first, replay = (consume(db, ref), consume(db, ref))
        assert first.outcome == "CONSUMED" and replay.outcome == "ALREADY_CONSUMED"
        assert replay.consumption_id == first.consumption_id
        assert db.reconcile(ref, peer_credentials={"uid": 1000, "pid": 42}).consumption_id == first.consumption_id
        assert db.verify_audit_chain()
    finally: db.close()

def test_expired_approval_stale_resource_and_wrong_operation_are_denied():
    db = store()
    try:
        rid = approval(db)
        assert db.decide(rid, approve=True, current_binding=BINDING, approver_credentials={"uid": 1000},
            audit_context=audit(), now=NOW + timedelta(minutes=2)) == "EXPIRED"
        ref = decide_and_issue(db)
        assert consume(db, ref, resource_scope=["disk:other"]).outcome == "BINDING_MISMATCH"
        ref = decide_and_issue(db)
        assert consume(db, ref, operation_id="broker.other.op").outcome == "BINDING_MISMATCH"
    finally: db.close()

def test_confused_deputy_wrong_peer_and_approval_id_are_denied():
    db = store()
    try:
        rid = approval(db)
        assert consume(db, rid).outcome == "BINDING_MISMATCH"
        ref = decide_and_issue(db)
        assert consume(db, ref, peer_credentials={"uid": 999}).outcome == "CALLER_UNAUTHORIZED"
    finally: db.close()

def test_policy_version_change_and_approver_authentication_fail_closed():
    db = store()
    try:
        rid = approval(db)
        assert db.decide(rid, approve=True, current_binding=BINDING, approver_credentials={"uid": 999},
            audit_context=audit(), now=NOW) == "CALLER_UNAUTHORIZED"
        ref = decide_and_issue(db)
        assert consume(db, ref, policy_version="policy-2").outcome == "BINDING_MISMATCH"
    finally: db.close()

def test_audit_failure_rolls_back_consume_and_redacts_payloads():
    db = store()
    try:
        ref = decide_and_issue(db)
        db._db.execute("CREATE TRIGGER fail_audit BEFORE INSERT ON audit_events BEGIN SELECT RAISE(ABORT, 'disk full'); END")
        assert consume(db, ref).outcome == "AUDIT_UNAVAILABLE"
        assert db.reconcile(ref, peer_credentials={"uid": 1000, "pid": 42}).outcome == "ISSUED"
    finally: db.close()

def test_hmac_audit_detects_tampering_and_remote_identity_is_required():
    db = store()
    try:
        event = audit(); event["email"] = "alice@example.com"; event["message"] = "Bearer abc.def.ghi"
        db._audit(event)
        assert "alice@example.com" not in str(db.audit_events()) and "abc.def.ghi" not in str(db.audit_events())
        assert db.verify_audit_chain()
        db._db.execute("UPDATE audit_events SET event_json=? WHERE seq=1", (b'{"tampered":true}',))
        assert not db.verify_audit_chain()
        remote = audit(); remote["origin"] = "remote"
        with pytest.raises(Exception): db._audit(remote)
        remote["device_binding"], remote["session_binding"] = D3, D2
        db._audit(remote)
    finally: db.close()

def test_two_concurrent_consumers_have_one_winner(tmp_path):
    path = str(tmp_path / "security.sqlite")
    db = store(path); ref = decide_and_issue(db); db.close()
    def attempt(_):
        conn = store(path)
        try: return consume(conn, ref).outcome
        finally: conn.close()
    with ThreadPoolExecutor(max_workers=2) as pool: outcomes = list(pool.map(attempt, range(2)))
    assert outcomes.count("CONSUMED") == 1 and outcomes.count("ALREADY_CONSUMED") == 1


def test_external_audit_checkpoint_detects_rollback_and_invalid_checkpoint():
    db = store()
    try:
        db._audit(audit())
        db._audit(audit())
        checkpoint = db.audit_checkpoint()
        db._audit(audit())
        assert db.verify_audit_chain(checkpoint)
        tampered = dict(checkpoint); tampered["sequence"] = 999
        assert not db.verify_audit_chain(tampered)
        db._db.execute("DELETE FROM audit_events WHERE seq > 1")
        assert not db.verify_audit_chain(checkpoint)
    finally: db.close()

def test_broker_gate_returns_a_narrow_grant_only_after_consume():
    from security.runtime.broker import BrokerAuthorizationGate, BrokerAuthorizationRequest
    db = store()
    try:
        ref = decide_and_issue(db)
        request = BrokerAuthorizationRequest(ref, "broker.disk.erase", D4, "policy-1", ("disk:wwn-123",),
                                             "registry-1", D4, {"uid": 1000, "pid": 42})
        result = BrokerAuthorizationGate(db).authorize(request, audit(), now=NOW)
        assert result.outcome == "CONSUMED"
        assert set(result.grant) == {"consumption_id", "operation_id", "resource_scope", "principal_binding",
                                     "session_binding", "device_binding", "action_digest", "registry_version",
                                     "precondition_digest"}
    finally: db.close()
def test_reconciliation_is_bound_to_original_principal_session_and_device():
    db = store()
    try:
        ref = decide_and_issue(db)
        first = consume(db, ref)
        assert first.outcome == "CONSUMED"
        mismatches = [
            {"authenticated": True, "principal_binding": D4, "session_binding": D2, "device_binding": D3},
            {"authenticated": True, "principal_binding": D1, "session_binding": D4, "device_binding": D3},
            {"authenticated": True, "principal_binding": D1, "session_binding": D2, "device_binding": D4},
        ]
        for identity in mismatches:
            db._peer_authenticator = lambda _credentials, identity=identity: identity
            result = db.reconcile(ref, peer_credentials={"uid": 1000, "pid": 42})
            assert result.outcome == "CALLER_UNAUTHORIZED"
            assert result.consumption_id is None
        db._peer_authenticator = peer
        legitimate = db.reconcile(ref, peer_credentials={"uid": 1000, "pid": 42})
        assert legitimate.outcome == "ALREADY_CONSUMED"
        assert legitimate.consumption_id == first.consumption_id
    finally:
        db.close()


def test_consumed_replay_disclosure_is_bound_to_original_peer_identity():
    db = store()
    try:
        ref = decide_and_issue(db)
        first = consume(db, ref)
        assert first.outcome == "CONSUMED"
        mismatches = [
            {"authenticated": True, "principal_binding": D4, "session_binding": D2, "device_binding": D3},
            {"authenticated": True, "principal_binding": D1, "session_binding": D4, "device_binding": D3},
            {"authenticated": True, "principal_binding": D1, "session_binding": D2, "device_binding": D4},
        ]
        for identity in mismatches:
            db._peer_authenticator = lambda _credentials, identity=identity: identity
            replay = consume(db, ref)
            assert replay.outcome == "CALLER_UNAUTHORIZED"
            assert replay.consumption_id is None
        db._peer_authenticator = peer
        legitimate_replay = consume(db, ref)
        assert legitimate_replay.outcome == "ALREADY_CONSUMED"
        assert legitimate_replay.consumption_id == first.consumption_id
    finally:
        db.close()


def test_resource_resolver_cannot_return_oversized_canonical_identifier():
    proposal = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "proposal_id": str(uuid.uuid4()), "task_id": "t1", "step_id": "s1",
        "arguments": {}, "resources": [{"kind": "system", "id": "host", "access": "read"}],
        "requested_at": NOW.isoformat()}
    context = {"authenticated": True, "principal_binding": D1, "session_binding": D2,
        "device_binding": D3, "origin": "local", "principal_class": "user"}
    registry = [{"schema_version": "0.1.0", "action_id": "system.info.read",
        "operation_schema_version": "1.0.0", "allowed_origins": ["local"],
        "allowed_principal_classes": ["user"],
        "resources": [{"kind": "system", "access_modes": ["read"]}],
        "minimum_risk_class": "R0", "approval_mode": "never",
        "broker_operation_id": "broker.system.info.read", "timeout_ms": 1000,
        "idempotency": "optional_read_only"}]
    engine = PolicyEngine("policy-1", identity_verifier=lambda c: c.get("authenticated") is True,
        registry_verifier=lambda r, v: bool(r) and v == "registry-1",
        argument_validator=lambda a, x: True,
        resource_resolver=lambda resources: [{"kind": "system", "id": "x" * 1025, "access": "read"}],
        precondition_verifier=lambda p, r: D4)
    result = engine.evaluate(proposal, context, registry, "registry-1")
    assert result.status == "DENY"
    assert result.reason_code == "POLICY_RESOURCE_RESOLUTION_MISMATCH"

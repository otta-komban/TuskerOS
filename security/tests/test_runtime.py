from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import uuid
import pytest
from security.runtime.canonical import CanonicalizationError, canonical_bytes, digest
from security.runtime.policy import PolicyEngine
from security.runtime.store import SecurityStore, SecurityStoreError

NOW = datetime(2026, 10, 31, 6, 0, tzinfo=timezone.utc)
D1, D2, D3, D4 = ["sha256:" + c * 64 for c in "1234"]
KEY = b"test-only-audit-key-material-32-bytes!!"
BINDING = {"session_binding": D2, "device_binding": D3, "registry_version": "registry-1",
           "resource_scope": ["disk:wwn-123"], "precondition_digest": D4}

def audit(**overrides):
    event = {"timestamp_utc": NOW.isoformat().replace("+00:00", "Z"), "event_type": "requested",
             "principal_binding": D1, "origin": "local", "proposal_id": str(uuid.uuid4()),
             "decision_id": str(uuid.uuid4()), "operation_id": "broker.disk.erase", "risk_class": "R3",
             "policy_version": "policy-1", "action_digest": D4, "result_status": "accepted",
             "correlation_id": str(uuid.uuid4()), "task_id": "task-1", "step_id": "step-1",
             "registry_version": "registry-1", "executor_id": None, "reason_code": None,
             "registry_status": "resolved"}
    event.update(overrides)
    return event

def peer(credentials):
    if credentials != {"uid": 1000, "pid": 42}: raise PermissionError
    return {"authenticated": True, "principal_binding": D1, "session_binding": D2, "device_binding": D3, "origin": "local"}

def store(path=":memory:"):
    return SecurityStore(path, audit_key=KEY, peer_authenticator=peer,
        approver_authenticator=lambda c, r: c == {"uid": 1000},
        policy_rechecker=lambda r, b, v: b == BINDING and v == "policy-1")

def approval(db):
    proposal_id = str(uuid.uuid4())
    return db.create_approval(action_id="system.disk.erase", broker_operation_id="broker.disk.erase",
        action_digest=D4, proposal_id=proposal_id, principal_binding=D1,
        policy_version="policy-1", risk_class="R3", task_id="task-1", step_id="step-1",
        binding=BINDING, expires_at=NOW + timedelta(minutes=2),
        audit_context=audit(proposal_id=proposal_id), now=NOW)

def audit_for_approval(db, rid):
    row = db._db.execute("SELECT * FROM approvals WHERE request_id=?", (rid,)).fetchone()
    binding = __import__("json").loads(bytes(row["binding_json"]).decode("utf-8"))
    return audit(principal_binding=row["principal_binding"], proposal_id=row["proposal_id"],
        operation_id=row["broker_operation_id"], risk_class=row["risk_class"],
        policy_version=row["policy_version"], action_digest=row["action_digest"],
        task_id=row["task_id"], step_id=row["step_id"], registry_version=binding["registry_version"])


def decide_and_issue(db):
    rid = approval(db)
    assert db.decide(rid, approve=True, current_binding=BINDING, approver_credentials={"uid": 1000},
                     audit_context=audit_for_approval(db, rid), now=NOW) == "APPROVED"
    return db.issue_authorization(rid, current_binding=BINDING, current_policy_version="policy-1",
                                  audit_context=audit_for_approval(db, rid), now=NOW)

def audit_for_ref(db, ref):
    try:
        token_hash = __import__("hashlib").sha256(ref.encode("utf-8", "strict")).hexdigest()
    except UnicodeEncodeError:
        return audit()
    row = db._db.execute("""SELECT a.*, r.state AS ref_state FROM auth_refs r
        JOIN approvals a ON a.request_id=r.request_id WHERE r.token_hash=?""", (token_hash,)).fetchone()
    # Invalid/oversized references intentionally have no row; the consume
    # method rejects them before audit-context validation.
    if row is None:
        return audit()
    binding = __import__("json").loads(bytes(row["binding_json"]).decode("utf-8"))
    return audit(principal_binding=row["principal_binding"], proposal_id=row["proposal_id"],
        operation_id=row["broker_operation_id"], risk_class=row["risk_class"],
        policy_version=row["policy_version"], action_digest=row["action_digest"],
        task_id=row["task_id"], step_id=row["step_id"],
        registry_version=binding["registry_version"])

def consume(db, ref, **changes):
    args = dict(operation_id="broker.disk.erase", resource_scope=["disk:wwn-123"], action_digest=D4,
        policy_version="policy-1", registry_version="registry-1", precondition_digest=D4,
        peer_credentials={"uid": 1000, "pid": 42}, audit_context=audit_for_ref(db, ref), now=NOW)
    args.update(changes)
    return db.consume(ref, **args)

@pytest.mark.parametrize("field,value", [
    ("principal_binding", D4), ("proposal_id", str(uuid.uuid4())),
    ("operation_id", "broker.other.op"), ("risk_class", "R4"),
    ("policy_version", "policy-2"), ("action_digest", D3),
    ("task_id", "other-task"), ("step_id", "other-step"),
    ("registry_version", "registry-2"), ("registry_status", "unavailable"),
])
def test_create_approval_rejects_mismatched_audit_context(field, value):
    db = store()
    try:
        proposal_id = str(uuid.uuid4())
        context = audit(proposal_id=proposal_id)
        context[field] = value
        with pytest.raises(SecurityStoreError, match="audit context"):
            db.create_approval(action_id="system.disk.erase", broker_operation_id="broker.disk.erase",
                action_digest=D4, proposal_id=proposal_id, principal_binding=D1,
                policy_version="policy-1", risk_class="R3", task_id="task-1", step_id="step-1",
                binding=BINDING, expires_at=NOW + timedelta(minutes=2), audit_context=context, now=NOW)
        assert db._db.execute("SELECT COUNT(*) FROM approvals").fetchone()[0] == 0
        assert db.audit_events() == []
    finally:
        db.close()


def test_policy_rechecker_cannot_mutate_authoritative_approval_bindings():
    import copy

    seen = []

    def mutating_rechecker(request_id, binding, policy_version):
        seen.append(request_id)
        binding.clear()
        binding["resource_scope"] = ["disk:attacker-selected"]
        return True

    db = SecurityStore(":memory:", audit_key=KEY, peer_authenticator=peer,
        approver_authenticator=lambda c, r: c == {"uid": 1000},
        policy_rechecker=mutating_rechecker)
    try:
        rid = approval(db)
        assert db.decide(rid, approve=True, current_binding=BINDING,
                         approver_credentials={"uid": 1000},
                         audit_context=audit_for_approval(db, rid), now=NOW) == "APPROVED"
        before = copy.deepcopy(BINDING)
        ref = db.issue_authorization(rid, current_binding=BINDING,
                                     current_policy_version="policy-1",
                                     audit_context=audit_for_approval(db, rid), now=NOW)
        assert isinstance(ref, str) and ref
        assert BINDING == before
        assert db._db.execute("SELECT state FROM approvals WHERE request_id=?", (rid,)).fetchone()["state"] == "APPROVED"
        assert seen == [rid]
        assert db._db.execute("SELECT COUNT(*) FROM auth_refs WHERE request_id=?", (rid,)).fetchone()[0] == 1
    finally:
        db.close()


def test_consume_policy_rechecker_cannot_mutate_authoritative_binding():
    def mutating_rechecker(request_id, binding, policy_version):
        binding.clear()
        binding["resource_scope"] = ["disk:attacker-selected"]
        return True

    db = SecurityStore(":memory:", audit_key=KEY, peer_authenticator=peer,
        approver_authenticator=lambda c, r: c == {"uid": 1000},
        policy_rechecker=mutating_rechecker)
    try:
        rid = approval(db)
        assert db.decide(rid, approve=True, current_binding=BINDING,
                         approver_credentials={"uid": 1000},
                         audit_context=audit_for_approval(db, rid), now=NOW) == "APPROVED"
        ref = db.issue_authorization(rid, current_binding=BINDING, current_policy_version="policy-1",
                                     audit_context=audit_for_approval(db, rid), now=NOW)
        # Use the authentic resource scope. The callback's mutation must not
        # alter the store's binding or the resource scope released in the grant.
        result = db.consume(ref, operation_id="broker.disk.erase", resource_scope=BINDING["resource_scope"],
                            action_digest=D4, policy_version="policy-1", registry_version="registry-1",
                            precondition_digest=D4, peer_credentials={"uid": 1000, "pid": 42},
                            audit_context=audit_for_ref(db, ref), now=NOW)
        assert result.outcome == "CONSUMED"
        assert result.grant["resource_scope"] == BINDING["resource_scope"]
    finally:
        db.close()


def test_approval_lifecycle_methods_fail_closed_on_invalid_timestamps():
    from datetime import tzinfo

    class PseudoTimezone(tzinfo):
        def utcoffset(self, dt):
            return None

        def dst(self, dt):
            return None

    invalid_now = datetime(2026, 10, 31, 12, 0, tzinfo=PseudoTimezone())
    db = store()
    try:
        with pytest.raises(SecurityStoreError, match="decision timestamp"):
            db.decide("not-a-request", approve=True, current_binding=BINDING,
                      approver_credentials={"uid": 1000}, audit_context={}, now=invalid_now)
        with pytest.raises(SecurityStoreError, match="authorization timestamp"):
            db.issue_authorization("not-a-request", current_binding=BINDING,
                                   current_policy_version="policy-1", audit_context={}, now=invalid_now)
        result = db.consume("not-a-token", operation_id="broker.disk.erase", resource_scope=BINDING["resource_scope"],
                            action_digest=D4, policy_version="policy-1", registry_version="registry-1",
                            precondition_digest=D4, peer_credentials={"uid": 1000, "pid": 42},
                            audit_context={}, now=invalid_now)
        assert result.outcome == "BINDING_MISMATCH"
        assert db._db.execute("SELECT COUNT(*) FROM approvals").fetchone()[0] == 0
        assert db._db.execute("SELECT COUNT(*) FROM auth_refs").fetchone()[0] == 0
        assert db.audit_events() == []
    finally:
        db.close()


def test_security_store_time_rejects_tzinfo_without_utc_offset():
    from datetime import tzinfo

    class PseudoTimezone(tzinfo):
        def utcoffset(self, dt):
            return None

        def dst(self, dt):
            return None

    pseudo_aware = datetime(2026, 10, 31, 12, 0, tzinfo=PseudoTimezone())
    with pytest.raises(ValueError, match="timezone-aware"):
        SecurityStore._time(pseudo_aware)


@pytest.mark.parametrize("overrides", [
    {"policy_version": 7},
    {"risk_class": []},
    {"task_id": 1},
    {"step_id": {}},
    {"action_digest": 7},
    {"principal_binding": 7},
    {"binding": None},
    {"audit_context": None},
    {"expires_at": "2026-10-31T06:02:00Z"},
    {"now": "2026-10-31T06:00:00Z"},
    {"action_id": "a" * 161},
    {"broker_operation_id": "b" * 161},
])
def test_create_approval_rejects_malformed_typed_inputs_with_security_error(overrides):
    db = store()
    try:
        proposal_id = str(uuid.uuid4())
        args = {
            "action_id": "system.disk.erase",
            "broker_operation_id": "broker.disk.erase",
            "action_digest": D4,
            "proposal_id": proposal_id,
            "principal_binding": D1,
            "policy_version": "policy-1",
            "risk_class": "R3",
            "task_id": "task-1",
            "step_id": "step-1",
            "binding": BINDING,
            "expires_at": NOW + timedelta(minutes=2),
            "audit_context": audit(proposal_id=proposal_id),
            "now": NOW,
        }
        args.update(overrides)
        with pytest.raises(SecurityStoreError):
            db.create_approval(**args)
        assert db._db.execute("SELECT COUNT(*) FROM approvals").fetchone()[0] == 0
        assert db.audit_events() == []
    finally:
        db.close()


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
    for invalid_id in (proposal["proposal_id"].upper(), "{" + proposal["proposal_id"] + "}",
                       proposal["proposal_id"].replace("-", "")):
        malformed = dict(proposal, proposal_id=invalid_id)
        assert engine.evaluate(malformed, context, [dict(
            schema_version="0.1.0", action_id="system.info.read", operation_schema_version="1.0.0",
            arguments_schema_ref="schemas/arguments/system-info.json", preconditions=[],
            postcondition_verifier="verify.system.info", allowed_origins=["local"],
            allowed_principal_classes=["user"], resources=[{"kind": "system", "access_modes": ["read"]}],
            minimum_risk_class="R0", approval_mode="never", broker_operation_id="broker.system.info.read",
            timeout_ms=1000, idempotency="optional_read_only")], "registry-1").reason_code == "POLICY_INVALID_ARGUMENTS"
    assert engine.evaluate(proposal, context, [], "registry-1").status == "DENY"
    reg = {"schema_version": "0.1.0", "action_id": "system.info.read", "operation_schema_version": "1.0.0",
        "arguments_schema_ref": "schemas/arguments/system-info.json",
        "preconditions": [], "postcondition_verifier": "verify.system.info",
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
        "operation_schema_version": "1.0.0",
        "arguments_schema_ref": "schemas/arguments/system-info.json",
        "preconditions": [], "postcondition_verifier": "verify.system.info", "allowed_origins": ["local"],
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
        "operation_schema_version": "1.0.0",
        "arguments_schema_ref": "schemas/arguments/system-info.json",
        "preconditions": [], "postcondition_verifier": "verify.system.info", "allowed_origins": ["local"],
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
        "operation_schema_version": "1.0.0",
        "arguments_schema_ref": "schemas/arguments/system-info.json",
        "preconditions": [], "postcondition_verifier": "verify.system.info", "allowed_origins": ["local"],
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


@pytest.mark.parametrize("field,value", [
    ("timeout_ms", True),
    ("max_input_bytes", True),
    ("max_input_bytes", False),
])
def test_registry_numeric_limits_reject_boolean_values(field, value):
    proposal = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "proposal_id": str(uuid.uuid4()), "task_id": "t1", "step_id": "s1",
        "arguments": {}, "resources": [{"kind": "system", "id": "host", "access": "read"}],
        "requested_at": NOW.isoformat()}
    context = {"authenticated": True, "principal_binding": D1, "session_binding": D2,
        "device_binding": D3, "origin": "local", "principal_class": "user"}
    entry = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "operation_schema_version": "1.0.0",
        "arguments_schema_ref": "schemas/arguments/system-info.json",
        "preconditions": [], "postcondition_verifier": "verify.system.info", "allowed_origins": ["local"],
        "allowed_principal_classes": ["user"],
        "resources": [{"kind": "system", "access_modes": ["read"]}],
        "minimum_risk_class": "R0", "approval_mode": "never",
        "broker_operation_id": "broker.system.info.read", "timeout_ms": 1000,
        "idempotency": "optional_read_only"}
    entry[field] = value
    engine = PolicyEngine("policy-1", identity_verifier=lambda c: True,
        registry_verifier=lambda r, v: bool(r) and v == "registry-1",
        argument_validator=lambda a, x: True, resource_resolver=lambda r: list(r),
        precondition_verifier=lambda p, r: D4)
    decision = engine.evaluate(proposal, context, [entry], "registry-1")
    assert decision.status == "DENY"
    assert decision.reason_code == "POLICY_REGISTRY_INVALID"


@pytest.mark.parametrize("field,value", [
    ("arguments_schema_ref", None), ("preconditions", "not-a-list"),
    ("preconditions", [""]), ("postcondition_verifier", ""),
    ("operation_schema_version", "1.0"), ("action_id", "A" * 161),
    ("unexpected_field", "must-not-be-ignored"),
    ("rate_limit", {"max_calls": True}), ("rate_limit", {"window_seconds": 0}),
    ("risk_escalation_rules", [""]), ("resources", [{"kind": "system", "access_modes": ["read"]}] * 33),
])
def test_registry_full_schema_shape_is_enforced(field, value):
    proposal = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "proposal_id": str(uuid.uuid4()), "task_id": "t1", "step_id": "s1",
        "arguments": {}, "resources": [{"kind": "system", "id": "host", "access": "read"}],
        "requested_at": NOW.isoformat()}
    context = {"authenticated": True, "principal_binding": D1, "session_binding": D2,
        "device_binding": D3, "origin": "local", "principal_class": "user"}
    entry = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "operation_schema_version": "1.0.0",
        "arguments_schema_ref": "schemas/arguments/system-info.json",
        "allowed_origins": ["local"], "allowed_principal_classes": ["user"],
        "resources": [{"kind": "system", "access_modes": ["read"]}],
        "minimum_risk_class": "R0", "approval_mode": "never",
        "broker_operation_id": "broker.system.info.read", "timeout_ms": 1000,
        "idempotency": "optional_read_only", "preconditions": [],
        "postcondition_verifier": "verify.system.info"}
    entry[field] = value
    engine = PolicyEngine("policy-1", identity_verifier=lambda c: True,
        registry_verifier=lambda r, v: True, argument_validator=lambda a, x: True,
        resource_resolver=lambda resources: list(resources),
        precondition_verifier=lambda p, r: D4)
    result = engine.evaluate(proposal, context, [entry], "registry-1")
    assert result.status == "DENY"
    assert result.reason_code == "POLICY_REGISTRY_INVALID"


def test_policy_enforces_input_size_before_calling_argument_validator():
    called = []
    proposal = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "proposal_id": str(uuid.uuid4()), "task_id": "t1", "step_id": "s1",
        "arguments": {"payload": "x" * 2048},
        "resources": [{"kind": "system", "id": "host", "access": "read"}],
        "requested_at": NOW.isoformat()}
    context = {"authenticated": True, "principal_binding": D1, "session_binding": D2,
        "device_binding": D3, "origin": "local", "principal_class": "user"}
    entry = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "operation_schema_version": "1.0.0",
        "arguments_schema_ref": "schemas/arguments/system-info.json",
        "allowed_origins": ["local"], "allowed_principal_classes": ["user"],
        "resources": [{"kind": "system", "access_modes": ["read"]}],
        "minimum_risk_class": "R0", "approval_mode": "never",
        "broker_operation_id": "broker.system.info.read", "timeout_ms": 1000,
        "idempotency": "optional_read_only", "preconditions": [],
        "postcondition_verifier": "verify.system.info", "max_input_bytes": 256}
    engine = PolicyEngine("policy-1", identity_verifier=lambda c: True,
        registry_verifier=lambda r, v: True,
        argument_validator=lambda action, args: called.append((action, args)) or True,
        resource_resolver=lambda resources: list(resources),
        precondition_verifier=lambda p, r: D4)
    result = engine.evaluate(proposal, context, [entry], "registry-1")
    assert result.status == "DENY"
    assert result.reason_code == "POLICY_INPUT_LIMIT"
    assert called == []


def test_policy_denies_configured_rate_limit_until_enforcement_is_available():
    proposal = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "proposal_id": str(uuid.uuid4()), "task_id": "t1", "step_id": "s1",
        "arguments": {}, "resources": [{"kind": "system", "id": "host", "access": "read"}],
        "requested_at": NOW.isoformat()}
    context = {"authenticated": True, "principal_binding": D1, "session_binding": D2,
        "device_binding": D3, "origin": "local", "principal_class": "user"}
    entry = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "operation_schema_version": "1.0.0",
        "arguments_schema_ref": "schemas/arguments/system-info.json",
        "allowed_origins": ["local"], "allowed_principal_classes": ["user"],
        "resources": [{"kind": "system", "access_modes": ["read"]}],
        "minimum_risk_class": "R0", "approval_mode": "never",
        "broker_operation_id": "broker.system.info.read", "timeout_ms": 1000,
        "idempotency": "optional_read_only", "preconditions": [],
        "postcondition_verifier": "verify.system.info",
        "rate_limit": {"max_calls": 5, "window_seconds": 60}}
    engine = PolicyEngine("policy-1", identity_verifier=lambda c: True,
        registry_verifier=lambda r, v: True, argument_validator=lambda a, x: True,
        resource_resolver=lambda resources: list(resources),
        precondition_verifier=lambda p, r: D4)
    result = engine.evaluate(proposal, context, [entry], "registry-1")
    assert result.status == "DENY"
    assert result.reason_code == "POLICY_RATE_LIMIT_UNSUPPORTED"


def test_policy_denies_configured_rate_limit_until_enforcement_is_available():
    proposal = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "proposal_id": str(uuid.uuid4()), "task_id": "t1", "step_id": "s1",
        "arguments": {}, "resources": [{"kind": "system", "id": "host", "access": "read"}],
        "requested_at": NOW.isoformat()}
    context = {"authenticated": True, "principal_binding": D1, "session_binding": D2,
        "device_binding": D3, "origin": "local", "principal_class": "user"}
    entry = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "operation_schema_version": "1.0.0",
        "arguments_schema_ref": "schemas/arguments/system-info.json",
        "allowed_origins": ["local"], "allowed_principal_classes": ["user"],
        "resources": [{"kind": "system", "access_modes": ["read"]}],
        "minimum_risk_class": "R0", "approval_mode": "never",
        "broker_operation_id": "broker.system.info.read", "timeout_ms": 1000,
        "idempotency": "optional_read_only", "preconditions": [],
        "postcondition_verifier": "verify.system.info",
        "rate_limit": {"max_calls": 5, "window_seconds": 60}}
    engine = PolicyEngine("policy-1", identity_verifier=lambda c: True,
        registry_verifier=lambda r, v: True, argument_validator=lambda a, x: True,
        resource_resolver=lambda resources: list(resources),
        precondition_verifier=lambda p, r: D4)
    result = engine.evaluate(proposal, context, [entry], "registry-1")
    assert result.status == "DENY"
    assert result.reason_code == "POLICY_RATE_LIMIT_UNSUPPORTED"


def test_registry_rejects_non_mapping_entries_before_lookup():
    engine = PolicyEngine("policy-1", identity_verifier=lambda c: True,
        registry_verifier=lambda r, v: bool(r) and v == "registry-1",
        argument_validator=lambda a, x: True, resource_resolver=lambda r: list(r),
        precondition_verifier=lambda p, r: D4)
    proposal = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "proposal_id": str(uuid.uuid4()), "task_id": "t1", "step_id": "s1",
        "arguments": {}, "resources": [{"kind": "system", "id": "host", "access": "read"}],
        "requested_at": NOW.isoformat()}
    context = {"authenticated": True, "principal_binding": D1, "session_binding": D2,
        "device_binding": D3, "origin": "local", "principal_class": "user"}
    decision = engine.evaluate(proposal, context, [None], "registry-1")
    assert decision.status == "DENY"
    assert decision.reason_code == "POLICY_REGISTRY_INVALID"


def test_resource_resolver_cannot_drop_add_or_widen_resources():
    proposal = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "proposal_id": str(uuid.uuid4()), "task_id": "t1", "step_id": "s1",
        "arguments": {}, "resources": [{"kind": "system", "id": "host", "access": "read"}],
        "requested_at": NOW.isoformat()}
    context = {"authenticated": True, "principal_binding": D1, "session_binding": D2,
        "device_binding": D3, "origin": "local", "principal_class": "user"}
    registry = [{"schema_version": "0.1.0", "action_id": "system.info.read",
        "operation_schema_version": "1.0.0",
        "arguments_schema_ref": "schemas/arguments/system-info.json",
        "preconditions": [], "postcondition_verifier": "verify.system.info", "allowed_origins": ["local"],
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

    # A registration with resource declarations cannot authorize an
    # unscoped proposal, even if the resolver would accept an empty list.
    proposal["resources"] = []
    assert evaluate_with(lambda resources: list(resources)).reason_code == "POLICY_SCOPE_EXCEEDED"


def test_action_digest_binds_original_and_resolved_resource_identifiers():
    proposal = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "proposal_id": str(uuid.uuid4()), "task_id": "t1", "step_id": "s1",
        "arguments": {}, "resources": [{"kind": "system", "id": "alias-a", "access": "read"}],
        "requested_at": NOW.isoformat()}
    context = {"authenticated": True, "principal_binding": D1, "session_binding": D2,
        "device_binding": D3, "origin": "local", "principal_class": "user"}
    registry = [{"schema_version": "0.1.0", "action_id": "system.info.read",
        "operation_schema_version": "1.0.0",
        "arguments_schema_ref": "schemas/arguments/system-info.json",
        "preconditions": [], "postcondition_verifier": "verify.system.info", "allowed_origins": ["local"],
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

@pytest.mark.parametrize("field,value", [
    ("principal_binding", D4),
    ("proposal_id", str(uuid.uuid4())),
    ("operation_id", "broker.other.operation"),
    ("risk_class", "R1"),
    ("policy_version", "policy-other"),
    ("action_digest", D1),
    ("task_id", "task-other"),
    ("step_id", "step-other"),
    ("registry_version", "registry-other"),
    ("registry_status", "unavailable"),
    ("origin", "remote"),
])
def test_consume_rejects_unbound_audit_context_without_consuming_authorization(field, value):
    db = store()
    try:
        ref = decide_and_issue(db)
        before = len(db.audit_events())
        context = audit_for_ref(db, ref)
        context[field] = value
        result = consume(db, ref, audit_context=context)
        assert result.outcome == "BINDING_MISMATCH"
        assert len(db.audit_events()) == before
        assert db.reconcile(ref, peer_credentials={"uid": 1000, "pid": 42}).outcome == "ISSUED"
        assert consume(db, ref).outcome == "CONSUMED"
    finally:
        db.close()


def test_expired_approval_stale_resource_and_wrong_operation_are_denied():
    db = store()
    try:
        rid = approval(db)
        assert db.decide(rid, approve=True, current_binding=BINDING, approver_credentials={"uid": 1000},
            audit_context=audit_for_approval(db, rid), now=NOW + timedelta(minutes=2)) == "EXPIRED"
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
        result = BrokerAuthorizationGate(db).authorize(request, audit_for_ref(db, ref), now=NOW)
        assert result.outcome == "CONSUMED"
        assert set(result.grant) == {"consumption_id", "operation_id", "resource_scope", "principal_binding",
                                     "session_binding", "device_binding", "action_digest", "registry_version",
                                     "precondition_digest"}
    finally: db.close()
def test_broker_gate_fails_closed_on_malformed_requests_and_authority_errors():
    from security.runtime.broker import BrokerAuthorizationGate, BrokerAuthorizationRequest
    class BrokenAuthority:
        def consume(self, *args, **kwargs):
            raise RuntimeError("authority unavailable")
    assert BrokerAuthorizationGate(BrokenAuthority()).authorize(None, {}).outcome == "BINDING_MISMATCH"
    request = BrokerAuthorizationRequest("opaque", "broker.disk.erase", D4, "policy-1",
                                         ("disk:wwn-123",), "registry-1", D4, {"uid": 1000})
    result = BrokerAuthorizationGate(BrokenAuthority()).authorize(request, {})
    assert result.outcome == "AUTHORITY_UNAVAILABLE"
    assert result.grant is None


def test_broker_gate_never_releases_an_incomplete_consumed_grant():
    from security.runtime.broker import BrokerAuthorizationGate, BrokerAuthorizationRequest
    class IncompleteAuthority:
        def consume(self, *args, **kwargs):
            return ConsumeResult("CONSUMED", "consumption-1", {"operation_id": "broker.disk.erase"})
    request = BrokerAuthorizationRequest("opaque", "broker.disk.erase", D4, "policy-1",
                                         ("disk:wwn-123",), "registry-1", D4, {"uid": 1000})
    result = BrokerAuthorizationGate(IncompleteAuthority()).authorize(request, {})
    assert result.outcome == "AUTHORITY_UNAVAILABLE"
    assert result.grant is None


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



def test_consume_rejects_oversized_or_non_utf8_authorization_reference():
    db = store()
    try:
        oversized = consume(db, "x" * 513)
        malformed_unicode = consume(db, chr(0xD800))
        assert oversized.outcome == "BINDING_MISMATCH"
        assert malformed_unicode.outcome == "BINDING_MISMATCH"

        # Rejected references must not mutate authorization state.
        ref = decide_and_issue(db)
        assert consume(db, ref).outcome == "CONSUMED"
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
        "operation_schema_version": "1.0.0",
        "arguments_schema_ref": "schemas/arguments/system-info.json",
        "preconditions": [], "postcondition_verifier": "verify.system.info", "allowed_origins": ["local"],
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

def test_registry_invalid_unmatched_entry_invalidates_entire_registry():
    proposal = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "proposal_id": str(uuid.uuid4()), "task_id": "t1", "step_id": "s1",
        "arguments": {}, "resources": [{"kind": "system", "id": "host", "access": "read"}],
        "requested_at": NOW.isoformat()}
    context = {"authenticated": True, "principal_binding": D1, "session_binding": D2,
        "device_binding": D3, "origin": "local", "principal_class": "user"}
    def entry(action_id, version="1.0.0"):
        return {"schema_version": "0.1.0", "action_id": action_id,
            "operation_schema_version": version,
            "arguments_schema_ref": "schemas/arguments/system-info.json",
            "allowed_origins": ["local"], "allowed_principal_classes": ["user"],
            "resources": [{"kind": "system", "access_modes": ["read"]}],
            "minimum_risk_class": "R0", "approval_mode": "never",
            "broker_operation_id": "broker.system.info.read", "timeout_ms": 1000,
            "idempotency": "optional_read_only", "preconditions": [],
            "postcondition_verifier": "verify.system.info"}
    engine = PolicyEngine("policy-1", identity_verifier=lambda c: True,
        registry_verifier=lambda r, v: True, argument_validator=lambda a, x: True,
        resource_resolver=lambda resources: list(resources),
        precondition_verifier=lambda p, r: D4)
    # The malformed entry does not match the proposal action. It must still fail
    # registry-wide validation instead of being hidden by action lookup.
    decision = engine.evaluate(proposal, context,
        [entry("system.info.read"), entry("other.info.read", "not-semver")], "registry-1")
    assert decision.status == "DENY"
    assert decision.reason_code == "POLICY_REGISTRY_INVALID"



def test_audit_checkpoint_rejects_non_genesis_hash_at_sequence_zero():
    import hashlib
    import hmac

    db = store()
    try:
        checkpoint = db.audit_checkpoint()
        forged = dict(checkpoint)
        forged["event_hash"] = "a" * 64
        payload = {key: forged[key] for key in ("schema_version", "sequence", "event_hash")}
        forged["mac"] = hmac.new(KEY, b"TUSKER-AUDIT-CHECKPOINT-v1\\0" + canonical_bytes(payload), hashlib.sha256).hexdigest()
        assert not db.verify_audit_chain(forged)
        assert db.verify_audit_chain(checkpoint)
    finally:
        db.close()


def test_audit_chain_rejects_boolean_checkpoint_sequence_and_sequence_gaps():
    db = store()
    try:
        db._audit(audit())
        checkpoint = db.audit_checkpoint()
        boolean_sequence = dict(checkpoint)
        boolean_sequence["sequence"] = True
        assert not db.verify_audit_chain(boolean_sequence)

        db._audit(audit())
        assert db.verify_audit_chain()
        # Alter only SQLite sequence metadata, leaving authenticated event bytes
        # and the HMAC chain untouched. The verifier must still detect the gap.
        db._db.execute("UPDATE audit_events SET seq=3 WHERE seq=2")
        assert not db.verify_audit_chain()
    finally:
        db.close()


def test_audit_checkpoint_refuses_to_sign_a_tampered_chain():
    db = store()
    try:
        db._audit(audit())
        db._db.execute("UPDATE audit_events SET event_json=? WHERE seq=1", (b'{"tampered":true}',))
        with pytest.raises(SecurityStoreError, match="invalid audit chain"):
            db.audit_checkpoint()
    finally:
        db.close()


def test_audit_checkpoint_rejects_existing_transaction_without_committing_it():
    db = store()
    try:
        db._db.execute("BEGIN")
        with pytest.raises(SecurityStoreError, match="active transaction"):
            db.audit_checkpoint()
        assert db._db.in_transaction
        db._db.execute("ROLLBACK")
        assert db.verify_audit_chain()
        assert db.audit_checkpoint()["sequence"] == 0
    finally:
        if db._db.in_transaction:
            db._db.execute("ROLLBACK")
        db.close()


def test_audit_chain_verification_fails_closed_when_table_is_unavailable():
    db = store()
    try:
        db._db.execute("DROP TABLE audit_events")
        assert db.verify_audit_chain() is False
    finally:
        db.close()


def test_audit_events_verifies_chain_before_returning_events():
    db = store()
    try:
        db._audit(audit())
        events = db.audit_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "requested"

        # Event export is an integrity boundary: do not return bytes whose
        # authenticated chain no longer verifies.
        db._db.execute("UPDATE audit_events SET event_json=? WHERE seq=1", (b'{"tampered":true}',))
        with pytest.raises(SecurityStoreError, match="invalid audit chain"):
            db.audit_events()
    finally:
        db.close()


def test_audit_events_rejects_existing_transaction_without_ending_it():
    db = store()
    try:
        db._db.execute("BEGIN")
        db._audit(audit())
        with pytest.raises(SecurityStoreError, match="active transaction"):
            db.audit_events()
        assert db._db.in_transaction
        db._db.execute("ROLLBACK")
        assert db.audit_events() == []
    finally:
        if db._db.in_transaction:
            db._db.execute("ROLLBACK")
        db.close()


@pytest.mark.parametrize("timestamp", [
    NOW.replace(tzinfo=timezone(timedelta(hours=5, minutes=30))).isoformat(),
    NOW.replace(tzinfo=None).isoformat(),
])
def test_audit_rejects_non_utc_or_timezone_naive_timestamps(timestamp):
    db = store()
    try:
        with pytest.raises(SecurityStoreError, match="invalid audit identifier or timestamp"):
            db._audit(audit(timestamp_utc=timestamp))
        assert db.audit_events() == []
    finally:
        db.close()


def test_audit_rejects_free_form_reason_codes():
    db = store()
    try:
        with pytest.raises(SecurityStoreError, match="reason code"):
            db._audit(audit(reason_code="user supplied secret: do not log"))
        assert db.audit_events() == []
    finally:
        db.close()


@pytest.mark.parametrize("overrides", [
    {"event_type": []},
    {"origin": {}},
    {"risk_class": []},
    {"result_status": {}},
    {"registry_status": []},
    {"transaction_id": {"unbounded": "nested"}, "snapshot_digest": D4},
    {"device_binding": [], "origin": "remote", "session_binding": D2},
    {"session_binding": {}, "origin": "remote", "device_binding": D3},
])
def test_audit_rejects_non_scalar_or_malformed_optional_fields(overrides):
    db = store()
    try:
        event = audit()
        event.update(overrides)
        with pytest.raises(SecurityStoreError):
            db._audit(event)
        assert db.audit_events() == []
    finally:
        db.close()


@pytest.mark.parametrize("field,value", [
    ("principal_binding", D4), ("proposal_id", str(uuid.uuid4())),
    ("operation_id", "broker.other.op"), ("risk_class", "R4"),
    ("policy_version", "policy-2"), ("action_digest", D3),
    ("task_id", "other-task"), ("step_id", "other-step"),
    ("registry_version", "registry-2"), ("registry_status", "unavailable"),
])
def test_decide_rejects_mismatched_audit_context_before_state_change(field, value):
    db = store()
    try:
        rid = approval(db)
        context = audit_for_approval(db, rid)
        context[field] = value
        result = db.decide(rid, approve=True, current_binding=BINDING,
            approver_credentials={"uid": 1000}, audit_context=context, now=NOW)
        assert result == "BINDING_MISMATCH"
        row = db._db.execute("SELECT state FROM approvals WHERE request_id=?", (rid,)).fetchone()
        assert row["state"] == "PENDING"
        assert len(db.audit_events()) == 1
    finally:
        db.close()


def test_decide_rejects_remote_audit_identity_not_bound_to_approval():
    db = store()
    try:
        rid = approval(db)
        context = audit_for_approval(db, rid)
        context.update(origin="remote", device_binding=D4, session_binding=D2)
        assert db.decide(rid, approve=True, current_binding=BINDING,
            approver_credentials={"uid": 1000}, audit_context=context, now=NOW) == "BINDING_MISMATCH"
        row = db._db.execute("SELECT state FROM approvals WHERE request_id=?", (rid,)).fetchone()
        assert row["state"] == "PENDING"
        assert len(db.audit_events()) == 1
    finally:
        db.close()


@pytest.mark.parametrize("invalid_decision", [1, 0, "true", "false", None, [], {}])
def test_decide_rejects_non_boolean_decisions_without_state_change(invalid_decision):
    db = store()
    try:
        rid = approval(db)
        result = db.decide(rid, approve=invalid_decision, current_binding=BINDING,
                           approver_credentials={"uid": 1000}, audit_context=audit_for_approval(db, rid), now=NOW)
        assert result == "INVALID_DECISION"
        row = db._db.execute("SELECT state FROM approvals WHERE request_id=?", (rid,)).fetchone()
        assert row["state"] == "PENDING"
        assert db.audit_events()[0]["event_type"] == "requested"
        assert len(db.audit_events()) == 1
    finally:
        db.close()


@pytest.mark.parametrize("field,value", [
    ("proposal_id", "{" + str(uuid.uuid4()) + "}"),
    ("proposal_id", str(uuid.uuid4()).upper()),
    ("proposal_id", str(uuid.uuid4()).replace("-", "")),
    ("decision_id", "{" + str(uuid.uuid4()) + "}"),
    ("decision_id", str(uuid.uuid4()).upper()),
    ("approval_request_id", str(uuid.uuid4()).upper()),
    ("approval_request_id", {"id": str(uuid.uuid4())}),
])
def test_audit_rejects_noncanonical_uuid_identifiers(field, value):
    db = store()
    try:
        with pytest.raises(SecurityStoreError):
            db._audit(audit(**{field: value}))
        assert db.audit_events() == []
    finally:
        db.close()


def test_create_approval_rejects_oversized_resource_scope():
    db = store()
    try:
        proposal_id = str(uuid.uuid4())
        binding = dict(BINDING)
        binding["resource_scope"] = [f"resource:{index}" for index in range(129)]
        with pytest.raises(SecurityStoreError, match="oversized approval binding"):
            db.create_approval(action_id="system.disk.erase", broker_operation_id="broker.disk.erase",
                action_digest=D4, proposal_id=proposal_id, principal_binding=D1,
                policy_version="policy-1", risk_class="R3", task_id="task-1", step_id="step-1",
                binding=binding, expires_at=NOW + timedelta(minutes=2),
                audit_context=audit(proposal_id=proposal_id), now=NOW)
        assert db._db.execute("SELECT COUNT(*) FROM approvals").fetchone()[0] == 0
        assert db.audit_events() == []
    finally:
        db.close()


def test_create_approval_rejects_noncanonical_proposal_uuid():
    db = store()
    try:
        with pytest.raises(SecurityStoreError, match="canonical lowercase UUID"):
            db.create_approval(action_id="system.disk.erase", broker_operation_id="broker.disk.erase",
                action_digest=D4, proposal_id=str(uuid.uuid4()).upper(), principal_binding=D1,
                policy_version="policy-1", risk_class="R3", task_id="task-1", step_id="step-1",
                binding=BINDING, expires_at=NOW + timedelta(minutes=2),
                audit_context=audit(), now=NOW)
        assert db._db.execute("SELECT COUNT(*) FROM approvals").fetchone()[0] == 0
        assert db.audit_events() == []
    finally:
        db.close()


@pytest.mark.parametrize("field,value", [
    ("principal_binding", D4), ("proposal_id", str(uuid.uuid4())),
    ("operation_id", "broker.other.op"), ("risk_class", "R4"),
    ("policy_version", "policy-2"), ("action_digest", D3),
    ("task_id", "other-task"), ("step_id", "other-step"),
    ("registry_version", "registry-2"), ("registry_status", "unavailable"),
])
def test_issue_authorization_rejects_mismatched_audit_context_without_state_change(field, value):
    db = store()
    try:
        rid = approval(db)
        context = audit_for_approval(db, rid)
        assert db.decide(rid, approve=True, current_binding=BINDING,
            approver_credentials={"uid": 1000}, audit_context=context, now=NOW) == "APPROVED"
        context = audit_for_approval(db, rid)
        context[field] = value
        with pytest.raises(SecurityStoreError, match="audit context does not match"):
            db.issue_authorization(rid, current_binding=BINDING, current_policy_version="policy-1",
                audit_context=context, now=NOW)
        row = db._db.execute("SELECT state FROM approvals WHERE request_id=?", (rid,)).fetchone()
        assert row["state"] == "APPROVED"
        assert db._db.execute("SELECT COUNT(*) AS n FROM auth_refs").fetchone()["n"] == 0
        assert len(db.audit_events()) == 2
    finally:
        db.close()


def test_issue_authorization_rejects_remote_audit_identity_not_bound_to_approval():
    db = store()
    try:
        rid = approval(db)
        context = audit_for_approval(db, rid)
        assert db.decide(rid, approve=True, current_binding=BINDING,
            approver_credentials={"uid": 1000}, audit_context=context, now=NOW) == "APPROVED"
        context = audit_for_approval(db, rid)
        context.update(origin="remote", device_binding=D4, session_binding=D2)
        with pytest.raises(SecurityStoreError, match="audit context does not match"):
            db.issue_authorization(rid, current_binding=BINDING, current_policy_version="policy-1",
                audit_context=context, now=NOW)
        row = db._db.execute("SELECT state FROM approvals WHERE request_id=?", (rid,)).fetchone()
        assert row["state"] == "APPROVED"
        assert db._db.execute("SELECT COUNT(*) AS n FROM auth_refs").fetchone()["n"] == 0
        assert len(db.audit_events()) == 2
    finally:
        db.close()


def test_security_database_file_is_created_and_reopened_owner_only(tmp_path):
    import stat

    path = tmp_path / "security.db"
    db = store(path)
    try:
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    finally:
        db.close()

    path.chmod(0o644)
    db = store(path)
    try:
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    finally:
        db.close()


def test_security_database_refuses_final_component_symlink(tmp_path):
    target = tmp_path / "sensitive.db"
    target.write_bytes(b"not a database")
    link = tmp_path / "security.db"
    link.symlink_to(target)

    with pytest.raises(SecurityStoreError, match="could not be opened privately"):
        SecurityStore(link, audit_key=KEY)
    assert target.read_bytes() == b"not a database"


def test_security_database_refuses_path_swap_during_sqlite_open(tmp_path, monkeypatch):
    import sqlite3
    from security.runtime import store as store_module

    path = tmp_path / "security.db"
    target = tmp_path / "attacker.db"
    original_connect = sqlite3.connect
    original_connect(target).close()

    def swap_before_sqlite_open(database, *args, **kwargs):
        path.unlink()
        path.symlink_to(target)
        return original_connect(database, *args, **kwargs)

    monkeypatch.setattr(store_module.sqlite3, "connect", swap_before_sqlite_open)
    with pytest.raises(SecurityStoreError, match="path changed during open"):
        SecurityStore(path, audit_key=KEY)

    # The redirected connection is closed before schema/PRAGMA writes occur.
    probe = original_connect(target)
    try:
        assert probe.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall() == []
    finally:
        probe.close()


@pytest.mark.parametrize("callback_result", [1, "authenticated", [], {}])
def test_decide_rejects_truthy_non_boolean_approver_authentication(callback_result):
    db = store()
    try:
        rid = approval(db)
        calls = []
        db._approver_authenticator = lambda credentials, request_id: calls.append(request_id) or callback_result
        result = db.decide(rid, approve=True, current_binding=BINDING,
            approver_credentials={"uid": 1000}, audit_context=audit_for_approval(db, rid), now=NOW)
        assert result == "CALLER_UNAUTHORIZED"
        assert calls == [rid]
        assert db._db.execute("SELECT state FROM approvals WHERE request_id=?", (rid,)).fetchone()["state"] == "PENDING"
        assert len(db.audit_events()) == 1
    finally:
        db.close()


@pytest.mark.parametrize("callback_result", [1, "allowed", [], {}])
def test_issue_authorization_rejects_truthy_non_boolean_policy_recheck(callback_result):
    db = store()
    try:
        rid = approval(db)
        assert db.decide(rid, approve=True, current_binding=BINDING,
            approver_credentials={"uid": 1000}, audit_context=audit_for_approval(db, rid), now=NOW) == "APPROVED"
        db._policy_rechecker = lambda request_id, binding, version: callback_result
        with pytest.raises(SecurityStoreError, match="re-evaluation unavailable or denied"):
            db.issue_authorization(rid, current_binding=BINDING, current_policy_version="policy-1",
                audit_context=audit_for_approval(db, rid), now=NOW)
        assert db._db.execute("SELECT state FROM approvals WHERE request_id=?", (rid,)).fetchone()["state"] == "INVALIDATED"
        assert db._db.execute("SELECT COUNT(*) FROM auth_refs").fetchone()[0] == 0
        assert len(db.audit_events()) == 3
    finally:
        db.close()


@pytest.mark.parametrize("callback_result", [1, "allowed", [], {}])
def test_consume_rejects_truthy_non_boolean_policy_recheck(callback_result):
    db = store()
    try:
        ref = decide_and_issue(db)
        db._policy_rechecker = lambda request_id, binding, version: callback_result
        result = consume(db, ref)
        assert result.outcome == "BINDING_MISMATCH"
        assert db._db.execute("SELECT state FROM approvals").fetchone()["state"] == "INVALIDATED"
        assert db._db.execute("SELECT state FROM auth_refs").fetchone()["state"] == "REVOKED"
        assert db.audit_events()[-1]["reason_code"] == "POLICY_BINDING_MISMATCH"
    finally:
        db.close()


@pytest.mark.parametrize("callback_result", [1, "verified", [], {}])
def test_policy_rejects_truthy_non_boolean_registry_verifier(callback_result):
    proposal = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "proposal_id": str(uuid.uuid4()), "task_id": "t1", "step_id": "s1",
        "arguments": {}, "resources": [{"kind": "system", "id": "host", "access": "read"}],
        "requested_at": NOW.isoformat()}
    context = {"authenticated": True, "principal_binding": D1, "session_binding": D2,
        "device_binding": D3, "origin": "local", "principal_class": "user"}
    registry = [{"schema_version": "0.1.0", "action_id": "system.info.read",
        "operation_schema_version": "1.0.0", "arguments_schema_ref": "schemas/arguments/system-info.json",
        "preconditions": [], "postcondition_verifier": "verify.system.info",
        "allowed_origins": ["local"], "allowed_principal_classes": ["user"],
        "resources": [{"kind": "system", "access_modes": ["read"]}],
        "minimum_risk_class": "R0", "approval_mode": "never",
        "broker_operation_id": "broker.system.info.read", "timeout_ms": 1000,
        "idempotency": "optional_read_only"}]
    engine = PolicyEngine("policy-1", identity_verifier=lambda c: True,
        registry_verifier=lambda r, v: callback_result, argument_validator=lambda a, x: True,
        resource_resolver=lambda r: list(r), precondition_verifier=lambda p, r: D4)
    result = engine.evaluate(proposal, context, registry, "registry-1")
    assert result.status == "DENY"
    assert result.reason_code == "POLICY_REGISTRY_UNAVAILABLE"


@pytest.mark.parametrize("callback_result", [1, "verified", [], {}])
def test_policy_rejects_truthy_non_boolean_identity_verifier(callback_result):
    proposal = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "proposal_id": str(uuid.uuid4()), "task_id": "t1", "step_id": "s1",
        "arguments": {}, "resources": [{"kind": "system", "id": "host", "access": "read"}],
        "requested_at": NOW.isoformat()}
    context = {"authenticated": True, "principal_binding": D1, "session_binding": D2,
        "device_binding": D3, "origin": "local", "principal_class": "user"}
    registry = [{"schema_version": "0.1.0", "action_id": "system.info.read",
        "operation_schema_version": "1.0.0", "arguments_schema_ref": "schemas/arguments/system-info.json",
        "preconditions": [], "postcondition_verifier": "verify.system.info",
        "allowed_origins": ["local"], "allowed_principal_classes": ["user"],
        "resources": [{"kind": "system", "access_modes": ["read"]}],
        "minimum_risk_class": "R0", "approval_mode": "never",
        "broker_operation_id": "broker.system.info.read", "timeout_ms": 1000,
        "idempotency": "optional_read_only"}]
    engine = PolicyEngine("policy-1", identity_verifier=lambda c: callback_result,
        registry_verifier=lambda r, v: True, argument_validator=lambda a, x: True,
        resource_resolver=lambda r: list(r), precondition_verifier=lambda p, r: D4)
    result = engine.evaluate(proposal, context, registry, "registry-1")
    assert result.status == "DENY"
    assert result.reason_code == "POLICY_UNKNOWN_PRINCIPAL"


@pytest.mark.parametrize("callback_result", [1, "valid", [], {}])
def test_policy_rejects_truthy_non_boolean_argument_validator(callback_result):
    proposal = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "proposal_id": str(uuid.uuid4()), "task_id": "t1", "step_id": "s1",
        "arguments": {}, "resources": [{"kind": "system", "id": "host", "access": "read"}],
        "requested_at": NOW.isoformat()}
    context = {"authenticated": True, "principal_binding": D1, "session_binding": D2,
        "device_binding": D3, "origin": "local", "principal_class": "user"}
    registry = [{"schema_version": "0.1.0", "action_id": "system.info.read",
        "operation_schema_version": "1.0.0", "arguments_schema_ref": "schemas/arguments/system-info.json",
        "preconditions": [], "postcondition_verifier": "verify.system.info",
        "allowed_origins": ["local"], "allowed_principal_classes": ["user"],
        "resources": [{"kind": "system", "access_modes": ["read"]}],
        "minimum_risk_class": "R0", "approval_mode": "never",
        "broker_operation_id": "broker.system.info.read", "timeout_ms": 1000,
        "idempotency": "optional_read_only"}]
    engine = PolicyEngine("policy-1", identity_verifier=lambda c: True,
        registry_verifier=lambda r, v: True, argument_validator=lambda a, x: callback_result,
        resource_resolver=lambda r: list(r), precondition_verifier=lambda p, r: D4)
    result = engine.evaluate(proposal, context, registry, "registry-1")
    assert result.status == "DENY"
    assert result.reason_code == "POLICY_INVALID_ARGUMENTS"


def test_security_database_refuses_hard_link_without_chmod_or_writes(tmp_path):
    import stat

    target = tmp_path / "shared.db"
    target.write_bytes(b"preserve external file")
    target.chmod(0o644)
    path = tmp_path / "security.db"
    path.hardlink_to(target)

    with pytest.raises(SecurityStoreError, match="must not have hard links"):
        SecurityStore(path, audit_key=KEY)

    assert target.read_bytes() == b"preserve external file"
    assert stat.S_IMODE(target.stat().st_mode) == 0o644

def test_security_database_rejection_closes_open_file_descriptor(tmp_path, monkeypatch):
    import os
    from security.runtime import store as store_module

    target = tmp_path / "shared.db"
    target.write_bytes(b"preserve external file")
    path = tmp_path / "security.db"
    path.hardlink_to(target)

    opened = []
    real_open = os.open

    def capture_open(*args, **kwargs):
        fd = real_open(*args, **kwargs)
        opened.append(fd)
        return fd

    monkeypatch.setattr(store_module.os, "open", capture_open)
    with pytest.raises(SecurityStoreError, match="must not have hard links"):
        SecurityStore(path, audit_key=KEY)

    assert len(opened) == 1
    with pytest.raises(OSError):
        os.fstat(opened[0])
    assert target.read_bytes() == b"preserve external file"

def test_security_database_closes_connection_when_initialization_fails(tmp_path, monkeypatch):
    import sqlite3
    from security.runtime import store as store_module

    path = tmp_path / "corrupt-security.db"
    path.write_bytes(b"not a sqlite database")
    opened = []
    real_connect = sqlite3.connect

    def capture_connect(*args, **kwargs):
        connection = real_connect(*args, **kwargs)
        opened.append(connection)
        return connection

    monkeypatch.setattr(store_module.sqlite3, "connect", capture_connect)
    with pytest.raises(SecurityStoreError, match="initialization failed closed"):
        SecurityStore(path, audit_key=KEY)

    assert len(opened) == 1
    with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
        opened[0].execute("SELECT 1")


@pytest.mark.parametrize("failing_dependency", [
    "identity_verifier", "registry_verifier", "argument_validator",
    "resource_resolver", "precondition_verifier",
])
def test_policy_fails_closed_when_trusted_dependency_raises(failing_dependency):
    proposal = {"schema_version": "0.1.0", "action_id": "system.info.read",
        "proposal_id": str(uuid.uuid4()), "task_id": "t1", "step_id": "s1",
        "arguments": {}, "resources": [{"kind": "system", "id": "host", "access": "read"}],
        "requested_at": NOW.isoformat()}
    context = {"authenticated": True, "principal_binding": D1, "session_binding": D2,
        "device_binding": D3, "origin": "local", "principal_class": "user"}
    registry = [{"schema_version": "0.1.0", "action_id": "system.info.read",
        "operation_schema_version": "1.0.0",
        "arguments_schema_ref": "schemas/arguments/system-info.json",
        "preconditions": [], "postcondition_verifier": "verify.system.info",
        "allowed_origins": ["local"], "allowed_principal_classes": ["user"],
        "resources": [{"kind": "system", "access_modes": ["read"]}],
        "minimum_risk_class": "R0", "approval_mode": "never",
        "broker_operation_id": "broker.system.info.read", "timeout_ms": 1000,
        "idempotency": "optional_read_only"}]

    def fail(*args, **kwargs):
        raise RuntimeError("dependency failure")

    dependencies = {
        "identity_verifier": lambda c: c.get("authenticated") is True,
        "registry_verifier": lambda r, v: bool(r) and v == "registry-1",
        "argument_validator": lambda a, x: True,
        "resource_resolver": lambda resources: list(resources),
        "precondition_verifier": lambda p, r: D4,
    }
    dependencies[failing_dependency] = fail
    engine = PolicyEngine("policy-1", **dependencies)
    decision = engine.evaluate(proposal, context, registry, "registry-1")
    assert decision.status == "DENY"
    assert decision.reason_code == "POLICY_INTERNAL_ERROR"

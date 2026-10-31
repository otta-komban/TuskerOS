"""SQLite approval authority and HMAC-chained audit; never dispatches handlers."""
from __future__ import annotations
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable, Mapping
from .canonical import canonical_bytes

_REDACT_KEY = re.compile(r"(secret|password|passwd|credential|private.?key|bearer|token|authorization_ref|email|phone|address|prompt|payload|raw_content)", re.I)
_BEARER = re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]+")
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)

class SecurityStoreError(RuntimeError):
    pass

@dataclass(frozen=True)
class ConsumeResult:
    outcome: str
    consumption_id: str | None = None
    grant: Mapping[str, Any] | None = None

def _redact(value: Any, key: str = "") -> Any:
    if _REDACT_KEY.search(key): return "[REDACTED]"
    if isinstance(value, Mapping): return {str(k): _redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list): return [_redact(item, key) for item in value]
    if isinstance(value, str): return _EMAIL.sub("[REDACTED_EMAIL]", _BEARER.sub(r"\1[REDACTED]", value))
    return value

class SecurityStore:
    def __init__(self, database: str | os.PathLike[str], *, audit_key: bytes,
                 peer_authenticator: Callable[[Any], Mapping[str, Any]] | None = None,
                 approver_authenticator: Callable[[Any, str], bool] | None = None,
                 policy_rechecker: Callable[[str, Mapping[str, Any], str], bool] | None = None):
        if not isinstance(audit_key, bytes) or len(audit_key) < 32:
            raise SecurityStoreError("an externally managed audit key of at least 32 bytes is required")
        self._audit_key, self._peer_authenticator = audit_key, peer_authenticator
        self._approver_authenticator, self._policy_rechecker = approver_authenticator, policy_rechecker
        self.path = str(database)
        if self.path != ":memory:": Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.execute("PRAGMA busy_timeout=10000")
        self._db.execute("PRAGMA synchronous=FULL")
        if self.path != ":memory:": self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript("""
        CREATE TABLE IF NOT EXISTS approvals (
          request_id TEXT PRIMARY KEY, state TEXT NOT NULL,
          binding_json BLOB NOT NULL, expires_at TEXT NOT NULL,
          action_digest TEXT NOT NULL, action_id TEXT NOT NULL,
          proposal_id TEXT NOT NULL, principal_binding TEXT NOT NULL, broker_operation_id TEXT NOT NULL,
          policy_version TEXT NOT NULL, risk_class TEXT NOT NULL, task_id TEXT NOT NULL, step_id TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS auth_refs (
          token_hash TEXT PRIMARY KEY, request_id TEXT NOT NULL REFERENCES approvals(request_id),
          state TEXT NOT NULL, expires_at TEXT NOT NULL, created_at TEXT NOT NULL, consumption_id TEXT
        );
        CREATE INDEX IF NOT EXISTS auth_refs_request ON auth_refs(request_id);
        CREATE TABLE IF NOT EXISTS audit_events (
          seq INTEGER PRIMARY KEY AUTOINCREMENT, event_json BLOB NOT NULL,
          previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL UNIQUE
        );
        """)

    def close(self) -> None:
        self._db.close()

    @staticmethod
    def _time(value: datetime | None = None) -> datetime:
        current = value or datetime.now(timezone.utc)
        if current.tzinfo is None: raise ValueError("timezone-aware timestamp required")
        return current.astimezone(timezone.utc)

    @staticmethod
    def _iso(value: datetime) -> str:
        return value.isoformat(timespec="microseconds").replace("+00:00", "Z")

    def _audit(self, event: Mapping[str, Any]) -> None:
        allowed = {"timestamp_utc", "event_type", "principal_binding", "origin", "proposal_id", "decision_id",
                   "operation_id", "risk_class", "policy_version", "action_digest", "approval_request_id",
                   "executor_id", "result_status", "reason_code", "correlation_id", "task_id", "step_id",
                   "registry_version", "registry_status", "transaction_id", "snapshot_digest",
                   "device_binding", "session_binding"}
        safe = _redact({k: v for k, v in dict(event).items() if k in allowed})
        safe.update(schema_version="0.2.0", event_id=str(uuid.uuid4()))
        required = {"schema_version", "event_id", "timestamp_utc", "event_type", "principal_binding", "origin",
                    "proposal_id", "decision_id", "operation_id", "risk_class", "policy_version", "action_digest",
                    "result_status", "correlation_id", "task_id", "step_id", "registry_version", "executor_id",
                    "reason_code", "registry_status"}
        if not required.issubset(safe): raise SecurityStoreError("audit event missing required v0.2.0 fields")
        statuses = {"requested":"accepted", "authorized":"success", "started":"pending", "succeeded":"success",
                    "failed":"failure", "cancellation_requested":"accepted", "cancelled":"cancelled",
                    "outcome_unknown":"unknown", "compensation_started":"pending", "compensation_verified":"success",
                    "compensation_failed":"failure", "approval_granted":"accepted", "approval_denied":"denied",
                    "approval_expired":"denied", "policy_denied":"denied"}
        if safe["event_type"] not in statuses or safe["result_status"] != statuses[safe["event_type"]]:
            raise SecurityStoreError("unsupported audit event or status mismatch")
        if safe["origin"] not in {"local", "remote", "extension", "system"}: raise SecurityStoreError("invalid audit origin")
        try:
            uuid.UUID(safe["proposal_id"])
            if safe["decision_id"] is not None: uuid.UUID(safe["decision_id"])
            stamp = datetime.fromisoformat(safe["timestamp_utc"].replace("Z", "+00:00"))
            if stamp.tzinfo is None: raise ValueError("timezone required")
        except (ValueError, TypeError, AttributeError) as exc:
            raise SecurityStoreError("invalid audit identifier or timestamp") from exc
        if (not isinstance(safe["operation_id"], str) or not 1 <= len(safe["operation_id"]) <= 160
            or not isinstance(safe["policy_version"], str) or not 1 <= len(safe["policy_version"]) <= 64
            or not isinstance(safe["correlation_id"], str) or not 1 <= len(safe["correlation_id"]) <= 128):
            raise SecurityStoreError("invalid audit correlation fields")
        for field in ("task_id", "step_id"):
            if safe[field] is not None and (not isinstance(safe[field], str) or len(safe[field]) > 128):
                raise SecurityStoreError("invalid task/step audit binding")
        if safe["executor_id"] is not None and (not isinstance(safe["executor_id"], str) or len(safe["executor_id"]) > 128):
            raise SecurityStoreError("invalid audit executor")
        if safe["reason_code"] is not None and (not isinstance(safe["reason_code"], str) or len(safe["reason_code"]) > 96):
            raise SecurityStoreError("invalid audit reason code")
        if safe.get("approval_request_id") is not None:
            try: uuid.UUID(safe["approval_request_id"])
            except (ValueError, TypeError) as exc: raise SecurityStoreError("invalid approval reference") from exc
        if safe["risk_class"] not in {"R0", "R1", "R2", "R3", "R4", "R5"}: raise SecurityStoreError("invalid audit risk class")
        for field in ("principal_binding", "action_digest"):
            if not isinstance(safe[field], str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", safe[field]):
                raise SecurityStoreError("invalid audit digest")
        if safe["registry_status"] not in {"resolved", "unavailable"}: raise SecurityStoreError("invalid registry status")
        if safe["registry_status"] == "resolved" and (not isinstance(safe["registry_version"], str) or not 1 <= len(safe["registry_version"]) <= 128):
            raise SecurityStoreError("resolved registry requires a version")
        if safe["registry_status"] == "unavailable" and safe["registry_version"] is not None:
            raise SecurityStoreError("unavailable registry cannot claim a version")
        if safe["registry_status"] == "unavailable" and not (
            safe["event_type"] == "requested" and safe["result_status"] == "accepted" and safe["reason_code"] is None
            or safe["event_type"] == "policy_denied" and safe["result_status"] == "denied" and safe["reason_code"] == "POLICY_REGISTRY_UNAVAILABLE"):
            raise SecurityStoreError("invalid unavailable-registry event")
        if ("transaction_id" in safe) != ("snapshot_digest" in safe): raise SecurityStoreError("transaction/snapshot fields must appear together")
        if "snapshot_digest" in safe and (not isinstance(safe["snapshot_digest"], str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", safe["snapshot_digest"])):
            raise SecurityStoreError("invalid snapshot digest")
        if safe["origin"] == "remote":
            for field in ("device_binding", "session_binding"):
                if not isinstance(safe.get(field), str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", safe[field]):
                    raise SecurityStoreError("remote audit requires device/session digests")
        elif "device_binding" in safe or "session_binding" in safe:
            raise SecurityStoreError("local audit cannot contain remote identity bindings")
        if safe["result_status"] in {"denied", "failure"} and not safe["reason_code"]:
            raise SecurityStoreError("denial/failure requires reason code")
        payload = canonical_bytes(safe)
        row = self._db.execute("SELECT event_hash FROM audit_events ORDER BY seq DESC LIMIT 1").fetchone()
        previous = row["event_hash"] if row else "0" * 64
        event_hash = hmac.new(self._audit_key, bytes.fromhex(previous) + payload, hashlib.sha256).hexdigest()
        self._db.execute("INSERT INTO audit_events(event_json, previous_hash, event_hash) VALUES (?, ?, ?)", (payload, previous, event_hash))

    def _transaction(self) -> None:
        self._db.execute("BEGIN IMMEDIATE")

    def create_approval(self, *, action_id: str, broker_operation_id: str, action_digest: str,
                        proposal_id: str, principal_binding: str, policy_version: str, risk_class: str,
                        task_id: str, step_id: str, binding: Mapping[str, Any], expires_at: datetime,
                        audit_context: Mapping[str, Any], now: datetime | None = None) -> str:
        current, expiry = (self._time(now), self._time(expires_at))
        if expiry <= current: raise SecurityStoreError("approval expiry must be in the future")
        op = r"[a-z][a-z0-9]*(\.[a-z][a-z0-9_-]*)+"
        if not isinstance(action_id, str) or not re.fullmatch(op, action_id) or not isinstance(broker_operation_id, str) or not re.fullmatch(op, broker_operation_id):
            raise SecurityStoreError("invalid fixed operation binding")
        if not policy_version or len(policy_version) > 64 or risk_class not in {"R0", "R1", "R2", "R3", "R4"}:
            raise SecurityStoreError("approval not permitted for this policy version/risk")
        if not task_id or len(task_id) > 128 or not step_id or len(step_id) > 128:
            raise SecurityStoreError("task and step correlation required")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", action_digest) or not re.fullmatch(r"sha256:[0-9a-f]{64}", principal_binding):
            raise SecurityStoreError("invalid digest binding")
        required = {"session_binding", "device_binding", "registry_version", "resource_scope", "precondition_digest"}
        if set(binding) != required or not isinstance(binding["resource_scope"], list) or not binding["resource_scope"]:
            raise SecurityStoreError("incomplete approval binding")
        for field in ("session_binding", "device_binding", "precondition_digest"):
            if not isinstance(binding[field], str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", binding[field]):
                raise SecurityStoreError("invalid approval binding digest")
        if not isinstance(binding["registry_version"], str) or not 1 <= len(binding["registry_version"]) <= 128:
            raise SecurityStoreError("invalid registry binding")
        if any(not isinstance(x, str) or not x or len(x) > 512 for x in binding["resource_scope"]) or len(binding["resource_scope"]) != len(set(binding["resource_scope"])):
            raise SecurityStoreError("invalid canonical resource scope")
        try: uuid.UUID(proposal_id)
        except (ValueError, TypeError) as exc: raise SecurityStoreError("invalid proposal UUID") from exc
        request_id = str(uuid.uuid4())
        try:
            self._transaction()
            self._db.execute("INSERT INTO approvals VALUES (?, 'PENDING', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (request_id, canonical_bytes(dict(binding)), self._iso(expiry), action_digest, action_id, proposal_id,
                 principal_binding, broker_operation_id, policy_version, risk_class, task_id, step_id, self._iso(current)))
            self._audit({**audit_context, "event_type":"requested", "approval_request_id":request_id,
                         "action_digest":action_digest, "result_status":"accepted", "timestamp_utc":self._iso(current)})
            self._db.execute("COMMIT")
            return request_id
        except Exception as exc:
            if self._db.in_transaction: self._db.execute("ROLLBACK")
            raise SecurityStoreError("approval creation/audit failed closed") from exc

    def decide(self, request_id: str, *, approve: bool, current_binding: Mapping[str, Any],
               approver_credentials: Any, audit_context: Mapping[str, Any], now: datetime | None = None) -> str:
        current = self._time(now)
        if self._approver_authenticator is None: return "CALLER_UNAUTHORIZED"
        try:
            if not self._approver_authenticator(approver_credentials, request_id): return "CALLER_UNAUTHORIZED"
        except Exception: return "CALLER_UNAUTHORIZED"
        try:
            self._transaction()
            row = self._db.execute("SELECT * FROM approvals WHERE request_id=?", (request_id,)).fetchone()
            if row is None or row["state"] != "PENDING":
                self._db.execute("ROLLBACK")
                return "NOT_PENDING"
            if current >= datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00")):
                self._db.execute("UPDATE approvals SET state='EXPIRED' WHERE request_id=?", (request_id,))
                self._audit({**audit_context, "event_type":"approval_expired", "approval_request_id":request_id,
                             "result_status":"denied", "reason_code":"POLICY_APPROVAL_EXPIRED", "timestamp_utc":self._iso(current)})
                self._db.execute("COMMIT")
                return "EXPIRED"
            if canonical_bytes(dict(current_binding)) != bytes(row["binding_json"]):
                self._db.execute("UPDATE approvals SET state='INVALIDATED' WHERE request_id=?", (request_id,))
                self._audit({**audit_context, "event_type":"policy_denied", "approval_request_id":request_id,
                             "result_status":"denied", "reason_code":"POLICY_BINDING_MISMATCH", "timestamp_utc":self._iso(current)})
                self._db.execute("COMMIT")
                return "INVALIDATED"
            state = "APPROVED" if approve else "DENIED"
            self._db.execute("UPDATE approvals SET state=? WHERE request_id=? AND state='PENDING'", (state, request_id))
            self._audit({**audit_context, "event_type":"approval_granted" if approve else "approval_denied",
                         "approval_request_id":request_id, "result_status":"accepted" if approve else "denied",
                         "timestamp_utc":self._iso(current)})
            self._db.execute("COMMIT")
            return state
        except Exception as exc:
            if self._db.in_transaction: self._db.execute("ROLLBACK")
            raise SecurityStoreError("approval decision/audit failed closed") from exc

    def issue_authorization(self, request_id: str, *, current_binding: Mapping[str, Any],
                            current_policy_version: str, audit_context: Mapping[str, Any],
                            ttl_seconds: int = 30, now: datetime | None = None) -> str:
        current = self._time(now)
        if not 1 <= ttl_seconds <= 120: raise SecurityStoreError("authorization TTL outside policy bound")
        token, token_hash = (secrets.token_urlsafe(32), None)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        try:
            self._transaction()
            row = self._db.execute("SELECT * FROM approvals WHERE request_id=?", (request_id,)).fetchone()
            if row is None or row["state"] != "APPROVED":
                self._db.execute("ROLLBACK")
                raise SecurityStoreError("approval is not approved")
            if self._policy_rechecker is None or not self._policy_rechecker(request_id, current_binding, current_policy_version):
                self._db.execute("UPDATE approvals SET state='INVALIDATED' WHERE request_id=?", (request_id,))
                self._audit({**audit_context, "event_type":"policy_denied", "approval_request_id":request_id,
                             "result_status":"denied", "reason_code":"POLICY_REEVALUATION_FAILED", "timestamp_utc":self._iso(current)})
                self._db.execute("COMMIT")
                raise SecurityStoreError("current policy re-evaluation unavailable or denied")
            if current >= datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00")) or canonical_bytes(dict(current_binding)) != bytes(row["binding_json"]) or current_policy_version != row["policy_version"]:
                self._db.execute("UPDATE approvals SET state='INVALIDATED' WHERE request_id=?", (request_id,))
                self._audit({**audit_context, "event_type":"policy_denied", "approval_request_id":request_id,
                             "result_status":"denied", "reason_code":"POLICY_BINDING_MISMATCH", "timestamp_utc":self._iso(current)})
                self._db.execute("COMMIT")
                raise SecurityStoreError("approval expired or binding changed")
            self._db.execute("UPDATE auth_refs SET state='REVOKED' WHERE request_id=? AND state='ISSUED'", (request_id,))
            approval_expiry = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
            expiry = self._iso(min(current + timedelta(seconds=ttl_seconds), approval_expiry))
            self._db.execute("INSERT INTO auth_refs(token_hash,request_id,state,expires_at,created_at,consumption_id) VALUES (?,?,'ISSUED',?,?,NULL)",
                             (token_hash, request_id, expiry, self._iso(current)))
            self._audit({**audit_context, "event_type":"authorized", "approval_request_id":request_id,
                         "result_status":"success", "timestamp_utc":self._iso(current)})
            self._db.execute("COMMIT")
            return token
        except SecurityStoreError: raise
        except Exception as exc:
            if self._db.in_transaction: self._db.execute("ROLLBACK")
            raise SecurityStoreError("authorization issue/audit failed closed") from exc

    def consume(self, authorization_ref: str, *, operation_id: str, resource_scope: list[str],
                action_digest: str, policy_version: str, registry_version: str, precondition_digest: str,
                peer_credentials: Any, audit_context: Mapping[str, Any], now: datetime | None = None) -> ConsumeResult:
        current = self._time(now)
        if self._peer_authenticator is None: return ConsumeResult("CALLER_UNAUTHORIZED")
        try: peer = self._peer_authenticator(peer_credentials)
        except Exception: return ConsumeResult("CALLER_UNAUTHORIZED")
        if not isinstance(peer, Mapping) or peer.get("authenticated") is not True: return ConsumeResult("CALLER_UNAUTHORIZED")
        if not authorization_ref or not isinstance(authorization_ref, str): return ConsumeResult("BINDING_MISMATCH")
        token_hash = hashlib.sha256(authorization_ref.encode()).hexdigest()
        try:
            self._transaction()
            row = self._db.execute("""SELECT a.*, r.state AS ref_state, r.expires_at AS ref_expiry,
                r.consumption_id AS consumption_id FROM auth_refs r JOIN approvals a
                ON a.request_id=r.request_id WHERE r.token_hash=?""", (token_hash,)).fetchone()
            if row is None:
                self._db.execute("ROLLBACK")
                return ConsumeResult("BINDING_MISMATCH")
            if row["ref_state"] == "CONSUMED":
                cid = row["consumption_id"]
                self._audit({**audit_context, "event_type":"policy_denied", "result_status":"denied",
                             "reason_code":"POLICY_APPROVAL_REPLAYED", "timestamp_utc":self._iso(current)})
                self._db.execute("COMMIT")
                return ConsumeResult("ALREADY_CONSUMED", cid)
            if row["ref_state"] != "ISSUED" or row["state"] != "APPROVED":
                outcome = "REVOKED" if row["ref_state"] == "REVOKED" else "NOT_APPROVED"
                self._audit({**audit_context, "event_type":"policy_denied", "result_status":"denied",
                             "reason_code":"POLICY_AUTHORIZATION_NOT_ACTIVE", "timestamp_utc":self._iso(current)})
                self._db.execute("COMMIT")
                return ConsumeResult(outcome)
            if current >= datetime.fromisoformat(row["ref_expiry"].replace("Z", "+00:00")) or current >= datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00")):
                self._db.execute("UPDATE auth_refs SET state='EXPIRED' WHERE token_hash=?", (token_hash,))
                self._audit({**audit_context, "event_type":"policy_denied", "result_status":"denied",
                             "reason_code":"POLICY_AUTHORIZATION_EXPIRED", "timestamp_utc":self._iso(current)})
                self._db.execute("COMMIT")
                return ConsumeResult("EXPIRED")
            binding = json.loads(bytes(row["binding_json"]).decode("utf-8"))
            peer_matches = row["principal_binding"] == peer.get("principal_binding") and binding["session_binding"] == peer.get("session_binding") and binding["device_binding"] == peer.get("device_binding")
            policy_current = self._policy_rechecker is not None and self._policy_rechecker(row["request_id"], binding, policy_version)
            exact = row["broker_operation_id"] == operation_id and row["action_digest"] == action_digest and row["policy_version"] == policy_version and policy_current and binding["registry_version"] == registry_version and binding["precondition_digest"] == precondition_digest and binding["resource_scope"] == resource_scope and peer_matches
            if not exact:
                self._db.execute("UPDATE approvals SET state='INVALIDATED' WHERE request_id=?", (row["request_id"],))
                self._db.execute("UPDATE auth_refs SET state='REVOKED' WHERE request_id=? AND state='ISSUED'", (row["request_id"],))
                self._audit({**audit_context, "event_type":"policy_denied", "result_status":"denied",
                             "reason_code":"POLICY_BINDING_MISMATCH", "timestamp_utc":self._iso(current)})
                self._db.execute("COMMIT")
                return ConsumeResult("BINDING_MISMATCH")
            cid = str(uuid.uuid4())
            self._db.execute("UPDATE auth_refs SET state='CONSUMED',consumption_id=? WHERE token_hash=? AND state='ISSUED'", (cid, token_hash))
            self._db.execute("UPDATE approvals SET state='CONSUMED' WHERE request_id=? AND state='APPROVED'", (row["request_id"],))
            try:
                self._audit({**audit_context, "event_type":"authorized", "result_status":"success", "timestamp_utc":self._iso(current)})
            except Exception:
                self._db.execute("ROLLBACK")
                return ConsumeResult("AUDIT_UNAVAILABLE")
            try: self._db.execute("COMMIT")
            except Exception:
                if self._db.in_transaction: self._db.execute("ROLLBACK")
                return ConsumeResult("CONSUME_OUTCOME_UNKNOWN", cid)
            grant = {"consumption_id":cid, "operation_id":operation_id, "resource_scope":list(resource_scope),
                     "principal_binding":row["principal_binding"], "session_binding":binding["session_binding"],
                     "device_binding":binding["device_binding"], "action_digest":action_digest,
                     "registry_version":registry_version, "precondition_digest":precondition_digest}
            return ConsumeResult("CONSUMED", cid, grant)
        except Exception:
            if self._db.in_transaction: self._db.execute("ROLLBACK")
            return ConsumeResult("AUTHORITY_UNAVAILABLE")

    def reconcile(self, authorization_ref: str, *, peer_credentials: Any) -> ConsumeResult:
        if self._peer_authenticator is None: return ConsumeResult("CALLER_UNAUTHORIZED")
        try: peer = self._peer_authenticator(peer_credentials)
        except Exception: return ConsumeResult("CALLER_UNAUTHORIZED")
        if not isinstance(peer, Mapping) or peer.get("authenticated") is not True: return ConsumeResult("CALLER_UNAUTHORIZED")
        token_hash = hashlib.sha256(authorization_ref.encode()).hexdigest()
        row = self._db.execute("SELECT state,consumption_id FROM auth_refs WHERE token_hash=?", (token_hash,)).fetchone()
        if row is None: return ConsumeResult("BINDING_MISMATCH")
        if row["state"] == "CONSUMED": return ConsumeResult("ALREADY_CONSUMED", row["consumption_id"])
        return ConsumeResult(row["state"])

    def audit_events(self) -> list[dict[str, Any]]:
        return [json.loads(bytes(row["event_json"]).decode("utf-8"))
                for row in self._db.execute("SELECT event_json FROM audit_events ORDER BY seq")]

    def audit_checkpoint(self) -> dict[str, Any]:
        """Create an externally storable authenticated chain checkpoint.

        Store the returned object outside this database (e.g. remote append-only
        storage). A local-only checkpoint cannot detect database rollback.
        """
        row = self._db.execute("SELECT seq,event_hash FROM audit_events ORDER BY seq DESC LIMIT 1").fetchone()
        seq, event_hash = (row["seq"], row["event_hash"]) if row else (0, "0" * 64)
        payload = {"schema_version": "1", "sequence": seq, "event_hash": event_hash}
        mac = hmac.new(self._audit_key, b"TUSKER-AUDIT-CHECKPOINT-v1\\0" + canonical_bytes(payload), hashlib.sha256).hexdigest()
        return {**payload, "mac": mac}

    def verify_audit_chain(self, checkpoint: Mapping[str, Any] | None = None) -> bool:
        previous = "0" * 64
        checkpoint_seq = 0
        checkpoint_hash = "0" * 64
        try:
            if checkpoint is not None:
                if set(checkpoint) != {"schema_version", "sequence", "event_hash", "mac"}:
                    return False
                if checkpoint["schema_version"] != "1" or not isinstance(checkpoint["sequence"], int) or checkpoint["sequence"] < 0:
                    return False
                if not isinstance(checkpoint["event_hash"], str) or not re.fullmatch(r"[0-9a-f]{64}", checkpoint["event_hash"]):
                    return False
                payload = {key: checkpoint[key] for key in ("schema_version", "sequence", "event_hash")}
                expected_mac = hmac.new(self._audit_key, b"TUSKER-AUDIT-CHECKPOINT-v1\\0" + canonical_bytes(payload), hashlib.sha256).hexdigest()
                if not isinstance(checkpoint["mac"], str) or not hmac.compare_digest(checkpoint["mac"], expected_mac):
                    return False
                checkpoint_seq, checkpoint_hash = checkpoint["sequence"], checkpoint["event_hash"]
            seen_checkpoint = checkpoint_seq == 0
            for row in self._db.execute("SELECT seq,event_json,previous_hash,event_hash FROM audit_events ORDER BY seq"):
                payload = bytes(row["event_json"])
                expected = hmac.new(self._audit_key, bytes.fromhex(previous) + payload, hashlib.sha256).hexdigest()
                if row["previous_hash"] != previous or not hmac.compare_digest(row["event_hash"], expected):
                    return False
                previous = row["event_hash"]
                if row["seq"] == checkpoint_seq:
                    if not hmac.compare_digest(row["event_hash"], checkpoint_hash):
                        return False
                    seen_checkpoint = True
            return seen_checkpoint
        except (ValueError, TypeError, KeyError):
            return False

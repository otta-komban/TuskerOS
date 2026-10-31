"""Deterministic deny-by-default policy evaluation; no execution side effects."""
from __future__ import annotations
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence, Callable
from .canonical import CanonicalizationError, canonical_bytes, digest

_RISKS = ("R0", "R1", "R2", "R3", "R4", "R5")
_ORIGINS = {"local", "remote", "extension", "system"}
_ACCESS = {"read", "create", "modify", "delete", "execute", "administer"}
_ACTION = re.compile(r"^[a-z][a-z0-9]*(\.[a-z][a-z0-9_-]*)+$")

@dataclass(frozen=True)
class PolicyResult:
    status: str
    reason_code: str
    action_digest: str | None = None
    risk_class: str | None = None
    approval_required: bool = False
    precondition_digest: str | None = None

class PolicyEngine:
    """Pure evaluator. Every injected dependency must be supplied by a trusted adapter."""
    def __init__(self, policy_version: str, *,
                 identity_verifier: Callable[[Mapping[str, Any]], bool] | None = None,
                 registry_verifier: Callable[[Sequence[Mapping[str, Any]], str], bool] | None = None,
                 argument_validator: Callable[[str, Mapping[str, Any]], bool] | None = None,
                 resource_resolver: Callable[[Sequence[Mapping[str, Any]]], Sequence[Mapping[str, Any]]] | None = None,
                 precondition_verifier: Callable[[Mapping[str, Any], Sequence[Mapping[str, Any]]], str | None] | None = None):
        if not policy_version or len(policy_version) > 64:
            raise ValueError("invalid policy version")
        self.policy_version = policy_version
        self.identity_verifier = identity_verifier
        self.registry_verifier = registry_verifier
        self.argument_validator = argument_validator
        self.resource_resolver = resource_resolver
        self.precondition_verifier = precondition_verifier

    def evaluate(self, proposal: Mapping[str, Any], context: Mapping[str, Any],
                 registry: Sequence[Mapping[str, Any]], registry_version: str) -> PolicyResult:
        deny = lambda code: PolicyResult("DENY", code)
        try:
            if not isinstance(proposal, Mapping) or not isinstance(context, Mapping):
                return deny("POLICY_INVALID_INPUT")
            if not registry or not registry_version or self.registry_verifier is None:
                return deny("POLICY_REGISTRY_UNAVAILABLE")
            if not self.registry_verifier(registry, registry_version):
                return deny("POLICY_REGISTRY_UNAVAILABLE")
            if self.identity_verifier is None or not self.identity_verifier(context):
                return deny("POLICY_UNKNOWN_PRINCIPAL")
            for field in ("principal_binding", "session_binding", "device_binding"):
                if not isinstance(context.get(field), str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", context[field]):
                    return deny("POLICY_IDENTITY_UNAVAILABLE")
            origin, principal_class = context.get("origin"), context.get("principal_class")
            if origin not in _ORIGINS or not isinstance(principal_class, str):
                return deny("POLICY_UNKNOWN_PRINCIPAL")
            required = {"schema_version", "action_id", "proposal_id", "task_id", "step_id", "arguments", "resources", "requested_at"}
            if not required.issubset(proposal) or set(proposal) - (required | {"idempotency_key"}):
                return deny("POLICY_INVALID_ARGUMENTS")
            if proposal.get("schema_version") != "0.1.0" or not _ACTION.fullmatch(str(proposal.get("action_id", ""))):
                return deny("POLICY_INVALID_ARGUMENTS")
            try:
                uuid.UUID(str(proposal["proposal_id"]))
                requested = datetime.fromisoformat(str(proposal["requested_at"]).replace("Z", "+00:00"))
                if requested.tzinfo is None: return deny("POLICY_INVALID_ARGUMENTS")
            except (ValueError, TypeError):
                return deny("POLICY_INVALID_ARGUMENTS")
            for field in ("task_id", "step_id"):
                if not isinstance(proposal[field], str) or not proposal[field] or len(proposal[field]) > 128:
                    return deny("POLICY_INVALID_ARGUMENTS")
            if not isinstance(proposal["arguments"], dict) or not isinstance(proposal["resources"], list):
                return deny("POLICY_INVALID_ARGUMENTS")
            if self.argument_validator is None or not self.argument_validator(proposal["action_id"], proposal["arguments"]):
                return deny("POLICY_INVALID_ARGUMENTS")
            if self.resource_resolver is None or self.precondition_verifier is None:
                return deny("POLICY_DEPENDENCY_UNAVAILABLE")
            matches = [entry for entry in registry if entry.get("action_id") == proposal["action_id"]]
            if len(matches) != 1: return deny("POLICY_UNKNOWN_ACTION")
            entry = matches[0]
            if (entry.get("schema_version") != "0.1.0" or entry.get("minimum_risk_class") not in _RISKS
                or entry.get("approval_mode") not in {"never", "on_escalation", "always", "out_of_band_admin"}
                or entry.get("idempotency") not in {"required", "optional_read_only", "not_supported"}
                or not isinstance(entry.get("broker_operation_id"), str)
                or not _ACTION.fullmatch(entry.get("broker_operation_id", ""))
                or not isinstance(entry.get("timeout_ms"), int) or not 1 <= entry["timeout_ms"] <= 3600000
                or not isinstance(entry.get("allowed_origins"), list) or not entry.get("allowed_origins")
                or not isinstance(entry.get("allowed_principal_classes"), list) or not entry.get("allowed_principal_classes")
                or not isinstance(entry.get("resources"), list) or not entry.get("resources")):
                return deny("POLICY_REGISTRY_INVALID")
            minimum = entry["minimum_risk_class"]
            if ((minimum == "R2" and entry["approval_mode"] not in {"on_escalation", "always"})
                or (minimum in {"R3", "R4"} and entry["approval_mode"] != "always")
                or (minimum == "R5" and entry["approval_mode"] != "out_of_band_admin")):
                return deny("POLICY_REGISTRY_INVALID")
            if entry.get("risk_escalation_rules"): return deny("POLICY_RISK_RULE_UNSUPPORTED")
            max_input = entry.get("max_input_bytes", 10485760)
            if not isinstance(max_input, int) or not 1 <= max_input <= 10485760:
                return deny("POLICY_REGISTRY_INVALID")
            if len(canonical_bytes(proposal)) > max_input: return deny("POLICY_INPUT_LIMIT")
            if origin not in entry["allowed_origins"] or principal_class not in entry["allowed_principal_classes"]:
                return deny("POLICY_SCOPE_EXCEEDED")
            resources = proposal["resources"]
            if len(resources) > 128: return deny("POLICY_SCOPE_EXCEEDED")
            allowed = {item["kind"]: set(item["access_modes"]) for item in entry["resources"]
                       if isinstance(item, Mapping) and isinstance(item.get("kind"), str)
                       and isinstance(item.get("access_modes"), list)}
            normalized, seen = ([], set())
            for resource in resources:
                if not isinstance(resource, Mapping) or set(resource) != {"kind", "id", "access"}:
                    return deny("POLICY_INVALID_RESOURCE")
                kind, rid, access = resource["kind"], resource["id"], resource["access"]
                if not isinstance(kind, str) or not 1 <= len(kind) <= 64 or not isinstance(rid, str) or not 1 <= len(rid) <= 1024 or access not in _ACCESS:
                    return deny("POLICY_INVALID_RESOURCE")
                if kind not in allowed or access not in allowed[kind]: return deny("POLICY_SCOPE_EXCEEDED")
                key = (kind, rid, access)
                if key in seen: return deny("POLICY_INVALID_RESOURCE")
                seen.add(key)
                normalized.append({"kind": kind, "id": rid, "access": access})
            resolved = list(self.resource_resolver(normalized))
            if not all(isinstance(item, Mapping) and set(item) == {"kind", "id", "access"} for item in resolved):
                return deny("POLICY_RESOURCE_RESOLUTION_MISMATCH")
            keys = [(item["kind"], item["id"], item["access"]) for item in resolved]
            if len(keys) != len(set(keys)): return deny("POLICY_RESOURCE_RESOLUTION_MISMATCH")
            for item in resolved:
                if item["kind"] not in allowed or item["access"] not in allowed[item["kind"]] or not isinstance(item["id"], str) or not item["id"]:
                    return deny("POLICY_RESOURCE_RESOLUTION_MISMATCH")
            normalized = resolved
            precondition_digest = self.precondition_verifier(proposal, resolved)
            if not isinstance(precondition_digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", precondition_digest):
                return deny("POLICY_PRECONDITION_FAILED")
            mutating = any(item["access"] != "read" for item in normalized)
            if mutating and entry["idempotency"] != "required": return deny("POLICY_IDEMPOTENCY_REQUIRED")
            if entry["idempotency"] == "required" and (not isinstance(proposal.get("idempotency_key"), str) or not 16 <= len(proposal["idempotency_key"]) <= 128):
                return deny("POLICY_IDEMPOTENCY_REQUIRED")
            risk = minimum
            if mutating:
                risk = "R4" if any(item["access"] in {"delete", "administer"} for item in normalized) else "R3"
                if minimum in {"R4", "R5"}: risk = minimum
            if risk == "R5" or entry["approval_mode"] == "out_of_band_admin":
                return deny("POLICY_R5_OUT_OF_BAND_DENY")
            envelope = {"schema_version": proposal["schema_version"], "action_id": proposal["action_id"],
                "proposal_id": proposal["proposal_id"], "task_id": proposal["task_id"], "step_id": proposal["step_id"],
                "arguments": proposal["arguments"], "resources": sorted(normalized, key=lambda r: (r["kind"], r["id"], r["access"])),
                "idempotency_key": proposal.get("idempotency_key"), "principal_binding": context["principal_binding"],
                "session_binding": context["session_binding"], "device_binding": context["device_binding"],
                "broker_operation_id": entry["broker_operation_id"], "operation_schema_version": entry.get("operation_schema_version"),
                "principal_class": principal_class, "origin": origin, "precondition_digest": precondition_digest,
                "policy_version": self.policy_version, "registry_version": registry_version}
            action_digest = digest(envelope)
            if risk in {"R2", "R3", "R4"} or entry["approval_mode"] == "always":
                return PolicyResult("REQUIRE_APPROVAL", "POLICY_RISK_REQUIRES_APPROVAL", action_digest, risk, True, precondition_digest)
            return PolicyResult("ALLOW", "POLICY_ALLOW_REGISTERED_LOW_RISK", action_digest, risk, False, precondition_digest)
        except (KeyError, TypeError, ValueError, CanonicalizationError):
            return deny("POLICY_INVALID_OR_UNTRUSTED_DATA")
        except Exception:
            return deny("POLICY_INTERNAL_ERROR")

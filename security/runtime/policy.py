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


def _valid_registry_entry(entry: Mapping[str, Any]) -> bool:
    """Validate the complete operation-registration v0.1.0 shape before use."""
    required = {"schema_version", "action_id", "operation_schema_version",
        "arguments_schema_ref", "allowed_principal_classes", "allowed_origins",
        "resources", "minimum_risk_class", "approval_mode", "broker_operation_id",
        "timeout_ms", "idempotency", "preconditions", "postcondition_verifier"}
    optional = {"max_input_bytes", "rate_limit", "risk_escalation_rules"}
    if not required.issubset(entry) or set(entry) - required - optional:
        return False
    if entry.get("schema_version") != "0.1.0":
        return False
    for field in ("action_id", "broker_operation_id"):
        value = entry.get(field)
        if not isinstance(value, str) or len(value) > 160 or not _ACTION.fullmatch(value):
            return False
    version = entry.get("operation_schema_version")
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        return False
    schema_ref = entry.get("arguments_schema_ref")
    if not isinstance(schema_ref, str) or not 1 <= len(schema_ref) <= 512:
        return False
    if not isinstance(entry.get("minimum_risk_class"), str) or entry["minimum_risk_class"] not in _RISKS:
        return False
    if not isinstance(entry.get("approval_mode"), str) or entry["approval_mode"] not in {"never", "on_escalation", "always", "out_of_band_admin"}:
        return False
    if not isinstance(entry.get("idempotency"), str) or entry["idempotency"] not in {"required", "optional_read_only", "not_supported"}:
        return False
    timeout = entry.get("timeout_ms")
    if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 3600000:
        return False
    if "max_input_bytes" in entry:
        limit = entry["max_input_bytes"]
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 10485760:
            return False
    origins = entry.get("allowed_origins")
    if (not isinstance(origins, list) or not origins
        or any(not isinstance(value, str) or value not in _ORIGINS for value in origins)
        or len(origins) != len(set(origins))):
        return False
    principals = entry.get("allowed_principal_classes")
    if (not isinstance(principals, list) or not principals
        or any(not isinstance(value, str) or not 1 <= len(value) <= 64 for value in principals)
        or len(principals) != len(set(principals))):
        return False
    resources = entry.get("resources")
    if not isinstance(resources, list) or not 1 <= len(resources) <= 32:
        return False
    for declaration in resources:
        if (not isinstance(declaration, Mapping) or set(declaration) != {"kind", "access_modes"}
            or not isinstance(declaration.get("kind"), str)
            or not 1 <= len(declaration["kind"]) <= 64
            or not isinstance(declaration.get("access_modes"), list)
            or not declaration["access_modes"]
            or any(not isinstance(mode, str) or mode not in _ACCESS for mode in declaration["access_modes"])
            or len(declaration["access_modes"]) != len(set(declaration["access_modes"]))):
            return False
    if len({item["kind"] for item in resources}) != len(resources):
        return False
    preconditions = entry.get("preconditions")
    if (not isinstance(preconditions, list) or len(preconditions) > 64
        or any(not isinstance(value, str) or not 1 <= len(value) <= 256 for value in preconditions)):
        return False
    verifier = entry.get("postcondition_verifier")
    if not isinstance(verifier, str) or not 1 <= len(verifier) <= 160:
        return False
    if "risk_escalation_rules" in entry:
        rules = entry["risk_escalation_rules"]
        if (not isinstance(rules, list) or len(rules) > 64
            or any(not isinstance(value, str) or not 1 <= len(value) <= 256 for value in rules)):
            return False
    if "rate_limit" in entry:
        rate = entry["rate_limit"]
        if not isinstance(rate, Mapping) or set(rate) - {"max_calls", "window_seconds"}:
            return False
        for value in rate.values():
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                return False
    minimum, mode = entry["minimum_risk_class"], entry["approval_mode"]
    if ((minimum == "R2" and mode not in {"on_escalation", "always"})
        or (minimum in {"R3", "R4"} and mode != "always")
        or (minimum == "R5" and mode != "out_of_band_admin")):
        return False
    return True

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
        if not isinstance(policy_version, str) or not 1 <= len(policy_version) <= 64:
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
            if (not isinstance(registry, Sequence) or isinstance(registry, (str, bytes))
                or not registry or not isinstance(registry_version, str)
                or not 1 <= len(registry_version) <= 64 or self.registry_verifier is None):
                return deny("POLICY_REGISTRY_UNAVAILABLE")
            if any(not isinstance(item, Mapping) for item in registry):
                return deny("POLICY_REGISTRY_INVALID")
            if self.registry_verifier(registry, registry_version) is not True:
                return deny("POLICY_REGISTRY_UNAVAILABLE")
            # Validate every signed registry entry before selecting an action. A malformed
            # unrelated entry invalidates the registry as a whole; lookup must not hide it.
            if any(not _valid_registry_entry(item) for item in registry):
                return deny("POLICY_REGISTRY_INVALID")
            if self.identity_verifier is None or self.identity_verifier(context) is not True:
                return deny("POLICY_UNKNOWN_PRINCIPAL")
            for field in ("principal_binding", "session_binding", "device_binding"):
                if not isinstance(context.get(field), str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", context[field]):
                    return deny("POLICY_IDENTITY_UNAVAILABLE")
            origin, principal_class = context.get("origin"), context.get("principal_class")
            if (origin not in _ORIGINS or not isinstance(principal_class, str)
                or not 1 <= len(principal_class) <= 64):
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
            if self.argument_validator is None or self.argument_validator(proposal["action_id"], proposal["arguments"]) is not True:
                return deny("POLICY_INVALID_ARGUMENTS")
            if self.resource_resolver is None or self.precondition_verifier is None:
                return deny("POLICY_DEPENDENCY_UNAVAILABLE")
            matches = [entry for entry in registry if entry.get("action_id") == proposal["action_id"]]
            if len(matches) != 1: return deny("POLICY_UNKNOWN_ACTION")
            entry = matches[0]
            if not _valid_registry_entry(entry):
                return deny("POLICY_REGISTRY_INVALID")
            if (entry.get("schema_version") != "0.1.0" or entry.get("minimum_risk_class") not in _RISKS
                or entry.get("approval_mode") not in {"never", "on_escalation", "always", "out_of_band_admin"}
                or entry.get("idempotency") not in {"required", "optional_read_only", "not_supported"}
                or not isinstance(entry.get("broker_operation_id"), str)
                or not _ACTION.fullmatch(entry.get("broker_operation_id", ""))
                or not isinstance(entry.get("timeout_ms"), int) or isinstance(entry.get("timeout_ms"), bool) or not 1 <= entry["timeout_ms"] <= 3600000
                or not isinstance(entry.get("allowed_origins"), list) or not entry.get("allowed_origins")
                or any(not isinstance(value, str) or value not in _ORIGINS for value in entry["allowed_origins"])
                or len(entry["allowed_origins"]) != len(set(entry["allowed_origins"]))
                or not isinstance(entry.get("allowed_principal_classes"), list) or not entry.get("allowed_principal_classes")
                or any(not isinstance(value, str) or not 1 <= len(value) <= 64
                       for value in entry["allowed_principal_classes"])
                or len(entry["allowed_principal_classes"]) != len(set(entry["allowed_principal_classes"]))
                or not isinstance(entry.get("resources"), list) or not entry.get("resources")):
                return deny("POLICY_REGISTRY_INVALID")
            minimum = entry["minimum_risk_class"]
            if ((minimum == "R2" and entry["approval_mode"] not in {"on_escalation", "always"})
                or (minimum in {"R3", "R4"} and entry["approval_mode"] != "always")
                or (minimum == "R5" and entry["approval_mode"] != "out_of_band_admin")):
                return deny("POLICY_REGISTRY_INVALID")
            if entry.get("risk_escalation_rules"): return deny("POLICY_RISK_RULE_UNSUPPORTED")
            # Do not treat configured quota metadata as an enforced control.
            # A trusted shared limiter must exist before this policy can allow it.
            if "rate_limit" in entry: return deny("POLICY_RATE_LIMIT_UNSUPPORTED")
            max_input = entry.get("max_input_bytes", 10485760)
            if not isinstance(max_input, int) or isinstance(max_input, bool) or not 1 <= max_input <= 10485760:
                return deny("POLICY_REGISTRY_INVALID")
            if len(canonical_bytes(proposal)) > max_input: return deny("POLICY_INPUT_LIMIT")
            if origin not in entry["allowed_origins"] or principal_class not in entry["allowed_principal_classes"]:
                return deny("POLICY_SCOPE_EXCEEDED")
            resources = proposal["resources"]
            # Every registered operation declares concrete resource kinds. An
            # empty proposal scope cannot be authorized against that declaration.
            if not resources or len(resources) > 128:
                return deny("POLICY_SCOPE_EXCEEDED")
            # Registry resource declarations are security policy, not best-effort
            # hints. Reject malformed or ambiguous declarations rather than
            # silently dropping entries or allowing duplicate kinds to overwrite.
            allowed = {}
            for declaration in entry["resources"]:
                if (not isinstance(declaration, Mapping)
                    or set(declaration) != {"kind", "access_modes"}
                    or not isinstance(declaration.get("kind"), str)
                    or not 1 <= len(declaration["kind"]) <= 64
                    or not isinstance(declaration.get("access_modes"), list)
                    or not declaration["access_modes"]
                    or declaration["kind"] in allowed
                    or any(not isinstance(mode, str) or mode not in _ACCESS
                           for mode in declaration["access_modes"])
                    or len(declaration["access_modes"]) != len(set(declaration["access_modes"]))):
                    return deny("POLICY_REGISTRY_INVALID")
                allowed[declaration["kind"]] = set(declaration["access_modes"])
            if not allowed:
                return deny("POLICY_REGISTRY_INVALID")
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
            # Preserve validated caller identifiers separately from resolver output.
            # The resolver may canonicalize an identifier, but cannot drop, add,
            # re-type, or widen a requested resource/access tuple.
            requested_resources = [dict(item) for item in normalized]
            resolver_input = [dict(item) for item in requested_resources]
            resolved_value = self.resource_resolver(resolver_input)
            if not isinstance(resolved_value, Sequence) or isinstance(resolved_value, (str, bytes)):
                return deny("POLICY_RESOURCE_RESOLUTION_MISMATCH")
            resolved = list(resolved_value)
            if len(resolved) != len(requested_resources):
                return deny("POLICY_RESOURCE_RESOLUTION_MISMATCH")
            if not all(isinstance(item, Mapping) and set(item) == {"kind", "id", "access"} for item in resolved):
                return deny("POLICY_RESOURCE_RESOLUTION_MISMATCH")
            requested_modes = sorted((item["kind"], item["access"]) for item in requested_resources)
            resolved_modes, keys = [], []
            for item in resolved:
                kind, rid, access = item["kind"], item["id"], item["access"]
                if (not isinstance(kind, str) or not isinstance(rid, str) or not 1 <= len(rid) <= 1024
                    or not isinstance(access, str) or access not in _ACCESS
                    or kind not in allowed or access not in allowed[kind]):
                    return deny("POLICY_RESOURCE_RESOLUTION_MISMATCH")
                resolved_modes.append((kind, access))
                keys.append((kind, rid, access))
            if sorted(resolved_modes) != requested_modes or len(keys) != len(set(keys)):
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
                risk = "R4" if any(item["access"] in {"execute", "delete", "administer"} for item in normalized) else "R3"
                if minimum in {"R4", "R5"}: risk = minimum
            if risk == "R5" or entry["approval_mode"] == "out_of_band_admin":
                return deny("POLICY_R5_OUT_OF_BAND_DENY")
            envelope = {"schema_version": proposal["schema_version"], "action_id": proposal["action_id"],
                "proposal_id": proposal["proposal_id"], "task_id": proposal["task_id"], "step_id": proposal["step_id"],
                "arguments": proposal["arguments"],
                "requested_resources": sorted(requested_resources, key=lambda r: (r["kind"], r["id"], r["access"])),
                "resources": sorted(normalized, key=lambda r: (r["kind"], r["id"], r["access"])),
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

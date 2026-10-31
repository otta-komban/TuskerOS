#!/usr/bin/env python3
"""Dependency-free structural validator for the TuskerOS v1 extension manifest.

This is a developer convenience check, not a signature verifier, permission
authority, archive scanner, or security boundary. Runtime enforcement belongs
to the trusted host and AEGIS-06 policy service.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ID_RE = re.compile(r"^[a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*)+\.[a-z][a-z0-9-]*$")
VERSION_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
PERMISSION_RE = re.compile(r"^[a-z][a-z0-9]*(?:\.[a-z][a-z0-9-]*)+$")
REQUIRED = {
    "manifest_version", "id", "name", "version", "description", "publisher",
    "license", "kind", "api", "os", "permissions", "dependencies"
}
ALLOWED = REQUIRED | {"artifacts"}


def validate(data: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["manifest root must be a JSON object"]
    missing, extra = REQUIRED - data.keys(), data.keys() - ALLOWED
    if missing:
        errors.append("missing required fields: " + ", ".join(sorted(missing)))
    if extra:
        errors.append("unknown fields: " + ", ".join(sorted(extra)))
    if data.get("manifest_version") != 1 or isinstance(data.get("manifest_version"), bool):
        errors.append("manifest_version must be integer 1")
    if not isinstance(data.get("id"), str) or not ID_RE.fullmatch(data["id"]):
        errors.append("id must be a reverse-DNS-style lowercase identifier")
    for field, limit in (("name", 80), ("description", 280), ("license", 80)):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            errors.append(f"{field} must be non-empty text of at most {limit} characters")
    if not isinstance(data.get("version"), str) or not VERSION_RE.fullmatch(data["version"]):
        errors.append("version must be semantic version X.Y.Z")
    if data.get("kind") not in {"extension", "theme", "layout", "workflow"}:
        errors.append("kind must be extension, theme, layout, or workflow")
    for field in ("api", "os"):
        value = data.get(field)
        if not isinstance(value, dict) or set(value) != {"min", "max"} or not all(
            isinstance(value.get(k), str) and value[k] for k in ("min", "max")
        ):
            errors.append(f"{field} must contain non-empty min and max strings")
    publisher = data.get("publisher")
    if not isinstance(publisher, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,63}", publisher):
        errors.append("publisher must be a stable 2-64 character identifier")
    permissions = data.get("permissions")
    if not isinstance(permissions, list) or any(
        not isinstance(p, str) or not PERMISSION_RE.fullmatch(p) for p in (permissions or [])
    ):
        errors.append("permissions must be an array of namespaced permission strings")
    elif len(permissions) != len(set(permissions)):
        errors.append("permissions must not contain duplicates")
    dependencies = data.get("dependencies")
    if not isinstance(dependencies, list):
        errors.append("dependencies must be an array")
    else:
        seen = set()
        for i, dep in enumerate(dependencies):
            if not isinstance(dep, dict) or set(dep) != {"id", "version"}:
                errors.append(f"dependencies[{i}] must contain exactly id and version")
                continue
            if not isinstance(dep["id"], str) or not ID_RE.fullmatch(dep["id"]):
                errors.append(f"dependencies[{i}].id is invalid")
            if not isinstance(dep["version"], str) or not dep["version"].strip():
                errors.append(f"dependencies[{i}].version must be non-empty text")
            if dep.get("id") in seen:
                errors.append(f"dependencies contains duplicate id: {dep.get('id')}")
            seen.add(dep.get("id"))
    artifacts = data.get("artifacts", [])
    if not isinstance(artifacts, list):
        errors.append("artifacts must be an array")
    else:
        for i, artifact in enumerate(artifacts):
            if not isinstance(artifact, dict) or not {"uri", "sha256"} <= artifact.keys() or artifact.keys() - {"uri", "sha256", "signature"}:
                errors.append(f"artifacts[{i}] must contain uri, sha256, and optional signature")
                continue
            if not isinstance(artifact["uri"], str) or not re.match(r"^https://", artifact["uri"]):
                errors.append(f"artifacts[{i}].uri must use HTTPS")
            if not isinstance(artifact["sha256"], str) or not re.fullmatch(r"[a-fA-F0-9]{64}", artifact["sha256"]):
                errors.append(f"artifacts[{i}].sha256 must be 64 hexadecimal characters")
            if "signature" in artifact and not isinstance(artifact["signature"], str):
                errors.append(f"artifacts[{i}].signature must be text")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} MANIFEST.json", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"invalid: {exc}", file=sys.stderr)
        return 1
    errors = validate(data)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"valid: {data['id']} (manifest v1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

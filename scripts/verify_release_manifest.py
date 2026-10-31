#!/usr/bin/env python3
"""Verify local byte-integrity and semantic consistency of a TuskerOS release manifest.

This tool does NOT verify cryptographic signatures, resolve Git commits, fetch remote
URIs, parse SBOM/provenance formats, or authorize release promotion. Those remain
separate owner-controlled gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "release-manifest.schema.json"
REQUIRED_TESTS = ("uefi_boot", "secure_boot", "desktop_smoke", "install", "recovery")


class DuplicateKeyError(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)


def _safe_local_file(root: Path, reference: str, label: str, errors: list[str]) -> Path | None:
    """Resolve a manifest-relative local file without URI, traversal, or symlink escape."""
    if not isinstance(reference, str) or not reference:
        errors.append(f"{label}: expected a non-empty manifest-relative path")
        return None
    parsed = urlsplit(reference)
    candidate = Path(reference)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        errors.append(f"{label}: only local relative paths are supported by this verifier")
        return None
    if "\\" in reference or candidate.is_absolute() or any(part in ("..", "") for part in candidate.parts):
        errors.append(f"{label}: absolute paths and parent traversal are not allowed")
        return None
    try:
        resolved_root = root.resolve(strict=True)
        resolved = (resolved_root / candidate).resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (OSError, ValueError):
        errors.append(f"{label}: file is missing or resolves outside the manifest directory")
        return None
    if not resolved.is_file():
        errors.append(f"{label}: expected a regular file")
        return None
    return resolved


def _sha256(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def verify_release_manifest(manifest_path: Path, schema_path: Path = SCHEMA_PATH) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    checks: list[dict[str, str]] = []
    manifest_path = manifest_path.resolve()
    try:
        manifest = _load_json(manifest_path)
    except (OSError, UnicodeError, json.JSONDecodeError, DuplicateKeyError) as exc:
        return {"valid": False, "promotion_ready": False, "errors": [f"manifest: {exc}"], "warnings": [], "checks": []}

    try:
        schema = _load_json(schema_path)
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        for error in sorted(validator.iter_errors(manifest), key=lambda item: list(map(str, item.absolute_path))):
            location = ".".join(str(part) for part in error.absolute_path) or "$"
            errors.append(f"schema {location}: {error.message}")
        if not errors:
            checks.append({"id": "schema", "status": "passed"})
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, SchemaError) as exc:
        errors.append(f"schema: cannot load or validate schema: {exc}")
        return {"valid": False, "promotion_ready": False, "errors": errors, "warnings": warnings, "checks": checks}

    if errors:
        return {"valid": False, "promotion_ready": False, "errors": errors, "warnings": warnings, "checks": checks}

    root = manifest_path.parent
    platform_arch = manifest["platform"]["architecture"]
    seen_ids: set[str] = set()
    seen_filenames: set[str] = set()

    for field in ("sbom", "provenance"):
        evidence = manifest[field]
        path = _safe_local_file(root, evidence["uri"], field, errors)
        if path is not None:
            _, actual = _sha256(path)
            if actual != evidence["sha256"]:
                errors.append(f"{field}: SHA-256 does not match referenced bytes")
            else:
                checks.append({"id": field, "status": "passed"})

    for index, artifact in enumerate(manifest["artifacts"]):
        prefix = f"artifacts[{index}]"
        artifact_id = artifact["id"]
        filename = artifact["filename"]
        if artifact_id in seen_ids:
            errors.append(f"{prefix}.id: duplicate artifact id {artifact_id!r}")
        seen_ids.add(artifact_id)
        if filename in seen_filenames:
            errors.append(f"{prefix}.filename: duplicate artifact filename {filename!r}")
        seen_filenames.add(filename)
        if artifact["architecture"] != platform_arch:
            errors.append(f"{prefix}.architecture: does not match platform architecture")

        path = _safe_local_file(root, filename, f"{prefix}.filename", errors)
        if path is not None:
            actual_size, actual_digest = _sha256(path)
            if actual_size != artifact["size_bytes"]:
                errors.append(f"{prefix}.size_bytes: expected {artifact['size_bytes']}, found {actual_size}")
            if actual_digest != artifact["sha256"]:
                errors.append(f"{prefix}.sha256: does not match artifact bytes")
            if actual_size == artifact["size_bytes"] and actual_digest == artifact["sha256"]:
                checks.append({"id": f"{prefix}.bytes", "status": "passed"})

        signature = artifact.get("signature")
        if signature is not None:
            sig_path = _safe_local_file(root, signature["uri"], f"{prefix}.signature", errors)
            if sig_path is not None:
                _, actual_signature_digest = _sha256(sig_path)
                if actual_signature_digest != signature["sha256"]:
                    errors.append(f"{prefix}.signature: SHA-256 does not match signature-file bytes")
                else:
                    checks.append({"id": f"{prefix}.signature_file_bytes", "status": "passed"})

        for test_id in REQUIRED_TESTS:
            result = artifact["tests"][test_id]
            if result["status"] != "passed" or not result.get("report"):
                warnings.append(f"{prefix}.tests.{test_id}: not a passed result with a report reference")

    warnings.append("cryptographic signature verification is NOT performed; AEGIS trust format/root policy is pending")
    warnings.append("source/recipe commit existence, SBOM/provenance format semantics and remote evidence are NOT verified")
    checks.append({"id": "cryptographic_signature_trust", "status": "blocked"})
    return {
        "valid": not errors,
        "promotion_ready": False,
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="release manifest JSON path")
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH, help="Draft 2020-12 schema path")
    parser.add_argument("--json", action="store_true", help="emit machine-readable result")
    args = parser.parse_args()
    result = verify_release_manifest(args.manifest, args.schema)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for check in result["checks"]:
            print(f"{check['status'].upper()}: {check['id']}")
        for warning in result["warnings"]:
            print(f"BLOCKED: {warning}", file=sys.stderr)
        for error in result["errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
        if result["valid"]:
            print("PASS: manifest structure and local byte-integrity checks")
        if result["promotion_ready"]:
            print("PASS: promotion readiness")
        else:
            print("NOT READY: release promotion is blocked", file=sys.stderr)
    if not result["valid"]:
        return 1
    return 0 if result["promotion_ready"] else 3


if __name__ == "__main__":
    raise SystemExit(main())

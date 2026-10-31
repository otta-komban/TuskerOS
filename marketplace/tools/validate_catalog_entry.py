#!/usr/bin/env python3
"""Fail-closed structural validation for TuskerOS marketplace catalog entries.

This module validates untrusted metadata only. It does not verify signatures,
publisher identity, catalog provenance, artifact contents, or install authority.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,127}$")
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
# Semantic Versioning 2.0.0: prerelease identifiers cannot be empty or
# numeric with leading zeroes; build identifiers may contain leading zeroes.
_PRE_ID = r"(?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)"
_BUILD_ID = r"[0-9A-Za-z-]+"
SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    rf"(?:-({_PRE_ID}(?:\.{_PRE_ID})*))?"
    rf"(?:\+({_BUILD_ID}(?:\.{_BUILD_ID})*))?$"
)
KINDS = {"extension", "theme", "layout", "workflow", "bundle"}
REVIEW = {"pending", "approved", "rejected", "quarantined", "revoked"}
SIGNATURE = {"unverified", "valid", "invalid", "revoked"}

TOP = {"catalog_version", "package", "publisher", "release", "compatibility", "trust", "community"}
PACKAGE = {"id", "name", "kind", "summary", "description_uri", "license", "categories", "tags", "conflicts"}
PUBLISHER = {"id", "display_name", "homepage", "verified"}
RELEASE = {"version", "manifest_uri", "artifact_uri", "sha256", "signature_uri", "published_at", "changelog_uri"}
COMPAT = {"tuskeros", "api"}
RANGE = {"min", "max"}
TRUST = {"review_status", "signature_status", "reviewed_at", "review_policy_version"}
COMMUNITY = {"rating_average", "rating_count", "download_count"}


def _keys(value: object, allowed: set[str], required: set[str], path: str, errors: list[str]) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{path}: expected object")
        return False
    for key in sorted(set(value) - allowed):
        errors.append(f"{path}.{key}: unsupported field")
    for key in sorted(required - set(value)):
        errors.append(f"{path}.{key}: required field missing")
    return True


def _text(value: object, path: str, errors: list[str], *, maximum: int = 512) -> bool:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        errors.append(f"{path}: expected non-empty string (max {maximum})")
        return False
    return True


def _https(value: object, path: str, errors: list[str]) -> None:
    if not _text(value, path, errors):
        return
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        errors.append(f"{path}: expected an HTTPS URL without embedded credentials")


def _date_time(value: object, path: str, errors: list[str]) -> None:
    if not _text(value, path, errors):
        return
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timezone required")
    except ValueError:
        errors.append(f"{path}: expected timezone-aware ISO-8601 date-time")


def validate_catalog_entry(entry: object) -> list[str]:
    """Return validation errors; an empty list means metadata is structurally valid."""
    errors: list[str] = []
    if not _keys(entry, TOP, TOP - {"community"}, "$", errors):
        return errors
    if entry.get("catalog_version") != 1 or isinstance(entry.get("catalog_version"), bool):
        errors.append("$.catalog_version: only integer version 1 is supported")

    p = entry.get("package")
    if _keys(p, PACKAGE, {"id", "name", "kind", "summary", "license"}, "$.package", errors):
        if _text(p.get("id"), "$.package.id", errors, maximum=128) and not ID_RE.fullmatch(p["id"]):
            errors.append("$.package.id: invalid package identifier")
        for key, limit in (("name", 80), ("summary", 280), ("license", 80)):
            _text(p.get(key), f"$.package.{key}", errors, maximum=limit)
        if not isinstance(p.get("kind"), str) or p.get("kind") not in KINDS:
            errors.append("$.package.kind: unsupported package kind")
        for key, limit in (("categories", 48), ("tags", 32)):
            if key in p:
                values = p[key]
                if (not isinstance(values, list)
                        or any(not isinstance(x, str) or not x.strip() or len(x) > limit for x in values)
                        or len(values) != len(set(values)) if isinstance(values, list) else True):
                    errors.append(f"$.package.{key}: expected unique non-empty strings (max {limit})")
        if "conflicts" in p:
            conflicts = p["conflicts"]
            if (not isinstance(conflicts, list)
                    or any(not isinstance(x, str) or not ID_RE.fullmatch(x) for x in conflicts)
                    or len(conflicts) != len(set(conflicts)) if isinstance(conflicts, list) else True):
                errors.append("$.package.conflicts: expected unique package identifiers")
            elif p.get("id") in conflicts:
                errors.append("$.package.conflicts: package cannot conflict with itself")
        if "description_uri" in p:
            _https(p["description_uri"], "$.package.description_uri", errors)

    pub = entry.get("publisher")
    if _keys(pub, PUBLISHER, {"id", "display_name"}, "$.publisher", errors):
        if _text(pub.get("id"), "$.publisher.id", errors, maximum=64) and not ID_RE.fullmatch(pub["id"]):
            errors.append("$.publisher.id: invalid publisher identifier")
        _text(pub.get("display_name"), "$.publisher.display_name", errors, maximum=80)
        if "verified" in pub and not isinstance(pub["verified"], bool):
            errors.append("$.publisher.verified: expected boolean")
        if "homepage" in pub:
            _https(pub["homepage"], "$.publisher.homepage", errors)

    rel = entry.get("release")
    if _keys(rel, RELEASE, {"version", "manifest_uri", "artifact_uri", "sha256", "published_at"}, "$.release", errors):
        if _text(rel.get("version"), "$.release.version", errors, maximum=128) and not SEMVER_RE.fullmatch(rel["version"]):
            errors.append("$.release.version: expected semantic version")
        for key in ("manifest_uri", "artifact_uri"):
            _https(rel.get(key), f"$.release.{key}", errors)
        for key in ("signature_uri", "changelog_uri"):
            if key in rel:
                _https(rel[key], f"$.release.{key}", errors)
        if not isinstance(rel.get("sha256"), str) or not SHA256_RE.fullmatch(rel["sha256"]):
            errors.append("$.release.sha256: expected 64 hexadecimal characters")
        _date_time(rel.get("published_at"), "$.release.published_at", errors)

    comp = entry.get("compatibility")
    if _keys(comp, COMPAT, COMPAT, "$.compatibility", errors):
        for key in ("tuskeros", "api"):
            value = comp.get(key)
            if _keys(value, RANGE, RANGE, f"$.compatibility.{key}", errors):
                _text(value.get("min"), f"$.compatibility.{key}.min", errors, maximum=64)
                _text(value.get("max"), f"$.compatibility.{key}.max", errors, maximum=64)

    trust = entry.get("trust")
    if _keys(trust, TRUST, {"review_status", "signature_status"}, "$.trust", errors):
        if not isinstance(trust.get("review_status"), str) or trust.get("review_status") not in REVIEW:
            errors.append("$.trust.review_status: unsupported state")
        if not isinstance(trust.get("signature_status"), str) or trust.get("signature_status") not in SIGNATURE:
            errors.append("$.trust.signature_status: unsupported state")
        if "reviewed_at" in trust:
            _date_time(trust["reviewed_at"], "$.trust.reviewed_at", errors)
        if "review_policy_version" in trust:
            _text(trust["review_policy_version"], "$.trust.review_policy_version", errors, maximum=64)

    if "community" in entry:
        c = entry["community"]
        if _keys(c, COMMUNITY, set(), "$.community", errors):
            rating = c.get("rating_average")
            if rating is not None and (isinstance(rating, bool) or not isinstance(rating, (int, float)) or not 0 <= rating <= 5):
                errors.append("$.community.rating_average: expected number from 0 to 5")
            for key in ("rating_count", "download_count"):
                val = c.get(key)
                if val is not None and (isinstance(val, bool) or not isinstance(val, int) or val < 0):
                    errors.append(f"$.community.{key}: expected non-negative integer")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {Path(argv[0]).name} CATALOG_ENTRY.json", file=sys.stderr)
        return 2
    try:
        entry = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"invalid input: {exc}", file=sys.stderr)
        return 2
    errors = validate_catalog_entry(entry)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("catalog metadata valid (trust and install authorization not evaluated)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

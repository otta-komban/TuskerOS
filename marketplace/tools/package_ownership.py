#!/usr/bin/env python3
"""Dry-run package ownership and safe removal planning for TuskerOS.

This module computes a plan only. It never invokes a package manager, deletes
files, mutates installed state, or treats catalog metadata as authorization.
"""
from __future__ import annotations

from collections import deque
from typing import Any, Mapping


class OwnershipPlanError(ValueError):
    """Raised when installed ownership state is malformed or unsafe to plan."""


OWNER_KINDS = {"bundle", "extension", "user", "system"}
REMOVABLE_OWNER_KINDS = {"bundle", "extension"}


def _non_empty_text(value: object, field: str, *, maximum: int = 128) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise OwnershipPlanError(
            f"{field} must be a non-empty string (max {maximum} characters)"
        )
    return value


def validate_installed_state(state: object) -> dict[str, dict[str, Any]]:
    """Validate and index a version-1 installed package ownership snapshot."""
    if not isinstance(state, Mapping) or set(state) != {"state_version", "packages"}:
        raise OwnershipPlanError("state must contain only state_version and packages")
    if state.get("state_version") != 1 or isinstance(state.get("state_version"), bool):
        raise OwnershipPlanError("only installed-state version 1 is supported")
    packages = state.get("packages")
    if not isinstance(packages, list):
        raise OwnershipPlanError("packages must be an array")

    indexed: dict[str, dict[str, Any]] = {}
    for position, raw in enumerate(packages):
        prefix = f"packages[{position}]"
        if not isinstance(raw, Mapping) or set(raw) != {
            "package_id", "version", "owners", "dependencies"
        }:
            raise OwnershipPlanError(
                f"{prefix} must contain only package_id, version, owners, dependencies"
            )
        package_id = _non_empty_text(raw.get("package_id"), f"{prefix}.package_id")
        if package_id in indexed:
            raise OwnershipPlanError(f"duplicate installed package: {package_id}")
        version = _non_empty_text(raw.get("version"), f"{prefix}.version")
        owners_raw, dependencies_raw = raw.get("owners"), raw.get("dependencies")
        if not isinstance(owners_raw, list) or not isinstance(dependencies_raw, list):
            raise OwnershipPlanError(f"{prefix}.owners and dependencies must be arrays")
        owners: list[dict[str, str]] = []
        owner_keys: set[tuple[str, str]] = set()
        for owner_pos, owner in enumerate(owners_raw):
            if not isinstance(owner, Mapping) or set(owner) != {"kind", "id"}:
                raise OwnershipPlanError(f"{prefix}.owners[{owner_pos}] must contain kind and id")
            kind = _non_empty_text(owner.get("kind"), f"{prefix}.owners[{owner_pos}].kind")
            owner_id = _non_empty_text(owner.get("id"), f"{prefix}.owners[{owner_pos}].id")
            if kind not in OWNER_KINDS:
                raise OwnershipPlanError(f"{prefix}.owners[{owner_pos}].kind is unsupported")
            key = (kind, owner_id)
            if key in owner_keys:
                raise OwnershipPlanError(f"{prefix} contains duplicate owner {kind}:{owner_id}")
            owner_keys.add(key)
            owners.append({"kind": kind, "id": owner_id})
        dependencies: list[str] = []
        for dep_pos, dependency in enumerate(dependencies_raw):
            dep_id = _non_empty_text(dependency, f"{prefix}.dependencies[{dep_pos}]")
            if dep_id == package_id:
                raise OwnershipPlanError(f"{package_id} cannot depend on itself")
            if dep_id in dependencies:
                raise OwnershipPlanError(f"{prefix} contains duplicate dependency {dep_id}")
            dependencies.append(dep_id)
        indexed[package_id] = {
            "package_id": package_id,
            "version": version,
            "owners": owners,
            "dependencies": dependencies,
        }

    for package_id, package in indexed.items():
        for dependency in package["dependencies"]:
            if dependency not in indexed:
                raise OwnershipPlanError(
                    f"{package_id} references missing installed dependency {dependency}"
                )
    return indexed


def plan_owner_removal(
    state: object,
    owner_kind: str,
    owner_id: str,
) -> dict[str, Any]:
    """Return a dry-run removal plan for one bundle or extension owner.

    A package is eligible only if it was explicitly attributed to the target
    owner and has no other owners after that ownership is removed. Packages
    still reachable from any non-eligible package are preserved, along with
    their transitive dependencies. User/system ownership is never removable.
    """
    if not isinstance(owner_kind, str) or owner_kind not in REMOVABLE_OWNER_KINDS:
        raise OwnershipPlanError("only bundle or extension ownership can be removed")
    owner_id = _non_empty_text(owner_id, "owner_id")
    indexed = validate_installed_state(state)
    target = (owner_kind, owner_id)
    owned = {
        package_id for package_id, package in indexed.items()
        if any((owner["kind"], owner["id"]) == target for owner in package["owners"])
    }
    if not owned:
        raise OwnershipPlanError(f"owner not found: {owner_kind}:{owner_id}")

    eligible: set[str] = set()
    reasons: dict[str, str] = {}
    for package_id in sorted(owned):
        remaining = [
            owner for owner in indexed[package_id]["owners"]
            if (owner["kind"], owner["id"]) != target
        ]
        if remaining:
            reasons[package_id] = "retained: shared with " + ", ".join(
                f"{owner['kind']}:{owner['id']}" for owner in remaining
            )
        else:
            eligible.add(package_id)

    # Any package not eligible for removal is a retention root. Protect its
    # complete dependency closure, including ownerless packages referenced by it.
    protected: set[str] = set()
    queue = deque(
        dependency
        for package_id, package in indexed.items()
        if package_id not in eligible
        for dependency in package["dependencies"]
    )
    while queue:
        package_id = queue.popleft()
        if package_id in protected:
            continue
        protected.add(package_id)
        queue.extend(indexed[package_id]["dependencies"])

    remove = sorted(eligible - protected)
    keep = sorted(set(indexed) - set(remove))
    for package_id in sorted(eligible & protected):
        reasons[package_id] = "retained: required by a package outside the removal set"
    for package_id in keep:
        reasons.setdefault(package_id, "retained: not exclusively owned by requested owner")

    return {
        "owner": {"kind": owner_kind, "id": owner_id},
        "remove": [
            {"package_id": package_id, "version": indexed[package_id]["version"]}
            for package_id in remove
        ],
        "keep": [
            {
                "package_id": package_id,
                "version": indexed[package_id]["version"],
                "reason": reasons[package_id],
            }
            for package_id in keep
        ],
        "summary": {
            "owned_by_target": len(owned),
            "remove_count": len(remove),
            "keep_count": len(keep),
        },
        "execution": "not_performed",
    }


__all__ = ["OwnershipPlanError", "validate_installed_state", "plan_owner_removal"]

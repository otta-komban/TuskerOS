"""Deterministic dependency ordering for already-resolved TuskerOS package candidates.

This helper does not choose versions, fetch packages, authorize permissions, or
install anything. A trusted catalog resolver must first select one candidate
per package ID and validate version constraints. This module only orders that
resolved graph and fails closed on malformed input, missing nodes or cycles.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping


class DependencyPlanError(ValueError):
    """Raised when a resolved dependency graph cannot be installed safely."""


def _package_ids(values: Iterable[str], *, field: str) -> list[str]:
    if isinstance(values, (str, bytes)):
        raise DependencyPlanError(f"{field} must be an iterable of package IDs, not text")
    try:
        result = list(values)
    except TypeError as exc:
        raise DependencyPlanError(f"{field} must be an iterable of package IDs") from exc
    if any(not isinstance(value, str) or not value.strip() for value in result):
        raise DependencyPlanError(f"{field} must contain only non-empty package ID strings")
    return result


def resolve_install_order(
    roots: Iterable[str],
    packages: Mapping[str, Iterable[str]],
) -> list[str]:
    """Return dependencies-before-dependents order for the requested roots.

    Ordering is deterministic (lexicographic among independent nodes). Each
    package appears once even when multiple roots share a dependency. Malformed
    graph values are rejected as DependencyPlanError rather than leaking
    implementation exceptions such as TypeError.
    """
    if not isinstance(packages, Mapping):
        raise DependencyPlanError("packages must be a mapping of package IDs to dependencies")
    root_values = _package_ids(roots, field="roots")
    root_ids = sorted(set(root_values))
    if not root_ids:
        return []
    for package_id in root_ids:
        if package_id not in packages:
            raise DependencyPlanError(f"requested package is missing: {package_id}")

    state: dict[str, int] = {}  # 0/unseen, 1/visiting, 2/complete
    ordered: list[str] = []
    stack: list[str] = []

    def visit(package_id: str) -> None:
        status = state.get(package_id, 0)
        if status == 2:
            return
        if status == 1:
            start = stack.index(package_id)
            cycle = stack[start:] + [package_id]
            raise DependencyPlanError("dependency cycle: " + " -> ".join(cycle))
        if package_id not in packages:
            parent = stack[-1] if stack else "<root>"
            raise DependencyPlanError(
                f"missing dependency {package_id} required by {parent}"
            )

        state[package_id] = 1
        stack.append(package_id)
        dependencies = _package_ids(
            packages[package_id], field=f"dependencies declared by {package_id}"
        )
        if len(dependencies) != len(set(dependencies)):
            raise DependencyPlanError(f"duplicate dependency declared by {package_id}")
        for dependency_id in sorted(dependencies):
            visit(dependency_id)
        stack.pop()
        state[package_id] = 2
        ordered.append(package_id)

    for root_id in root_ids:
        visit(root_id)
    return ordered

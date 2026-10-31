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
    active_path: list[str] = []
    active_index: dict[str, int] = {}

    # Iterative depth-first traversal avoids Python recursion limits on valid
    # package graphs while preserving deterministic dependency-first ordering.
    for root_id in root_ids:
        if state.get(root_id) == 2:
            continue
        state[root_id] = 1
        active_index[root_id] = len(active_path)
        active_path.append(root_id)
        root_dependencies = _package_ids(
            packages[root_id], field=f"dependencies declared by {root_id}"
        )
        if len(root_dependencies) != len(set(root_dependencies)):
            raise DependencyPlanError(f"duplicate dependency declared by {root_id}")
        frames: list[tuple[str, object]] = [
            (root_id, iter(sorted(root_dependencies)))
        ]

        while frames:
            package_id, dependencies = frames[-1]
            try:
                dependency_id = next(dependencies)
            except StopIteration:
                frames.pop()
                active_path.pop()
                active_index.pop(package_id)
                state[package_id] = 2
                ordered.append(package_id)
                continue

            dependency_state = state.get(dependency_id, 0)
            if dependency_state == 2:
                continue
            if dependency_state == 1:
                cycle_start = active_index[dependency_id]
                cycle = active_path[cycle_start:] + [dependency_id]
                raise DependencyPlanError("dependency cycle: " + " -> ".join(cycle))
            if dependency_id not in packages:
                raise DependencyPlanError(
                    f"missing dependency {dependency_id} required by {package_id}"
                )

            state[dependency_id] = 1
            active_index[dependency_id] = len(active_path)
            active_path.append(dependency_id)
            child_dependencies = _package_ids(
                packages[dependency_id],
                field=f"dependencies declared by {dependency_id}",
            )
            if len(child_dependencies) != len(set(child_dependencies)):
                raise DependencyPlanError(
                    f"duplicate dependency declared by {dependency_id}"
                )
            frames.append((dependency_id, iter(sorted(child_dependencies))))
    return ordered

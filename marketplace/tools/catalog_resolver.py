"""Semantic-version compatibility and deterministic marketplace candidate selection.

Release selection is metadata resolution only. It does not establish trust,
verify signatures, authorize permissions, fetch artifacts, or install packages.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping, Any

from marketplace.tools.validate_catalog_entry import validate_catalog_entry
from sdk.tools.dependency_plan import resolve_install_order, DependencyPlanError


_RELEASE_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$"
)
_COMPAT_RE = re.compile(
    r"^(0|[1-9]\d*)(?:\.(0|[1-9]\d*))?(?:\.(0|[1-9]\d*))?"
    r"(?:-([0-9A-Za-z.-]+))?$"
)
_WILDCARD_RE = re.compile(r"^(0|[1-9]\d*)(?:\.(0|[1-9]\d*))?\.x$")


class CatalogResolutionError(ValueError):
    """Raised when catalog metadata cannot yield one unambiguous candidate."""


@dataclass(frozen=True)
class Version:
    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()

    def _compare(self, other: "Version") -> int:
        core_a = (self.major, self.minor, self.patch)
        core_b = (other.major, other.minor, other.patch)
        if core_a != core_b:
            return (core_a > core_b) - (core_a < core_b)
        if not self.prerelease and not other.prerelease:
            return 0
        if not self.prerelease:
            return 1
        if not other.prerelease:
            return -1
        for left, right in zip(self.prerelease, other.prerelease):
            if left == right:
                continue
            left_num, right_num = left.isdigit(), right.isdigit()
            if left_num and right_num:
                return (int(left) > int(right)) - (int(left) < int(right))
            if left_num != right_num:
                return -1 if left_num else 1
            return (left > right) - (left < right)
        return (len(self.prerelease) > len(other.prerelease)) - (
            len(self.prerelease) < len(other.prerelease)
        )

    def __lt__(self, other: "Version") -> bool:
        return self._compare(other) < 0

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Version) and self._compare(other) == 0


def _prerelease_parts(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    parts = tuple(value.split("."))
    if any(not p or (p.isdigit() and len(p) > 1 and p.startswith("0")) for p in parts):
        raise CatalogResolutionError("invalid semantic-version prerelease identifier")
    return parts


def parse_release_version(value: str) -> Version:
    """Parse a strict MAJOR.MINOR.PATCH release version."""
    if not isinstance(value, str):
        raise CatalogResolutionError("release version must be a string")
    match = _RELEASE_RE.fullmatch(value)
    if not match:
        raise CatalogResolutionError(f"invalid semantic release version: {value!r}")
    major, minor, patch, prerelease = match.groups()
    return Version(int(major), int(minor), int(patch), _prerelease_parts(prerelease))


def parse_compat_version(value: str) -> Version:
    """Parse compatibility versions as MAJOR[.MINOR[.PATCH]], optionally prerelease."""
    if not isinstance(value, str):
        raise CatalogResolutionError("compatibility version must be a string")
    match = _COMPAT_RE.fullmatch(value)
    if not match:
        raise CatalogResolutionError(f"invalid compatibility version: {value!r}")
    major, minor, patch, prerelease = match.groups()
    return Version(int(major), int(minor or 0), int(patch or 0), _prerelease_parts(prerelease))


def _matches_range(version: Version, minimum: str, maximum: str) -> bool:
    lower = parse_compat_version(minimum)
    if version < lower:
        return False
    wildcard = _WILDCARD_RE.fullmatch(maximum) if isinstance(maximum, str) else None
    if wildcard:
        major, minor = wildcard.groups()
        if version.major != int(major):
            return False
        return minor is None or version.minor == int(minor)
    upper = parse_compat_version(maximum)
    return not upper < version


def is_compatible(entry: Mapping[str, Any], tuskeros_version: str, api_version: str) -> bool:
    """Check inclusive min/max compatibility; max may use MAJOR.x or MAJOR.MINOR.x."""
    try:
        os_target = parse_compat_version(tuskeros_version)
        api_target = parse_compat_version(api_version)
        compatibility = entry["compatibility"]
        os_range = compatibility["tuskeros"]
        api_range = compatibility["api"]
        return (
            _matches_range(os_target, os_range["min"], os_range["max"])
            and _matches_range(api_target, api_range["min"], api_range["max"])
        )
    except (KeyError, TypeError) as exc:
        raise CatalogResolutionError("malformed compatibility metadata") from exc


def parse_dependency_constraint(value: str) -> tuple[tuple[str, Version], ...]:
    """Parse comma-conjoined exact/comparison constraints, e.g. >=1.2.0,<2.0.0."""
    if not isinstance(value, str) or not value.strip():
        raise CatalogResolutionError("dependency version constraint must be a non-empty string")
    parsed = []
    for raw in value.split(","):
        match = re.fullmatch(r"(>=|<=|>|<|=)?\s*(.+)", raw.strip())
        if not match:
            raise CatalogResolutionError(f"invalid dependency version constraint: {value!r}")
        operator, version_text = match.groups()
        try:
            version = parse_release_version(version_text.strip())
        except CatalogResolutionError as exc:
            raise CatalogResolutionError(f"invalid dependency version constraint: {value!r}") from exc
        parsed.append((operator or "=", version))
    return tuple(parsed)


def satisfies_dependency_constraints(version: str | Version, constraints: Iterable[str]) -> bool:
    """Return whether a release satisfies every supplied edge constraint."""
    actual = parse_release_version(version) if isinstance(version, str) else version
    for constraint in constraints:
        for operator, expected in parse_dependency_constraint(constraint):
            comparison = actual._compare(expected)
            if operator == "=" and comparison != 0:
                return False
            if operator == ">" and comparison <= 0:
                return False
            if operator == ">=" and comparison < 0:
                return False
            if operator == "<" and comparison >= 0:
                return False
            if operator == "<=" and comparison > 0:
                return False
    return True


def select_catalog_release(
    candidates: Iterable[Mapping[str, Any]],
    package_id: str,
    tuskeros_version: str,
    api_version: str,
    *,
    include_prerelease: bool = False,
    version_constraints: Iterable[str] = (),
) -> Mapping[str, Any]:
    """Select the highest compatible release for one package ID.

    All matching entries must pass structural validation. Equal-precedence
    duplicates are rejected, including releases differing only by build metadata.
    """
    matching: list[tuple[Version, Mapping[str, Any]]] = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        package = candidate.get("package")
        if not isinstance(package, Mapping) or package.get("id") != package_id:
            continue
        errors = validate_catalog_entry(candidate)
        if errors:
            raise CatalogResolutionError(
                f"invalid catalog entry for {package_id}: " + "; ".join(errors)
            )
        # Revocation/rejection is a hard exclusion even during metadata-only
        # planning. Pending/unverified entries may still be previewed, but this
        # resolver never treats them as trusted or install-authorized.
        trust = candidate["trust"]
        if trust["review_status"] in {"rejected", "quarantined", "revoked"}:
            continue
        if trust["signature_status"] in {"invalid", "revoked"}:
            continue
        version = parse_release_version(candidate["release"]["version"])
        if version.prerelease and not include_prerelease:
            continue
        if is_compatible(candidate, tuskeros_version, api_version) and satisfies_dependency_constraints(version, version_constraints):
            matching.append((version, candidate))
    if not matching:
        raise CatalogResolutionError(f"no compatible release found for {package_id}")
    matching.sort(key=lambda pair: pair[0], reverse=True)
    if len(matching) > 1 and matching[0][0] == matching[1][0]:
        raise CatalogResolutionError(
            f"ambiguous catalog releases for {package_id}: equal-precedence versions"
        )
    return matching[0][1]


def resolve_catalog_plan(
    roots: Iterable[str],
    candidates: Iterable[Mapping[str, Any]],
    dependencies: Mapping[str, Iterable[str]],
    tuskeros_version: str,
    api_version: str,
    *,
    include_prerelease: bool = False,
    dependency_constraints: Mapping[str, Mapping[str, str]] | None = None,
) -> dict[str, Any]:
    """Select releases satisfying all declared incoming dependency-edge constraints.

    dependency_constraints maps parent package ID to dependency ID to a
    comma-conjoined version constraint. When supplied, every graph edge must
    have exactly one corresponding constraint. Constraints are intersected
    across all parents before selecting each dependency release.
    """
    root_ids = sorted(set(roots))
    normalized_dependencies = {package_id: list(children) for package_id, children in dependencies.items()}
    order = resolve_install_order(root_ids, normalized_dependencies)
    candidate_list = list(candidates)
    incoming: dict[str, list[str]] = {package_id: [] for package_id in order}
    if dependency_constraints is not None:
        for parent, child_constraints in dependency_constraints.items():
            if parent not in normalized_dependencies:
                raise CatalogResolutionError(f"constraints supplied for unknown parent: {parent}")
            if not isinstance(child_constraints, Mapping):
                raise CatalogResolutionError(f"dependency constraints for {parent} must be a mapping")
            declared = set(normalized_dependencies[parent])
            if set(child_constraints) != declared:
                raise CatalogResolutionError(
                    f"dependency constraints for {parent} must match declared dependency edges"
                )
            for child, constraint in child_constraints.items():
                parse_dependency_constraint(constraint)
                incoming.setdefault(child, []).append(constraint)
        for parent, children in normalized_dependencies.items():
            if parent in order and parent not in dependency_constraints and list(children):
                raise CatalogResolutionError(f"missing dependency constraints for {parent}")
    selected: dict[str, Mapping[str, Any]] = {}
    for package_id in order:
        selected[package_id] = select_catalog_release(
            candidate_list,
            package_id,
            tuskeros_version,
            api_version,
            include_prerelease=include_prerelease,
            version_constraints=incoming.get(package_id, ()),
        )
    # Conflict declarations are advisory metadata until resolution. Treat either
    # side's declaration as sufficient and fail closed before returning a plan.
    selected_ids = set(selected)
    for package_id, entry in selected.items():
        conflicts = entry.get("package", {}).get("conflicts", [])
        overlap = sorted(set(conflicts) & selected_ids)
        if overlap:
            raise CatalogResolutionError(
                f"package conflict: {package_id} conflicts with {', '.join(overlap)}"
            )
    return {"order": order, "releases": selected}


__all__ = [
    "CatalogResolutionError",
    "Version",
    "parse_release_version",
    "parse_compat_version",
    "parse_dependency_constraint",
    "satisfies_dependency_constraints",
    "is_compatible",
    "select_catalog_release",
    "resolve_catalog_plan",
    "DependencyPlanError",
]

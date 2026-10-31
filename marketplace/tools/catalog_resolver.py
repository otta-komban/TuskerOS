"""Semantic-version compatibility and deterministic marketplace candidate selection.

Release selection is metadata resolution only. It does not establish trust,
verify signatures, authorize permissions, fetch artifacts, or install packages.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping, Any

from marketplace.tools.validate_catalog_entry import SEMVER_RE, validate_catalog_entry
from sdk.tools.dependency_plan import resolve_install_order, DependencyPlanError


# Direct parser calls share the catalog validator's strict ASCII SemVer grammar.
_COMPAT_RE = re.compile(
    r"^(0|[1-9][0-9]*)(?:\.(0|[1-9][0-9]*))?(?:\.(0|[1-9][0-9]*))?"
    r"(?:-([0-9A-Za-z.-]+))?$"
)
_WILDCARD_RE = re.compile(r"^(0|[1-9][0-9]*)(?:\.(0|[1-9][0-9]*))?\.x$")


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
    if not isinstance(value, str) or not value or len(value) > 128:
        raise CatalogResolutionError(
            "release version must be a non-empty string (max 128 characters)"
        )
    match = SEMVER_RE.fullmatch(value)
    if not match:
        raise CatalogResolutionError(f"invalid semantic release version: {value!r}")
    major, minor, patch, prerelease, _build = match.groups()
    return Version(int(major), int(minor), int(patch), _prerelease_parts(prerelease))


def parse_compat_version(value: str) -> Version:
    """Parse compatibility versions as MAJOR[.MINOR[.PATCH]], optionally prerelease."""
    if not isinstance(value, str) or not value or len(value) > 64:
        raise CatalogResolutionError(
            "compatibility version must be a non-empty string (max 64 characters)"
        )
    match = _COMPAT_RE.fullmatch(value)
    if not match:
        raise CatalogResolutionError(f"invalid compatibility version: {value!r}")
    major, minor, patch, prerelease = match.groups()
    return Version(int(major), int(minor or 0), int(patch or 0), _prerelease_parts(prerelease))


def _matches_range(version: Version, minimum: str, maximum: str) -> bool:
    lower = parse_compat_version(minimum)
    if version < lower:
        return False
    # Wildcard maxima bypass parse_compat_version(), so enforce the same
    # schema bound before the wildcard path performs integer conversion.
    if isinstance(maximum, str) and len(maximum) > 64:
        raise CatalogResolutionError(
            "compatibility version must be a non-empty string (max 64 characters)"
        )
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
    if isinstance(version, str):
        actual = parse_release_version(version)
    elif isinstance(version, Version):
        if any(
            isinstance(part, bool) or not isinstance(part, int) or part < 0
            for part in (version.major, version.minor, version.patch)
        ):
            raise CatalogResolutionError("version components must be non-negative integers")
        if not isinstance(version.prerelease, tuple) or any(
            not isinstance(part, str)
            or not re.fullmatch(r"[0-9A-Za-z-]+", part)
            or (part.isascii() and part.isdigit() and len(part) > 1 and part.startswith("0"))
            for part in version.prerelease
        ):
            raise CatalogResolutionError("version contains invalid prerelease identifiers")
        actual = version
    else:
        raise CatalogResolutionError("version must be a SemVer string or Version")
    if isinstance(constraints, (str, bytes)):
        raise CatalogResolutionError("constraints must be an iterable of constraint strings, not text")
    try:
        constraint_values = list(constraints)
    except TypeError as exc:
        raise CatalogResolutionError("constraints must be an iterable of constraint strings") from exc
    for constraint in constraint_values:
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
    if not isinstance(package_id, str) or not package_id.strip():
        raise CatalogResolutionError("package_id must be a non-empty string")
    if not isinstance(include_prerelease, bool):
        raise CatalogResolutionError("include_prerelease must be a boolean")
    # Materialize once: callers may pass a generator, and every candidate must
    # be checked against the exact same complete constraint set.
    if isinstance(version_constraints, (str, bytes, Mapping)):
        raise CatalogResolutionError(
            "version_constraints must be an iterable of constraint strings, not text or a mapping"
        )
    try:
        constraint_values = tuple(version_constraints)
    except TypeError as exc:
        raise CatalogResolutionError("version_constraints must be an iterable") from exc
    for constraint in constraint_values:
        parse_dependency_constraint(constraint)
    if isinstance(candidates, (str, bytes, Mapping)):
        raise CatalogResolutionError("candidates must be an iterable of catalog entries, not text or a mapping")
    try:
        candidate_values = tuple(candidates)
    except TypeError as exc:
        raise CatalogResolutionError("candidates must be an iterable of catalog entries") from exc
    # Reject malformed target versions even when the candidate collection is
    # empty, so invalid caller input cannot masquerade as an absent release.
    parse_compat_version(tuskeros_version)
    parse_compat_version(api_version)
    matching: list[tuple[Version, Mapping[str, Any]]] = []
    for candidate in candidate_values:
        if not isinstance(candidate, Mapping):
            raise CatalogResolutionError("candidate entries must be mappings")
        package = candidate.get("package")
        if not isinstance(package, Mapping) or not isinstance(package.get("id"), str):
            raise CatalogResolutionError("candidate package metadata must contain a string package ID")
        if package.get("id") != package_id:
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
        if is_compatible(candidate, tuskeros_version, api_version) and satisfies_dependency_constraints(version, constraint_values):
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
    if isinstance(roots, (str, bytes)):
        raise CatalogResolutionError("roots must be an iterable of package IDs, not text")
    try:
        root_values = list(roots)
    except TypeError as exc:
        raise CatalogResolutionError("roots must be an iterable of package IDs") from exc
    if any(not isinstance(package_id, str) or not package_id.strip() for package_id in root_values):
        raise CatalogResolutionError("roots must contain only non-empty package ID strings")
    if not isinstance(dependencies, Mapping):
        raise CatalogResolutionError("dependencies must be a mapping of package IDs to dependency lists")
    normalized_dependencies: dict[str, list[str]] = {}
    for package_id, children in dependencies.items():
        if not isinstance(package_id, str) or not package_id.strip():
            raise CatalogResolutionError("dependency graph keys must be non-empty package ID strings")
        if isinstance(children, (str, bytes)):
            raise CatalogResolutionError(
                f"dependencies declared by {package_id} must be an iterable of package IDs, not text"
            )
        try:
            child_ids = list(children)
        except TypeError as exc:
            raise CatalogResolutionError(
                f"dependencies declared by {package_id} must be an iterable of package IDs"
            ) from exc
        if any(not isinstance(child, str) or not child.strip() for child in child_ids):
            raise CatalogResolutionError(
                f"dependencies declared by {package_id} must contain only non-empty package ID strings"
            )
        normalized_dependencies[package_id] = child_ids
    root_ids = sorted(set(root_values))
    order = resolve_install_order(root_ids, normalized_dependencies)
    if isinstance(candidates, (str, bytes, Mapping)):
        raise CatalogResolutionError("candidates must be an iterable of catalog entries, not text or a mapping")
    try:
        candidate_list = list(candidates)
    except TypeError as exc:
        raise CatalogResolutionError("candidates must be an iterable of catalog entries") from exc
    incoming: dict[str, list[str]] = {package_id: [] for package_id in order}
    if dependency_constraints is not None:
        if not isinstance(dependency_constraints, Mapping):
            raise CatalogResolutionError("dependency_constraints must be a mapping")
        for parent, child_constraints in dependency_constraints.items():
            if not isinstance(parent, str) or not parent.strip():
                raise CatalogResolutionError("dependency constraint parent IDs must be non-empty strings")
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

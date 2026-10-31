"""Deterministic, policy-aware resolution of declarative theme token layers.

This module deliberately has no filesystem, Qt, KDE, or package-loading side effects.
Callers must validate pack manifests and token values before passing them here.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any


class TokenResolutionError(ValueError):
    """Raised when theme layers cannot be resolved unambiguously."""


def _flatten(value: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, child in value.items():
        if not isinstance(key, str) or not key or "." in key:
            raise TokenResolutionError("token keys must be non-empty strings without dots")
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(child, Mapping):
            result.update(_flatten(child, path))
        else:
            result[path] = deepcopy(child)
    return result


def _unflatten(flat: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for path, value in flat.items():
        cursor = result
        parts = path.split(".")
        for part in parts[:-1]:
            existing = cursor.setdefault(part, {})
            if not isinstance(existing, dict):
                raise TokenResolutionError(f"token path collision at {path}")
            cursor = existing
        cursor[parts[-1]] = deepcopy(value)
    return result


def _mapping(name: str, value: Mapping[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TokenResolutionError(f"{name} must be a mapping")
    return _flatten(value)


def resolve_tokens(
    *,
    system_defaults: Mapping[str, Any],
    base_theme: Mapping[str, Any],
    mixins: Mapping[str, Mapping[str, Any]] | None = None,
    mixin_winners: Mapping[str, str] | None = None,
    profile_overrides: Mapping[str, Any] | None = None,
    user_overrides: Mapping[str, Any] | None = None,
    enforced_overrides: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Return (nested token snapshot, per-token provenance).

    Precedence: defaults < base < explicit mixins < profile < user < enforced.
    Mixins are keyed by stable pack ID. Unequal overlapping values require an
    explicit winner for that dotted token path; mapping insertion order never
    decides a conflict. All inputs are copied and remain unchanged.
    """
    layers = [
        ("system-default", _mapping("system_defaults", system_defaults)),
        ("base-theme", _mapping("base_theme", base_theme)),
    ]
    flat: dict[str, Any] = {}
    provenance: dict[str, str] = {}
    for source, values in layers:
        flat.update(values)
        provenance.update({path: source for path in values})

    selected = mixins or {}
    if not isinstance(selected, Mapping):
        raise TokenResolutionError("mixins must be a mapping of pack ID to tokens")
    winners = dict(mixin_winners or {})
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in winners.items()):
        raise TokenResolutionError("mixin_winners must map token paths to pack IDs")

    contributions: dict[str, list[tuple[str, Any]]] = {}
    for pack_id in sorted(selected):
        if not isinstance(pack_id, str) or not pack_id:
            raise TokenResolutionError("mixin IDs must be non-empty strings")
        values = _mapping(f"mixin {pack_id}", selected[pack_id])
        for path, value in values.items():
            contributions.setdefault(path, []).append((pack_id, value))

    for path, entries in contributions.items():
        distinct = []
        for _, value in entries:
            if not any(value == prior for prior in distinct):
                distinct.append(value)
        if len(distinct) == 1:
            chosen_id, chosen_value = entries[0]
        else:
            winner = winners.get(path)
            matching = [(pack_id, value) for pack_id, value in entries if pack_id == winner]
            if len(matching) != 1:
                ids = ", ".join(pack_id for pack_id, _ in entries)
                raise TokenResolutionError(
                    f"mixin conflict for {path} between [{ids}]; choose an explicit winner"
                )
            chosen_id, chosen_value = matching[0]
        flat[path] = deepcopy(chosen_value)
        provenance[path] = f"mixin:{chosen_id}"

    for source, layer in (
        ("profile", profile_overrides),
        ("user", user_overrides),
        ("enforced-policy", enforced_overrides),
    ):
        values = _mapping(source, layer)
        flat.update(values)
        provenance.update({path: source for path in values})

    return _unflatten(flat), provenance

"""Side-effect-free composition of persisted theme profiles and an inert pack catalog.

The catalog is supplied by the caller after pack validation. This module never
opens pack files, imports pack code, or applies desktop settings.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
import re
from typing import Any

from profile_store import ProfileStore
from token_resolver import TokenResolutionError, _flatten, resolve_tokens

_VERSION = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:[-+][0-9A-Za-z.-]+)?$")


class ProfileCompositionError(ValueError):
    """A persisted profile cannot be composed against the supplied catalog."""


@dataclass(frozen=True)
class CompositionResult:
    """Resolved snapshot. Dict members are detached copies, not live store data."""

    profile_id: str
    base_theme_id: str
    base_theme_version: str
    mixin_ids: tuple[str, ...]
    tokens: dict[str, Any]
    provenance: dict[str, str]
    diagnostics: tuple[str, ...] = ()


def _catalog_record(catalog: Mapping[str, Any], pack_id: str, expected_kind: str) -> Mapping[str, Any]:
    record = catalog.get(pack_id)
    if not isinstance(record, Mapping):
        raise ProfileCompositionError(f"required {expected_kind} pack is not installed: {pack_id}")
    if record.get("id", pack_id) != pack_id:
        raise ProfileCompositionError(f"catalog ID mismatch for pack: {pack_id}")
    if record.get("kind") != expected_kind:
        raise ProfileCompositionError(f"pack {pack_id} must have kind {expected_kind}")
    version = record.get("version")
    if not isinstance(version, str) or not _VERSION.fullmatch(version):
        raise ProfileCompositionError(f"catalog pack {pack_id} has an invalid version")
    tokens = record.get("tokens")
    if not isinstance(tokens, Mapping):
        raise ProfileCompositionError(f"catalog pack {pack_id} has invalid token data")
    return record


def compose_profile(
    store: ProfileStore,
    catalog: Mapping[str, Any],
    *,
    profile_id: str | None = None,
    system_defaults: Mapping[str, Any] | None = None,
    user_overrides: Mapping[str, Any] | None = None,
    enforced_overrides: Mapping[str, Any] | None = None,
) -> CompositionResult:
    """Compose an active or named profile without mutating state.

    Catalog shape: {pack_id: {kind: "theme"|"mixin", version: "x.y.z",
    tokens: {...}}}. Base themes must match the profile's pinned version.
    Mixins are selected by ID and use the version exposed by the already
    validated catalog; profile format v1 does not pin mixin versions.
    """
    if not isinstance(catalog, Mapping):
        raise ProfileCompositionError("catalog must be a mapping")
    document = store.load()
    selected_id = profile_id if profile_id is not None else document["active_profile"]
    if selected_id is None:
        raise ProfileCompositionError("no active profile is selected")
    if selected_id not in document["profiles"]:
        raise ProfileCompositionError(f"unknown profile: {selected_id}")
    profile = document["profiles"][selected_id]
    base_ref = profile.get("base_theme")
    if not isinstance(base_ref, Mapping):
        raise ProfileCompositionError("profile has no pinned base theme")

    base_id, pinned_version = base_ref["id"], base_ref["version"]
    base_record = _catalog_record(catalog, base_id, "theme")
    if base_record["version"] != pinned_version:
        raise ProfileCompositionError(
            f"base theme version mismatch for {base_id}: expected {pinned_version}, "
            f"found {base_record['version']}"
        )

    mixin_tokens: dict[str, Mapping[str, Any]] = {}
    for mixin_id in profile["mixins"]:
        record = _catalog_record(catalog, mixin_id, "mixin")
        mixin_tokens[mixin_id] = deepcopy(record["tokens"])

    winners = deepcopy(profile["mixin_winners"])
    for path, winner in winners.items():
        if winner not in mixin_tokens:
            raise ProfileCompositionError(f"mixin winner for {path} is not selected")
        try:
            contributions = _flatten(mixin_tokens[winner])
        except TokenResolutionError as exc:
            raise ProfileCompositionError(f"invalid tokens in mixin {winner}: {exc}") from exc
        if path not in contributions:
            raise ProfileCompositionError(f"mixin winner {winner} does not define token {path}")

    try:
        tokens, provenance = resolve_tokens(
            system_defaults=deepcopy(system_defaults or {}),
            base_theme=deepcopy(base_record["tokens"]),
            mixins=mixin_tokens,
            mixin_winners=winners,
            profile_overrides=deepcopy(profile["overrides"]),
            user_overrides=deepcopy(user_overrides or {}),
            enforced_overrides=deepcopy(enforced_overrides or {}),
        )
    except TokenResolutionError as exc:
        raise ProfileCompositionError(str(exc)) from exc

    return CompositionResult(
        profile_id=selected_id,
        base_theme_id=base_id,
        base_theme_version=pinned_version,
        mixin_ids=tuple(profile["mixins"]),
        tokens=deepcopy(tokens),
        provenance=deepcopy(provenance),
    )

"""Atomic user-scoped persistence for declarative theme profiles."""
from __future__ import annotations
import json, os, re, stat, tempfile, threading
from copy import deepcopy
from pathlib import Path
from typing import Any

FORMAT_VERSION = 1
MAX_STORE_BYTES = 2 * 1024 * 1024
PROFILE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
PACK_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")

class ProfileStoreError(ValueError):
    """Invalid or unsafe profile store data."""

def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProfileStoreError(f"duplicate JSON key: {key}")
        result[key] = value
    return result

def _profile(profile_id: str, value: Any) -> dict:
    if not isinstance(profile_id, str) or not PROFILE_ID.fullmatch(profile_id):
        raise ProfileStoreError("invalid profile ID")
    if not isinstance(value, dict):
        raise ProfileStoreError("profile must be an object")
    allowed = {"name", "base_theme", "mixins", "mixin_winners", "overrides"}
    if set(value) - allowed:
        raise ProfileStoreError("profile contains unknown fields")
    name = value.get("name", profile_id)
    if not isinstance(name, str) or not name.strip() or len(name) > 80:
        raise ProfileStoreError("invalid profile name")
    base = value.get("base_theme")
    if base is not None:
        if not isinstance(base, dict) or set(base) != {"id", "version"}:
            raise ProfileStoreError("base_theme must contain id and version")
        if not isinstance(base["id"], str) or not PACK_ID.fullmatch(base["id"]):
            raise ProfileStoreError("invalid base theme ID")
        if not isinstance(base["version"], str) or not VERSION.fullmatch(base["version"]):
            raise ProfileStoreError("invalid pinned theme version")
    mixins = value.get("mixins", [])
    if not isinstance(mixins, list) or any(not isinstance(x, str) or not PACK_ID.fullmatch(x) for x in mixins):
        raise ProfileStoreError("mixins must be pack IDs")
    if len(set(mixins)) != len(mixins):
        raise ProfileStoreError("duplicate mixin IDs")
    winners = value.get("mixin_winners", {})
    if not isinstance(winners, dict) or any(not isinstance(k, str) or not k or not isinstance(v, str) or v not in mixins for k, v in winners.items()):
        raise ProfileStoreError("mixin winners must reference selected mixins")
    overrides = value.get("overrides", {})
    if not isinstance(overrides, dict):
        raise ProfileStoreError("overrides must be an object")
    return {"name": name.strip(), "base_theme": deepcopy(base), "mixins": list(mixins),
            "mixin_winners": deepcopy(winners), "overrides": deepcopy(overrides)}

class ProfileStore:
    """Atomic JSON persistence; parent directory must be private to the user.

    Thread-safe in-process only. This store persists selection metadata; it does
    not validate installed packs or apply desktop settings.
    """
    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.RLock()

    def _empty(self):
        return {"format_version": FORMAT_VERSION, "active_profile": None, "profiles": {}}

    def _validate(self, doc):
        if not isinstance(doc, dict) or set(doc) != {"format_version", "active_profile", "profiles"}:
            raise ProfileStoreError("invalid profile document shape")
        if doc["format_version"] != FORMAT_VERSION:
            raise ProfileStoreError("unsupported profile format")
        if not isinstance(doc["profiles"], dict):
            raise ProfileStoreError("profiles must be an object")
        profiles = {key: _profile(key, val) for key, val in doc["profiles"].items()}
        active = doc["active_profile"]
        if active is not None and (not isinstance(active, str) or active not in profiles):
            raise ProfileStoreError("active profile must exist")
        return {"format_version": FORMAT_VERSION, "active_profile": active, "profiles": profiles}

    def load(self):
        with self._lock:
            try:
                info = self.path.lstat()
            except FileNotFoundError:
                return self._empty()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                raise ProfileStoreError("store must be a regular non-symlink file")
            if info.st_size > MAX_STORE_BYTES:
                raise ProfileStoreError("profile store exceeds size limit")
            try:
                with self.path.open("rb") as stream:
                    raw = stream.read(MAX_STORE_BYTES + 1)
                if len(raw) > MAX_STORE_BYTES:
                    raise ProfileStoreError("profile store exceeds size limit")
                doc = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs)
            except ProfileStoreError:
                raise
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ProfileStoreError(f"cannot read profile store: {exc}") from exc
            return self._validate(doc)

    def _write(self, doc):
        doc = self._validate(doc)
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            info = self.path.lstat()
        except FileNotFoundError:
            info = None
        if info is not None and (stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode)):
            raise ProfileStoreError("refusing non-regular or symlink store")
        data = json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
        if len(data) > MAX_STORE_BYTES:
            raise ProfileStoreError("profile store exceeds size limit")
        fd, tmp = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, self.path)
            dfd = os.open(self.path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
        except Exception:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass
            raise

    def save_profile(self, profile_id, profile):
        with self._lock:
            doc = self.load()
            doc["profiles"][profile_id] = _profile(profile_id, profile)
            self._write(doc)
            return deepcopy(doc["profiles"][profile_id])

    def activate_profile(self, profile_id):
        with self._lock:
            doc = self.load()
            if profile_id not in doc["profiles"]:
                raise ProfileStoreError(f"unknown profile: {profile_id}")
            doc["active_profile"] = profile_id
            self._write(doc)
            return deepcopy(doc["profiles"][profile_id])

    def delete_profile(self, profile_id, *, activate_fallback=None):
        with self._lock:
            doc = self.load()
            if profile_id not in doc["profiles"]:
                raise ProfileStoreError(f"unknown profile: {profile_id}")
            if doc["active_profile"] == profile_id:
                if activate_fallback not in doc["profiles"] or activate_fallback == profile_id:
                    raise ProfileStoreError("active profile deletion requires an existing fallback")
                doc["active_profile"] = activate_fallback
            del doc["profiles"][profile_id]
            self._write(doc)

    def get_profile(self, profile_id):
        doc = self.load()
        if profile_id not in doc["profiles"]:
            raise ProfileStoreError(f"unknown profile: {profile_id}")
        return deepcopy(doc["profiles"][profile_id])

    def list_profiles(self):
        doc = self.load()
        return sorted((key, val["name"]) for key, val in doc["profiles"].items())

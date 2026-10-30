"""In-memory, owner-scoped theme preview sessions.

A preview is an immutable-by-copy snapshot for UI rendering only. This module
never activates a profile, writes profile data, or calls desktop/KDE adapters.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
import math
import secrets
import threading
import time
from typing import Any, Callable

from profile_composer import CompositionResult


class PreviewSessionError(ValueError):
    """Base error for preview-session lifecycle failures."""


class PreviewSessionNotFound(PreviewSessionError):
    """The session is missing, expired, or does not belong to this owner."""


class PreviewCapacityError(PreviewSessionError):
    """The bounded in-memory preview-session capacity has been reached."""


@dataclass(frozen=True)
class PreviewSession:
    """Detached view of a preview; nested values are caller-owned copies."""

    session_id: str
    owner_id: str
    profile_id: str
    base_theme_id: str
    base_theme_version: str
    tokens: dict[str, Any]
    provenance: dict[str, str]
    created_at: float
    expires_at: float


@dataclass(frozen=True)
class _StoredPreview:
    session_id: str
    owner_id: str
    profile_id: str
    base_theme_id: str
    base_theme_version: str
    tokens: dict[str, Any]
    provenance: dict[str, str]
    created_at: float
    expires_at: float


class PreviewSessionManager:
    """Thread-safe volatile preview store with bounded lifetime and capacity.

    The monotonic clock is used only for elapsed-time expiry; timestamps are
    process-local and must not be persisted or interpreted as wall-clock time.
    The default limits are five minutes and 32 concurrent previews.
    """

    def __init__(
        self,
        *,
        ttl_seconds: float = 300.0,
        max_sessions: int = 32,
        clock: Callable[[], float] = time.monotonic,
        id_factory: Callable[[], str] = lambda: secrets.token_urlsafe(24),
    ) -> None:
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, (int, float)) or ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be a positive number")
        if isinstance(max_sessions, bool) or not isinstance(max_sessions, int) or max_sessions < 1:
            raise ValueError("max_sessions must be a positive integer")
        if not callable(clock) or not callable(id_factory):
            raise ValueError("clock and id_factory must be callable")
        self._ttl = float(ttl_seconds)
        self._max_sessions = max_sessions
        self._clock = clock
        self._id_factory = id_factory
        self._sessions: dict[str, _StoredPreview] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _owner(owner_id: str) -> str:
        if not isinstance(owner_id, str) or not owner_id.strip() or len(owner_id) > 256:
            raise ValueError("owner_id must be a non-empty string of at most 256 characters")
        return owner_id

    @staticmethod
    def _view(item: _StoredPreview) -> PreviewSession:
        return PreviewSession(
            session_id=item.session_id,
            owner_id=item.owner_id,
            profile_id=item.profile_id,
            base_theme_id=item.base_theme_id,
            base_theme_version=item.base_theme_version,
            tokens=deepcopy(item.tokens),
            provenance=deepcopy(item.provenance),
            created_at=item.created_at,
            expires_at=item.expires_at,
        )

    def _now(self) -> float:
        """Return a finite monotonic timestamp; reject broken clock providers."""
        now = self._clock()
        if isinstance(now, bool) or not isinstance(now, (int, float)) or not math.isfinite(now):
            raise ValueError("clock must return a finite numeric monotonic value")
        return float(now)

    def _purge_expired(self, now: float) -> int:
        expired = [key for key, value in self._sessions.items() if now >= value.expires_at]
        for key in expired:
            del self._sessions[key]
        return len(expired)

    def create(self, composition: CompositionResult, *, owner_id: str) -> PreviewSession:
        """Create a volatile preview from a resolved composition snapshot."""
        owner = self._owner(owner_id)
        if not isinstance(composition, CompositionResult):
            raise TypeError("composition must be a CompositionResult")
        if not isinstance(composition.tokens, Mapping) or not isinstance(composition.provenance, Mapping):
            raise ValueError("composition must contain token and provenance mappings")
        if not all(isinstance(key, str) and isinstance(value, str)
                   for key, value in composition.provenance.items()):
            raise ValueError("composition provenance must map token paths to source strings")
        tokens = deepcopy(composition.tokens)
        provenance = deepcopy(composition.provenance)
        now = self._now()

        with self._lock:
            self._purge_expired(now)
            if len(self._sessions) >= self._max_sessions:
                raise PreviewCapacityError("preview session capacity reached")
            session_id = self._id_factory()
            if not isinstance(session_id, str) or not session_id or len(session_id) > 256 or session_id in self._sessions:
                raise PreviewSessionError("session ID factory returned an invalid or duplicate ID")
            item = _StoredPreview(
                session_id=session_id,
                owner_id=owner,
                profile_id=composition.profile_id,
                base_theme_id=composition.base_theme_id,
                base_theme_version=composition.base_theme_version,
                tokens=tokens,
                provenance=provenance,
                created_at=float(now),
                expires_at=float(now) + self._ttl,
            )
            self._sessions[session_id] = item
            return self._view(item)

    def get(self, session_id: str, *, owner_id: str) -> PreviewSession:
        """Read a preview only for its owner; expired sessions are discarded."""
        owner = self._owner(owner_id)
        if not isinstance(session_id, str) or not session_id:
            raise PreviewSessionNotFound("preview session not found")
        now = self._now()
        with self._lock:
            self._purge_expired(now)
            item = self._sessions.get(session_id)
            if item is None or item.owner_id != owner:
                raise PreviewSessionNotFound("preview session not found")
            return self._view(item)

    def cancel(self, session_id: str, *, owner_id: str) -> bool:
        """Cancel an owned preview; return False when it has already expired."""
        owner = self._owner(owner_id)
        if not isinstance(session_id, str) or not session_id:
            raise PreviewSessionNotFound("preview session not found")
        now = self._now()
        with self._lock:
            self._purge_expired(now)
            item = self._sessions.get(session_id)
            if item is None:
                return False
            if item.owner_id != owner:
                raise PreviewSessionNotFound("preview session not found")
            del self._sessions[session_id]
            return True

    def cleanup_expired(self) -> int:
        """Remove all expired sessions and return the number removed."""
        now = self._now()
        with self._lock:
            return self._purge_expired(now)

    def count(self) -> int:
        """Return the current non-expired session count."""
        now = self._now()
        with self._lock:
            self._purge_expired(now)
            return len(self._sessions)

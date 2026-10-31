from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import Event
from typing import Any, Mapping, Sequence


class Capability(str, Enum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ProviderCapabilities:
    chat: Capability = Capability.UNKNOWN
    streaming: Capability = Capability.UNKNOWN
    cancellation: Capability = Capability.UNKNOWN
    embeddings: Capability = Capability.UNKNOWN
    structured_output: Capability = Capability.UNKNOWN
    tool_call_proposals: Capability = Capability.UNKNOWN
    vision: Capability = Capability.UNKNOWN
    audio: Capability = Capability.UNKNOWN
    inventory: Capability = Capability.UNKNOWN
    install: Capability = Capability.UNKNOWN
    remove: Capability = Capability.UNKNOWN
    unload: Capability = Capability.UNKNOWN
    resource_metrics: Capability = Capability.UNKNOWN
    offline_inference: Capability = Capability.UNKNOWN


@dataclass(frozen=True)
class InferenceRequest:
    request_id: str
    model: str
    messages: Sequence[Mapping[str, Any]]
    max_output_tokens: int = 256
    context_limit: int = 4096
    timeout_seconds: float = 60.0


@dataclass(frozen=True)
class InferenceEvent:
    request_id: str
    sequence: int
    event_type: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))


class CancellationToken:
    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()


class RuntimeErrorCode(str, Enum):
    INVALID_REQUEST = "invalid_request"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PROVIDER_DISCONNECTED = "provider_disconnected"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    INSUFFICIENT_RESOURCES = "insufficient_resources"
    DEADLINE_EXCEEDED = "deadline_exceeded"
    CANCELLED = "cancelled"
    STORAGE_FULL = "storage_full"
    INTEGRITY_CHECK_FAILED = "integrity_check_failed"
    PERMISSION_DENIED = "permission_denied"
    MODEL_NOT_FOUND = "model_not_found"


class RuntimeError(Exception):
    def __init__(self, code: RuntimeErrorCode, safe_message: str, *, retryable: bool = False):
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message
        self.retryable = retryable


@dataclass(frozen=True)
class RuntimeLimits:
    max_concurrent_requests: int = 1
    max_input_characters: int = 100_000
    max_output_tokens: int = 2048
    max_context_tokens: int = 8192
    request_timeout_seconds: float = 120.0
    minimum_available_memory_bytes: int = 0

    def __post_init__(self) -> None:
        if self.max_concurrent_requests < 1 or self.max_input_characters < 1:
            raise ValueError("runtime limits must be positive")
        if self.max_output_tokens < 1 or self.max_context_tokens < 1:
            raise ValueError("token limits must be positive")
        if self.minimum_available_memory_bytes < 0:
            raise ValueError("memory reserve must not be negative")
        if self.request_timeout_seconds <= 0:
            raise ValueError("timeouts must be positive")

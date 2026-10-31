from __future__ import annotations

import logging
import math
import threading
import time
from datetime import datetime
from pathlib import Path
from collections.abc import Mapping, Sequence
from typing import Iterable

from .providers.base import InferenceProvider
from .types import CancellationToken, InferenceEvent, InferenceRequest, RuntimeError as TuskerRuntimeError, RuntimeErrorCode, RuntimeLimits

_LOG = logging.getLogger("tusker_ai.trace")


class InferenceRuntime:
    """Provider-neutral request guard. Trace records contain metadata only."""

    def __init__(self, provider: InferenceProvider, limits: RuntimeLimits | None = None):
        self.provider = provider
        self.limits = limits or RuntimeLimits()
        self._slots = threading.BoundedSemaphore(self.limits.max_concurrent_requests)

    def infer(self, request: InferenceRequest, cancellation: CancellationToken | None = None) -> Iterable[InferenceEvent]:
        token = cancellation or CancellationToken()
        self._validate(request)
        acquired = self._slots.acquire(blocking=False)
        if not acquired:
            raise TuskerRuntimeError(RuntimeErrorCode.INSUFFICIENT_RESOURCES, "Inference capacity is currently exhausted", retryable=True)
        start = time.monotonic()
        terminal = False
        started = False
        previous_sequence = -1
        previous_timestamp = None
        try:
            available = self._available_memory_bytes()
            if self.limits.minimum_available_memory_bytes and (available is None or available < self.limits.minimum_available_memory_bytes):
                raise TuskerRuntimeError(RuntimeErrorCode.INSUFFICIENT_RESOURCES, "Available memory is below the configured safety reserve", retryable=True)
            _LOG.info("inference_started", extra={"request_id": request.request_id, "provider_id": self.provider.provider_id, "model_id": request.model})
            for event in self.provider.infer(request, token):
                if (
                    not isinstance(event, InferenceEvent)
                    or not isinstance(event.request_id, str)
                    or isinstance(event.sequence, bool)
                    or not isinstance(event.sequence, int)
                    or event.sequence < 0
                    or not isinstance(event.event_type, str)
                    or not isinstance(event.payload, Mapping)
                    or not isinstance(event.timestamp, str)
                ):
                    raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Provider returned a malformed inference event")
                if terminal:
                    raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Provider emitted an event after a terminal event")
                if time.monotonic() - start > min(request.timeout_seconds, self.limits.request_timeout_seconds):
                    raise TuskerRuntimeError(RuntimeErrorCode.DEADLINE_EXCEEDED, "Inference deadline exceeded", retryable=True)
                if token.cancelled and event.event_type not in {"cancelled", "failed", "completed"}:
                    continue
                if event.event_type not in {"started", "text_delta", "tool_call_delta", "usage", "resource", "completed", "cancelled", "failed"}:
                    raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Provider returned an unknown event type")
                if event.request_id != request.request_id:
                    raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Provider returned a mismatched request identifier")
                if event.sequence <= previous_sequence:
                    raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Provider returned an out-of-order event sequence")
                previous_sequence = event.sequence
                try:
                    event_time = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
                    if event_time.tzinfo is None or (previous_timestamp is not None and event_time < previous_timestamp):
                        raise ValueError
                except (AttributeError, TypeError, ValueError):
                    raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Provider returned an invalid or regressing event timestamp") from None
                previous_timestamp = event_time
                self._validate_event_payload(event)
                if not started and event.event_type != "started":
                    raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Provider stream did not begin with a started event")
                if event.event_type == "started":
                    if started or terminal:
                        raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Provider returned an invalid start event")
                    started = True
                if event.event_type in {"completed", "cancelled", "failed"}:
                    if not started:
                        raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Provider terminated before starting")
                    if terminal:
                        raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Provider returned duplicate terminal events")
                    terminal = True
                _LOG.debug("inference_event", extra={"request_id": request.request_id, "sequence": event.sequence, "event_type": event.event_type})
                yield event
            if not started or not terminal:
                raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Provider stream ended without a terminal event", retryable=True)
        finally:
            _LOG.info("inference_finished", extra={"request_id": request.request_id, "elapsed_ms": int((time.monotonic() - start) * 1000)})
            self._slots.release()

    @staticmethod
    def _validate_event_payload(event: InferenceEvent) -> None:
        payload = event.payload
        valid = True
        if event.event_type == "text_delta":
            delta = payload.get("delta")
            valid = isinstance(delta, str) and bool(delta)
        elif event.event_type == "completed":
            reason = payload.get("finish_reason")
            valid = reason is None or (
                isinstance(reason, str)
                and reason in {"stop", "output_limit", "tool_calls", "cancelled", "provider_specific", "unknown"}
            )
        elif event.event_type == "usage":
            for key in ("input_tokens", "output_tokens"):
                value = payload.get(key)
                if value is not None and (
                    isinstance(value, bool) or not isinstance(value, int) or value < 0
                ):
                    valid = False
                    break
        elif event.event_type == "cancelled":
            reason = payload.get("reason")
            valid = reason is None or isinstance(reason, str)
        if not valid:
            raise TuskerRuntimeError(
                RuntimeErrorCode.PROVIDER_DISCONNECTED,
                "Provider returned a malformed inference event payload",
            )

    @staticmethod
    def _available_memory_bytes() -> int | None:
        host_available = None
        try:
            for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
                if line.startswith("MemAvailable:"):
                    host_available = int(line.split()[1]) * 1024
                    break
        except (OSError, ValueError, IndexError):
            pass
        # Respect cgroup v2 memory ceilings when running in a managed service/container.
        try:
            limit_text = Path("/sys/fs/cgroup/memory.max").read_text(encoding="ascii").strip()
            current_text = Path("/sys/fs/cgroup/memory.current").read_text(encoding="ascii").strip()
            if limit_text != "max":
                cgroup_available = max(0, int(limit_text) - int(current_text))
                return cgroup_available if host_available is None else min(host_available, cgroup_available)
        except (OSError, ValueError):
            pass
        return host_available

    def _validate(self, request: InferenceRequest) -> None:
        if not isinstance(request, InferenceRequest):
            raise TuskerRuntimeError(RuntimeErrorCode.INVALID_REQUEST, "A typed inference request is required")
        if (
            not isinstance(request.request_id, str)
            or not request.request_id.strip()
            or len(request.request_id) > 128
            or not isinstance(request.model, str)
            or not request.model.strip()
            or len(request.model) > 256
        ):
            raise TuskerRuntimeError(RuntimeErrorCode.INVALID_REQUEST, "Request identifier and model must be non-empty bounded strings")
        if (
            not isinstance(request.messages, Sequence)
            or isinstance(request.messages, (str, bytes, bytearray))
            or not request.messages
        ):
            raise TuskerRuntimeError(RuntimeErrorCode.INVALID_REQUEST, "At least one typed message is required")
        allowed_roles = {"system", "developer", "user", "assistant", "tool"}
        total_characters = 0
        for message in request.messages:
            if not isinstance(message, Mapping):
                raise TuskerRuntimeError(RuntimeErrorCode.INVALID_REQUEST, "Each message must be an object")
            role = message.get("role")
            content = message.get("content")
            if not isinstance(role, str) or role not in allowed_roles or not isinstance(content, str):
                raise TuskerRuntimeError(RuntimeErrorCode.INVALID_REQUEST, "Each message requires a supported role and string content")
            total_characters += len(content)
            if total_characters > self.limits.max_input_characters:
                raise TuskerRuntimeError(RuntimeErrorCode.INVALID_REQUEST, "Input exceeds the configured size limit")
        if (
            isinstance(request.max_output_tokens, bool)
            or not isinstance(request.max_output_tokens, int)
            or not 1 <= request.max_output_tokens <= self.limits.max_output_tokens
        ):
            raise TuskerRuntimeError(RuntimeErrorCode.INVALID_REQUEST, "Output token limit is outside the configured bound")
        if (
            isinstance(request.context_limit, bool)
            or not isinstance(request.context_limit, int)
            or not 1 <= request.context_limit <= self.limits.max_context_tokens
        ):
            raise TuskerRuntimeError(RuntimeErrorCode.INVALID_REQUEST, "Context limit is outside the configured bound")
        if (
            isinstance(request.timeout_seconds, bool)
            or not isinstance(request.timeout_seconds, (int, float))
            or (isinstance(request.timeout_seconds, float) and not math.isfinite(request.timeout_seconds))
            or not 0 < request.timeout_seconds <= self.limits.request_timeout_seconds
        ):
            raise TuskerRuntimeError(RuntimeErrorCode.INVALID_REQUEST, "Request timeout is outside the configured bound")

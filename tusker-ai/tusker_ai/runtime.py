from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from pathlib import Path
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
        available = self._available_memory_bytes()
        if self.limits.minimum_available_memory_bytes and (available is None or available < self.limits.minimum_available_memory_bytes):
            self._slots.release()
            raise TuskerRuntimeError(RuntimeErrorCode.INSUFFICIENT_RESOURCES, "Available memory is below the configured safety reserve", retryable=True)
        start = time.monotonic()
        terminal = False
        started = False
        previous_sequence = -1
        previous_timestamp = None
        try:
            _LOG.info("inference_started", extra={"request_id": request.request_id, "provider_id": self.provider.provider_id, "model_id": request.model})
            for event in self.provider.infer(request, token):
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
    def _available_memory_bytes() -> int | None:
        try:
            for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) * 1024
        except (OSError, ValueError, IndexError):
            return None
        return None

    def _validate(self, request: InferenceRequest) -> None:
        if not request.request_id or len(request.request_id) > 128 or not request.model:
            raise TuskerRuntimeError(RuntimeErrorCode.INVALID_REQUEST, "Request identifier and model are required")
        if not request.messages or any(not isinstance(m, dict) for m in request.messages):
            raise TuskerRuntimeError(RuntimeErrorCode.INVALID_REQUEST, "At least one typed message is required")
        if sum(len(str(m.get("content", ""))) for m in request.messages) > self.limits.max_input_characters:
            raise TuskerRuntimeError(RuntimeErrorCode.INVALID_REQUEST, "Input exceeds the configured size limit")
        if not 1 <= request.max_output_tokens <= self.limits.max_output_tokens:
            raise TuskerRuntimeError(RuntimeErrorCode.INVALID_REQUEST, "Output token limit is outside the configured bound")
        if not 1 <= request.context_limit <= self.limits.max_context_tokens:
            raise TuskerRuntimeError(RuntimeErrorCode.INVALID_REQUEST, "Context limit is outside the configured bound")
        if not 0 < request.timeout_seconds <= self.limits.request_timeout_seconds:
            raise TuskerRuntimeError(RuntimeErrorCode.INVALID_REQUEST, "Request timeout is outside the configured bound")

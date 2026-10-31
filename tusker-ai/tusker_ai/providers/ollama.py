from __future__ import annotations

import json
import socket
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from ..types import (
    CancellationToken, InferenceEvent, InferenceRequest, ProviderCapabilities,
    RuntimeError as TuskerRuntimeError, RuntimeErrorCode,
)


class OllamaProvider:
    """Ollama local HTTP adapter. Never starts, stops, or kills the shared daemon."""

    provider_id = "ollama"

    def __init__(self, endpoint: str = "http://127.0.0.1:11434", *, read_timeout: float = 2.0):
        parsed = urlsplit(endpoint)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Ollama endpoint must use HTTP on loopback")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Ollama endpoint must not contain credentials or query data")
        if read_timeout <= 0:
            raise ValueError("read_timeout must be positive")
        self._base = endpoint.rstrip("/")
        self._read_timeout = read_timeout

    def capabilities(self) -> ProviderCapabilities:
        # Do not advertise support until a pinned live Ollama version passes conformance.
        return ProviderCapabilities()

    def version(self) -> str | None:
        try:
            req = Request(self._base + "/api/version", method="GET")
            with urlopen(req, timeout=self._read_timeout) as response:
                data = json.loads(response.read(65536))
                value = data.get("version")
                return value if isinstance(value, str) else None
        except (OSError, URLError, HTTPError, socket.timeout, json.JSONDecodeError):
            return None

    def health(self) -> bool:
        return self.version() is not None

    def infer(self, request: InferenceRequest, cancellation: CancellationToken) -> Iterable[InferenceEvent]:
        if cancellation.cancelled:
            yield InferenceEvent(request.request_id, 0, "cancelled", {"reason": "caller_cancelled"})
            return
        payload = {
            "model": request.model,
            "messages": list(request.messages),
            "stream": True,
            "options": {"num_predict": request.max_output_tokens, "num_ctx": request.context_limit},
        }
        req = Request(
            self._base + "/api/chat",
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/x-ndjson"},
            method="POST",
        )
        seq = 0
        try:
            with urlopen(req, timeout=min(request.timeout_seconds, self._read_timeout)) as response:
                yield InferenceEvent(request.request_id, seq, "started", {"provider_id": self.provider_id, "model_id": request.model})
                seq += 1
                for raw_line in response:
                    if cancellation.cancelled:
                        yield InferenceEvent(request.request_id, seq, "cancelled", {"reason": "caller_cancelled"})
                        return
                    if not raw_line.strip():
                        continue
                    try:
                        chunk = json.loads(raw_line)
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Provider returned an invalid stream frame")
                    message = chunk.get("message") or {}
                    delta = message.get("content")
                    if isinstance(delta, str) and delta:
                        yield InferenceEvent(request.request_id, seq, "text_delta", {"delta": delta})
                        seq += 1
                    if chunk.get("done") is True:
                        input_tokens = chunk.get("prompt_eval_count")
                        output_tokens = chunk.get("eval_count")
                        if input_tokens is not None or output_tokens is not None:
                            yield InferenceEvent(request.request_id, seq, "usage", {"input_tokens": input_tokens, "output_tokens": output_tokens})
                            seq += 1
                        reason = chunk.get("done_reason")
                        finish_reason = reason if reason in {"stop", "output_limit", "tool_calls"} else "provider_specific" if reason else "unknown"
                        yield InferenceEvent(request.request_id, seq, "completed", {"finish_reason": finish_reason})
                        return
                raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Provider stream ended without a terminal event", retryable=True)
        except HTTPError as exc:
            # Never propagate provider response bodies: they may contain prompts or secrets.
            code = RuntimeErrorCode.MODEL_NOT_FOUND if exc.code == 404 else RuntimeErrorCode.PROVIDER_UNAVAILABLE
            raise TuskerRuntimeError(code, "Local inference provider rejected the request") from None
        except (URLError, socket.timeout, TimeoutError, OSError):
            raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Local inference provider is unavailable or timed out", retryable=True) from None

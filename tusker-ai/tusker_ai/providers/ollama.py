from __future__ import annotations

import json
import math
import socket
import time
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, ProxyHandler, HTTPRedirectHandler, build_opener

from ..types import (
    CancellationToken, InferenceEvent, InferenceRequest, ProviderCapabilities,
    RuntimeError as TuskerRuntimeError, RuntimeErrorCode,
)


_MAX_STREAM_FRAME_BYTES = 1_048_576
_MAX_REQUEST_BODY_BYTES = 4_194_304
_MAX_STREAM_RESPONSE_BYTES = 8_388_608


class _NoRedirectHandler(HTTPRedirectHandler):
    """A local inference endpoint must not redirect prompts to another host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class OllamaProvider:
    """Ollama local HTTP adapter. Never starts, stops, or kills the shared daemon."""

    provider_id = "ollama"

    def __init__(self, endpoint: str = "http://127.0.0.1:11434", *, read_timeout: float = 2.0):
        parsed = urlsplit(endpoint)
        try:
            port = parsed.port
        except ValueError:
            raise ValueError("Ollama endpoint has an invalid port") from None
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.path not in {"", "/"}
            or (port is not None and not 1 <= port <= 65535)
        ):
            raise ValueError("Ollama endpoint must use HTTP on loopback with a valid port and no path")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Ollama endpoint must not contain credentials or query data")
        if (
            isinstance(read_timeout, bool)
            or not isinstance(read_timeout, (int, float))
            or not math.isfinite(read_timeout)
            or read_timeout <= 0
        ):
            raise ValueError("read_timeout must be a finite positive number")
        self._base = endpoint.rstrip("/")
        self._read_timeout = read_timeout
        # Local inference must not inherit HTTP(S)_PROXY / ALL_PROXY from the
        # user's shell, and a local endpoint must not redirect prompt-bearing
        # requests to a different host.
        self._opener = build_opener(ProxyHandler({}), _NoRedirectHandler())

    def capabilities(self) -> ProviderCapabilities:
        # Do not advertise a provider capability as supported until a pinned live
        # Ollama version has passed the corresponding conformance case.
        return ProviderCapabilities()

    def version(self) -> str | None:
        try:
            req = Request(self._base + "/api/version", method="GET")
            with self._opener.open(req, timeout=self._read_timeout) as response:
                raw = response.read(65537)
                if len(raw) > 65536:
                    return None
                data = json.loads(raw)
                if not isinstance(data, dict):
                    return None
                value = data.get("version")
                return value if isinstance(value, str) and value else None
        except (OSError, URLError, HTTPError, socket.timeout, json.JSONDecodeError, UnicodeDecodeError):
            return None

    def health(self) -> bool:
        return self.version() is not None

    def infer(self, request: InferenceRequest, cancellation: CancellationToken) -> Iterable[InferenceEvent]:
        if cancellation.cancelled:
            raise TuskerRuntimeError(RuntimeErrorCode.CANCELLED, "Inference was cancelled before dispatch")
        payload = {
            "model": request.model,
            "messages": list(request.messages),
            "stream": True,
            "options": {"num_predict": request.max_output_tokens, "num_ctx": request.context_limit},
        }
        try:
            encoded_payload = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode("utf-8")
        except (TypeError, ValueError, RecursionError, UnicodeEncodeError):
            raise TuskerRuntimeError(
                RuntimeErrorCode.INVALID_REQUEST,
                "Inference request contains data that cannot be encoded for the local provider",
            ) from None
        if len(encoded_payload) > _MAX_REQUEST_BODY_BYTES:
            raise TuskerRuntimeError(
                RuntimeErrorCode.INVALID_REQUEST,
                "Inference request exceeds the local provider payload limit",
            )
        req = Request(
            self._base + "/api/chat",
            data=encoded_payload,
            headers={"Content-Type": "application/json", "Accept": "application/x-ndjson"},
            method="POST",
        )
        seq = 0
        stream_bytes = 0
        deadline = time.monotonic() + request.timeout_seconds
        try:
            with self._opener.open(req, timeout=min(request.timeout_seconds, self._read_timeout)) as response:
                yield InferenceEvent(request.request_id, seq, "started", {"provider_id": self.provider_id, "model_id": request.model})
                seq += 1
                while True:
                    if cancellation.cancelled:
                        yield InferenceEvent(request.request_id, seq, "cancelled", {"reason": "caller_cancelled"})
                        return
                    try:
                        raw_line = response.readline(_MAX_STREAM_FRAME_BYTES + 1)
                    except socket.timeout:
                        if cancellation.cancelled:
                            yield InferenceEvent(request.request_id, seq, "cancelled", {"reason": "caller_cancelled"})
                            return
                        if time.monotonic() >= deadline:
                            raise TuskerRuntimeError(RuntimeErrorCode.DEADLINE_EXCEEDED, "Inference deadline exceeded", retryable=True) from None
                        continue
                    stream_bytes += len(raw_line)
                    if stream_bytes > _MAX_STREAM_RESPONSE_BYTES:
                        raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Provider stream exceeded the response size limit")
                    if cancellation.cancelled:
                        yield InferenceEvent(request.request_id, seq, "cancelled", {"reason": "caller_cancelled"})
                        return
                    if time.monotonic() >= deadline:
                        raise TuskerRuntimeError(RuntimeErrorCode.DEADLINE_EXCEEDED, "Inference deadline exceeded", retryable=True) from None
                    if len(raw_line) > _MAX_STREAM_FRAME_BYTES:
                        raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Provider stream frame exceeded the size limit")
                    if not raw_line:
                        break
                    if not raw_line.strip():
                        continue
                    try:
                        chunk = json.loads(raw_line)
                    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
                        raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Provider returned an invalid stream frame") from None
                    if not isinstance(chunk, dict):
                        raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Provider returned an invalid stream frame")
                    message = chunk.get("message", {})
                    if not isinstance(message, dict):
                        raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Provider returned an invalid stream frame")
                    delta = message.get("content")
                    if delta is not None and not isinstance(delta, str):
                        raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Provider returned an invalid stream frame")
                    done = chunk.get("done", False)
                    if not isinstance(done, bool):
                        raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Provider returned an invalid stream frame")
                    input_tokens = chunk.get("prompt_eval_count")
                    output_tokens = chunk.get("eval_count")
                    for token_count in (input_tokens, output_tokens):
                        if token_count is not None and (
                            isinstance(token_count, bool) or not isinstance(token_count, int) or token_count < 0
                        ):
                            raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Provider returned invalid usage metadata")
                    reason = chunk.get("done_reason")
                    if reason is not None and not isinstance(reason, str):
                        raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Provider returned an invalid stream frame")
                    if isinstance(delta, str) and delta:
                        yield InferenceEvent(request.request_id, seq, "text_delta", {"delta": delta})
                        seq += 1
                    if done:
                        if input_tokens is not None or output_tokens is not None:
                            yield InferenceEvent(request.request_id, seq, "usage", {"input_tokens": input_tokens, "output_tokens": output_tokens})
                            seq += 1
                        finish_reason = reason if reason in {"stop", "output_limit", "tool_calls"} else "provider_specific" if reason else "unknown"
                        yield InferenceEvent(request.request_id, seq, "completed", {"finish_reason": finish_reason})
                        return
                raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Provider stream ended without a terminal event", retryable=True)
        except HTTPError as exc:
            # Never propagate provider response bodies: they may contain prompts or secrets.
            code = RuntimeErrorCode.MODEL_NOT_FOUND if exc.code == 404 else RuntimeErrorCode.PROVIDER_UNAVAILABLE
            raise TuskerRuntimeError(code, "Local inference provider rejected the request") from None
        except (URLError, socket.timeout, TimeoutError, OSError):
            if time.monotonic() >= deadline:
                raise TuskerRuntimeError(RuntimeErrorCode.DEADLINE_EXCEEDED, "Inference deadline exceeded", retryable=True) from None
            raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "Local inference provider is unavailable", retryable=True) from None

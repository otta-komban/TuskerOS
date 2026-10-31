import logging
import time
import unittest
from unittest.mock import patch

from tusker_ai.runtime import InferenceRuntime
from tusker_ai.types import (
    CancellationToken, Capability, InferenceEvent, InferenceRequest,
    ProviderCapabilities, RuntimeError as TuskerRuntimeError, RuntimeErrorCode, RuntimeLimits,
)
from tusker_ai.providers.ollama import OllamaProvider


class FakeProvider:
    provider_id = "fake"

    def __init__(self, events=None):
        self.events = events or [
            InferenceEvent("r1", 0, "started", {}),
            InferenceEvent("r1", 1, "text_delta", {"delta": "hello"}),
            InferenceEvent("r1", 2, "completed", {"finish_reason": "stop"}),
        ]

    def capabilities(self):
        return ProviderCapabilities(chat=Capability.SUPPORTED)

    def health(self):
        return True

    def infer(self, request, cancellation):
        yield from self.events


class RuntimeTests(unittest.TestCase):
    def request(self, **kwargs):
        values = dict(request_id="r1", model="tiny", messages=[{"role": "user", "content": "hello"}])
        values.update(kwargs)
        return InferenceRequest(**values)

    def test_successful_stream_has_one_terminal(self):
        events = list(InferenceRuntime(FakeProvider()).infer(self.request()))
        self.assertEqual([e.event_type for e in events], ["started", "text_delta", "completed"])

    def test_rejects_oversized_input_before_provider(self):
        runtime = InferenceRuntime(FakeProvider(), RuntimeLimits(max_input_characters=3))
        with self.assertRaises(TuskerRuntimeError) as ctx:
            list(runtime.infer(self.request()))
        self.assertEqual(ctx.exception.code, RuntimeErrorCode.INVALID_REQUEST)

    def test_rejects_output_limit_above_policy(self):
        with self.assertRaises(TuskerRuntimeError):
            list(InferenceRuntime(FakeProvider()).infer(self.request(max_output_tokens=999999)))

    def test_rejects_missing_terminal(self):
        fake = FakeProvider([InferenceEvent("r1", 0, "started", {})])
        with self.assertRaises(TuskerRuntimeError) as ctx:
            list(InferenceRuntime(fake).infer(self.request()))
        self.assertEqual(ctx.exception.code, RuntimeErrorCode.PROVIDER_DISCONNECTED)

    def test_rejects_cross_request_event(self):
        fake = FakeProvider([InferenceEvent("other", 0, "started", {})])
        with self.assertRaises(TuskerRuntimeError):
            list(InferenceRuntime(fake).infer(self.request()))

    def test_trace_never_logs_prompt_or_delta(self):
        fake = FakeProvider([InferenceEvent("r1", 0, "started", {}), InferenceEvent("r1", 1, "text_delta", {"delta": "secret prompt output"}), InferenceEvent("r1", 2, "completed", {})])
        with self.assertLogs("tusker_ai.trace", level=logging.DEBUG) as captured:
            list(InferenceRuntime(fake).infer(self.request(messages=[{"role": "user", "content": "secret prompt output"}])))
        self.assertNotIn("secret prompt output", "\n".join(captured.output))

    def test_ollama_rejects_non_loopback_endpoint(self):
        with self.assertRaises(ValueError):
            OllamaProvider("http://0.0.0.0:11434")

    def test_ollama_unknown_capabilities_stay_unknown(self):
        caps = OllamaProvider().capabilities()
        self.assertEqual(caps.chat, Capability.UNKNOWN)
        self.assertEqual(caps.streaming, Capability.UNKNOWN)
        self.assertEqual(caps.cancellation, Capability.UNKNOWN)
        self.assertEqual(caps.vision, Capability.UNKNOWN)

    def test_cancel_during_inference_is_terminal_and_request_scoped(self):
        class CancellingProvider(FakeProvider):
            def infer(self, request, cancellation):
                yield InferenceEvent(request.request_id, 0, "started", {})
                cancellation.cancel()
                yield InferenceEvent(request.request_id, 1, "cancelled", {"reason": "caller_cancelled"})
        events = list(InferenceRuntime(CancellingProvider()).infer(self.request()))
        self.assertEqual([event.event_type for event in events], ["started", "cancelled"])

    def test_deadline_is_enforced(self):
        class SlowProvider(FakeProvider):
            def infer(self, request, cancellation):
                time.sleep(0.02)
                yield InferenceEvent(request.request_id, 0, "started", {})
        limits = RuntimeLimits(request_timeout_seconds=0.01)
        with self.assertRaises(TuskerRuntimeError) as ctx:
            list(InferenceRuntime(SlowProvider(), limits).infer(self.request(timeout_seconds=0.01)))
        self.assertEqual(ctx.exception.code, RuntimeErrorCode.DEADLINE_EXCEEDED)

    def test_available_memory_reserve_is_enforced(self):
        runtime = InferenceRuntime(FakeProvider(), RuntimeLimits(minimum_available_memory_bytes=1024))
        with patch.object(runtime, "_available_memory_bytes", return_value=512):
            with self.assertRaises(TuskerRuntimeError) as ctx:
                list(runtime.infer(self.request()))
        self.assertEqual(ctx.exception.code, RuntimeErrorCode.INSUFFICIENT_RESOURCES)

    def test_concurrency_is_bounded(self):
        runtime = InferenceRuntime(FakeProvider(), RuntimeLimits(max_concurrent_requests=1))
        first = runtime.infer(self.request())
        self.assertEqual(next(iter(first)).event_type, "started")
        with self.assertRaises(TuskerRuntimeError) as ctx:
            list(runtime.infer(self.request(request_id="r2")))
        self.assertEqual(ctx.exception.code, RuntimeErrorCode.INSUFFICIENT_RESOURCES)
        self.assertEqual([event.event_type for event in first], ["text_delta", "completed"])

    def test_rejects_non_monotonic_sequence(self):
        fake = FakeProvider([InferenceEvent("r1", 0, "started", {}), InferenceEvent("r1", 0, "completed", {})])
        with self.assertRaises(TuskerRuntimeError):
            list(InferenceRuntime(fake).infer(self.request()))

    def test_rejects_event_after_terminal(self):
        fake = FakeProvider([InferenceEvent("r1", 0, "started", {}), InferenceEvent("r1", 1, "completed", {}), InferenceEvent("r1", 2, "text_delta", {"delta": "late"})])
        with self.assertRaises(TuskerRuntimeError):
            list(InferenceRuntime(fake).infer(self.request()))

    def test_rejects_regressing_timestamps(self):
        from datetime import datetime, timezone, timedelta
        first = datetime.now(timezone.utc)
        earlier = first - timedelta(seconds=1)
        fake = FakeProvider([InferenceEvent("r1", 0, "started", {}, first.isoformat()), InferenceEvent("r1", 1, "completed", {}, earlier.isoformat())])
        with self.assertRaises(TuskerRuntimeError):
            list(InferenceRuntime(fake).infer(self.request()))

    def test_memory_probe_exception_releases_concurrency_slot(self):
        runtime = InferenceRuntime(FakeProvider(), RuntimeLimits(max_concurrent_requests=1))
        with patch.object(runtime, "_available_memory_bytes", side_effect=OSError("fixture probe failure")):
            with self.assertRaises(OSError):
                list(runtime.infer(self.request()))
        events = list(runtime.infer(self.request()))
        self.assertEqual(events[-1].event_type, "completed")

    def test_provider_failure_releases_concurrency_slot(self):
        class FailingProvider(FakeProvider):
            def infer(self, request, cancellation):
                if request.request_id == "r1":
                    yield InferenceEvent(request.request_id, 0, "started", {})
                    raise TuskerRuntimeError(RuntimeErrorCode.PROVIDER_DISCONNECTED, "fixture failure")
                yield InferenceEvent(request.request_id, 0, "started", {})
                yield InferenceEvent(request.request_id, 1, "completed", {})

        runtime = InferenceRuntime(FailingProvider(), RuntimeLimits(max_concurrent_requests=1))
        with self.assertRaises(TuskerRuntimeError):
            list(runtime.infer(self.request()))
        events = list(runtime.infer(self.request(request_id="after-failure")))
        self.assertEqual(events[-1].event_type, "completed")

    def test_closing_partial_stream_releases_concurrency_slot(self):
        runtime = InferenceRuntime(FakeProvider(), RuntimeLimits(max_concurrent_requests=1))
        stream = runtime.infer(self.request())
        self.assertEqual(next(iter(stream)).event_type, "started")
        stream.close()
        events = list(runtime.infer(self.request()))
        self.assertEqual(events[-1].event_type, "completed")

    def test_cancel_before_dispatch_returns_typed_error_without_start_event(self):
        token = CancellationToken()
        token.cancel()
        with self.assertRaises(TuskerRuntimeError) as ctx:
            list(OllamaProvider().infer(self.request(), token))
        self.assertEqual(ctx.exception.code, RuntimeErrorCode.CANCELLED)


if __name__ == "__main__":
    unittest.main()

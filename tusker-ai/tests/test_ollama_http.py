import json
import os
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from tusker_ai.providers.ollama import OllamaProvider
from tusker_ai.types import InferenceRequest, CancellationToken


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/version" and getattr(type(self), "version_body", None) is not None:
            body = type(self).version_body
        else:
            body = json.dumps({"version": "test-live-http"}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        if request.get("model") == "oversized":
            chunks = [{"message": {"content": "x" * (1024 * 1024 + 100)}, "done": False}]
        elif request.get("model") == "aggregate-oversized":
            chunks = [{"message": {"content": "x" * 900_000}, "done": False} for _ in range(10)]
        elif request.get("model") == "deep-json":
            chunks = [None]
        elif request.get("model") == "bad-shape":
            chunks = [[]]
        elif request.get("model") == "bad-message":
            chunks = [{"message": "not-an-object", "done": False}]
        elif request.get("model") == "falsey-message":
            chunks = [{"message": [], "done": False}]
        elif request.get("model") == "bad-content":
            chunks = [{"message": {"content": []}, "done": False}]
        elif request.get("model") == "bad-done":
            chunks = [{"message": {}, "done": "yes"}]
        elif request.get("model") == "bad-reason":
            chunks = [{"message": {}, "done": True, "done_reason": []}]
        elif request.get("model") == "bad-usage":
            chunks = [{"message": {}, "done": True, "prompt_eval_count": True}]
        else:
            chunks = [
                {"message": {"content": "Tusker "}, "done": False},
            {"message": {"content": "runtime"}, "done": False},
                {"done": True, "done_reason": "stop", "prompt_eval_count": 8, "eval_count": 2},
            ]
        self.send_response(200); self.send_header("Content-Type", "application/x-ndjson"); self.end_headers()
        try:
            for index, chunk in enumerate(chunks):
                if request.get("model") in {"late-frame", "cancel-frame"} and index == 0:
                    time.sleep(0.08)
                raw = (b"[" * 1200 + b"0" + b"]" * 1200 + b"\n") if request.get("model") == "deep-json" else (json.dumps(chunk) + "\n").encode()
                self.wfile.write(raw); self.wfile.flush()
                if request.get("model") == "slow" and index == 0:
                    time.sleep(0.12)
                if request.get("model") == "stall" and index == 0:
                    time.sleep(0.2)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *_args):
        pass


class RedirectHandler(BaseHTTPRequestHandler):
    target = None
    def do_GET(self):
        self.send_response(307); self.send_header("Location", self.target); self.end_headers()
    def do_POST(self):
        self.send_response(307); self.send_header("Location", self.target); self.end_headers()
    def log_message(self, *_args):
        pass


class TargetHandler(BaseHTTPRequestHandler):
    hits = 0
    def do_GET(self):
        type(self).hits += 1
        self.send_response(200); self.end_headers()
    def do_POST(self):
        type(self).hits += 1
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        self.send_response(200); self.end_headers()
    def log_message(self, *_args):
        pass


class OllamaHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.endpoint = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=2)

    def test_request_deadline_is_distinct_from_provider_disconnect(self):
        from tusker_ai.types import RuntimeError as TuskerRuntimeError, RuntimeErrorCode
        provider = OllamaProvider(self.endpoint, read_timeout=1)
        req = InferenceRequest("slow-request", "slow", [{"role": "user", "content": "hello"}], timeout_seconds=0.03)
        with self.assertRaises(TuskerRuntimeError) as ctx:
            list(provider.infer(req, CancellationToken()))
        self.assertEqual(ctx.exception.code, RuntimeErrorCode.DEADLINE_EXCEEDED)

    def test_frame_arriving_after_deadline_is_rejected(self):
        from tusker_ai.types import RuntimeError as TuskerRuntimeError, RuntimeErrorCode
        provider = OllamaProvider(self.endpoint, read_timeout=1)
        req = InferenceRequest("late-frame", "late-frame", [{"role": "user", "content": "hello"}], timeout_seconds=0.03)
        with self.assertRaises(TuskerRuntimeError) as ctx:
            list(provider.infer(req, CancellationToken()))
        self.assertEqual(ctx.exception.code, RuntimeErrorCode.DEADLINE_EXCEEDED)

    def test_oversized_and_malformed_frames_are_typed_provider_errors(self):
        from tusker_ai.types import RuntimeError as TuskerRuntimeError, RuntimeErrorCode
        provider = OllamaProvider(self.endpoint, read_timeout=2)
        for model in ("oversized", "deep-json", "bad-shape", "bad-message", "falsey-message", "bad-content", "bad-done", "bad-reason", "bad-usage"):
            request = InferenceRequest(model, model, [{"role": "user", "content": "hello"}])
            with self.subTest(model=model):
                with self.assertRaises(TuskerRuntimeError) as ctx:
                    list(provider.infer(request, CancellationToken()))
                self.assertEqual(ctx.exception.code, RuntimeErrorCode.PROVIDER_DISCONNECTED)

    def test_aggregate_stream_response_size_is_bounded(self):
        from tusker_ai.types import RuntimeError as TuskerRuntimeError, RuntimeErrorCode
        provider = OllamaProvider(self.endpoint, read_timeout=2)
        request = InferenceRequest(
            "aggregate-oversized",
            "aggregate-oversized",
            [{"role": "user", "content": "hello"}],
        )
        with self.assertRaises(TuskerRuntimeError) as caught:
            list(provider.infer(request, CancellationToken()))
        self.assertEqual(caught.exception.code, RuntimeErrorCode.PROVIDER_DISCONNECTED)

    def test_version_health_rejects_non_object_and_oversized_responses(self):
        provider = OllamaProvider(self.endpoint, read_timeout=2)
        original = getattr(Handler, "version_body", None)
        try:
            for body in (b"[]", b'"version-string"', b'{"version": 7}', b"{" + b" " * 65536):
                with self.subTest(body_prefix=body[:16], body_length=len(body)):
                    Handler.version_body = body
                    self.assertIsNone(provider.version())
                    self.assertFalse(provider.health())
        finally:
            Handler.version_body = original

    def test_read_timeout_must_be_finite_and_positive(self):
        for timeout in (0, -1, float("nan"), float("inf"), float("-inf"), True):
            with self.subTest(timeout=timeout):
                with self.assertRaises(ValueError):
                    OllamaProvider(self.endpoint, read_timeout=timeout)

    def test_endpoint_rejects_paths_and_invalid_ports(self):
        for endpoint in (
            "http://127.0.0.1:bad",
            "http://127.0.0.1:0",
            "http://127.0.0.1:65536",
            "http://127.0.0.1:11434/api",
        ):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(ValueError):
                    OllamaProvider(endpoint)

    def test_unserializable_request_is_a_typed_invalid_request(self):
        from tusker_ai.types import RuntimeError as TuskerRuntimeError, RuntimeErrorCode
        cyclic = {}
        cyclic["self"] = cyclic
        request = InferenceRequest(
            "bad-json",
            "fixture",
            [{"role": "user", "content": "hello", "extra": cyclic}],
        )
        with self.assertRaises(TuskerRuntimeError) as ctx:
            list(OllamaProvider(self.endpoint).infer(request, CancellationToken()))
        self.assertEqual(ctx.exception.code, RuntimeErrorCode.INVALID_REQUEST)

    def test_non_finite_nested_values_are_rejected_before_dispatch(self):
        from tusker_ai.types import RuntimeError as TuskerRuntimeError, RuntimeErrorCode
        for value in (float("nan"), float("inf"), float("-inf")):
            request = InferenceRequest(
                "non-finite-json",
                "fixture",
                [{"role": "user", "content": "hello", "metadata": {"score": value}}],
            )
            with self.subTest(value=value):
                with self.assertRaises(TuskerRuntimeError) as ctx:
                    list(OllamaProvider("http://127.0.0.1:1").infer(request, CancellationToken()))
                self.assertEqual(ctx.exception.code, RuntimeErrorCode.INVALID_REQUEST)

    def test_version_health_stream_and_usage(self):
        provider = OllamaProvider(self.endpoint, read_timeout=2)
        self.assertTrue(provider.health())
        self.assertEqual(provider.version(), "test-live-http")
        req = InferenceRequest("r1", "fixture", [{"role": "user", "content": "hello"}])
        events = list(provider.infer(req, CancellationToken()))
        self.assertEqual([e.event_type for e in events], ["started", "text_delta", "text_delta", "usage", "completed"])
        self.assertEqual(events[1].payload["delta"] + events[2].payload["delta"], "Tusker runtime")
        self.assertEqual(events[3].payload["output_tokens"], 2)

    def test_cancellation_while_waiting_for_frame_discards_that_frame(self):
        provider = OllamaProvider(self.endpoint, read_timeout=0.5)
        cancellation = CancellationToken()
        timer = threading.Timer(0.03, cancellation.cancel)
        req = InferenceRequest("cancel-frame", "cancel-frame", [{"role": "user", "content": "hello"}], timeout_seconds=1)
        timer.start()
        try:
            events = list(provider.infer(req, cancellation))
        finally:
            timer.cancel()
        self.assertEqual([event.event_type for event in events], ["started", "cancelled"])
        self.assertEqual(events[-1].payload["reason"], "caller_cancelled")

    def test_cancellation_during_stream_is_request_scoped(self):
        provider = OllamaProvider(self.endpoint, read_timeout=0.05)
        cancellation = CancellationToken()
        timer = threading.Timer(0.03, cancellation.cancel)
        req = InferenceRequest("cancel-one", "stall", [{"role": "user", "content": "hello"}], timeout_seconds=1)
        timer.start()
        try:
            events = list(provider.infer(req, cancellation))
        finally:
            timer.cancel()
        self.assertIn("started", [event.event_type for event in events])
        self.assertIn("cancelled", [event.event_type for event in events])
        self.assertNotIn("completed", [event.event_type for event in events])

        # The cancelled request must not stop the shared daemon or poison a
        # subsequent independent request.
        next_req = InferenceRequest("after-cancel", "fixture", [{"role": "user", "content": "still available"}])
        next_events = list(provider.infer(next_req, CancellationToken()))
        self.assertEqual(next_events[-1].event_type, "completed")

    def test_oversized_serialized_request_is_rejected_before_dispatch(self):
        from tusker_ai.types import RuntimeError as TuskerRuntimeError, RuntimeErrorCode
        provider = OllamaProvider("http://127.0.0.1:1", read_timeout=0.1)
        request = InferenceRequest(
            "oversized-request",
            "fixture",
            [{"role": "user", "content": "small", "metadata": "x" * (4 * 1024 * 1024)}],
        )
        with self.assertRaises(TuskerRuntimeError) as caught:
            list(provider.infer(request, CancellationToken()))
        self.assertEqual(caught.exception.code, RuntimeErrorCode.INVALID_REQUEST)

    def test_local_requests_ignore_ambient_proxy_environment(self):
        proxy_env = {
            "HTTP_PROXY": "http://127.0.0.1:1", "http_proxy": "http://127.0.0.1:1",
            "HTTPS_PROXY": "http://127.0.0.1:1", "https_proxy": "http://127.0.0.1:1",
            "ALL_PROXY": "http://127.0.0.1:1", "all_proxy": "http://127.0.0.1:1",
            "NO_PROXY": "", "no_proxy": "",
        }
        with patch.dict(os.environ, proxy_env, clear=False):
            provider = OllamaProvider(self.endpoint, read_timeout=1)
            self.assertTrue(provider.health())
            req = InferenceRequest("proxy-isolation", "fixture", [{"role": "user", "content": "private"}])
            events = list(provider.infer(req, CancellationToken()))
        self.assertEqual(events[-1].event_type, "completed")

    def test_local_provider_does_not_follow_redirects(self):
        from tusker_ai.types import RuntimeError as TuskerRuntimeError
        target = ThreadingHTTPServer(("127.0.0.1", 0), TargetHandler)
        target_thread = threading.Thread(target=target.serve_forever, daemon=True)
        target_thread.start()
        redirect = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
        RedirectHandler.target = f"http://127.0.0.1:{target.server_port}/capture"
        redirect_thread = threading.Thread(target=redirect.serve_forever, daemon=True)
        redirect_thread.start()
        TargetHandler.hits = 0
        try:
            provider = OllamaProvider(f"http://127.0.0.1:{redirect.server_port}", read_timeout=1)
            self.assertFalse(provider.health())
            req = InferenceRequest("redirect-block", "fixture", [{"role": "user", "content": "must-not-leak"}])
            with self.assertRaises(TuskerRuntimeError):
                list(provider.infer(req, CancellationToken()))
            self.assertEqual(TargetHandler.hits, 0)
        finally:
            redirect.shutdown(); redirect.server_close(); redirect_thread.join(timeout=2)
            target.shutdown(); target.server_close(); target_thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()

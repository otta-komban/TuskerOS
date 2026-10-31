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
        body = json.dumps({"version": "test-live-http"}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
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
                self.wfile.write((json.dumps(chunk) + "\n").encode()); self.wfile.flush()
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

import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from tusker_ai.providers.ollama import OllamaProvider
from tusker_ai.types import InferenceRequest, CancellationToken


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"version": "test-live-http"}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        if request.get("model") == "slow":
            time.sleep(0.12)
        chunks = [
            {"message": {"content": "Tusker "}, "done": False},
            {"message": {"content": "runtime"}, "done": False},
            {"done": True, "done_reason": "stop", "prompt_eval_count": 8, "eval_count": 2},
        ]
        self.send_response(200); self.send_header("Content-Type", "application/x-ndjson"); self.end_headers()
        try:
            for chunk in chunks:
                self.wfile.write((json.dumps(chunk) + "\n").encode()); self.wfile.flush()
        except BrokenPipeError:
            pass

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

    def test_version_health_stream_and_usage(self):
        provider = OllamaProvider(self.endpoint, read_timeout=2)
        self.assertTrue(provider.health())
        self.assertEqual(provider.version(), "test-live-http")
        req = InferenceRequest("r1", "fixture", [{"role": "user", "content": "hello"}])
        events = list(provider.infer(req, CancellationToken()))
        self.assertEqual([e.event_type for e in events], ["started", "text_delta", "text_delta", "usage", "completed"])
        self.assertEqual(events[1].payload["delta"] + events[2].payload["delta"], "Tusker runtime")
        self.assertEqual(events[3].payload["output_tokens"], 2)


if __name__ == "__main__":
    unittest.main()

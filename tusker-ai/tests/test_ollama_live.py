"""Optional real-provider tests. Set TUSKER_OLLAMA_MODEL to run against a live local Ollama."""
from __future__ import annotations

import os
import threading
import unittest

from tusker_ai.providers.ollama import OllamaProvider
from tusker_ai.runtime import InferenceRuntime
from tusker_ai.types import CancellationToken, InferenceRequest, RuntimeLimits

MODEL = os.environ.get("TUSKER_OLLAMA_MODEL")
ENDPOINT = os.environ.get("TUSKER_OLLAMA_ENDPOINT", "http://127.0.0.1:11434")


@unittest.skipUnless(MODEL, "set TUSKER_OLLAMA_MODEL to run live Ollama conformance tests")
class LiveOllamaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provider = OllamaProvider(ENDPOINT, read_timeout=1.0)
        if not cls.provider.health():
            raise RuntimeError("configured local Ollama endpoint is not healthy")
        cls.version = cls.provider.version()
        if not cls.version:
            raise RuntimeError("Ollama version could not be identified")
        cls.runtime = InferenceRuntime(cls.provider, RuntimeLimits(max_concurrent_requests=2))

    def test_live_chat_stream_and_terminal_event(self):
        request = InferenceRequest(
            "live-smoke-1", MODEL,
            [{"role": "user", "content": "Reply with exactly: TUSKER-LIVE-OK"}],
            max_output_tokens=32, context_limit=2048, timeout_seconds=90,
        )
        events = list(self.runtime.infer(request))
        text = "".join(str(event.payload.get("delta", "")) for event in events if event.event_type == "text_delta")
        terminals = [event for event in events if event.event_type in {"completed", "cancelled", "failed"}]
        self.assertIn("TUSKER-LIVE-OK", text)
        self.assertEqual(len(terminals), 1)
        self.assertEqual(terminals[0].event_type, "completed")
        self.assertEqual([event.sequence for event in events], sorted(event.sequence for event in events))

    def test_cancelling_one_live_request_does_not_break_another(self):
        token = CancellationToken()
        first_delta = threading.Event()
        a_events = []
        b_events = []
        errors = []

        def run_a():
            try:
                request = InferenceRequest(
                    "live-cancel-a", MODEL,
                    [{"role": "user", "content": "Write a long numbered list from 1 to 1000."}],
                    max_output_tokens=512, context_limit=4096, timeout_seconds=90,
                )
                for event in self.runtime.infer(request, token):
                    a_events.append(event)
                    if event.event_type == "text_delta":
                        first_delta.set()
            except Exception as exc:
                errors.append(exc)

        def run_b():
            try:
                request = InferenceRequest(
                    "live-cancel-b", MODEL,
                    [{"role": "user", "content": "Reply with exactly: TUSKER-SECOND-OK"}],
                    max_output_tokens=32, context_limit=2048, timeout_seconds=90,
                )
                b_events.extend(self.runtime.infer(request))
            except Exception as exc:
                errors.append(exc)

        thread_a = threading.Thread(target=run_a, daemon=True)
        thread_b = threading.Thread(target=run_b, daemon=True)
        thread_a.start()
        thread_b.start()
        self.assertTrue(first_delta.wait(45), "first request produced no stream delta")
        token.cancel()
        thread_a.join(15)
        thread_b.join(90)
        self.assertFalse(thread_a.is_alive(), "cancelled request did not stop within the adapter bound")
        self.assertFalse(thread_b.is_alive(), "unrelated request did not complete")
        self.assertFalse(errors, "live request raised an unexpected error")
        a_terminal = [event.event_type for event in a_events if event.event_type in {"completed", "cancelled", "failed"}]
        b_terminal = [event.event_type for event in b_events if event.event_type in {"completed", "cancelled", "failed"}]
        self.assertEqual(a_terminal, ["cancelled"])
        self.assertEqual(b_terminal, ["completed"])


if __name__ == "__main__":
    unittest.main()

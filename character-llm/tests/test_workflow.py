import io
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from character_chat import OllamaBackend, bounded_messages, conservative_tokens, load_config, Conversation, ROOT


class FakeBackend(OllamaBackend):
    def __init__(self, events):
        super().__init__({"model": "test", "options": {}, "keep_alive": "5m"})
        self.events = events
        self.payload = None

    def request(self, route, body=None):
        self.payload = body
        return io.BytesIO(b"\n".join(json.dumps(event).encode() for event in self.events))


class WorkflowTests(unittest.TestCase):
    def test_stream_keeps_spoken_text_separate_and_requests_no_thinking(self):
        backend = FakeBackend([{"message": {"thinking": "unexpected"}},
                               {"message": {"content": "Hello "}},
                               {"message": {"content": "there"}},
                               {"done": True, "done_reason": "stop", "eval_count": 2, "eval_duration": 100000000}])
        chunks = []
        text, metrics = backend.chat([], chunks.append)
        self.assertEqual(text, "Hello there")
        self.assertEqual(chunks, ["Hello ", "there"])
        self.assertFalse(backend.payload["think"])
        self.assertEqual(metrics["thinking_characters"], 10)
        self.assertIsNotNone(metrics["ttft_seconds"])

    def test_incomplete_stream_does_not_commit_history(self):
        backend = FakeBackend([{"message": {"content": "partial"}}])
        conversation = Conversation(load_config(ROOT / "character/config.json"), backend)
        with self.assertRaisesRegex(RuntimeError, "completion event"):
            conversation.turn("Hello")
        self.assertEqual(conversation.history, [])

    def test_stream_errors_are_not_spoken_replies(self):
        with self.assertRaisesRegex(RuntimeError, "out of memory"):
            FakeBackend([{"error": "out of memory"}]).chat([])

    def test_context_eviction_preserves_identity_and_whole_exchanges(self):
        prefix = [{"role": "system", "content": "Stable identity"}]
        history = [{"role": "user", "content": "a" * 500}, {"role": "assistant", "content": "b" * 500},
                   {"role": "user", "content": "recent"}, {"role": "assistant", "content": "reply"}]
        options = {"num_ctx": 1000, "num_predict": 100}
        messages, dropped = bounded_messages(prefix, history, "now", options)
        self.assertEqual(dropped, 2)
        self.assertEqual(messages[0], prefix[0])
        self.assertEqual(messages[1]["content"], "recent")
        self.assertLessEqual(conservative_tokens(messages), 644)

    def test_oversized_input_rejected_instead_of_silent_truncation(self):
        with self.assertRaisesRegex(ValueError, "too large"):
            bounded_messages([], [], "x" * 1000, {"num_ctx": 1000, "num_predict": 100})


if __name__ == "__main__":
    unittest.main()

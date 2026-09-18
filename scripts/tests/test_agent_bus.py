import json
import tempfile
import unittest
from pathlib import Path

from scripts.agent_bus import EventBus


class EventBusTest(unittest.TestCase):
    def test_poll_returns_only_new_events_from_other_agents(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bus = EventBus(Path(directory))

            bus.publish("codex", "progress", "Codex update")
            bus.publish("claude", "decision", "Claude decision")

            first_poll = bus.poll("codex")
            second_poll = bus.poll("codex")

            self.assertEqual(
                [(event["agent"], event["kind"], event["message"]) for event in first_poll],
                [("claude", "decision", "Claude decision")],
            )
            self.assertEqual(second_poll, [])

            stored = [
                json.loads(line)
                for line in (Path(directory) / "events.jsonl").read_text().splitlines()
            ]
            self.assertEqual(len(stored), 2)

    def test_publish_rejects_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bus = EventBus(Path(directory))

            with self.assertRaisesRegex(ValueError, "secret"):
                bus.publish("codex", "progress", "ANTHROPIC_API_KEY=sk-ant-secret")


if __name__ == "__main__":
    unittest.main()

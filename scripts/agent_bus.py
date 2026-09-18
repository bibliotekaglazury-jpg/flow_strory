#!/usr/bin/env python3
"""Small local JSONL bus for handoffs between coding agents."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_BUS_DIR = Path(__file__).resolve().parents[1] / ".local" / "agent-bus"
AGENT_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
SECRET_PATTERN = re.compile(
    r"(?i)(?:api[_-]?key|access[_-]?token|secret|password)\s*[:=]\s*\S+"
    r"|\bsk-(?:ant-)?[A-Za-z0-9_-]{8,}"
)


class EventBus:
    def __init__(self, directory: Path = DEFAULT_BUS_DIR) -> None:
        self.directory = directory
        self.events_path = directory / "events.jsonl"
        self.lock_path = directory / "events.lock"
        self.cursors_dir = directory / "cursors"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.cursors_dir.mkdir(parents=True, exist_ok=True)

    def publish(
        self,
        agent: str,
        kind: str,
        message: str,
        files: Iterable[str] = (),
    ) -> dict[str, Any]:
        self._validate_agent(agent)
        if not kind.strip() or not message.strip():
            raise ValueError("kind and message must not be empty")
        if SECRET_PATTERN.search(message):
            raise ValueError("message appears to contain a secret")

        event = {
            "version": 1,
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent,
            "kind": kind.strip(),
            "message": message.strip(),
            "files": list(files),
        }
        payload = (json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8")

        with self._locked():
            descriptor = os.open(
                self.events_path,
                os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                0o600,
            )
            try:
                os.write(descriptor, payload)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        return event

    def poll(self, agent: str) -> list[dict[str, Any]]:
        self._validate_agent(agent)
        cursor_path = self.cursors_dir / f"{agent}.cursor"

        with self._locked():
            position = self._read_cursor(cursor_path)
            if not self.events_path.exists():
                return []
            with self.events_path.open("rb") as stream:
                stream.seek(position)
                lines = stream.readlines()
                next_position = stream.tell()
            self._write_cursor(cursor_path, next_position)

        events = [json.loads(line) for line in lines if line.strip()]
        return [event for event in events if event.get("agent") != agent]

    def _locked(self):
        self.lock_path.touch(mode=0o600, exist_ok=True)
        lock = self.lock_path.open("r+")

        class LockContext:
            def __enter__(self_nonlocal):
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                return lock

            def __exit__(self_nonlocal, exc_type, exc, traceback):
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                lock.close()

        return LockContext()

    @staticmethod
    def _validate_agent(agent: str) -> None:
        if not AGENT_PATTERN.fullmatch(agent):
            raise ValueError("agent must contain only letters, numbers, dot, dash, or underscore")

    @staticmethod
    def _read_cursor(path: Path) -> int:
        try:
            return max(0, int(path.read_text(encoding="utf-8").strip()))
        except (FileNotFoundError, ValueError):
            return 0

    @staticmethod
    def _write_cursor(path: Path, position: int) -> None:
        temporary = path.with_suffix(".tmp")
        temporary.write_text(str(position), encoding="utf-8")
        os.replace(temporary, path)


def _print_events(events: Iterable[dict[str, Any]]) -> None:
    for event in events:
        print(json.dumps(event, ensure_ascii=False), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bus-dir", type=Path, default=DEFAULT_BUS_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)

    publish = subparsers.add_parser("publish", help="Append an event")
    publish.add_argument("--agent", required=True)
    publish.add_argument("--kind", required=True)
    publish.add_argument("--message", required=True)
    publish.add_argument("--file", action="append", default=[])

    poll = subparsers.add_parser("poll", help="Read unread events from other agents")
    poll.add_argument("--agent", required=True)

    watch = subparsers.add_parser("watch", help="Continuously print new events")
    watch.add_argument("--agent", required=True)
    watch.add_argument("--interval", type=float, default=1.0)

    arguments = parser.parse_args()
    bus = EventBus(arguments.bus_dir)

    if arguments.command == "publish":
        _print_events(
            [bus.publish(arguments.agent, arguments.kind, arguments.message, arguments.file)]
        )
        return 0
    if arguments.command == "poll":
        _print_events(bus.poll(arguments.agent))
        return 0

    try:
        while True:
            _print_events(bus.poll(arguments.agent))
            time.sleep(max(0.1, arguments.interval))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

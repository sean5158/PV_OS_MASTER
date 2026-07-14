"""Minimal in-process event bus for PV_OS automation engine.

Allows triggers to emit events and orchestrator steps to subscribe.
No external dependencies beyond the Python standard library.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

Handler = Callable[["Event"], Any]


class Event:
    """A single event emitted on the bus."""

    def __init__(self, name: str, payload: dict[str, Any] | None = None) -> None:
        self.name = name
        self.payload = payload or {}
        # For convenience, support dict-like access
        for key, value in self.payload.items():
            setattr(self, key, value)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "payload": self.payload}


class EventBus:
    """Single-process pub/sub event bus.

    Usage::

        bus = EventBus()
        bus.subscribe("new_comment_received", my_handler)
        bus.emit("new_comment_received", {"comment": {...}})
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self._events_log: list[Event] = []

    def subscribe(self, event_name: str, handler: Handler) -> None:
        self._handlers[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: Handler) -> None:
        if handler in self._handlers[event_name]:
            self._handlers[event_name].remove(handler)

    def emit(self, event_name: str, payload: dict[str, Any] | None = None) -> list[Any]:
        event = Event(event_name, payload)
        self._events_log.append(event)
        results: list[Any] = []
        for handler in self._handlers.get(event_name, []):
            try:
                result = handler(event)
                results.append(result)
            except Exception:
                logger.exception("Handler for %r failed", event_name)
        return results

    def replay(self) -> list[Event]:
        return list(self._events_log)

    def clear_log(self) -> None:
        self._events_log.clear()


# ---------------------------------------------------------------------------
# convenience: file-system watcher trigger
# ---------------------------------------------------------------------------

def watch_raw_comments(comments_dir: str, event_bus: EventBus) -> int:
    """Scan the raw-comments directory and emit one event per comment file.

    Returns the number of events emitted.
    """
    raw_path = Path(comments_dir)
    if not raw_path.exists():
        logger.warning("Raw comments directory %s does not exist", raw_path)
        return 0

    count = 0
    for comment_file in sorted(raw_path.glob("*.json")):
        try:
            data = json.loads(comment_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Skipping %s: %s", comment_file, exc)
            continue
        event_bus.emit("new_comment_received", dict(data))
        logger.info("Emitted new_comment_received for %s", comment_file.name)
        count += 1
    return count

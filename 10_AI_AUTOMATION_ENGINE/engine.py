"""PV_OS Automation Engine — minimal YAML-driven workflow runner.

Reads a workflow definition (e.g. comment_to_lead_pipeline.yml),
executes each step via the step_registry, and reports results.

Usage::

    from engine import Engine
    from triggers.event_bus import EventBus

    bus = EventBus()
    engine = Engine(workflow_path="workflows/comment_to_lead_pipeline.yml")
    engine.run_from_event(bus)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import yaml

from triggers.event_bus import EventBus, watch_raw_comments

from orchestrator.step_executor import STEP_REGISTRY

logger = logging.getLogger(__name__)


class Engine:
    """Loads a workflow YAML and executes steps in sequence."""

    def __init__(self, workflow_path: str | Path) -> None:
        self.workflow_path = Path(workflow_path)
        self.workflow: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        raw = self.workflow_path.read_text(encoding="utf-8")
        self.workflow = yaml.safe_load(raw)
        if not self.workflow or "steps" not in self.workflow:
            raise ValueError(f"Invalid workflow: {self.workflow_path}")
        logger.info("Loaded workflow: %s v%s",
                     self.workflow.get("name"), self.workflow.get("version"))

    @property
    def name(self) -> str:
        return self.workflow.get("name", "unknown")

    @property
    def steps(self) -> list[dict[str, Any]]:
        return self.workflow.get("steps", [])

    def run_from_event(self, bus: EventBus) -> list[dict[str, Any]]:
        """Subscribe to events, run the pipeline for each event, return results."""
        results: list[dict[str, Any]] = []

        trigger_events = self.workflow.get("trigger", {}).get("event", [])
        for event_name in trigger_events:
            bus.subscribe(event_name, lambda ev: results.append(self._execute(ev)))

        # Emit events from file-system watcher
        raw_dir = Path("02_DATA/raw")
        count = watch_raw_comments(str(raw_dir), bus)
        logger.info("Triggered %d events from %s", count, raw_dir)

        return results

    def run_single(self, comment_data: dict[str, Any]) -> dict[str, Any]:
        """Run the pipeline for a single comment dict (test helper)."""
        bus = EventBus()

        # Create a one-shot event
        from triggers.event_bus import Event
        event = Event("new_comment_received", comment_data)

        return self._execute(event)

    def _execute(self, event: Any) -> dict[str, Any]:
        """Execute all workflow steps sequentially."""
        ctx: dict[str, Any] = {}
        logger.info("── Pipeline start: %s ──", self.name)

        for i, step_def in enumerate(self.steps, 1):
            step_name = step_def.get("name", f"step_{i}")
            handler = STEP_REGISTRY.get(step_name)

            if handler is None:
                logger.warning("  [%d/%d] %s — no handler registered, skipping",
                               i, len(self.steps), step_name)
                continue

            logger.info("  [%d/%d] %s", i, len(self.steps), step_name)
            try:
                # Steps may accept (ctx, event) or (ctx) only
                import inspect
                sig = inspect.signature(handler)
                if len(sig.parameters) >= 2:
                    ctx = handler(ctx, event)
                else:
                    ctx = handler(ctx)
            except Exception:
                logger.exception("  ✗ %s FAILED", step_name)
                ctx["_pipeline_error"] = step_name
                break
            else:
                logger.info("  ✓ %s", step_name)

        logger.info("── Pipeline end: %s ──", self.name)
        return ctx

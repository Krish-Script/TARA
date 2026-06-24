"""
Central dispatcher for all agentic tools.

ToolResult is the standard return type for every tool.
The registry maps Intent → handler and dispatches with
error isolation — a tool failure never crashes the pipeline.

Adding a new tool:
  1. Create components/tools/your_tool.py
  2. Import and register in _build_registry()
  3. Nothing else changes

Pipeline position: Stage 3 (Tool Execution) in orchestrator.py
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from components.intent import Intent


@dataclass
class ToolResult:
    """
    Standard return type for every tool call.

    raw_output        — structured data dict from the tool
    formatted_output  — TTS-ready natural language string
    tool_name         — which tool produced this result
    latency           — seconds from dispatch to return
    success           — False means formatter should use error fallback
    error             — exception message if success=False
    source            — tag for memory filtering (always 'tool')
    """
    tool_name:        str
    raw_output:       dict
    formatted_output: str
    latency:          float
    success:          bool
    error:            str | None = None
    source:           str        = "tool"


class ToolRegistry:

    def __init__(self):
        self._registry: dict[Intent, Callable] = {}
        self._build_registry()

    def _build_registry(self):
        """
        Register all tools here.
        Key   = Intent enum value
        Value = callable that accepts (query: str) → dict
        """
        from components.tools.time_tool import TimeTool
        time_tool = TimeTool()
        self._registry[Intent.TIME_QUERY] = time_tool.run

        from components.tools.system_monitor import SystemMonitor
        system_monitor = SystemMonitor()
        self._registry[Intent.SYSTEM_QUERY] = system_monitor.run

    def dispatch(self, intent: Intent, query: str) -> ToolResult | None:
        """
        Dispatch to the registered tool for this intent.

        Returns ToolResult on success or graceful failure.
        Returns None if no tool is registered for this intent
        (caller should fall through to LLM).
        """
        handler = self._registry.get(intent)

        if handler is None:
            return None

        start = time.time()
        try:
            raw_output = handler(query)
            latency    = time.time() - start

            from components.tools.formatter import ToolFormatter
            formatted = ToolFormatter.format(intent, raw_output)

            return ToolResult(
                tool_name        = intent.name.lower(),
                raw_output       = raw_output,
                formatted_output = formatted,
                latency          = latency,
                success          = True,
            )

        except Exception as e:
            latency = time.time() - start
            return ToolResult(
                tool_name        = intent.name.lower(),
                raw_output       = {},
                formatted_output = "Sorry, I couldn't retrieve that information right now.",
                latency          = latency,
                success          = False,
                error            = str(e),
            )
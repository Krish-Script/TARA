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
import traceback
from dataclasses import dataclass, field
from typing import Callable

from components.intent import Intent
from components.error_manager import ToolExpectedError, error_logger


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

    def __init__(self, llm=None):
        self.llm = llm
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

        from components.tools.notes_tool import NotesTool
        notes_tool = NotesTool(self.llm)
        
        self._registry[Intent.NOTES_CREATE] = notes_tool.create_note
        self._registry[Intent.NOTES_READ]   = notes_tool.read_last_note
        self._registry[Intent.NOTES_LIST]   = notes_tool.list_notes
        self._registry[Intent.NOTES_SEARCH] = notes_tool.search_notes

        from components.tools.file_reader import FileReaderTool
        file_reader = FileReaderTool(self.llm)
        self._registry[Intent.FILE_READ] = file_reader.read_file

        from components.tools.calculator_tool import CalculatorTool
        calculator = CalculatorTool(llm=self.llm)  # pass llm same as notes/file reader
        self._registry[Intent.CALCULATION] = calculator.run

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

        except ToolExpectedError as e:
            # TIER 1: Expected Tool Error
            # The tool caught a known edge case. We speak the error message naturally.
            latency = time.time() - start
            return ToolResult(
                tool_name        = intent.name.lower(),
                raw_output       = {},
                formatted_output = str(e),
                latency          = latency,
                success          = False,
                error            = str(e)
            )

        except Exception as e:
            # TIER 2: Unexpected Tool Error
            # Total crash. Log it silently and speak the graceful degradation phrase.
            latency = time.time() - start
            error_logger.error(
                f"Unexpected failure in tool '{intent.name.lower()}': {str(e)}", 
                exc_info=True
            )
            return ToolResult(
                tool_name        = intent.name.lower(),
                raw_output       = {},
                formatted_output = "Something went wrong with that, but I'm still here.",
                latency          = latency,
                success          = False,
                error            = str(e)
            )
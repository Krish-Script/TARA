"""
Converts raw tool output dicts into TTS-ready natural language.

Two layers:
  1. Template formatting — fast, deterministic, used for all known tools
  2. LLM formatting     — flexible fallback for unknown/compound output
                          (stub for now, wired in Week 5)

Why this layer exists:
  Raw psutil output like {"cpu_percent": 67.2} spoken directly is
  unlistenable. This layer owns the translation from structured data
  to spoken language — no other component does this.

Rules for all templates:
  - No markdown, no units like "GB" or "%" — say "gigabytes", "percent"
  - One or two sentences maximum
  - Numbers rounded to 0-1 decimal places
  - Spell out "CPU", "RAM", "VRAM" (they are spoken as letters, not words)

Adding a new tool formatter:
  1. Add a _format_yourkey() static method
  2. Add Intent.YOUR_INTENT → _format_yourkey mapping in format()
"""

from __future__ import annotations

from components.intent import Intent


class ToolFormatter:

    @staticmethod
    def format(intent: Intent, raw_output: dict) -> str:
        """
        Dispatch to the correct formatter for this intent.
        Falls back to a generic formatter if no match.
        """
        formatters = {
            Intent.TIME_QUERY:   ToolFormatter._format_time,
            Intent.SYSTEM_QUERY: ToolFormatter._format_system,
        }

        formatter = formatters.get(intent, ToolFormatter._format_generic)
        return formatter(raw_output)

    # ── Time formatter ───────────────────────────────────────

    @staticmethod
    def _format_time(data: dict) -> str:
        """
        Produces natural responses based on what was asked.
        Currently returns both time and date — refine per query in Week 5.
        """
        time_str = data.get("time_12h",   "unknown time")
        date_str = data.get("date_full",  "unknown date")
        return f"It's {time_str} on {date_str}."

    # ── System formatter ─────────────────────────────────────

    @staticmethod
    def _format_system(data: dict) -> str:
        """
        Formats system monitor output.
        Only speaks fields that are present in the dict —
        allows partial queries (CPU-only, RAM-only, etc.)
        """
        parts = []

        if "cpu_percent" in data:
            parts.append(f"CPU is at {data['cpu_percent']:.0f} percent")

        if "ram_used_gb" in data and "ram_total_gb" in data:
            parts.append(
                f"RAM is {data['ram_used_gb']:.1f} of "
                f"{data['ram_total_gb']:.0f} gigabytes used"
            )

        if "disk_free_gb" in data:
            parts.append(f"disk has {data['disk_free_gb']:.0f} gigabytes free")

        if "battery_percent" in data:
            charging = data.get("charging", False)
            status   = "charging" if charging else "not charging"
            parts.append(
                f"battery is at {data['battery_percent']:.0f} percent and {status}"
            )

        if "vram_used_gb" in data and "vram_total_gb" in data:
            parts.append(
                f"VRAM is {data['vram_used_gb']:.1f} of "
                f"{data['vram_total_gb']:.1f} gigabytes used"
            )

        if not parts:
            return "I couldn't retrieve system information."

        if len(parts) == 1:
            return f"{parts[0].capitalize()}."

        return f"{', '.join(parts[:-1])}, and {parts[-1]}."

    # ── Generic fallback ─────────────────────────────────────

    @staticmethod
    def _format_generic(data: dict) -> str:
        """Last-resort fallback — should rarely be reached."""
        if not data:
            return "I completed the action but have no result to report."
        return "I retrieved the information, but I'm not sure how to summarise it."
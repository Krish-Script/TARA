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
        Formats system monitor output into spoken sentences.
        Only speaks fields present in the dict — allows partial
        queries (CPU-only, RAM-only, temperature-only, etc.)
        """
        parts = []

        # CPU
        if "cpu_percent" in data:
            parts.append(f"Your CPU is at {data['cpu_percent']:.0f} percent")

        # RAM
        if "ram_used_gb" in data and "ram_total_gb" in data:
            parts.append(
                f"Your RAM is {data['ram_used_gb']:.1f} of "
                f"{data['ram_total_gb']:.0f} gigabytes used"
            )

        # Disk
        if "disk_free_gb" in data:
            parts.append(
                f"Your disk has {data['disk_free_gb']:.0f} gigabytes free"
            )

        # Battery
        if data.get("battery_available") is False:
            parts.append("battery sensor is not available on this device")
        elif "battery_percent" in data:
            status = "charging" if data.get("charging") else "not charging"
            parts.append(
                f"Your battery is at {data['battery_percent']:.0f} percent "
                f"and {status}"
            )

        # VRAM
        if data.get("vram_available") is False:
            parts.append("GPU metrics are unavailable")
        elif "vram_used_gb" in data and "vram_total_gb" in data:
            parts.append(
                f"Your VRAM is {data['vram_used_gb']:.2f} of "
                f"{data['vram_total_gb']:.1f} gigabytes used"
            )

        # Temperature
        if data.get("gpu_temp_available"):
            parts.append(
                f"Your GPU temperature is {data['gpu_temp_c']} degrees Celsius"
            )
        if data.get("cpu_temp_available"):
            parts.append(
                f"Your CPU temperature is {data['cpu_temp_c']} degrees Celsius"
            )

        # Uptime
        if "uptime_hours" in data:
            h = data["uptime_hours"]
            m = data["uptime_minutes"]
            if h > 0:
                parts.append(f"Your system has been running for {h} hours and {m} minutes")
            else:
                parts.append(f"Your system has been running for {m} minutes")

        if not parts:
            return "I couldn't retrieve system information."

        if len(parts) == 1:
            return f"{ToolFormatter._cap_first(parts[0])}."

        # Two parts: "X and Y."
        if len(parts) == 2:
            return f"{ToolFormatter._cap_first(parts[0])} and {parts[1]}."

        # Three or more: "X, Y, and Z."
        return f"{', '.join(ToolFormatter._cap_first(p) if i == 0 else p for i, p in enumerate(parts[:-1]))}, and {parts[-1]}."

    # ── Generic fallback ─────────────────────────────────────

    @staticmethod
    def _format_generic(data: dict) -> str:
        """Last-resort fallback — should rarely be reached."""
        if not data:
            return "I completed the action but have no result to report."
        return "I retrieved the information, but I'm not sure how to summarise it."
    
    @staticmethod
    def _cap_first(s: str) -> str:
        """Uppercase first character only — preserves acronyms like GPU, RAM, VRAM."""
        return s[0].upper() + s[1:] if s else s
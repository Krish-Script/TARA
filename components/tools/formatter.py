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
            
            # --- T1: Notes Tool Formatters ---
            Intent.NOTES_CREATE: ToolFormatter._format_notes_create,
            Intent.NOTES_READ:   ToolFormatter._format_notes_read,
            Intent.NOTES_LIST:   ToolFormatter._format_notes_list,
            Intent.NOTES_SEARCH: ToolFormatter._format_notes_search,
            
            Intent.FILE_LIST: ToolFormatter._format_file_list,
            Intent.FILE_READ: ToolFormatter._format_file_read,

            Intent.CALCULATION: ToolFormatter._format_calculation,

            Intent.LOCAL_SEARCH: ToolFormatter._format_local_search,
        }

        formatter = formatters.get(intent, ToolFormatter._format_generic)
        return formatter(raw_output)

    # ── Tool-specific formatters ─────────────────────────────

    @staticmethod
    def _format_time(data: dict) -> str:
        time_str = data.get("time_12h", "unknown time")
        date_str = data.get("date_full", "unknown date")
        
        return f"It's {time_str} on {date_str}."

    @staticmethod
    def _format_system(data: dict) -> str:
        parts = []

        # CPU
        if "cpu_percent" in data:
            parts.append(f"CPU usage is at {data['cpu_percent']:.0f} percent")

        # Memory (RAM)
        if "ram_used_gb" in data and "ram_total_gb" in data:
            parts.append(
                f"RAM is {data['ram_used_gb']:.1f} of "
                f"{data['ram_total_gb']:.1f} gigabytes used"
            )

        # GPU / VRAM
        if "vram_used_gb" in data and "vram_total_gb" in data:
            parts.append(
                f"VRAM is {data['vram_used_gb']:.1f} of "
                f"{data['vram_total_gb']:.1f} gigabytes used"
            )

        # Battery
        if "battery_percent" in data:
            bp = data["battery_percent"]
            plugged = "and charging" if data.get("battery_plugged") else "and discharging"
            parts.append(f"battery is at {bp:.0f} percent {plugged}")

        # Temperature
        if "cpu_temp_c" in data:
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

    # ── T1 Notes Formatters ──────────────────────────────────

    @staticmethod
    def _format_notes_create(data: dict) -> str:
        return f"Note saved: {data.get('content')}"

    @staticmethod
    def _format_notes_read(data: dict) -> str:
        return f"Your last note says: {data.get('content')}"

    @staticmethod
    def _format_notes_list(data: dict) -> str:
        count = data.get('count', 0)
        date = data.get('latest_date', 'recently')
        if count == 1:
            return f"You have 1 note, from {date}."
        return f"You have {count} notes. The most recent one is from {date}."

    @staticmethod
    def _format_notes_search(data: dict) -> str:
        term = data.get('term')
        match = data.get('match')
        return f"I found a note about {term}. It says: {match}"
    
    @staticmethod
    def _format_file_list(data: dict) -> str:
        count = data.get("count", 0)
        latest_date = data.get("latest_date", "recently")
        if count == 1:
            return f"You have one note saved, modified {latest_date}."
        return f"You have {count} notes saved. The latest one was modified {latest_date}."
    
    @staticmethod
    def _format_file_read(data: dict) -> str:
        action = data.get('action')
        filename = data.get('filename')
        content = data.get('content')

        if action == "summarize":
            return f"The file {filename} is quite long, so here is a summary: {content}"

        return f"Here is what {filename} says: {content}"
    
    @staticmethod
    def _format_calculation(data: dict) -> str:
        spoken = data.get("spoken_result", "")
        if not spoken:
            return "I couldn't compute that."
        return f"That's {spoken}."

    # ── Generic fallback ─────────────────────────────────────

    @staticmethod
    def _format_generic(data: dict) -> str:
        """Last-resort fallback — should rarely be reached."""
        if not data:
            return "I completed the action but have no result to report."
        return "I retrieved the information, but I'm not sure how to read it out loud."

    # ── Helpers ──────────────────────────────────────────────

    @staticmethod
    def _cap_first(text: str) -> str:
        """Capitalize first letter safely."""
        if not text:
            return text
        
        # Week 5 fix: Ensure VRAM, CPU, RAM stay uppercase if they are the first word
        first_word = text.split()[0]
        if first_word.isupper():
            return text
            
        return text[0].upper() + text[1:]
    
    @staticmethod
    def _format_local_search(data: dict) -> str:
        return data.get('answer', "I couldn't synthesize the information.")
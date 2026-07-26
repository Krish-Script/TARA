"""
Compound query router for multi-step tool chains.

Runs before IntentDetector in the pipeline (Stage 1.5).
Compound patterns must be more specific than single-intent
patterns in intent.py — they will shadow single-intent routing
for any query they match.

Adding a new chain:
  1. Add trigger phrases to _build_patterns()
  2. Add execution method _chain_*()
  3. Register chain_name in execute()
  4. Add positive + negative test cases to tests/test_benchmark.py
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from components.error_manager import error_logger

compound_logger = __import__("logging").getLogger("compound")


@dataclass
class CompoundResult:
    """Standard return type for all compound chain executions."""
    chain_name:       str
    formatted_output: str
    latency:          float
    success:          bool
    source:           str       = "tool"
    error:            str | None = None


class CompoundRouter:

    def __init__(self, tool_registry):
        self.tool_registry = tool_registry
        self._patterns = self._build_patterns()

    def _build_patterns(self) -> list[tuple[list[str], str]]:
        """
        Ordered list of (trigger_phrases, chain_name).
        More specific phrases first — same rule as intent.py.
        """
        return [
            # Chain 2 — note with live system data
            # Must precede Chain 1: "take a note with my current system status"
            # would otherwise match the system status chain first.
            (
                [
                    "take a note with my current",
                    "note my current",
                    "record my current",
                    "take a note with my",
                ],
                "note_with_system_data",
            ),
            # Chain 3 — timestamped note
            (
                [
                    "timestamped note",
                    "note the time",
                    "note with timestamp",
                ],
                "timestamped_note",
            ),
            # Chain 1 — full system status snapshot (broadest — last)
            (
                [
                    "how is my system doing",
                    "how's my system doing",
                    "hows my system doing",
                    "full system report",
                    "give me a full system",
                    "system status report",
                ],
                "system_status_snapshot",
            ),
        ]

    def match(self, text: str) -> str | None:
        """
        Return chain name if text matches a compound pattern.
        Returns None if no match — caller continues to normal routing.
        """
        lower = text.lower().strip()
        for phrases, chain_name in self._patterns:
            for phrase in phrases:
                if phrase in lower:
                    compound_logger.debug(
                        f"Compound match: chain={chain_name} phrase='{phrase}'"
                    )
                    return chain_name
        return None

    def execute(self, chain_name: str, text: str) -> CompoundResult:
        """
        Execute the named chain. Always returns a CompoundResult —
        never raises. Errors are logged and returned as failed results.
        """
        start = time.time()
        try:
            if chain_name == "system_status_snapshot":
                return self._chain_system_status(text, start)
            elif chain_name == "note_with_system_data":
                return self._chain_note_with_system_data(text, start)
            elif chain_name == "timestamped_note":
                return self._chain_timestamped_note(text, start)
            else:
                return CompoundResult(
                    chain_name=chain_name,
                    formatted_output="I don't know how to handle that compound request.",
                    latency=time.time() - start,
                    success=False,
                    error=f"Unknown chain: {chain_name}",
                )
        except Exception as e:
            error_logger.error(
                f"Compound chain '{chain_name}' crashed: {e}", exc_info=True
            )
            return CompoundResult(
                chain_name=chain_name,
                formatted_output="Something went wrong with that, but I'm still here.",
                latency=time.time() - start,
                success=False,
                error=str(e),
            )

    # ── Chain implementations ────────────────────────────────────

    def _chain_system_status(self, text: str, start: float) -> CompoundResult:
        """
        Chain 1 — System status snapshot.
        Single SYSTEM_QUERY dispatch with 'system status' → _get_all().
        Template synthesis — no LLM call.
        Target TTFS: ≤1.60s
        """
        from components.intent import Intent

        result = self.tool_registry.dispatch(Intent.SYSTEM_QUERY, "system status")

        if not result or not result.raw_output:
            return CompoundResult(
                chain_name="system_status_snapshot",
                formatted_output="I couldn't retrieve system metrics right now.",
                latency=time.time() - start,
                success=False,
            )

        d = result.raw_output
        cpu   = d.get("cpu_percent",  "unknown")
        r_used  = d.get("ram_used_gb",  "?")
        r_total = d.get("ram_total_gb", "?")
        disk  = d.get("disk_percent", "unknown")

        output = (
            f"CPU is at {cpu} percent, "
            f"RAM is {r_used} of {r_total} gigabytes, "
            f"and disk is {disk} percent full."
        )

        compound_logger.info(
            f"system_status_snapshot | latency={time.time()-start:.3f}s"
        )
        return CompoundResult(
            chain_name="system_status_snapshot",
            formatted_output=output,
            latency=time.time() - start,
            success=True,
        )

    def _chain_note_with_system_data(self, text: str, start: float) -> CompoundResult:
        """
        Chain 2 — Note with live system data.
        Detects metric keyword → fetches value → saves as note.
        Target TTFS: ≤2.0s
        """
        from components.intent import Intent

        lower = text.lower()

        # Map user keywords to SystemMonitor dispatch queries
        metric_map = [
            ("cpu",         "cpu usage"),
            ("processor",   "cpu usage"),
            ("ram",         "ram usage"),
            ("memory",      "ram usage"),
            ("disk",        "disk usage"),
            ("storage",     "disk usage"),
            ("battery",     "battery level"),
            ("vram",        "vram usage"),
            ("gpu",         "vram usage"),
            ("temperature", "gpu temperature"),
            ("temp",        "gpu temperature"),
        ]

        detected_query = "system status"   # fallback
        for keyword, query in metric_map:
            if keyword in lower:
                detected_query = query
                break

        # Step 1 — fetch the metric
        metric_result = self.tool_registry.dispatch(
            Intent.SYSTEM_QUERY, detected_query
        )
        if not metric_result or not metric_result.raw_output:
            return CompoundResult(
                chain_name="note_with_system_data",
                formatted_output="I couldn't retrieve system data to save.",
                latency=time.time() - start,
                success=False,
            )

        # Step 2 — save as note using the formatted tool output
        note_query  = f"take a note: {metric_result.formatted_output}"
        note_result = self.tool_registry.dispatch(Intent.NOTES_CREATE, note_query)

        if not note_result or not note_result.success:
            return CompoundResult(
                chain_name="note_with_system_data",
                formatted_output="I got the data but couldn't save the note.",
                latency=time.time() - start,
                success=False,
            )

        output = f"Noted. {metric_result.formatted_output}"
        compound_logger.info(
            f"note_with_system_data | metric='{detected_query}' "
            f"latency={time.time()-start:.3f}s"
        )
        return CompoundResult(
            chain_name="note_with_system_data",
            formatted_output=output,
            latency=time.time() - start,
            success=True,
        )

    def _chain_timestamped_note(self, text: str, start: float) -> CompoundResult:
        """
        Chain 3 — Timestamped note.
        Fetches current time → prepends to note content → saves.
        Template synthesis — no LLM call.
        Target TTFS: ≤1.70s
        """
        from components.intent import Intent

        # Step 1 — fetch current time
        time_result = self.tool_registry.dispatch(
            Intent.TIME_QUERY, "what time is it"
        )
        if not time_result or not time_result.raw_output:
            return CompoundResult(
                chain_name="timestamped_note",
                formatted_output="I couldn't get the current time to timestamp your note.",
                latency=time.time() - start,
                success=False,
            )

        timestamp = time_result.formatted_output

        # Step 2 — extract note content by stripping trigger phrase
        lower   = text.lower()
        content = text.strip()
        for trigger in [
            "timestamped note:", "timestamped note",
            "note the time:", "note the time",
            "note with timestamp:", "note with timestamp",
        ]:
            if trigger in lower:
                idx     = lower.index(trigger) + len(trigger)
                content = text[idx:].strip()
                break

        note_text = (
            f"{timestamp} — {content}"
            if content and content.lower() not in ("", "please", "now")
            else timestamp
        )

        # Step 3 — save the note
        note_result = self.tool_registry.dispatch(
            Intent.NOTES_CREATE, f"take a note: {note_text}"
        )
        if not note_result or not note_result.success:
            return CompoundResult(
                chain_name="timestamped_note",
                formatted_output="I got the time but couldn't save the note.",
                latency=time.time() - start,
                success=False,
            )

        compound_logger.info(
            f"timestamped_note | latency={time.time()-start:.3f}s"
        )
        return CompoundResult(
            chain_name="timestamped_note",
            formatted_output=f"Noted at {timestamp.rstrip('.')}.",
            latency=time.time() - start,
            success=True,
        )
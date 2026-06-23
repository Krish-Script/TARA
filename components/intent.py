"""
Keyword-pattern router. Returns an Intent for every input.

Design decision: keyword matching, NOT LLM classification.
  - LLM classification: 0.8-1.2s added latency, ~80-85% accuracy
  - Keyword matching:   <5ms added latency, 100% accuracy on
                        well-defined unambiguous commands

Pattern trap to avoid: bare single words ("ram", "time", "memory")
will misclassify conversational queries like "explain how RAM works"
or "do you have a good memory?" Require specific phrases instead.

Adding a new intent:
  1. Add value to Intent enum
  2. Add (pattern_list, Intent.YOUR_INTENT) to _build_patterns()
  3. Write a test for the ambiguous edge cases
"""

from __future__ import annotations

from enum import Enum, auto


class Intent(Enum):
    CHAT         = auto()   # default — goes to LLM
    SYSTEM_QUERY = auto()   # CPU, RAM, disk, battery, VRAM
    TIME_QUERY   = auto()   # time, date, day of week
    CALCULATION  = auto()   # math queries (Week 4+)
    MEMORY       = auto()   # memory commands — handled by command registry


class IntentDetector:

    def __init__(self):
        self._patterns = self._build_patterns()

    def _build_patterns(self) -> list[tuple[list[str], Intent]]:
        """
        Ordered list of (trigger_phrases, Intent) pairs.
        First match wins — order matters.

        Phrases are matched as substrings of the lowercased input.
        More specific phrases first to prevent shadowing.
        """
        return [
            # ── Time & Date ───────────────────────────────────
            (
                [
                    "what time is it",
                    "what's the time",
                    "whats the time",
                    "current time",
                    "what time",
                    "what day is it",
                    "what's today",
                    "whats today",
                    "today's date",
                    "todays date",
                    "what date",
                    "what is the date",
                    "what is today",
                ],
                Intent.TIME_QUERY,
            ),

            # ── System Monitor ────────────────────────────────
            # Specific multi-word phrases only — avoids misclassifying
            # "explain how RAM works" or "tell me about CPUs"
            (
                [
                    "cpu usage",
                    "cpu percent",
                    "how much cpu",
                    "ram usage",
                    "memory usage",
                    "how much ram",
                    "how much memory",
                    "disk usage",
                    "disk space",
                    "how much disk",
                    "battery level",
                    "battery status",
                    "how much battery",
                    "vram usage",
                    "how much vram",
                    "gpu memory",
                    "system status",
                    "system stats",
                    "computer status",
                ],
                Intent.SYSTEM_QUERY,
            ),

            # ── Calculation (stub — Week 4+) ──────────────────
            (
                [
                    "calculate ",
                    "what is the result",
                ],
                Intent.CALCULATION,
            ),

            # CHAT is the default — no patterns needed
        ]

    def classify(self, text: str) -> Intent:
        """
        Return the Intent for this text.
        Falls back to CHAT if no pattern matches.

        Args:
            text: raw transcribed user speech

        Returns:
            Intent enum value
        """
        lower = text.lower().strip()

        for phrases, intent in self._patterns:
            if any(phrase in lower for phrase in phrases):
                return intent

        return Intent.CHAT

    def classify_with_confidence(self, text: str) -> tuple[Intent, str]:
        """
        Return (Intent, matched_phrase) for debugging and logging.
        Returns (Intent.CHAT, "") if no match.
        """
        lower = text.lower().strip()

        for phrases, intent in self._patterns:
            for phrase in phrases:
                if phrase in lower:
                    return intent, phrase

        return Intent.CHAT, ""
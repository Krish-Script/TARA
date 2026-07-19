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

    # --- Notes Intents ---
    NOTES_CREATE = auto()
    NOTES_READ   = auto()
    NOTES_LIST   = auto()
    NOTES_SEARCH = auto()

    FILE_READ    = auto()

    FILE_LIST    = auto()
    LOCAL_SEARCH = auto() 


class IntentDetector:

    def __init__(self):
        print("DEBUG: The new Intent Detector just loaded!")
        self._patterns = self._build_patterns()

    def _build_patterns(self) -> list[tuple[list[str], Intent]]:
        """
        Ordered list of (trigger_phrases, Intent) pairs.
        First match wins — order matters.

        Phrases are matched as substrings of the lowercased input.
        More specific phrases first to prevent shadowing.
        """
        return [
            (
                [
                    "take a note",
                    "take the note",
                    "take note",
                    "note that",
                    "remember to",  
                    "write down",
                    "add a note",
                ],
                Intent.NOTES_CREATE,
            ),
            (
                [
                    "read my last note",
                    "what was my last note",
                    "read my notes",
                ],
                Intent.NOTES_READ,
            ),
            (
                [
                    "find my note about",
                    "do i have a note about",
                    "search my notes",
                ],
                Intent.NOTES_SEARCH,
            ),
            (
                [
                    "list my notes",
                    "what notes do i have",
                    "how many notes",
                ],
                Intent.NOTES_LIST,
            ),
            (
                [
                    "read the ",
                    "read my ",
                    "summarize the ",
                    "summarize my ",
                    "from my desktop",
                    "from my documents",
                    "from my downloads",
                ],
                Intent.FILE_READ,
            ),
            # File listing
            (
                [
                    "list files in",
                    "what files are in",
                    "show files in",
                    "what's in my",
                    "files on my desktop",
                    "files in my documents",
                ],
                Intent.FILE_LIST,
            ),
            
            (
                [
                    "remember that",
                    "remember ",
                ],
                Intent.MEMORY,
            ),

            # ── Time & Date ───────────────────────────────────
            (
                [
                    "what time is it",
                    "what's the time",
                    "whats the time",
                    "current time",
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

            # ── System Monitor ────────────────────────────────────────
            (
                [
                    # CPU
                    "cpu usage",
                    "cpu percent",
                    "cpu utilization",
                    "cpu load",
                    "cpu used",
                    "how much cpu",
                    "what's my cpu",
                    "whats my cpu",
                    "processor usage",

                    # RAM
                    "ram usage",
                    "memory usage",
                    "how much ram",
                    "how much memory",

                    # Disk / Storage
                    "disk usage",
                    "disk space",
                    "how much disk",
                    "storage",
                    "how much storage",
                    "storage left",
                    "storage space",
                    "free space",

                    # Battery
                    "battery level",
                    "battery status",
                    "how much battery",

                    # VRAM / GPU
                    "vram usage",
                    "how much vram",
                    "gpu memory",

                    # Temperature
                    "gpu temperature",
                    "cpu temperature",
                    "gpu temp",
                    "cpu temp",
                    "how hot",
                    "thermal",

                    # General
                    "system status",
                    "system stats",
                    "computer status",
                ],
                Intent.SYSTEM_QUERY,
            ),

            # ── Calculation (stub — Week 4+) ──────────────────
            (
                [
                    "calculate",
                    "how much is",
                    "compute",
                    "divided by",
                    "times",
                    "multiplied by",
                    "percent of",
                    "squared",
                    "square root",
                    "plus",
                    "minus",
                ],
                Intent.CALCULATION,
            ),
            (
                [
                    "search for",
                    "look up",
                    "do you know anything about",
                    "find anything about",
                    "search my notes for",
                ],
                Intent.LOCAL_SEARCH,
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
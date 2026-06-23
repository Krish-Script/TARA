"""
The Orchestrator sits between audio input and AI components.
It owns two responsibilities:
  1. Command routing  — deciding what kind of input was received
  2. Pipeline execution — coordinating the response pipeline stages

Current pipeline:
    [User Speech]
        ↓
    [STT]  ← SpeechToText (main.py)
        ↓
    [Orchestrator] ← you are here
        ↓
    Stage 1: Memory Context Retrieval
        ↓
    Stage 2: Intent Detection
        ↓
    Stage 3: Tool Execution
        ↓
    Stage 4: RAG Retrieval             [FUTURE — Week 5]
        ↓
    Stage 5: LLM Generation
        ↓
    Stage 6: Response Delivery
        ↓
    Stage 7: Persistence
        ↓
    [Audio Output]

Adding a new pipeline stage: insert it between existing stages above
and add the corresponding code block in _run_pipeline().

Adding a new voice command: add a (_is_X, _handle_X) tuple to
_build_command_registry(). No other method needs to change.

NOT responsible for:
  - Audio capture (SpeechToText / main.py)
  - Component initialization (main.py)
  - UI / banner printing (main.py)
"""

import time

from components.memory import MemoryStore
from components.intent import Intent, IntentDetector
from components.tools.registry import ToolRegistry


class Orchestrator:

    # ── Command trigger phrases ───────────────────────────────
    # Kept here (not config.py) because these are behavioral constants,
    # not runtime parameters. config.py is for paths, thresholds, and
    # settings a deployer might change — not system logic.

    STOP_COMMANDS   = ["quit", "exit", "goodbye", "bye"]
    CLEAR_COMMANDS  = ["clear memory"]
    RECALL_COMMANDS = [
        "what do you remember",
        "what do you know about me",
        "what have i told you",
    ]

    def __init__(
        self,
        llm,
        tts,
        memory: MemoryStore,
        session_id: str,
        memory_config: dict,
    ):
        self.llm           = llm
        self.tts           = tts
        self.memory        = memory
        self.session_id    = session_id
        self.memory_config = memory_config
        self.intent_detector = IntentDetector()
        self.tool_registry   = ToolRegistry()

        self.stats = {
            "stt":           [],
            "llm":           [],
            "tts":           [],
            "tts_synthesis": [],
            "ttfs":          [],
            "ttfs_tool":     [],
            "tool_latency":  [],
            "session_start": time.time(),
        }

        # Build command registry once at startup
        self._command_registry = self._build_command_registry()

    # ── Public API ───────────────────────────────────────────

    def process_turn(self, text: str, stt_latency: float) -> bool:
        """
        Process one full conversation turn.

        Walks the command registry in order — first matching command wins.
        Falls through to the main pipeline if no command matches.

        Args:
            text:        transcribed speech from the user
            stt_latency: seconds taken by STT

        Returns:
            True  → keep the session running
            False → exit command received, stop the loop
        """
        self.stats["stt"].append(stt_latency)
        lower = text.lower().strip()

        # Walk command registry — isolated, ordered, easy to extend
        for condition, handler in self._command_registry:
            if condition(text, lower):
                return handler(text)

        # No command matched — run the full response pipeline
        return self._run_pipeline(text, stt_latency)

    def print_report(self):
        """Print end-of-session performance report."""
        self._print_baseline_report()

    # ── Command Registry ─────────────────────────────────────

    def _build_command_registry(self) -> list[tuple]:
        """
        Ordered list of (condition, handler) pairs.

        Evaluated top-to-bottom — first match wins, rest are skipped.
        To add a new command:
          1. Define _is_yourcommand(text, lower) -> bool
          2. Define _handle_yourcommand(text) -> bool
          3. Add (_is_yourcommand, _handle_yourcommand) here

        Nothing else needs to change.
        """
        return [
            (self._is_exit,     self._handle_exit),
            (self._is_clear,    self._handle_clear),
            (self._is_remember, self._handle_remember),
            (self._is_recall,   self._handle_recall),
        ]

    # ── Command Conditions ───────────────────────────────────

    def _is_exit(self, text: str, lower: str) -> bool:
        return any(cmd in lower for cmd in self.STOP_COMMANDS)

    def _is_clear(self, text: str, lower: str) -> bool:
        return any(cmd in lower for cmd in self.CLEAR_COMMANDS)

    def _is_remember(self, text: str, lower: str) -> bool:
        # Delegate text parsing to MemoryStore's static utility —
        # but the DECISION of whether to remember stays here.
        return MemoryStore.extract_fact_from_text(text) is not None

    def _is_recall(self, text: str, lower: str) -> bool:
        return any(phrase in lower for phrase in self.RECALL_COMMANDS)

    # ── Command Handlers ─────────────────────────────────────

    def _handle_exit(self, text: str) -> bool:
        self._say("Goodbye! Have a great day.")
        return False  # signal main loop to stop

    def _handle_clear(self, text: str) -> bool:
        self.llm.clear_history()
        self._say("Memory cleared. Starting fresh.")
        return True

    def _handle_remember(self, text: str) -> bool:
        """
        Orchestrator detects the intent, extracts the fact, calls storage.
        MemoryStore.save_fact() only stores — it does not decide when to store.
        """
        fact = MemoryStore.extract_fact_from_text(text)
        if fact:
            self.memory.save_fact(fact, source_message=text)
            self._say("Got it, I'll remember that.")
        return True

    def _handle_recall(self, text: str) -> bool:
        facts = self.memory.get_facts()
        if facts:
            fact_list = ". ".join(f.fact for f in facts)
            self._say(f"Here's what I remember about you: {fact_list}")
        else:
            self._say("I don't have anything stored about you yet.")
        return True

    # ── Pipeline ─────────────────────────────────────────────

    def _run_pipeline(self, text: str, stt_latency: float) -> bool:
        """
        Full response pipeline for a normal conversation turn.

        Stages are clearly marked so future additions have obvious
        insertion points. See module docstring for the full stage map.
        """

        # ── Stage 1: Memory Context Retrieval ────────────────
        memory_context = self.memory.build_context(
            session_id=None,
            recent_turns=self.memory_config["context_turns"],
            fact_limit=self.memory_config["fact_limit"],
        )

        # ── Stage 2: Intent Detection──────
        intent, matched = self.intent_detector.classify_with_confidence(text)
        if intent != Intent.CHAT:
            print(f"[Intent] {intent.name}  (matched: '{matched}')")

        # ── Stage 3: Tool Execution────────
        if intent != Intent.CHAT:
            tool_result = self.tool_registry.dispatch(intent, text)
            if tool_result:
                print(f"\n[TARA] {tool_result.formatted_output}")
                print(f"       Tool: {tool_result.tool_name} | "
                    f"latency: {tool_result.latency:.3f}s")
                tts_result = self.tts.speak(tool_result.formatted_output)
                self.stats["tts_synthesis"].append(tts_result.synthesis_latency)
                self.stats["tts"].append(tts_result.total_latency)
                ttfs = stt_latency + tts_result.synthesis_latency
                self.stats["tool_latency"].append(tool_result.latency)
                self.stats["ttfs_tool"].append(ttfs)
                print(f"       ── TTFS: {ttfs:.2f}s ──")
                self.memory.save_turn(
                    session_id=self.session_id,
                    user_message=text,
                    assistant_response=tool_result.formatted_output,
                )
                return True

        # ── Stage 4: RAG Retrieval [FUTURE — Week 5] ─────────
        # Placeholder for future RAG retrieval stage.

        # ── Stage 5: LLM Generation ──────────────────────────
        print("[Thinking...]")
        response, llm_latency = self.llm.generate(
            text, memory_context=memory_context
        )
        print(f"\n[TARA] {response}")
        print(f"       LLM latency: {llm_latency:.2f}s")
        self.stats["llm"].append(llm_latency)

        # ── Stage 6: Response Delivery (Chunked TTS) ───────
        # Splits response at sentence boundaries.
        # Producer thread synthesises each chunk with piper.exe.
        # Consumer thread plays chunks as they arrive.
        # synthesis_latency = first-chunk time only (TTFS component).
        tts_result = self.tts.speak(response)
        print(f"       TTS chunks:    {tts_result.chunks}")
        print(f"       TTS synthesis: {tts_result.synthesis_latency:.2f}s  ← first chunk (TTFS)")
        print(f"       TTS playback:  {tts_result.playback_latency:.2f}s")
        print(f"       TTS total:     {tts_result.total_latency:.2f}s")
        self.stats["tts"].append(tts_result.total_latency)
        self.stats["tts_synthesis"].append(tts_result.synthesis_latency)

        # TTFS = silence between user finishing speaking and TARA starting
        ttfs = stt_latency + llm_latency + tts_result.synthesis_latency
        self.stats["ttfs"].append(ttfs)
        print(f"       ── TTFS: {ttfs:.2f}s ──")

        # ── Stage 7: Persistence ──────────────────────────────
        self.memory.save_turn(
            session_id=self.session_id,
            user_message=text,
            assistant_response=response,
        )

        return True

    # ── Helpers ──────────────────────────────────────────────

    def _say(self, text: str) -> float:
        """
        Print and speak together.
        All command handlers use this. The main pipeline (Stage 6)
        calls tts.speak() directly to capture the latency return value.
        """
        print(f"\n[TARA] {text}")
        return self.tts.speak(text)

    def _print_baseline_report(self):
        def avg(lst): return sum(lst) / len(lst) if lst else 0.0
        def mn(lst):  return min(lst)             if lst else 0.0
        def mx(lst):  return max(lst)             if lst else 0.0

        session_mins = (time.time() - self.stats["session_start"]) / 60
        chat_turns   = len(self.stats["llm"])
        tool_turns   = len(self.stats["tool_latency"])
        total_turns  = chat_turns + tool_turns

        print("\n" + "=" * 55)
        print("  WEEK 4 BASELINE PERFORMANCE REPORT")
        print("=" * 55)
        print(f"  Session duration : {session_mins:.1f} min")
        print(f"  Total turns      : {total_turns}  "
            f"(chat: {chat_turns} | tool: {tool_turns})")
        print()

        # ── TTFS ─────────────────────────────────────────────────
        all_ttfs = self.stats["ttfs"] + self.stats["ttfs_tool"]
        print(f"  ★ TTFS (all)     | avg: {avg(all_ttfs):.2f}s  "
            f"min: {mn(all_ttfs):.2f}s  max: {mx(all_ttfs):.2f}s")
        if self.stats["ttfs"]:
            print(f"    Chat path      | avg: {avg(self.stats['ttfs']):.2f}s  "
                f"(W3 baseline: 2.46s)")
        if self.stats["ttfs_tool"]:
            print(f"    Tool path      | avg: {avg(self.stats['ttfs_tool']):.2f}s  "
                f"(target: ≤1.50s)")
        print()

        # ── Component breakdown ───────────────────────────────────
        print(f"  Component        | avg    | min    | max")
        print(f"  ─────────────────|--------|--------|--------")
        print(f"  STT (Whisper)    | {avg(self.stats['stt']):.2f}s  "
            f"| {mn(self.stats['stt']):.2f}s  | {mx(self.stats['stt']):.2f}s")

        if self.stats["llm"]:
            print(f"  LLM (chat only)  | {avg(self.stats['llm']):.2f}s  "
                f"| {mn(self.stats['llm']):.2f}s  | {mx(self.stats['llm']):.2f}s")

        if self.stats["tool_latency"]:
            print(f"  Tool execution   | {avg(self.stats['tool_latency']):.3f}s "
                f"| {mn(self.stats['tool_latency']):.3f}s "
                f"| {mx(self.stats['tool_latency']):.3f}s")

        print(f"  TTS synthesis    | {avg(self.stats['tts_synthesis']):.2f}s  "
            f"| {mn(self.stats['tts_synthesis']):.2f}s  "
            f"| {mx(self.stats['tts_synthesis']):.2f}s")
        print(f"  TTS playback     | {avg(self.stats['tts']):.2f}s  "
            f"| — irreducible —")

        print(f"  ─────────────────|--------|--------|--------")
        if chat_turns:
            chat_total = avg(self.stats["stt"]) + avg(self.stats["llm"]) + avg(self.stats["tts"])
            print(f"  Chat path total  | {chat_total:.2f}s")
        if tool_turns:
            tool_total = avg(self.stats["stt"]) + avg(self.stats["tool_latency"]) + avg(self.stats["tts"])
            print(f"  Tool path total  | {tool_total:.2f}s")
        print("=" * 55 + "\n")
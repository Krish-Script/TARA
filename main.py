"""
main.py — TARA End-to-End Voice Pipeline
=========================================
Data flow:
    Your Voice
        → PyAudio (microphone capture)
        → faster-whisper on CPU  (speech → text)
        → Ollama / LLaMA 3.2 3b on GPU  (text → response)
        → Piper TTS (response → speech)
        → Your Speakers
"""

import time

from components.stt import SpeechToText
from components.llm import LanguageModel
from components.tts import TextToSpeech
from components.memory import MemoryStore, create_session_id
from config import STT_CONFIG, AUDIO_CONFIG, LLM_CONFIG, PIPER_CONFIG, MEMORY_CONFIG


class TARA:
    """Central orchestrator — owns all components and runs the voice loop."""

    def __init__(self):
        self._print_banner()
        print("Loading components...\n")

        stt_config = {**STT_CONFIG, **AUDIO_CONFIG}

        self.stt    = SpeechToText(stt_config)
        self.tts    = TextToSpeech(PIPER_CONFIG)
        self.llm    = LanguageModel(LLM_CONFIG)

        self.memory     = MemoryStore(MEMORY_CONFIG["db_path"])
        self.session_id = create_session_id()
        self.memory.print_stats()

        self.stats = {
            "stt":           [],
            "llm":           [],
            "tts":           [],
            "session_start": time.time(),
        }

        print("\n✅ All components loaded. TARA is ready!\n")

    # ── Helpers ──────────────────────────────────────────────

    def _say(self, text: str) -> float:
        """
        Print and speak a TARA response in one call.
        Every branch that speaks MUST use this method — never call
        self.tts.speak() directly, or the print will be missed again.
        Returns TTS latency.
        """
        print(f"\n[TARA] {text}")
        return self.tts.speak(text)

    # ── Main Loop ────────────────────────────────────────────

    def run(self):
        print("─" * 55)
        print("Say 'quit', 'exit', or 'goodbye' to stop.")
        print("Say 'clear memory' to forget conversation history.")
        print("Say 'remember that [fact]' to store something permanently.")
        print("─" * 55 + "\n")

        self._say("Hello! I'm TARA, your offline AI assistant. How can I help?")

        while True:
            try:
                # ── Step 1: Listen + Transcribe ──────────────
                print("\n[Waiting for speech...]")
                text, stt_latency = self.stt.listen_and_transcribe()

                if not text:
                    continue

                print(f"\n[You]  {text}")
                print(f"       STT latency: {stt_latency:.2f}s")
                self.stats["stt"].append(stt_latency)

                lower_text = text.lower().strip()

                # ── Exit ─────────────────────────────────────
                if any(cmd in lower_text for cmd in ["quit", "exit", "goodbye", "bye"]):
                    self._say("Goodbye! Have a great day.")
                    break

                # ── Clear LLM history ─────────────────────────
                if "clear memory" in lower_text:
                    self.llm.clear_history()
                    self._say("Memory cleared. Starting fresh.")
                    continue

                # ── Remember command ──────────────────────────
                if self.memory.remember_if_requested(text):
                    self._say("Got it, I'll remember that.")
                    continue

                # ── Recall command ────────────────────────────
                if any(phrase in lower_text for phrase in [
                    "what do you remember",
                    "what do you know about me",
                    "what have i told you",
                ]):
                    facts = self.memory.get_facts()
                    if facts:
                        fact_list = ". ".join(f.fact for f in facts)
                        self._say(f"Here's what I remember about you: {fact_list}")
                    else:
                        self._say("I don't have anything stored about you yet.")
                    continue

                # ── Step 2: Build memory context ──────────────
                memory_context = self.memory.build_context(
                    session_id=None,
                    recent_turns=MEMORY_CONFIG["context_turns"],
                    fact_limit=MEMORY_CONFIG["fact_limit"],
                )

                # ── Step 3: LLM response ──────────────────────
                print("[Thinking...]")
                response, llm_latency = self.llm.generate(
                    text, memory_context=memory_context
                )
                print(f"\n[TARA] {response}")
                print(f"       LLM latency: {llm_latency:.2f}s")
                self.stats["llm"].append(llm_latency)

                # ── Step 4: Speak response ─────────────────────
                tts_latency = self.tts.speak(response)
                print(f"       TTS latency: {tts_latency:.2f}s")
                self.stats["tts"].append(tts_latency)

                # ── Step 5: Save to memory ─────────────────────
                self.memory.save_turn(
                    session_id=self.session_id,
                    user_message=text,
                    assistant_response=response,
                )

            except KeyboardInterrupt:
                print("\n\n[Ctrl+C detected — shutting down]")
                break

            except Exception as e:
                print(f"\n[ERROR] {e}")
                self.tts.speak("Sorry, something went wrong. Please try again.")

        self._print_baseline_report()

    # ── Reporting ────────────────────────────────────────────

    def _print_baseline_report(self):
        def avg(lst): return sum(lst) / len(lst) if lst else 0.0
        def mn(lst):  return min(lst)             if lst else 0.0
        def mx(lst):  return max(lst)             if lst else 0.0

        session_mins = (time.time() - self.stats["session_start"]) / 60
        turns        = len(self.stats["llm"])

        print("\n" + "=" * 55)
        print("  WEEK 3 BASELINE PERFORMANCE REPORT")
        print("=" * 55)
        print(f"  Session duration : {session_mins:.1f} min")
        print(f"  Total turns      : {turns}")
        print()
        print(f"  Component    | avg    | min    | max")
        print(f"  -------------|--------|--------|--------")
        print(f"  STT (Whisper)| {avg(self.stats['stt']):.2f}s  | {mn(self.stats['stt']):.2f}s  | {mx(self.stats['stt']):.2f}s")
        print(f"  LLM (Ollama) | {avg(self.stats['llm']):.2f}s  | {mn(self.stats['llm']):.2f}s  | {mx(self.stats['llm']):.2f}s")
        print(f"  TTS (piper)  | {avg(self.stats['tts']):.2f}s  | {mn(self.stats['tts']):.2f}s  | {mx(self.stats['tts']):.2f}s")
        total = avg(self.stats["stt"]) + avg(self.stats["llm"]) + avg(self.stats["tts"])
        print(f"  -------------|--------|--------|--------")
        print(f"  TOTAL (avg)  | {total:.2f}s")
        print("=" * 55 + "\n")

    # ── Banner ───────────────────────────────────────────────

    @staticmethod
    def _print_banner():
        print()
        print("=" * 55)
        print("  ╔═══════════════════════════════╗")
        print("  ║   T A R A  v0.3.2  — Week 3   ║")
        print("  ║   Offline Voice AI Assistant  ║")
        print("  ╚═══════════════════════════════╝")
        print("=" * 55)
        print()


if __name__ == "__main__":
    tara = TARA()
    tara.run()
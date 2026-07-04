"""
Data flow:
    Your Voice
        → PyAudio (microphone capture)
        → faster-whisper on CPU  (speech → text)
        → Ollama / LLaMA 3.2 3b on GPU  (text → response)
        → Piper TTS (response → speech)
        → Your Speakers

Responsibilities:
  - Initialize all components
  - Create the Orchestrator
  - Run the audio capture loop
  - Delegate all pipeline logic to Orchestrator
"""

import time

from components.stt         import SpeechToText
from components.llm         import LanguageModel
from components.tts         import TextToSpeech
from components.memory      import MemoryStore, create_session_id
from components.orchestrator import Orchestrator
from config import STT_CONFIG, AUDIO_CONFIG, LLM_CONFIG, PIPER_CONFIG, MEMORY_CONFIG


class TARA:
    """
    Entry point and component owner.
    Initializes all components and delegates pipeline execution to Orchestrator.
    """

    def __init__(self):
        self._print_banner()
        print("Loading components...\n")

        stt_config = {**STT_CONFIG, **AUDIO_CONFIG}

        self.stt = SpeechToText(stt_config)
        self.tts = TextToSpeech(PIPER_CONFIG)
        self.llm = LanguageModel(LLM_CONFIG)

        memory     = MemoryStore(MEMORY_CONFIG["db_path"])
        session_id = create_session_id()
        memory.print_stats()

        self.orchestrator = Orchestrator(
            llm=self.llm,
            tts=self.tts,
            memory=memory,
            session_id=session_id,
            memory_config=MEMORY_CONFIG,
        )

        print("\n✅ All components loaded. TARA is ready!\n")

    def run(self):
        """Audio capture loop — listens and delegates each turn to Orchestrator."""
        print("─" * 55)
        print("Say 'quit', 'exit', or 'goodbye'     → stop")
        print("Say 'clear memory'                   → reset conversation")
        print("Say 'remember that [fact]'           → store permanently")
        print("Say 'what do you remember about me'  → recall stored facts")
        print("─" * 55 + "\n")

        # Greeting
        greeting = "Hello! I'm TARA, your offline AI assistant. How can I help?"
        print(f"\n[TARA] {greeting}")
        self.tts.speak(greeting)

        while True:
            try:
                print("\n[Waiting for speech...]")
                text, stt_latency = self.stt.listen_and_transcribe()

                if not text:
                    continue

                print(f"\n[You]  {text}")
                print(f"       STT latency: {stt_latency:.2f}s")

                should_continue = self.orchestrator.process_turn(text, stt_latency)
                if not should_continue:
                    break

            except KeyboardInterrupt:
                print("\n\n[Ctrl+C detected — shutting down]")
                break

            except Exception as e:
                print(f"\n[ERROR] {e}")
                self.tts.speak("Sorry, something went wrong. Please try again.")

        self.orchestrator.print_report()

    @staticmethod
    def _print_banner():
        print()
        print("=" * 55)
        print("  ╔═══════════════════════════════╗")
        print("  ║   T A R A  v0.5.7  — Week 5   ║")
        print("  ║   Offline Voice AI Assistant  ║")
        print("  ╚═══════════════════════════════╝")
        print("=" * 55)
        print()


if __name__ == "__main__":
    tara = TARA()
    tara.run()
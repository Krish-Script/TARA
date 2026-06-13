"""
components/tts.py — Text-to-Speech Component
============================================
Uses pyttsx3 with Windows SAPI5 (built-in Windows speech engine).
"""

import time

import pyttsx3


class TextToSpeech:
    def __init__(self, config: dict):
        self.config = config
        self.engine = None
        self._init_engine()

    # ── Initialisation ───────────────────────────────────────

    def _init_engine(self):
        """Set up the TTS engine with your configured settings."""
        self.engine = pyttsx3.init()

        # Apply settings from config
        self.engine.setProperty("rate",   self.config.get("rate",   175))
        self.engine.setProperty("volume", self.config.get("volume", 1.0))

        # Pick a voice
        voices      = self.engine.getProperty("voices")
        voice_index = self.config.get("voice_index", 1)

        if voices:
            # Clamp index so it never crashes if voice_index is too high
            idx = min(voice_index, len(voices) - 1) # type: ignore
            self.engine.setProperty("voice", voices[idx].id) # type: ignore
            print(f"[TTS] Using voice [{idx}]: {voices[idx].name} ✓") # type: ignore
        else:
            print("[TTS] ⚠  No voices found. Check Windows speech settings.")

    # ── Speaking ─────────────────────────────────────────────

    def speak(self, text: str) -> float:
        """
        Convert text to speech and play it through speakers.
        This call BLOCKS until speaking is finished.
        Returns how long speaking took in seconds.

        NOTE — Windows pyttsx3 bug workaround:
          pyttsx3.init() does NOT create a new engine each time — it
          caches one internally and hands back the same broken object,
          which is why only the FIRST speak() call ever produces audio.

          The fix: clear pyttsx3's internal engine cache before calling
          init(), forcing it to build a genuinely new SAPI5 driver.
          This adds ~0.1-0.2s overhead per call but is fully reliable.
        """
        if not text:
            return 0.0

        start = time.time()

        # Force pyttsx3 to forget its cached engine so init() below
        # is forced to construct a brand new one.
        pyttsx3._activeEngines.clear()

        engine = pyttsx3.init()
        engine.setProperty("rate",   self.config.get("rate",   175))
        engine.setProperty("volume", self.config.get("volume", 1.0))

        voices      = engine.getProperty("voices")
        voice_index = self.config.get("voice_index", 1)
        if voices:
            idx = min(voice_index, len(voices) - 1) # type: ignore
            engine.setProperty("voice", voices[idx].id) # type: ignore

        engine.say(text)
        engine.runAndWait()        # blocks here until audio finishes

        return time.time() - start

    # ── Utility ──────────────────────────────────────────────

    def list_voices(self):
        """Print all available Windows TTS voices. Use this to pick one."""
        voices = self.engine.getProperty("voices") # type: ignore
        print(f"\n[TTS] Found {len(voices)} available voice(s):") # type: ignore
        for i, voice in enumerate(voices): # type: ignore
            print(f"  [{i}] {voice.name}")
            print(f"       {voice.id}")
        print("\nTo change voice: set 'voice_index' in config.py\n")
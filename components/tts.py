"""
components/tts.py — Text-to-Speech Component
============================================
Uses pyttsx3 with Windows SAPI5 (built-in Windows speech engine).

Why pyttsx3?
  - 100% offline — no model downloads required
  - Uses zero GPU memory
  - Tiny CPU footprint
  - Works immediately on any Windows machine

The trade-off: it sounds more robotic than neural TTS.
Week 2+ you can swap this for Coqui-TTS or Kokoro for better voice quality.
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
            idx = min(voice_index, len(voices) - 1)
            self.engine.setProperty("voice", voices[idx].id)
            print(f"[TTS] Using voice [{idx}]: {voices[idx].name} ✓")
        else:
            print("[TTS] ⚠  No voices found. Check Windows speech settings.")

    # ── Speaking ─────────────────────────────────────────────

    def speak(self, text: str) -> float:
        """
        Convert text to speech and play it through speakers.
        This call BLOCKS until speaking is finished.
        Returns how long speaking took in seconds.
        """
        if not text:
            return 0.0

        start = time.time()
        self.engine.say(text)
        self.engine.runAndWait()        # blocks here until audio finishes
        return time.time() - start

    # ── Utility ──────────────────────────────────────────────

    def list_voices(self):
        """Print all available Windows TTS voices. Use this to pick one."""
        voices = self.engine.getProperty("voices")
        print(f"\n[TTS] Found {len(voices)} available voice(s):")
        for i, voice in enumerate(voices):
            print(f"  [{i}] {voice.name}")
            print(f"       {voice.id}")
        print("\nTo change voice: set 'voice_index' in config.py\n")
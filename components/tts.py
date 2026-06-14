"""
components/tts.py — Text-to-Speech Component (Week 2: Piper Binary)
====================================================================
Uses piper.exe directly via subprocess — bypasses all Python package
compatibility issues on Windows.

How it works:
  1. Text is piped into piper.exe as stdin
  2. piper.exe outputs raw PCM audio bytes to stdout
  3. PyAudio plays the raw bytes through speakers

Why subprocess instead of the Python piper package?
  - piper-phonemize (required by pip piper-tts) has no Windows wheels
  - The OHF fork (1.4.2) has an incompatible API
  - The binary approach works identically on all platforms
"""

import io
import subprocess
import time
import wave

import pyaudio


class TextToSpeech:
    def __init__(self, config: dict):
        self.config = config
        self._verify_setup()

    def _verify_setup(self):
        """Check piper.exe and model file exist before first use."""
        import os
        exe   = self.config["piper_exe"]
        model = self.config["model_path"]

        if not os.path.exists(exe):
            print(f"[TTS] ❌ piper.exe not found at: {exe}")
            print("[TTS]    Download from: https://github.com/rhasspy/piper/releases/latest")
        elif not os.path.exists(model):
            print(f"[TTS] ❌ Voice model not found at: {model}")
            print("[TTS]    Download en_US-lessac-medium.onnx from HuggingFace")
        else:
            print("[TTS] Piper binary + voice model ready ✓")

    def speak(self, text: str) -> float:
        """
        Synthesize text to speech and play it.
        Returns time taken in seconds.
        """
        if not text:
            return 0.0

        start = time.time()

        # ── Step 1: Run piper.exe ─────────────────────────────
        # Pipe text in → get raw PCM int16 audio bytes out
        result = subprocess.run(
            [
                self.config["piper_exe"],
                "--model",       self.config["model_path"],
                "--output-raw",  # raw PCM bytes on stdout, no wav header
            ],
            input=text.encode("utf-8"),
            capture_output=True,
        )

        if result.returncode != 0:
            print(f"[TTS] ❌ Piper error: {result.stderr.decode()}")
            return 0.0

        raw_audio   = result.stdout
        sample_rate = self.config.get("sample_rate", 22050)

        # ── Step 2: Play audio via PyAudio ───────────────────
        p      = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            output=True,
        )
        stream.write(raw_audio)
        stream.stop_stream()
        stream.close()
        p.terminate()

        return time.time() - start
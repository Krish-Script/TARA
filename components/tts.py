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
from components.orchestrator import Orchestrator
from dataclasses import dataclass

@dataclass
class TTSResult:
    """Separate synthesis and playback timings for TTFS measurement."""
    synthesis_latency: float  # piper.exe processing time — contributes to TTFS
    playback_latency:  float  # audio playing time — irreducible, not part of TTFS

    @property
    def total_latency(self) -> float:
        return self.synthesis_latency + self.playback_latency

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
            print("[TTS]    Download Voice(en_US-lessac-medium.onnx) from HuggingFace")
        else:
            print("[TTS] Piper binary + voice model ready ✓")


    def speak(self, text: str) -> TTSResult:
        """
        Synthesize text and play audio.
        Returns TTSResult with synthesis and playback timed separately.

        Why separate?
        synthesis_latency → contributes to TTFS (dead silence the user feels)
        playback_latency  → TARA is speaking, user is listening, not dead time
        """
        if not text:
            return TTSResult(synthesis_latency=0.0, playback_latency=0.0)

        # ── Synthesis: piper.exe generates raw PCM ────────────
        t0 = time.time()
        result = subprocess.run(
            [
                self.config["piper_exe"],
                "--model",      self.config["model_path"],
                "--output-raw",
            ],
            input=text.encode("utf-8"),
            capture_output=True,
        )
        synthesis_latency = time.time() - t0

        if result.returncode != 0:
            print(f"[TTS] ❌ Piper error: {result.stderr.decode()}")
            return TTSResult(synthesis_latency=synthesis_latency, playback_latency=0.0)

        # ── Playback: PyAudio plays the raw PCM ───────────────
        t1 = time.time()
        sample_rate = self.config.get("sample_rate", 22050)
        p     = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            output=True,
        )
        stream.write(result.stdout)
        stream.stop_stream()
        stream.close()
        p.terminate()
        playback_latency = time.time() - t1

        return TTSResult(
            synthesis_latency=synthesis_latency,
            playback_latency=playback_latency,
        )
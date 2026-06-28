"""
components/tts.py — Text-to-Speech Component (Week 3 T6: Chunked Streaming)
=============================================================================
Uses piper.exe binary via subprocess + PyAudio for playback.

Week 3 upgrade: chunked streaming via producer-consumer threading.

Architecture:
    Thread A (Producer) — splits response into sentences, calls piper.exe
                          for each chunk, puts raw PCM audio into a Queue
    Thread B (Consumer) — reads audio chunks from Queue, plays each through
                          PyAudio as soon as it arrives

Why this reduces TTFS:
    Before: synthesize full response (~0.69s) → play full response
    After:  synthesize sentence 1 (~0.20s)   → start playing immediately
            synthesize sentence 2 while sentence 1 is already playing

The Queue is the synchronisation point. Consumer blocks on an empty queue
and unblocks the moment Producer puts the first chunk in. No busy-waiting,
no sleep() calls, no manual locks needed — Queue handles all of this.

Sentinel pattern: Producer puts None into the queue when done.
Consumer sees None and knows to stop. This is the standard way to signal
"no more data" in producer-consumer patterns.
"""

import os
import queue
import re
import subprocess
import threading
import time
from dataclasses import dataclass

import pyaudio


# ── Return type ──────────────────────────────────────────────

@dataclass
class TTSResult:
    """
    Separate synthesis and playback timings for TTFS measurement.

    synthesis_latency — time for first sentence chunk to be ready.
                        This is TARA's contribution to TTFS (dead silence).
    playback_latency  — time audio was playing through speakers.
                        This is TARA speaking — not dead silence.
    total_latency     — wall clock from speak() call to return.
    chunks            — number of sentence chunks processed.
    """
    synthesis_latency: float
    playback_latency:  float
    total_latency:     float
    chunks:            int

    @property
    def ttfs_component(self) -> float:
        """The part of TTFS this component contributes (synthesis only)."""
        return self.synthesis_latency


# ── Component ────────────────────────────────────────────────

class TextToSpeech:

    def __init__(self, config: dict):
        self.config = config
        self._verify_setup()

    def _verify_setup(self):
        exe   = self.config.get("piper_exe",  "")
        model = self.config.get("model_path", "")

        if not os.path.exists(exe):
            print(f"[TTS] ❌ piper.exe not found: {exe}")
            print("[TTS]    Download from: https://github.com/rhasspy/piper/releases/latest")
        elif not os.path.exists(model):
            print(f"[TTS] ❌ Voice model not found: {model}")
        else:
            print("[TTS] Piper binary + voice model ready ✓")

    # ── Public API ───────────────────────────────────────────

    def speak(self, text: str) -> TTSResult:
        """
        Synthesize and play text using chunked streaming.

        Splits text at sentence boundaries, starts playing the first
        chunk as soon as it is synthesised, then synthesises subsequent
        chunks in parallel with playback of earlier chunks.

        Returns TTSResult. synthesis_latency = first-chunk time (TTFS).
        """
        if not text or not text.strip():
            return TTSResult(0.0, 0.0, 0.0, 0)

        text = self._preprocess_for_tts(text)
        sentences = self._split_sentences(text)
        if len(sentences) == 1:
            return self._speak_sequential(sentences[0])
        
        return self._speak_chunked(sentences)
    
    # ── TTS Preprocessing ─────────────────────────────────────

    _TTS_REPLACEMENTS = [
    ("VRAM", "V Ram"),
    ("RAM",  "Ram"),
    ]

    def _preprocess_for_tts(self, text: str) -> str:
        """
        Convert acronyms to Piper-friendly pronunciation form.
        Piper reads ALL CAPS as individual letters.
        RAM → Ram (word), VRAM → V Ram (natural spoken form).
        CPU/GPU kept as-is — spelling out letters is correct for those.
        """
        for original, pronunciation in self._TTS_REPLACEMENTS:
            text = text.replace(original, pronunciation)
        return text
    
    def _speak_sequential(self, text: str) -> TTSResult:
        """
        Single-chunk path — no threading overhead.
        Used when the response is one sentence.
        """
        t0    = time.time()
        audio = self._synthesize_chunk(text)
        synthesis_latency = time.time() - t0

        if audio is None:
            return TTSResult(synthesis_latency, 0.0, synthesis_latency, 1)

        t1 = time.time()
        p      = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.config.get("sample_rate", 22050),
            output=True,
        )
        stream.write(audio)
        stream.stop_stream()
        stream.close()
        p.terminate()
        playback_latency = time.time() - t1

        return TTSResult(
            synthesis_latency = synthesis_latency,
            playback_latency  = playback_latency,
            total_latency     = synthesis_latency + playback_latency,
            chunks            = 1,
        )

    # ── Sentence splitting ───────────────────────────────────

    def _split_sentences(self, text: str) -> list[str]:
        """
        Split text into sentence-level chunks.

        Splits after . ! ? followed by whitespace.
        Filters fragments shorter than 3 characters.
        Falls back to the full text as a single chunk if no
        boundaries are found (e.g. a single short sentence).
        """
        parts     = re.split(r'(?<=[.!?])\s+', text.strip())
        sentences = [s.strip() for s in parts if len(s.strip()) > 2]
        return sentences if sentences else [text.strip()]

    # ── Synthesis ────────────────────────────────────────────

    def _synthesize_chunk(self, text: str) -> bytes | None:
        """
        Call piper.exe for one sentence chunk.
        Returns raw PCM int16 bytes, or None on error.
        """
        result = subprocess.run(
            [
                self.config["piper_exe"],
                "--model",      self.config["model_path"],
                "--output-raw",
            ],
            input=text.encode("utf-8"),
            capture_output=True,
        )
        if result.returncode != 0:
            print(f"[TTS] ❌ Piper error: {result.stderr.decode()}")
            return None
        return result.stdout

    # ── Producer-Consumer ────────────────────────────────────

    def _speak_chunked(self, sentences: list[str]) -> TTSResult:
        """
        Producer-consumer streaming TTS.

        Producer (Thread A): synthesises each sentence, puts bytes in queue.
        Consumer (Thread B): plays chunks from queue as they arrive.

        Sentinel: Producer puts None when done. Consumer stops on None.
        """
        audio_queue: "queue.Queue[bytes | None]" = queue.Queue()

        # Shared state written by producer, read after join
        first_synthesis_latency = [0.0]
        synthesis_error         = [False]

        # ── Producer ─────────────────────────────────────────
        def producer():
            for i, sentence in enumerate(sentences):
                t0    = time.time()
                audio = self._synthesize_chunk(sentence)
                elapsed = time.time() - t0

                if i == 0:
                    # Record first-chunk time — this is the TTFS component
                    first_synthesis_latency[0] = elapsed

                if audio is None:
                    synthesis_error[0] = True
                    break

                audio_queue.put(audio)

            audio_queue.put(None)   # sentinel — tells consumer to stop

        # ── Consumer ─────────────────────────────────────────
        playback_durations: list[float] = []

        def consumer():
            p      = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.config.get("sample_rate", 22050),
                output=True,
            )

            while True:
                chunk = audio_queue.get()   # blocks until Producer puts something
                if chunk is None:           # sentinel received — done
                    break

                t0 = time.time()
                stream.write(chunk)
                playback_durations.append(time.time() - t0)

            stream.stop_stream()
            stream.close()
            p.terminate()

        # ── Run both threads ──────────────────────────────────
        t_wall_start = time.time()

        producer_thread = threading.Thread(target=producer, daemon=True)
        consumer_thread = threading.Thread(target=consumer, daemon=True)

        producer_thread.start()
        consumer_thread.start()

        producer_thread.join()
        consumer_thread.join()

        total_latency    = time.time() - t_wall_start
        playback_latency = sum(playback_durations)

        return TTSResult(
            synthesis_latency = first_synthesis_latency[0],
            playback_latency  = playback_latency,
            total_latency     = total_latency,
            chunks            = len(sentences),
        )
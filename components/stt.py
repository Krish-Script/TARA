"""
components/stt.py — Speech-to-Text Component
=============================================
Uses faster-whisper (optimised version of OpenAI Whisper) on CPU.
"""

import re
import os
import time
import wave

import numpy as np
import pyaudio
from faster_whisper import WhisperModel


class SpeechToText:
    def __init__(self, config: dict):
        self.config = config
        self.model = None
        self._load_model()

    # ── Model Loading ────────────────────────────────────────

    def _load_model(self):
        """Load Whisper into memory."""
        print("[STT] Loading Whisper model...")
        self.model = WhisperModel(
            model_size_or_path=self.config["model_size"],
            device=self.config["device"],          # "cpu"
            compute_type=self.config["compute_type"],  # "int8"
        )
        print("[STT] Whisper ready ✓")

    # ── Audio Recording ──────────────────────────────────────

    def record_audio(self) -> str | None:
        """
        Record microphone audio until silence is detected.
        Returns the path to a saved .wav file, or None if nothing was heard.

        How silence detection works:
          1. Measure the average loudness (amplitude) of each audio chunk.
          2. Once speaking starts (amplitude > threshold), start counting
             consecutive quiet chunks.
          3. When quiet chunks exceed silence_duration, stop recording.
        """
        sample_rate       = self.config.get("sample_rate",       16000)
        chunk_size        = self.config.get("chunk_size",         1024)
        silence_threshold = self.config.get("silence_threshold",  300)
        silence_duration  = self.config.get("silence_duration",   1.8)
        max_duration      = self.config.get("max_duration",       30)

        audio_interface = pyaudio.PyAudio()
        stream = audio_interface.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            input=True,
            frames_per_buffer=chunk_size,
        )

        print("[STT] 🎤 Listening... speak now!")

        frames = []
        speaking_started   = False
        silent_chunk_count = 0

        # How many consecutive silent chunks before we stop?
        chunks_per_sec        = sample_rate / chunk_size
        silent_chunks_needed  = int(silence_duration * chunks_per_sec)
        max_chunks            = int(max_duration      * chunks_per_sec)

        for _ in range(max_chunks):
            data = stream.read(chunk_size, exception_on_overflow=False)
            frames.append(data)

            # Calculate loudness of this chunk
            audio_array = np.frombuffer(data, dtype=np.int16)
            amplitude   = float(np.abs(audio_array).mean())

            if amplitude > silence_threshold:
                speaking_started   = True
                silent_chunk_count = 0          # reset silence counter
            elif speaking_started:
                silent_chunk_count += 1
                if silent_chunk_count >= silent_chunks_needed:
                    break                       # enough silence → stop

        stream.stop_stream()
        stream.close()
        audio_interface.terminate()

        if not speaking_started:
            print("[STT] No speech detected.")
            return None

        # Write recorded frames to a temporary WAV file
        temp_path = "temp_recording.wav"
        with wave.open(temp_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(audio_interface.get_sample_size(pyaudio.paInt16))
            wf.setframerate(sample_rate)
            wf.writeframes(b"".join(frames))

        return temp_path

    # ── STT Post-Recognition Corrections ────────────────────────

    _STT_CORRECTIONS: dict[str, str] = {
        r"\bkrishna\b": "krishnendu",
        r"\bTara\b": "TARA",
        r"\btara\b": "TARA",
    }

    # ── Transcription ────────────────────────────────────────

    def transcribe(self, audio_path: str) -> tuple[str, float]:
        """
        Transcribe a .wav file to text.
        Returns (transcribed_text, latency_seconds).
        """
        start = time.time()

        segments, _ = self.model.transcribe(  # type: ignore
            audio_path,
            language=self.config.get("language", "en"),
            beam_size=self.config.get("beam_size", 5),
            vad_filter=True,   # skip truly silent portions automatically
        )

        # Concatenate all segments into one clean string
        text    = " ".join(seg.text for seg in segments).strip()
        latency = time.time() - start

        # Clean up temp file
        if os.path.exists(audio_path):
            os.remove(audio_path)

        text = self._apply_corrections(text)

        return text, latency

    # ── Convenience Method ───────────────────────────────────

    def listen_and_transcribe(self) -> tuple[str | None, float]:
        """
        Record + transcribe in one call.
        Returns (text, latency) or (None, 0.0) if nothing was heard.
        """
        audio_path = self.record_audio()
        if audio_path is None:
            return None, 0.0
        return self.transcribe(audio_path)

    # ── STT corrections ───────────────────────────────────

    def _apply_corrections(self, text: str) -> str:
        result = text
        for pattern, replacement in self._STT_CORRECTIONS.items():
            if re.search(pattern, result, flags=re.IGNORECASE):
                result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
                print(f"[STT] Correction applied: '{pattern}' → '{replacement}'")
        return result
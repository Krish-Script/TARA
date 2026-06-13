# ============================================================
# config.py — ARIA Central Configuration
# Change settings here without touching any other file.
# ============================================================

# ── Speech-to-Text (Whisper) ─────────────────────────────────
STT_CONFIG = {
    "model_size":   "base",   # tiny=fastest, base=best balance, small=most accurate
    "device":       "cpu",    # ALWAYS cpu — saves 4GB VRAM entirely for LLM
    "compute_type": "int8",   # int8 = faster CPU math, smaller memory footprint
    "language":     "en",     # transcription language
    "beam_size":    5,        # higher = more accurate, slower
}

# ── Audio Recording ──────────────────────────────────────────
AUDIO_CONFIG = {
    "sample_rate":       16000,  # Whisper requires exactly 16 kHz
    "channels":          1,      # mono microphone input
    "chunk_size":        1024,   # audio buffer size in bytes
    "silence_threshold": 300,    # amplitude below this = silence
                                 # ↑ raise if too sensitive, lower if cuts off early
    "silence_duration":  1.8,    # seconds of silence before stopping
    "max_duration":      30,     # safety cap: stop after 30s no matter what
}

# ── Language Model (Ollama + LLaMA) ─────────────────────────
LLM_CONFIG = {
    "model": "llama3.2:3b",   # 3b = ~2.0 GB VRAM, safe for RTX 3050 4GB
                               # upgrade to llama3.2:7b in Week 2 if VRAM allows
    "system_prompt": (
        "You are TARA, a helpful voice assistant running entirely "
        "on the user's local device with no internet connection. "
        "Always respond in 2 to 3 sentences maximum. "
        "Never use markdown, bullet points, headers, or asterisks. "
        "Speak naturally as if talking, not writing. "
        "Be concise, warm, and conversational."
    ),
    "temperature": 0.7,   # 0=robotic/predictable, 1=creative/random
    "num_ctx":     2048,  # context window tokens — keep low to save VRAM
    "max_history": 10,    # max conversation turns to remember (each = 2 messages)
}

# ── Text-to-Speech (pyttsx3 / Windows SAPI5) ────────────────
TTS_CONFIG = {
    "rate":        175,   # words per minute (default 200, slower = clearer)
    "volume":      1.0,   # 0.0 to 1.0
    "voice_index": 1,     # 0 = David, 1 = Zira (current) — run tests/test_tts.py to list voices
}
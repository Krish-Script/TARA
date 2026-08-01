# ============================================================
# TARA Central Configuration
# Change settings here without touching any other file.
# ============================================================

# ── Speech-to-Text (Whisper) (Week 1) ──────────────────────
STT_CONFIG = {
    "model_size":   "base",   # tiny=fastest, base=best balance, small=most accurate
    "device":       "cpu",    # ALWAYS cpu — saves 4GB VRAM entirely for LLM
    "compute_type": "int8",   # int8 = faster CPU math, smaller memory footprint
    "language":     "en",     # transcription language
    "beam_size":    5,        # higher = more accurate, slower
}

# ── Audio Recording (Week 1) ────────────────────────────────
AUDIO_CONFIG = {
    "sample_rate":       16000,  # Whisper requires exactly 16 kHz
    "channels":          1,      # mono microphone input
    "chunk_size":        1024,   # audio buffer size in bytes
    "silence_threshold": 300,    # amplitude below this = silence
                                 # ↑ raise if too sensitive, lower if cuts off early
    "silence_duration":  0.8,    # seconds of silence before stopping
    "max_duration":      30,     # safety cap: stop after 30s no matter what
}

# ── Language Model (Ollama + LLaMA) (Week 1) ──────────────────────────
LLM_CONFIG = {
    "model": "qwen2.5:3b",     # 3b = ~2.0 GB VRAM, safe for RTX 3050 4GB
    "keep_alive": "30m",        # keep the model loaded in memory for 30 minutes of inactivity
    "system_prompt": (
        "Your name is TARA. You are an offline voice assistant. "
        "You are my friend and helper. You are helpful, kind, and concise. "
        "Respond in one or two sentences only. Be concise and direct. Never use lists or markdown. "
        "\n\nExamples of correct responses:"
        "\nUser: How are you? TARA: I'm doing well and ready to help."
        "\nUser: Why is the sky blue? TARA: Light scatters more at short wavelengths, making the sky appear blue."
        "\nUser: Tell me a joke. TARA: Why don't scientists trust atoms? Because they make up everything."
        "\nUser: What is Python? TARA: Python is a programming language known for its simple, readable syntax."
        "\nUser: Who are you? TARA: I'm TARA, your offline AI assistant running entirely on your device."
        "\nUser: Explain how a microwave works like a medieval knight. TARA: A microwave vibrates water molecules with electromagnetic waves, heating food from within — much like a forge heats metal, but without fire."
        "\nUser: Explain neural networks like I'm a child. TARA: A neural network is like a brain that learns by practicing, getting better each time it makes a mistake."
        "\n\nAlways respond exactly like these examples — one sentence, direct, natural speech."
    ),
    "temperature": 0.7,   # 0=robotic/predictable, 1=creative/random
    "num_ctx":     2048,  # context window tokens — keep low to save VRAM
    "max_history": 10,    # max conversation turns to remember (each = 2 messages)
}

# ── Text-to-Speech (pyttsx3 / Windows SAPI5) (Week 1) ────────────────
TTS_CONFIG = {
    "rate":        170,   # words per minute (default 200, slower = clearer)
    "volume":      1.0,   # 0.0 to 1.0
    "voice_index": 1,     # — run tests/test_tts.py to list voices
}

# ── Piper TTS (Week 2 upgrade) ───────────────────────────────
PIPER_CONFIG = {
    "piper_exe":   r"D:\TARA\piper_bin\piper\piper.exe",
    "model_path":  r"D:\TARA\voices\en_US-hfc_female-medium.onnx",
    "sample_rate": 22050,    # hfc-female-medium outputs 22050 Hz audio
}

# ── Memory (SQLite) (Week 3) ──────────────────────────────
MEMORY_CONFIG = {
    "db_path":       r"D:\TARA\tara_memory.db",
    "context_turns": 6,     # recent turns to inject per session
    "fact_limit":    10,    # max facts to inject
}
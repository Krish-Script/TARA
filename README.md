# TARA — Totally Autonomous Responsive Assistant

A fully offline, voice-controlled AI personal assistant running entirely on local hardware. No cloud APIs, no internet dependency, no data leaving the device.

**Hardware:** NVIDIA RTX 3050 Laptop (4GB VRAM) · Windows 11 · Python 3.11.7  
**Sprint:** Week 5 of 10 complete

---

## Current Capabilities

| Capability | Status | Example query |
|------------|--------|---------------|
| Voice input | ✅ | Speak naturally into microphone |
| Speech transcription | ✅ | faster-whisper base, CPU, int8 |
| Conversational AI | ✅ | "Tell me about black holes" |
| Cross-session memory | ✅ | "Remember that my name is Krishnendu" |
| Fact recall | ✅ | "What do you remember about me?" |
| Time and date | ✅ | "What time is it?" |
| CPU monitoring | ✅ | "What's my CPU usage?" |
| RAM monitoring | ✅ | "How much RAM am I using?" |
| Disk monitoring | ✅ | "How much storage is left?" |
| Battery monitoring | ✅ | "What's my battery level?" |
| VRAM monitoring | ✅ | "How much VRAM am I using?" |
| GPU temperature | ✅ | "What's the GPU temperature?" |
| System uptime | ✅ | "How long has my system been running?" |
| Offline TTS | ✅ | Natural voice via Piper hfc_female |
| **File management** | **❌ Not built** | Stated requirement — Week 6 |
| **Information retrieval** | **❌ Not built** | Stated requirement — Week 6 |

---

## Pipeline Architecture

```
Your Voice
    ↓
[STT] faster-whisper (CPU, int8)
    ↓ 0.59s avg
[STT Corrections] regex word-boundary substitutions
    ↓
[Orchestrator]
    ↓
    ├── Command Registry (memory commands, exit)
    │
    └── _run_pipeline()
            ↓
        Stage 2: Intent Detection (<1ms, keyword routing)
            ├── TIME_QUERY   ──→ TimeTool
            ├── SYSTEM_QUERY ──→ SystemMonitor
            └── CHAT
                    ↓
                Stage 1: Memory Context Retrieval (SQLite)
                    ↓
                Stage 5: LLM Generation (qwen2.5:3b, GPU)
                    ↓ 1.04s avg
        Stage 6: Response Delivery (Piper TTS, CPU)
            ↓ 0.66s synthesis avg
        Stage 7: Persistence (SQLite)
            ↓
Your Speakers
```

**TTFS (time-to-first-syllable):**
- Tool path: 1.25s avg
- Chat path: 2.30s avg

---

## Performance Baseline (Week 5)

| Component | Avg | Notes |
|-----------|-----|-------|
| STT (Whisper base, CPU) | 0.59s | int8 quantisation |
| Intent detection | <1ms | keyword matching |
| Tool execution | 0.002–0.101s | 0.1s for CPU (psutil interval) |
| LLM generation (qwen2.5:3b) | 1.04s | warm inference, GPU |
| TTS synthesis (Piper) | 0.66s | first chunk only |
| **TTFS — tool path** | **1.25s** | |
| **TTFS — chat path** | **2.30s** | |
| VRAM steady-state | ~2.2GB | 1.8GB headroom on 4GB card |

---

## Hardware Requirements

| Component | Minimum | Used in this project |
|-----------|---------|----------------------|
| GPU | Any NVIDIA with 4GB+ VRAM | RTX 3050 Laptop 4GB |
| RAM | 8GB | 16GB |
| OS | Windows 10/11 | Windows 11 |
| Python | 3.10+ | 3.11.7 |
| Storage | 5GB free | ~8GB used |

---

## Tech Stack

| Layer | Technology | Version |
|-------|------------|---------|
| STT | faster-whisper | ≥1.0.0 |
| LLM inference | Ollama + qwen2.5:3b | ≥0.4.0 |
| TTS | Piper TTS binary | rhasspy release |
| TTS voice | en_US-hfc_female-medium | rhasspy |
| Memory | SQLite (built-in) | — |
| System monitoring | psutil + pynvml | 7.2.2 / nvidia-ml-py |
| Audio I/O | PyAudio | — |
| Language | Python | 3.11.7 |

---

## Project Structure

```
D:\TARA\
├── main.py                        # Entry point — audio loop only
├── config.py                      # All runtime configuration
├── requirements.txt
├── components\
│   ├── stt.py                     # Speech-to-Text (Whisper)
│   ├── llm.py                     # LLM interface (Ollama)
│   ├── tts.py                     # TTS (Piper binary + PyAudio)
│   ├── memory.py                  # SQLite memory layer
│   ├── intent.py                  # Keyword intent router
│   └── orchestrator.py            # Pipeline coordinator
│       └── tools\
│           ├── registry.py        # Tool dispatcher + ToolResult
│           ├── time_tool.py       # Date and time
│           ├── system_monitor.py  # Hardware metrics
│           └── formatter.py       # Raw dict → spoken language
├── tests\
│   ├── test_stt.py
│   ├── test_llm.py
│   ├── test_tts.py
│   ├── test_piper.py
│   ├── test_benchmark.py          # Intent + tool pipeline validation
│   └── test_model_eval.py         # Model quality harness
├── docs\
│   ├── week1_report.md → week5_report.md
│   ├── model_evaluation.txt       # llama3.2:3b / phi3.5 / qwen2.5:3b scores
│   ├── research_notes.md
│   └── known_limitations.md
├── voices\                        # Piper voice models (gitignored)
├── piper_bin\                     # Piper binary (gitignored)
└── tara_memory.db                 # SQLite database (gitignored)
```

---

## Setup

```bash
# 1. Install Ollama from https://ollama.com/download
ollama pull qwen2.5:3b

# 2. Download Piper binary from https://github.com/rhasspy/piper/releases
# Extract to D:\TARA\piper_bin\

# 3. Download voice model from HuggingFace rhasspy/piper-voices
# en_US-hfc_female-medium.onnx + .onnx.json → D:\TARA\voices\

# 4. Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# 5. Install PyAudio (Windows)
pip install pyaudio

# 6. Install remaining dependencies
pip install -r requirements.txt

# 7. Run
python main.py
```

---

## Voice Commands

| Say | Effect |
|-----|--------|
| "Quit" / "Exit" / "Goodbye" | Stop TARA |
| "Clear memory" | Reset LLM conversation history |
| "Remember that [fact]" | Store fact permanently |
| "What do you remember about me?" | Recall stored facts |

---

## Known Limitations

See `docs/known_limitations.md` for full list. Key items:

- Creative and persona prompts produce responses longer than one sentence
- CPU temperature unavailable on Windows without third-party drivers
- STT correction for "krishna" → "krishnendu" fires on queries about Krishna the deity
- File management and information retrieval not yet implemented
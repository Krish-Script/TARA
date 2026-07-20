# TARA — Totally Autonomous Responsive Assistant

A fully offline, voice-controlled AI personal assistant running entirely on local hardware. No cloud APIs, no internet dependency, no data leaving the device.

**Hardware:** NVIDIA RTX 3050 Laptop (4GB VRAM) · Windows 11 · Python 3.11.7
**Sprint:** Week 6 of 10 complete 

---

## Current Capabilities

| Capability | Status | Example query |
|------------|--------|---------------|
| Voice input | ✅ | Speak naturally into microphone |
| Speech transcription | ✅ | faster-whisper base, CPU, int8 |
| Conversational AI | ✅ | "Tell me about black holes" |
| Cross-session memory | ✅ | "Remember that my name is Krishnendu" |
| Fact recall | ✅ | "What do you remember about me?" |
| System monitoring | ✅ | "What's my CPU usage?" / "How much VRAM?" |
| Time and date | ✅ | "What time is it?" |
| Offline TTS | ✅ | Natural voice via Piper hfc_female |
| **Calculation** | ✅ | "Calculate 15% of 340" |
| **File Management (Notes)** | ✅ | "Take a note, buy milk tomorrow" |
| **Information Retrieval** | ✅ | "What do you know about my flight?" |
| **File Reading** | ✅ | "Read the README file" |
| **Error Architecture** | ✅ | 3-Tier graceful degradation (No fatal crashes) |

---

## Pipeline Architecture

```text
Your Voice
    ↓
[STT] faster-whisper (CPU, int8)
    ↓ 0.72s avg
[STT Corrections] regex word-boundary substitutions
    ↓
[Orchestrator] & [ErrorManager]
    ↓
    ├── Command Registry (memory commands, exit)
    │
    └── _run_pipeline()
            ↓
        Stage 2: Intent Detection (<1ms, keyword routing)
            ├── SYSTEM_QUERY ──→ SystemMonitor
            ├── TIME_QUERY   ──→ TimeTool
            ├── CALCULATION  ──→ CalculatorTool (LLM normalization -> safe_eval)
            ├── NOTES_*      ──→ NotesTool (Create/Read/List/Search)
            ├── FILE_READ    ──→ FileReader (Path resolution -> LLM Summarization)
            ├── LOCAL_SEARCH ──→ LocalSearchTool (Hybrid SQLite + File extraction)
            └── CHAT
                    ↓
                Stage 1: Memory Context Retrieval (SQLite)
                    ↓
                Stage 5: LLM Generation (qwen2.5:3b, GPU)
                    ↓ 1.04s - 1.27s avg
        Stage 6: Response Delivery (Piper TTS, CPU)
            ↓ ~0.67s synthesis avg
        Stage 7: Persistence (SQLite)
            ↓
Your Speakers
```

---

## TTFS (time-to-first-syllable):
- Standard Tool path: ~1.37s avg
- LLM-Assisted Tool path: ~1.50s - 1.80s avg
- Chat path: ~2.90s avg

---

## Hardware Requirements

| Component | Minimum | Used in this project |
|-----------|---------|----------------------|
| GPU      | Any NVIDIA with 4GB+ VRAM | RTX 3050 Laptop 4GB |
| RAM      | 8GB     | 16GB                  |
| OS       | Windows 10/11 | Windows 11         |
| Python   | 3.10+   | 3.11.7                |
| Storage  | 5GB free| ~8GB used             |

---

## Tech Stack

| Layer | Technology | Version |
|-------|------------|---------|
| STT   | faster-whisper | ≥1.0.0 |
| LLM inference | Ollama + qwen2.5:3b | ≥0.4.0 |
| TTS   | Piper TTS binary | rhasspy release |
| TTS voice | en_US-hfc_female-medium | rhasspy |
| Memory | SQLite (built-in) | — |
| System monitoring | psutil + pynvml | 7.2.2 / nvidia-ml-py |
| Audio I/O | PyAudio | — |
| Language | Python | 3.11.7 |

---
## Project Structure
```text
D:\TARA\
├── main.py                        # Entry point — audio loop only
├── config.py                      # All runtime configuration
├── requirements.txt
├── components\
│   ├── stt.py                     
│   ├── llm.py                     
│   ├── tts.py                     
│   ├── memory.py                  # SQLite memory layer
│   ├── intent.py                  # 37-case intent routing dictionary
│   ├── error_manager.py           # 3-Tier graceful degradation architecture
│   └── orchestrator.py            # Pipeline coordinator
│       └── tools\
│           ├── registry.py        # Tool dispatcher + ToolResult
│           ├── time_tool.py       
│           ├── system_monitor.py  
│           ├── calculator_tool.py # Two-stage safe math evaluation
│           ├── notes_tool.py      # Local text file generation/management
│           ├── file_reader.py     # OS path resolution & LLM file summarization
│           ├── local_search.py    # Hybrid SQLite/file context retrieval
│           └── formatter.py       # Raw dict → spoken language
├── tests\
│   ├── test_benchmark.py          # 100% passing intent + tool pipeline validation
│   └── test_model_eval.py         # Automated model quality & adversarial harness
├── docs\
│   └── week1_report.md → week6_report.md
├── data\
│   └── notes\                     # TARA's generated text files
├── voices\                        # Piper voice models (gitignored)
├── piper_bin\                     # Piper binary (gitignored)
└── tara_memory.db                 # SQLite database (gitignored)
```
---

## Setup
```Bash
# 1. Install Ollama from [https://ollama.com/download](https://ollama.com/download)
ollama pull qwen2.5:3b

# 2. Download Piper binary from [https://github.com/rhasspy/piper/releases](https://github.com/rhasspy/piper/releases)
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

## Core Voice Commands
| Say | Effect |
|-----|--------|
| "Quit" / "Exit" / "Goodbye" | Stop TARA |
| "Clear memory" | Reset LLM conversation history |
| "Remember that [fact]" | Store fact permanently |
| "What do you remember about me?" | Recall stored facts |
| "Take a note [content]" | Saves a timestamped text file |
| "Read the [filename] file" | Auto-summarizes a local file |
| "What do you know about my [topic]?" | Hybrid search of local notes and memory |

---

## Known Limitations
See docs/known_limitations.md for full list. Key items:
- Creative and persona prompts produce responses longer than one sentence. (Documented in A2 Adversarial Harness).
- CPU temperature unavailable on Windows without third-party drivers.
- LLM-assisted tools (Calculator, File Reader) incur cold-start latency on the first invocation, resulting in TTFS > 1.50s.
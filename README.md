# TARA — Totally Autonomous Responsive Assistant

A fully offline, voice-controlled AI personal assistant running entirely on local hardware. No cloud APIs, no internet dependency, no data leaving the device.

**Hardware:** NVIDIA RTX 3050 Laptop (4GB VRAM) · Windows 11 · Python 3.11.7  
**Sprint:** Week 9 of 10 complete  
**Benchmark:** 70/70 (100%) intent + tool + compound routing accuracy  

---

## Current Capabilities

| Capability | Status | Example voice command |
|------------|--------|-----------------------|
| Voice input | ✅ | Speak naturally into microphone |
| Speech transcription | ✅ | faster-whisper base, CPU, int8 |
| Conversational AI | ✅ | "Tell me about black holes" |
| Cross-session memory | ✅ | "Remember that my name is Krishnendu" |
| Fact recall | ✅ | "What do you remember about me?" |
| System monitoring | ✅ | "What's my CPU usage?" / "How much VRAM?" |
| GPU temperature | ✅ | "What's the GPU temperature?" |
| Time and date | ✅ | "What time is it?" |
| Offline TTS | ✅ | Natural voice via Piper hfc_female |
| Arithmetic | ✅ | "Calculate 15 percent of 340" |
| Notes — create | ✅ | "Take a note, buy milk tomorrow" |
| Notes — read / list / search | ✅ | "What was my last note?" / "List my notes" |
| File reading + summarisation | ✅ | "Summarize the README file" |
| Local information retrieval | ✅ | "What do you know about my demonstration?" |
| Compound tool chains | ✅ | "How is my system doing?" |
| Session-end summary | ✅ | Spoken + saved on "Goodbye" |
| 3-tier error architecture | ✅ | No fatal crashes — graceful degradation per component |

---

## Pipeline Architecture

```text
Your Voice
    │
    ▼
[STT] faster-whisper (base, CPU, int8)                    ~0.70s avg
    │
    ▼
[STT Corrections] regex word-boundary substitutions       <1ms
    │
    ▼
[Orchestrator]
    │
    ├── Command Registry (exit, remember, recall)
    │       ↓ on "goodbye / quit / exit / bye"
    │   Session summary → speak → save to notes → stop
    │
    └── _run_pipeline()
            │
            ▼
        Stage 1: Memory Context (CHAT path only, SQLite)  <10ms
            │
            ▼
        Stage 1.5: CompoundRouter                         <1ms
            ├── "How is my system doing?" ──→ system_status_snapshot
            ├── "Take a note with my current CPU" ──→ note_with_system_data
            ├── "Note the time right now" ──→ timestamped_note
            └── [no match] → Stage 2
            │
            ▼
        Stage 2: Intent Detection (keyword routing)       <0.01ms
            ├── SYSTEM_QUERY  ──→ SystemMonitor (psutil + pynvml)
            ├── TIME_QUERY    ──→ TimeTool (datetime)
            ├── CALCULATION   ──→ CalculatorTool (LLM normalise → safe_eval)
            ├── NOTES_*       ──→ NotesTool (Create / Read / List / Search)
            ├── FILE_READ     ──→ FileReader (path resolve → LLM summarise)
            ├── LOCAL_SEARCH  ──→ LocalSearchTool (SQLite + filesystem)
            ├── MEMORY        ──→ MemoryStore (store user fact)
            └── CHAT          ──→ LLM Generation (qwen2.5:3b, GPU)
            │
            ▼
        Stage 6: Response Delivery (Piper TTS, CPU)       ~0.81s synthesis
            │
            ▼
        Stage 7: Persistence (SQLite)
            │
            ▼
    Your Speakers
```

---

## Performance (Week 9 — cold-boot benchmark, August 17 2026)

All logged TTFS values exclude the VAD silence window (0.8s). User-perceived TTFS = logged TTFS + 0.8s.

| Path | Logged TTFS | User-perceived TTFS | Target |
|------|------------|---------------------|--------|
| Tool path (no LLM) | avg 1.42s (1.17–1.53s) | ~2.0–2.3s | ≤1.50s ✅ |
| Compound chains | 1.45–1.85s | ~2.3–2.7s | ≤2.0s ✅ |
| LLM-assisted tool | 1.63–1.98s | ~2.4–2.8s | ≤2.0s ✅ |
| Chat path | floor 3.00s, avg 3.16s | ~3.8–4.0s | ≤4.0s ✅ |

**Benchmark:** 70/70 (100%) — intent accuracy 51/51, tool success 7/7, compound routing 12/12. Verified from cold boot (0MiB VRAM, no prior processes). Run date: Mon Aug 17 2026.  
**Hardware floor:** 3.00s logged (STT 0.70s + LLM 1.58s + TTS 0.72s). Cannot be reduced in software without streaming LLM output.  
**Intent classification latency:** <0.01ms (keyword matching, no model call).

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

```text
D:\TARA\
├── main.py                         # Entry point — audio loop only
├── config.py                       # All runtime configuration
├── setup.md                        # One-time setup checklist
├── requirements.txt
│
├── components\
│   ├── orchestrator.py             # Pipeline coordinator — 7 named stages
│   ├── compound_router.py          # Stage 1.5 — multi-step deterministic chains
│   ├── intent.py                   # Keyword intent routing — 51-case dictionary
│   ├── stt.py                      # faster-whisper STT + VAD + corrections
│   ├── llm.py                      # Ollama LLM interface
│   ├── tts.py                      # Piper TTS — chunked synthesis
│   ├── memory.py                   # SQLite memory layer
│   ├── error_manager.py            # 3-tier graceful degradation
│   └── tools\
│       ├── registry.py             # Tool dispatcher + ToolResult
│       ├── time_tool.py
│       ├── system_monitor.py       # psutil + pynvml — live hardware metrics
│       ├── calculator_tool.py      # Two-stage safe math evaluation
│       ├── notes_tool.py           # Local text file generation/management
│       ├── file_reader.py          # Path resolution + LLM summarisation
│       ├── local_search.py         # Hybrid SQLite/filesystem retrieval
│       └── formatter.py            # Raw dict → spoken language
│
├── tests\
│   ├── test_benchmark.py           # 70/70 intent + tool + compound routing
│   ├── test_model_eval.py          # Automated model quality harness
│   ├── test_llm.py
│   ├── test_stt.py
│   ├── test_tts.py
│   └── test_pipeline.py
│
├── docs\
│   ├── demo_script.md              # 10-query demo sequence + dry run log
│   ├── research_notes.md           # 9 research findings with evidence
│   ├── known_limitations.md        # Documented limitations with root causes
│   ├── robustness_test.md          # Adversarial test log — 15/15 pass
│   ├── roadmap.md
│   ├── model_evaluation.txt
│   └── week1_report.md → week8_report.md
│
├── data\
│   └── notes\                      # TARA's generated text files
│
├── logs\
│   └── errors.log                  # Component crash log
│
├── voices\                         # Piper voice models (gitignored)
├── piper_bin\                      # Piper binary (gitignored)
├── .venv\                          # Python virtual environment (gitignored)
└── tara_memory.db                  # SQLite database (gitignored)
```

---

## Setup

```bash
# 1. Install Ollama from https://ollama.com/download
ollama pull qwen2.5:3b

# 2. Download Piper binary from https://github.com/rhasspy/piper/releases
#    Extract to D:\TARA\piper_bin\

# 3. Download voice model from HuggingFace rhasspy/piper-voices
#    en_US-hfc_female-medium.onnx + .onnx.json → D:\TARA\voices\

# 4. Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# 5. Install PyAudio (Windows — must be installed separately)
pip install pyaudio

# 6. Install remaining dependencies
pip install -r requirements.txt

# 7. Run
python main.py
```

See `setup.md` for a full one-time setup checklist including Ollama verification and Piper binary path configuration.

---

## Core Voice Commands

| Say | Effect |
|-----|--------|
| "Quit" / "Exit" / "Goodbye" / "Bye" | Stop TARA — speaks session summary first |
| "Remember that [fact]" | Store fact permanently in SQLite |
| "What do you remember about me?" | Recall all stored facts |
| "Take a note [content]" | Save timestamped text file |
| "What was my last note?" | Read most recent note |
| "List my notes" | List all saved notes |
| "Find my note about [topic]" | Search notes by keyword |
| "Summarize the [filename] file" | Read and summarise a local file |
| "What do you know about my [topic]?" | Search notes and facts |
| "How is my system doing?" | CPU + RAM + disk snapshot |
| "What's my CPU / RAM / disk / VRAM?" | Individual hardware metric |
| "What's the GPU temperature?" | Live thermal reading via pynvml |
| "What time is it?" / "What's today's date?" | Time and date |
| "Calculate [expression]" | Arithmetic via safe_eval |

---

## Known Limitations

See `docs/known_limitations.md` for full entries with root causes. Key items:

- **VAD silence window:** All logged TTFS excludes 0.8s VAD window. User-perceived TTFS = logged TTFS + 0.8s. Prior weeks used 1.8s window (calibrated Week 8).
- **Chat path floor:** 3.00s minimum logged TTFS on this hardware. Hardware-determined and irreducible without streaming LLM output.
- **CPU temperature:** Unavailable on Windows without third-party sensor drivers. GPU temperature via pynvml works correctly.
- **Single-word queries:** Fall to CHAT — multi-word trigger phrases required for tool routing. Coherent responses produced but tool routing not attempted.
- **Pattern specificity tradeoff:** "What's my memory?" routes to CHAT — "memory" without "usage" suffix does not trigger SYSTEM_QUERY. Intentional design to prevent false positives on conversational memory references.

---

## Research Findings

Ten findings documented in `docs/research_notes.md`:

1. Intent-routed tool bypass — 58% TTFS reduction vs chat path (1.25s vs 3.00s)
2. Response length as dominant TTFS lever on 4GB VRAM hardware
3. LLM hallucination of hardware metrics is systematic and confident
4. [Superseded — see Finding 5]
5. Dual memory injection as a latency anti-pattern
6. Context-TTFS tradeoff is hardware-determined and irreducible
7. Compound tool chains as deterministic agentic behaviour
8. Keyword routing pattern specificity as an irreducible coverage tradeoff
9. keep_alive state stability under rapid succession queries
10. VAD Configuration as a User-Perceived Latency Lever
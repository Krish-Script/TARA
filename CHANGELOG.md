# Changelog

All notable changes to **TARA (Totally Autonomous Responsive Assistant)** are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)  
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

## [Unreleased]

### Planned — Week 3 remaining
- Chunked TTS streaming (T6) — first sentence chunk plays while remainder generates

### Planned — Week 4
- Intent detection layer
- Tool execution framework
- System monitoring tool (psutil)
- Basic file management tool

---

## [0.4.1] - 2026-06-20

### Added
- `TTSResult` dataclass in `components/tts.py` — splits TTS timing into `synthesis_latency` and `playback_latency`
- TTFS (time-to-first-syllable) tracking in `Orchestrator` — calculated as `STT + LLM + synthesis` per turn
- TTFS displayed per-turn in terminal output and as primary metric in session report
- `tts_synthesis` stat tracked separately from `tts` total in `Orchestrator.stats`

### Changed
- `tts.speak()` return type changed from `float` to `TTSResult` — callers access `.total_latency`, `.synthesis_latency`, `.playback_latency`
- Baseline report now leads with TTFS rather than total latency
- `_run_pipeline()` accepts `stt_latency` parameter to enable TTFS calculation

### Performance

| Metric | Value | Notes |
|--------|-------|-------|
| TTFS avg | 2.52s | STT 0.64s + LLM 1.19s + synthesis 0.69s |
| TTS synthesis avg | 0.69s | T6 target: <0.20s |
| TTS playback avg | 6.65s | Irreducible — scales with response length |
| Total avg | 8.48s | Includes playback |

---

## [0.4.0] - 2026-06-20

### Changed
- Extracted all pipeline logic from `main.py` into a dedicated `Orchestrator` class (`components/orchestrator.py`)
- `main.py` now owns only component initialization and the audio capture loop (~70 lines, down from ~130)
- Replaced `if/elif` command chain with a command registry pattern — adding new commands requires no structural changes
- Moved intent detection for memory commands from `MemoryStore` to `Orchestrator` — `MemoryStore` is now a pure storage layer

### Architecture
- `Orchestrator._build_command_registry()` — single location for all voice command registration
- `Orchestrator._run_pipeline()` — seven named pipeline stages with explicit placeholders for Week 4 (intent detection, tool execution) and Week 5 (RAG retrieval)
- `_say()` helper enforces print+speak consistency across all command handlers

---

## [0.3.0] - 2026-06-17

### Added
- SQLite-backed persistent memory system (`components/memory.py`)
- `conversations` table — stores every exchange with session ID, turn index, and timestamp
- `user_facts` table — stores permanent user-provided facts across all sessions
- `MemoryStore` class with WAL journal mode, connection-per-operation pattern, and upsert deduplication
- Session ID generation (`create_session_id()`)
- Memory context builder for LLM prompt injection
- Automatic conversation persistence after every pipeline turn
- Voice command: "Remember that [fact]" — extracts and stores user facts permanently
- Voice command: "What do you remember about me?" — recalls all stored facts aloud
- Voice command: "Clear memory" — resets LLM conversation history (stored facts preserved)
- `_say()` helper method — enforces print+speak consistency, preventing silent responses

### Fixed
- Cold start latency: `keep_alive="30m"` passed as top-level `ollama.chat()` parameter (previously placed inside `options` where Ollama silently ignores it). Model now stays loaded in VRAM for 30 minutes of inactivity
- Missing terminal output for all command branches (remember, recall, clear, goodbye)
- `response` variable scope bug in recall branch — response was spoken but never assigned, causing empty print

### Performance

| Metric | Week 2 | Week 3 | Change |
|--------|--------|--------|--------|
| STT avg | 0.59s | 0.62s | +0.03s |
| LLM avg | 1.05s | 1.04s | stable |
| TTS avg | 5.42s | 5.74s | +0.32s |
| Total avg | 7.06s | 7.35s | +0.29s |
| Cold start | ~7–80s | eliminated | ✅ |

The +0.29s increase reflects memory context injection cost — recent turns and user facts loaded into every LLM request.

---

## [0.2.0] - 2026-06-12

### Added
- Piper TTS integration via standalone binary (`piper.exe`) — bypasses Python package compatibility issues on Windows
- `en_US-hfc_female-medium` voice model (rhasspy, Hugging Face)
- Few-shot prompting — system prompt now demonstrates correct response format via examples rather than rules
- PyAudio-based raw PCM playback for Piper output

### Changed
- Replaced pyttsx3 (Windows SAPI5) with Piper TTS for noticeably more natural voice output
- System prompt restructured from instruction-rules to few-shot examples — more effective on llama3.2:3b

### Performance

| Component | Before (0.1.0) | After (0.2.0) | Change |
|-----------|----------------|---------------|--------|
| STT avg | 0.62s | 0.59s | -0.03s |
| LLM avg | 1.41s | 1.05s | -0.36s |
| TTS avg | 11.23s | 5.42s | -5.81s |
| **Total** | **13.27s** | **7.06s** | **-47%** |

TTS improvement came from two sources: Piper generates audio faster than pyttsx3 synthesised it, and shorter responses (from few-shot prompt) reduced audio duration.

---

## [0.1.0] - 2026-06-04

### Added
- Project structure and virtual environment setup
- Offline Speech-to-Text via faster-whisper (base model, int8, CPU)
- Local LLM inference via Ollama with llama3.2:3b (GPU)
- Offline Text-to-Speech via pyttsx3 (Windows SAPI5, Zira voice)
- End-to-end voice pipeline: microphone → STT → LLM → TTS → speaker
- Silence-detection based audio recording (PyAudio)
- Modular component architecture (stt.py, llm.py, tts.py)
- Isolated test scripts per component (tests/)
- Session performance baseline reporting

### Fixed
- pyttsx3 engine singleton bug — `_activeEngines.clear()` before each `init()` call forces a fresh COM object, resolving silent-after-first-call behaviour
- Assistant identity: system prompt corrected from ARIA to TARA after find-and-replace missed the prompt string

### Performance

| Component | Result |
|-----------|--------|
| STT avg latency | 0.70s |
| LLM warm inference | 0.68s |
| LLM cold start (disk→VRAM) | 80.82s |
| TTS avg (short phrases) | 4.95s |
| TTS avg (full responses) | 11.23s |
| Time-to-first-response | ~2.0s |
| VRAM steady-state | 2.2GB |

---

## Version History

| Version | Description | Sprint | Status |
|---------|-------------|--------|--------|
| 0.1.0 | Offline voice pipeline | Week 1 | ✅ Released |
| 0.2.0 | Piper TTS + few-shot prompting | Week 2 | ✅ Released |
| 0.3.0 | SQLite memory + cold start fix | Week 3 | ✅ Released |
| 0.4.0 | Orchestrator refactor | Week 3 | ✅ Released |
| 0.4.1 | TTFS instrumentation | Week 3 | ✅ Released |
| 0.5.0 | Chunked TTS streaming | Week 3 | 🔄 In Progress |
| 0.6.0 | Agentic tool framework | Week 4 | ⏳ Planned |

---

*Maintained by **Krishnendu Mandal** — TARA Project*
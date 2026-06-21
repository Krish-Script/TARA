# Changelog

All notable changes to **TARA (Totally Autonomous Responsive Assistant)** are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)  
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

## [Unreleased]

### Planned — Week 4
- Intent detection layer (Orchestrator Stage 2)
- Tool execution framework (Orchestrator Stage 3)
- System monitoring tool (psutil — CPU, RAM, battery by voice)
- Basic file management tool

---

## [0.5.0] - 2026-06-21

### Added
- `TTSResult` dataclass separating `synthesis_latency` from `playback_latency` — enables accurate TTFS measurement
- TTFS (time-to-first-syllable) as primary latency metric, replacing total pipeline latency
- Chunked TTS streaming via producer-consumer threading — splits responses at sentence boundaries, plays first chunk while synthesising subsequent chunks in parallel
- Sequential fallback in `TextToSpeech.speak()` — single-sentence responses bypass threading to avoid overhead cost with no parallelism benefit
- `tts_synthesis` and `ttfs` stat trackers in Orchestrator session stats
- TTFS summary block in baseline performance report

### Performance

| Metric | T5 Baseline | T6 Result (controlled) | Change |
|--------|-------------|------------------------|--------|
| TTFS | 2.52s | 2.46s | -0.06s |
| TTS synthesis | 0.69s | 0.65s | -0.04s |

### Technical Notes
- Threading overhead (~0.20s) exceeds parallelism benefit for single-sentence responses — sequential fallback is the correct path for TARA's current response pattern
- Multi-sentence chunking benefit deferred to Week 4 where tool responses produce longer structured output
- Fair benchmark comparison requires controlled test conditions — response length variation between sessions invalidates direct measurement comparison

---

## [0.4.0] - 2026-06-20

### Changed
- Extracted all pipeline logic from `main.py` into `Orchestrator` class (`components/orchestrator.py`)
- `main.py` reduced from ~130 to ~70 lines — now owns only component initialisation and the audio loop
- Replaced `if/elif` command chain with command registry pattern — `(condition, handler)` tuples evaluated in order
- Moved "remember" intent detection from `MemoryStore` to `Orchestrator` — `MemoryStore` is now a pure storage layer

### Architecture
- `_build_command_registry()` — single location for all voice command registration; adding a command requires one tuple and two methods only
- `_run_pipeline()` — seven named stages with explicit placeholders for Week 4 (intent detection, tool execution) and Week 5 (RAG retrieval)
- `_say()` helper enforces print+speak consistency across all command handlers

---

## [0.3.0] - 2026-06-17

### Added
- SQLite-backed persistent memory system (`components/memory.py`)
- `conversations` table — session ID, turn index, timestamp, user message, assistant response
- `user_facts` table — permanent user-provided facts, persists across all sessions
- `MemoryStore` class with WAL journal mode, upsert deduplication, connection-per-operation thread safety
- Session ID generation (`create_session_id()`)
- Memory context builder for LLM prompt injection (few-shot format)
- Automatic conversation persistence after every pipeline turn
- Voice command: "Remember that [fact]" — extracts and stores permanently
- Voice command: "What do you remember about me?" — recalls all stored facts aloud
- Voice command: "Clear memory" — resets LLM conversation history (facts preserved)
- `_say()` helper method — enforces print+speak consistency, making silent responses architecturally impossible

### Fixed
- Cold start latency: `keep_alive="30m"` passed as **top-level** `ollama.chat()` parameter (placing inside `options` silently ignored by Ollama). Model stays in VRAM for 30 minutes of inactivity
- Missing terminal output for all command branches (remember, recall, clear, goodbye)
- `response` variable scope bug in recall branch — response was spoken but never assigned, causing empty print output

### Performance

| Metric | Week 2 | Week 3 | Change |
|--------|--------|--------|--------|
| STT avg | 0.59s | 0.62s | +0.03s |
| LLM avg | 1.05s | 1.04s | stable |
| TTS avg | 5.42s | 5.74s | +0.32s |
| Total avg | 7.06s | 7.35s | +0.29s |
| Cold start | ~7–80s | eliminated | ✅ |

The +0.29s increase is the cost of memory context injection on every LLM request.

---

## [0.2.0] - 2026-06-12

### Added
- Piper TTS integration via standalone `piper.exe` binary — bypasses Python package compatibility issues on Windows (both `piper-tts==1.4.2` OHF fork and rhasspy `1.1.x` failed; binary approach is stable)
- `en_US-hfc_female-medium` voice model (rhasspy, Hugging Face)
- Few-shot prompting — system prompt demonstrates correct response format via examples
- PyAudio-based raw PCM playback pipeline for Piper output

### Changed
- Replaced pyttsx3 (Windows SAPI5) with Piper TTS
- System prompt restructured from instruction-rules to few-shot examples

### Performance

| Component | 0.1.0 | 0.2.0 | Change |
|-----------|-------|-------|--------|
| STT avg | 0.62s | 0.59s | -0.03s |
| LLM avg | 1.41s | 1.05s | -0.36s |
| TTS avg | 11.23s | 5.42s | -5.81s |
| **Total** | **13.27s** | **7.06s** | **-47%** |

TTS improvement from two sources: Piper generates audio faster than pyttsx3, and shorter responses from few-shot prompt reduce audio duration.

---

## [0.1.0] - 2026-06-04

### Added
- Project structure and virtual environment setup
- Offline Speech-to-Text via faster-whisper (base model, int8, CPU)
- Local LLM inference via Ollama with llama3.2:3b (GPU)
- Offline Text-to-Speech via pyttsx3 (Windows SAPI5, Zira voice)
- End-to-end voice pipeline: microphone → STT → LLM → TTS → speaker
- Silence-detection audio recording (PyAudio)
- Modular component architecture (stt.py, llm.py, tts.py)
- Isolated per-component test scripts (tests/)
- Session performance baseline reporting

### Fixed
- pyttsx3 engine singleton bug — `_activeEngines.clear()` before each `init()` forces a fresh COM object, resolving silent-after-first-call behaviour on Windows
- Assistant identity: system prompt corrected from ARIA to TARA

### Performance

| Metric | Value |
|--------|-------|
| STT avg | 0.70s |
| LLM warm inference | 0.68s |
| LLM cold start (disk→VRAM) | 80.82s |
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
| 0.5.0 | TTFS measurement + chunked TTS | Week 3 | ✅ Released |
| 0.6.0 | Agentic tool framework | Week 4 | ⏳ Planned |

---

*Maintained by **Krishnendu Mandal** — TARA Project*
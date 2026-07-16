# Changelog

All notable changes to **TARA (Totally Autonomous Responsive Assistant)** are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)  
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

## [Unreleased]
 
### Planned — Week 6 (remaining)
- T4: Calculator Tool (sandboxed mathematical evaluation)
- T5: Evaluation Harness Upgrade (Adversarial Category A2)
- T6: IntentDetector Extension (regression benchmark)
- T7: Local Information Retrieval (notes and facts search)
---

## [0.17.0] - 2026-07-16

### Added
- `components/tools/file_reader.py` — New local file reading tool capable of cross-drive search, secure directory whitelisting, and automatic LLM-driven summarization for large text documents.
- `FILE_READ` intent classification added to `IntentDetector`.

### Changed
- `components/tools/formatter.py` — Expanded with a new `_format_file_read` template that intelligently branches its spoken response based on whether the document was read verbatim or summarized.
- `components/intent.py` — Refactored pattern ordering to safely isolate broad file-reading triggers from specific note-reading triggers.
- Path resolution logic dynamically handles Windows OS "OneDrive" folder hijacking without requiring hardcoded configuration files.

---
 
## [0.16.0] - 2026-07-12
 
### Fixed
- `components/tools/formatter.py` — `_format_time()` was producing "Sunday, Sunday, July 12, 2026" because `day_str` was manually prepended before `date_full`, which already includes the day name. Removed `day_str` from the return string and added `.strip()` to `date_full` to eliminate trailing space artifact
- `components/orchestrator.py` — Stage 1 debug print restored: `[Orchestrator] Stage 1: memory context building (CHAT path)` — confirms memory retrieval fires only on CHAT path turns
### Verified
- Stage 1 skip confirmed via 4-turn regression test:
  - Turn 1: TIME_QUERY — Stage 1 silent ✅
  - Turn 2: SYSTEM_QUERY — Stage 1 silent ✅
  - Turn 3: NOTES_CREATE — Stage 1 silent ✅
  - Turn 4: CHAT — Stage 1 fired ✅
- qwen2.5:3b warm inference latency confirmed: **0.78s** (corrects contaminated 9.47s cold-start measurement from Week 5 harness)
### Performance — Week 6 T1–T2 baseline
 
| Metric | Value | Notes |
|--------|-------|-------|
| TTFS (tool path) | 1.44s avg | Beats ≤1.50s target |
| TTFS (chat path) | 2.92s | Single data point — session variance |
| TTFS (LLM-assisted tool) | 1.28s | Notes create path — short extraction prompt |
| LLM warm latency | 0.78s | Confirmed via explicit warm-up call |
| Stage 1 on tool turns | never | Confirmed ✅ |
 
---
 
## [0.15.0] - 2026-07-11
 
### Added
- `components/tools/notes_tool.py` — persistent voice-to-file note management with four operations: create, read last, list, search
- `data/notes/` — local storage directory for timestamped note files (created on first use)
- Four new Intent classifications: `NOTES_CREATE`, `NOTES_READ`, `NOTES_LIST`, `NOTES_SEARCH`
- LLM-assisted tool path: `ToolRegistry` updated to accept `LanguageModel` instance — enables tools that require zero-shot NLP extraction before executing filesystem tasks
### Changed
- `components/tools/formatter.py` — four new templates for note metadata and content TTS delivery
- `components/intent.py` — "remember to" (NOTES_CREATE) ordered strictly above "remember" (MEMORY) to prevent routing collision
### Performance
- LLM-assisted TTFS (note create): **1.28s** — short extraction prompt keeps latency below chat-path baseline of 2.30s
- Note: 1.28s is specific to short extraction tasks; file summarization on 3000-char documents will be slower — do not treat 1.28s as a general LLM-assisted tool property
---
 
## [0.14.0] - 2026-07-10
 
### Added
- `components/error_manager.py` — centralised error management: `ToolExpectedError` class + `tara_errors` file logger (non-propagating, ERROR level)
- `logs/errors.log` — silent file logger for Tier 2 and Tier 3 faults; user-facing terminal never shows Python tracebacks after this version
- `logs/memory_fallback.txt` — SQLite failure fallback: conversation turns written locally rather than dropped
- Three-tier error architecture guaranteeing session survival:
  - **Tier 1 (Expected):** Tools raise `ToolExpectedError(message)`. Dispatcher converts to spoken response, session continues.
  - **Tier 2 (Unexpected):** Unhandled tool exceptions caught by `ToolRegistry`, full traceback logged to `logs/errors.log`, graceful spoken fallback delivered.
  - **Tier 3 (Component):** STT, TTS, and SQLite each wrapped individually. TTS crash → response printed to terminal with `[TTS FAULT - AUDIO FAILED]` tag. SQLite failure → turn appended to `logs/memory_fallback.txt`.
### Changed
- `components/tools/registry.py` — `dispatch()` refactored to route Tier 1 and Tier 2 errors via `ToolResult` dataclass, preventing pipeline breakage
- `main.py` — STT capture and main loop wrapped in Tier 3 protections
- `components/orchestrator.py` — Stage 3 (Tool TTS/SQLite), Stage 6 (Chat TTS), Stage 7 (Chat SQLite), and `_say()` helper all wrapped in Tier 3 protections
### Fixed
- Project objective gap closed: "robust error handling and recovery mechanisms" now implemented structurally. Replaced global catch-all with per-component recovery across all three pipeline tiers.
### Validation
- All three tiers deliberately triggered and confirmed:
  - Tier 1: `ToolExpectedError` spoken naturally, session continued
  - Tier 2: Injected `ValueError` logged silently to `logs/errors.log`, graceful fallback spoken
  - Tier 3: Injected `RuntimeError` in Piper TTS fell back to terminal print, session continued without dropping

---

## [0.13.0] - 2026-07-04

### Added
- `README.md` — project overview, capability table, 7-stage pipeline ASCII diagram, Week 5 performance baseline table, hardware requirements, full setup instructions, voice command reference
- `docs/known_limitations.md` — eight documented limitations with root cause, current behaviour, and fix status:
  - Creative/persona response length (accepted, Option B)
  - STT name correction side effect (krishna → deity queries)
  - CPU temperature unavailable on Windows
  - File management not implemented (stated requirement gap)
  - Information retrieval not implemented (stated requirement gap)
  - Chat path TTFS ~2.30s perceptible silence
  - VRAM misroute on ambiguous STT
  - Error handling: crash suppressor only, not recovery mechanism (stated requirement gap)
  - Chunked TTS overhead on single-sentence responses
- `docs/research_notes.md` — midpoint research analysis
  - Three confirmed findings: tool-path TTFS advantage (45%), response length as primary TTFS lever, systematic LLM hardware hallucination
  - Three unmeasured hypotheses: VRAM/format-compliance Pareto frontier, memory injection overhead at scale, STT domain vocabulary error rate

### Technical Notes
- Error handling gap explicitly documented: project objective requires "robust error handling and recovery mechanisms" — current implementation is a generic exception catcher, not a recovery system. Closing this gap is a Week 6–7 priority
- README capability table explicitly marks file management and information retrieval as not built — stated requirements, not stretch goals

---

## [0.12.1] - 2026-07-04

### Added
- `components/stt.py` — STT post-recognition correction layer
  - `_STT_CORRECTIONS` dict mapping regex patterns to replacements
  - `_apply_corrections()` method using `re.sub` with `\b` word boundaries — prevents substring matches (e.g. "krishna" inside "krishnendu")
  - Correction fires print to console — never silent
  - Called inside `transcribe()` before return

### Changed
- `components/stt.py` — `import re` added at module level

### Removed
- "so much" → "how much" correction removed: fires on grammatically correct English ("Why is there so much pollution?") — ambiguity is unfixable without context
- "so many" → "how many" removed for same reason

### Known Limitations
- `r"\bkrishna\b"` correction fires on queries about Krishna the deity (e.g. "Tell me about Krishna"). Acceptable risk for personal assistant use — documented, not hidden.

### Bug Fixed
- First implementation used `str.replace()` — caused mid-word substitution ("krishnendu" → "krishnendundu"). Fixed with `re.sub` + `\b` word boundary.

### Technical Notes
- STT correction dictionary entries must be observed misrecognitions only — each entry overrides Whisper output and can silently corrupt valid queries
- "so much"/"so many" removal is permanent — the ambiguity is not solvable at this layer without semantic context the corrector does not have

---

## [0.12.0] - 2026-07-03

### Changed
- `config.py` — system prompt restructured: closing instruction ("Always respond exactly like these examples") moved after all few-shot examples. Previously placed mid-block, causing final examples to appear outside the rule
- `components/tools/formatter.py` — CPU tool response framing: "CPU is at X percent" → "your CPU is at X percent". Previous attempt incorrectly placed this in the system prompt which is only injected on CHAT turns; tool path queries never reach the LLM

### Added
- Two persona/creative few-shot examples added to system prompt demonstrating one-sentence responses to character-based prompts

### Documented Limitation
- Creative, persona, and multi-part list prompts produce responses longer than one sentence despite the one-sentence constraint. Root cause: qwen2.5:3b cannot hold persona instruction and length constraint simultaneously — creative mode overrides length rule. Post-processing truncation rejected (Option B accepted): creativity not killed for rigid standardisation. Affects edge-case queries only; all factual, tool, memory, and time queries remain within constraint.

### Technical Notes
- System prompt examples are only effective for CHAT path — tool path (SYSTEM_QUERY, TIME_QUERY) bypasses LLM entirely; tool response formatting belongs in ToolFormatter, not the system prompt
- Prompt instruction placement is semantic: order in the context window affects which instructions the model treats as the active rule

---

## [0.11.0] - 2026-07-02

### Changed
- `config.py` — LLM model upgraded from `llama3.2:3b` to `qwen2.5:3b`

### Added
- `tests/test_model_eval.py` — model evaluation harness
  - Category A: 5-prompt format compliance test (manual grading)
  - Category B: 5-pair context recall test (automatic keyword scoring)
  - Category C: 5-prompt verbosity stress test (word count distribution)
  - Appends results to `docs/model_evaluation.txt` for cross-model comparison
- `docs/model_evaluation.txt` — evaluation results for all three models

### Model Evaluation Results

| Metric | llama3.2:3b | phi3.5 | qwen2.5:3b |
|--------|-------------|--------|------------|
| Category A — Format compliance | 5/5 | 2/5 | 5/5 |
| Category B — Context recall | 5/5 | 4/5 | 5/5 |
| Category C — Avg word count | 29.0w | 34.0w | 24.4w |
| Warm LLM latency | 0.93s | 2.80s | 0.85s |
| Chat TTFS | 2.50s | rejected | 2.30s |

### Decision rationale
- phi3.5 rejected: Category A 2/5 (fails upgrade rule); self-commentary appended to responses would be spoken aloud by Piper TTS
- qwen2.5:3b selected: matches baseline on all quality metrics; 16% shorter responses reduce TTS latency; keep_alive confirmed over 7.5-minute idle test; 22/22 intent benchmark unaffected

### Performance

| Metric | Before (llama3.2:3b) | After (qwen2.5:3b) | Change |
|--------|---------------------|---------------------|--------|
| LLM avg latency | 0.93s | 1.04s | +0.11s |
| Chat TTFS | 2.50s | 2.30s | **-0.20s** |
| Avg response length | 29.0w | 24.4w | -4.6w |

### Technical Notes
- LLM latency increased +0.11s but TTFS improved -0.20s — shorter responses reduce TTS synthesis time, more than offsetting the generation cost increase
- Scorer bug found in T3: Category B checked for digit "2" instead of word "two" — corrected before T4 evaluation
- Model override failure observed on llama3.2:3b (B[5]): model argued with injected VRAM fact, substituting its own prior — documented as known small-model limitation

---

## [0.10.0] - 2026-07-01

### Changed
- `components/orchestrator.py` — Stage 2 (Intent Detection) moved before Stage 1 (Memory Retrieval) in `_run_pipeline()`
  - Stage 1 (SQLite memory read) now only executes on CHAT intent — tool path queries no longer pay memory retrieval overhead
  - Stage 2 (keyword routing, 0ms) executes first on every turn
  - Memory context injection behaviour on CHAT path is unchanged

### Performance

| Metric | Before (0.9.0) | After (0.10.0) | Change |
|--------|----------------|----------------|--------|
| TTFS (chat path) | 2.49s | 2.26s | -0.23s |
| TTFS (tool path) | 1.59s | 1.17s | -0.42s |
| Stage 1 on tool turns | always | never | ✅ |

### Technical Notes
- Regression test confirmed: chat-path context injection unaffected after tool-path turns that skip Stage 1
- Memory recall ("What's my name?" after a CPU query) confirmed correct — cross-path memory integrity preserved

---

## [0.9.0] - 2026-06-28

### Fixed
- `components/tts.py` — Piper TTS pronunciation: "RAM" was spoken as "R-A-M" (individual letters) because Piper reads ALL CAPS as initials. Added `_preprocess_for_tts()` which replaces "RAM" → "Ram" and "VRAM" → "V Ram" before text reaches `piper.exe`. CPU and GPU intentionally unchanged — letter-by-letter is correct for those
- `components/tools/formatter.py` — `.capitalize()` replaced with `_cap_first()` throughout. `str.capitalize()` lowercases all characters after the first, turning "VRAM" into "Vram". `_cap_first()` uppercases only the first character, preserving acronym casing
- `components/intent.py` — SYSTEM_QUERY patterns extended with storage and CPU variants that were causing LLM misrouting:
  - Added: "storage", "how much storage", "storage left", "storage space", "free space"
  - Added: "cpu utilization", "cpu load", "what's my cpu", "processor usage"

### Changed
- `tests/test_benchmark.py` — three new test cases added covering the misrouted queries:
  - "What's the CPU utilization?" → SYSTEM_QUERY
  - "How much storage is left?" → SYSTEM_QUERY
  - "What's the CPU used?" → SYSTEM_QUERY
  - Benchmark score: 22/22 (100%)

### Performance
- Tool path TTFS: 1.59s this session (vs 1.37s Week 4) — session variance from higher STT latency, not regression. Benchmark-estimated TTFS remains 1.37s
- Intent accuracy: 22/22 (100%) after pattern extensions

### Technical Notes
- One LLM hallucination incidents during T1 testing confirmed pattern coverage is a safety constraint, not optional: LLM reported 83.5GB free / 1TB for storage (actual: 41GB / 512GB) - fabricated with no uncertainty signal
- TTS preprocessing order matters: VRAM replaced before RAM to prevent "VRAM" being processed by both rules

---

## [0.8.0] - 2026-06-25

### Added
- `tests/test_benchmark.py` — Week 4 validation suite
  - Section 1: 19-query intent classification test (expected vs actual, accuracy score)
  - Section 2: 7-tool pipeline test (ToolResult correctness, formatted output verification)
  - Section 3: latency benchmark (20-call intent timing, per-tool dispatch timing, TTFS estimate)
  - False positive detection with actionable fix suggestions

### Fixed
- Removed bare `"what time"` from TIME_QUERY patterns — was misclassifying "What time do trains run?" as TIME_QUERY. "What time is it?" still matches via `"what time is it"`
- Removed bare `"temperature"` from SYSTEM_QUERY patterns — was misclassifying "How is temperature measured?" as SYSTEM_QUERY. "What's the GPU temperature?" still matches via `"gpu temperature"`

### Performance — Final Week 4 Benchmark

| Metric | Result | Target |
|--------|--------|--------|
| Intent accuracy | 19/19 (100%) | 100% |
| Tool pipeline success | 7/7 (100%) | 100% |
| False positives | 0 | 0 |
| Intent classification latency | 0.00ms | <5ms |
| Tool TTFS estimate | 1.37s | ≤1.50s |
| Tool queries supported | 8 | ≥6 |

### Technical Notes
- False positives caused by bare trigger words matching as substrings of conversational queries — fixed by requiring specific multi-word phrases throughout intent patterns
- CPU tool latency ~100ms is expected: `psutil.cpu_percent(interval=0.1)` requires two samples separated by 0.1s to calculate delta usage
- Tool path TTFS (1.37s) vs chat path TTFS (2.50s) — 1.13s difference from bypassing LLM generation for deterministic queries

---

## [0.7.0] - 2026-06-24

### Added
- `components/tools/system_monitor.py` — SystemMonitor with 7 hardware metrics
  - CPU usage (`psutil.cpu_percent`, warm-up call in `__init__` discards always-zero first reading)
  - RAM (used/total GB, percent)
  - Disk (used/free GB, percent — C: drive)
  - Battery (percent, charging state, None guard for devices without sensor)
  - VRAM (used/total/free GB, GPU utilisation — via pynvml)
  - GPU temperature (pynvml — confirmed working on RTX 3050)
  - Uptime (hours and minutes since last boot)
- Thermal-aware operation: GPU temperature via pynvml, CPU temperature attempted via `psutil.sensors_temperatures()` with graceful "unavailable" fallback on Windows
- `hasattr(psutil, "sensors_temperatures")` guard — correct runtime behaviour on Windows and resolves Pylance false positive

### Changed
- `components/tools/registry.py` — SystemMonitor registered for SYSTEM_QUERY intent
- `components/tools/formatter.py` — `_format_system()` extended to handle all 7 metrics including temperature, uptime, battery availability flag, and VRAM unavailability flag
- `components/intent.py` — SYSTEM_QUERY patterns extended with "temperature", "gpu temp", "cpu temp", "thermal", "how hot", "gpu temperature", "cpu temperature"

### Fixed
- Temperature queries routing to LLM — "What's the GPU temperature?" was falling through to LLM which fabricated plausible but completely wrong temperature values. Added temperature trigger phrases to SYSTEM_QUERY pattern list

### Performance

| Metric | Value |
|--------|-------|
| TTFS (tool path avg) | 1.34–1.42s |
| Tool execution (system queries) | 0.000–0.004s |
| Tool execution (CPU query) | ~0.1s (psutil interval cost) |
| GPU temperature at idle | 48–53°C |
| VRAM with Ollama loaded | 2.37GB / 4.0GB |

### Technical Notes
- LLM hallucinated CPU temperature (85°C) and GPU temperature (78°C) when temperature queries fell through to chat path — confirmed that hardware queries must never route to LLM
- "VRAM usage" matches `ram usage` pattern in IntentDetector (substring match) but SystemMonitor.run() correctly dispatches to `_get_vram()` via full query inspection — correct behaviour, misleading log

---

## [0.6.0] - 2026-06-23

### Added
- `components/intent.py` — IntentDetector with keyword-pattern routing
  - Five Intent types: CHAT, TIME_QUERY, SYSTEM_QUERY, CALCULATION, MEMORY
  - `classify()` and `classify_with_confidence()` — latter returns matched phrase for logging
  - Specific multi-word phrase patterns only — avoids bare-keyword false positives ("ram usage" not "ram")
- `components/tools/registry.py` — ToolRegistry dispatcher and ToolResult dataclass
  - Maps `Intent → handler` with full error isolation — tool failures return graceful fallback, never crash pipeline
  - `ToolResult` standardises all tool output: `raw_output`, `formatted_output`, `latency`, `success`, `source`
- `components/tools/time_tool.py` — TimeTool returning structured datetime dict
- `components/tools/formatter.py` — ToolFormatter converting raw dicts to TTS-ready natural language
  - Template-based formatting: no markdown, spells out "gigabytes"/"percent", max two sentences
- `components/tools/__init__.py` — tools package initialiser

### Changed
- `components/orchestrator.py` — Stage 2 (Intent Detection) and Stage 3 (Tool Execution) now active
- `orchestrator.stats` — added `ttfs_tool` and `tool_latency` tracking
- `_print_baseline_report()` — split into chat path / tool path with separate TTFS lines

### Performance

| Metric | Week 3 | Week 4 T1 | Change |
|--------|--------|-----------|--------|
| TTFS (chat path) | 2.46s | 2.52s | stable |
| TTFS (tool path) | — | **1.17s** | new — beats ≤1.50s target |
| Tool execution latency | — | 0.000s | new (time tool) |
| Tool queries supported | 0 | 1 | +1 (time/date) |

### Technical Notes
- Keyword matching chosen over LLM intent classification: <5ms vs 0.8–1.2s latency, 100% vs ~85% accuracy on well-defined commands
- Tool path total time (7.03s) is not a meaningful speed comparison — TTS playback dominates and scales with response length regardless of path. TTFS (1.17s vs 2.52s chat) is the correct metric
- Week 3 Orchestrator refactor validated: Stage 2&3 wiring took under 30 minutes due to explicit placeholder comments

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
| LLM model warm-up (during startup) | ~8.5s |
| LLM cold start (disk→VRAM) (one-time) | 80.82s |
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
| 0.6.0 | Agentic tool framework | Week 4 | ✅ Released |
| 0.7.0 | System monitor + thermal-aware operation | Week 4 | ✅ Released |
| 0.8.0 | Benchmark suite + false positive fixes | Week 4 | ✅ Released |
| 0.9.0 | TTS pronunciation fix + intent pattern extension | Week 5 | ✅ Released |
| 0.10.0 | Stage ordering optimisation — memory skip on tool path | Week 5 | ✅ Released |
| 0.11.0 | Model upgrade to qwen2.5:3b (evaluation-based) | Week 5 | ✅ Released |
| 0.12.0 | Prompt restructure + formatter tool framing | Week 5 | ✅ Released |
| 0.12.1 | STT correction layer + substring bug fix | Week 5 | ✅ Released |
| 0.13.0 | Midpoint documentation — README, limitations, research notes | Week 5 | ✅ Released |
| 0.14.0 | 3-Tier error architecture | Week 6 | ✅ Released |
| 0.15.0 | Notes tool + file management | Week 6 | ✅ Released |
| 0.16.0 | Time formatter fix + Stage 1 verification | Week 6 | ✅ Released |
| 0.17.0 | File Reader & Auto-Summarization | Week 6 | ✅ Released |
---

*Maintained by **Krishnendu Mandal** — TARA Project*
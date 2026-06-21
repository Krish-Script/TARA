# TARA — Week 3 Report
## Memory & Context Sprint

**Sprint duration:** Week 3 of 10  
**Primary goal:** Transform TARA from a stateless voice assistant into a persistent conversational assistant using SQLite  
**Status:** ✅ Completed

---

## Sprint Summary

Week 3 focused on giving TARA memory — the ability to remember conversations across sessions and store facts the user explicitly provides. Before this sprint, every session started from zero. After it, TARA recalls previous exchanges, addresses the user by name, and maintains context across restarts.

Six tasks were completed this week: SQLite memory layer, LLM context injection, cold-start fix, Orchestrator class refactor, TTFS measurement instrumentation, and chunked TTS streaming architecture.

---

## Performance Baseline

| Metric | Week 2 | Week 3 (T5) | Week 3 (T6) | Change W2→W3 |
|--------|--------|-------------|-------------|--------------|
| STT avg | 0.59s | 0.63s | 0.58s | stable |
| LLM avg | 1.05s | 1.19s | 1.21s | +0.16s (memory context overhead) |
| TTS synthesis | — | 0.69s | 0.65s | measured for first time |
| TTS playback | — | — | 4.71s | irreducible |
| **TTFS (primary)** | — | **2.52s** | **2.46s** | **-0.06s** |
| Total avg | 7.06s | 7.35s | 6.51s | -0.55s |
| Cold start | ~7–80s | eliminated | eliminated | ✅ fixed |

TTFS (time-to-first-syllable) was introduced this week as the primary metric, replacing total pipeline latency. TTFS measures the silence the user experiences — the gap between finishing speaking and hearing TARA's first word. Total latency includes playback duration, which is TARA speaking and is not dead silence.

---

## What Was Built

### T1 — Cold Start Fix (`components/llm.py`)

The 80.82s cold start measured in Week 1 was resolved by passing `keep_alive="30m"` as a **top-level parameter** to `ollama.chat()`. Two attempts were required:

- **First attempt (failed):** placed inside `options` dict — Ollama silently ignores it there
- **Second attempt (working):** top-level parameter — model stays in VRAM for 30 minutes

Confirmed by running a 7.3-minute session with zero LLM latency spikes. The original 80s was a disk→VRAM load; subsequent loads are RAM→VRAM (~7s). With `keep_alive`, neither happens during a session.

### T2 — SQLite Memory Layer (`components/memory.py`)

A self-contained memory module with two tables:

**`conversations`** — stores every exchange with session ID, turn index, timestamp, user message, and assistant response.

**`user_facts`** — stores permanent user-provided facts. Persists across all sessions indefinitely.

Key design decisions:
- `fact_key` normalization prevents duplicate facts from different phrasings
- `ON CONFLICT DO UPDATE` upsert pattern for clean fact management
- WAL journal mode for better concurrent read performance
- Connection-per-operation pattern for thread safety

### T3 — Explicit Memory Commands

Three voice commands for direct memory interaction:

| Command | Behaviour |
|---------|-----------|
| "Remember that [fact]" | Extracts and stores permanently |
| "What do you remember about me?" | Recalls all stored facts aloud |
| "Clear memory" | Resets LLM conversation history (facts preserved) |

### T4 — Orchestrator Class Refactor (`components/orchestrator.py`)

All pipeline logic extracted from `main.py` into a dedicated `Orchestrator` class.

**Command registry pattern** — `(condition, handler)` tuples evaluated in order. Adding a new command requires adding one tuple and two methods. Nothing else changes.

**Staged pipeline with insertion points:**
```
Stage 1: Memory Context Retrieval      ← active
Stage 2: Intent Detection              [FUTURE — Week 4]
Stage 3: Tool Execution                [FUTURE — Week 4]
Stage 4: RAG Retrieval                 [FUTURE — Week 5]
Stage 5: LLM Generation                ← active
Stage 6: Response Delivery             ← active (chunked TTS)
Stage 7: Persistence                   ← active
```

**Single Responsibility fix on MemoryStore** — intent detection for "remember" commands moved from `MemoryStore` to `Orchestrator`. `MemoryStore` is now a pure storage layer.

`main.py` shrank from ~130 lines to ~70. It now only initializes components and runs the audio loop.

### T5 — TTFS Measurement

TTFS instrumentation added to the pipeline by separating TTS timing into two distinct measurements:

- **`synthesis_latency`** — time for piper.exe to generate audio (dead silence, contributes to TTFS)
- **`playback_latency`** — time audio plays through speakers (TARA is speaking, not dead time)

```python
@dataclass
class TTSResult:
    synthesis_latency: float  # TTFS component
    playback_latency:  float  # irreducible
    total_latency:     float
    chunks:            int
```

T5 baseline TTFS established: **2.52s** (STT 0.63s + LLM 1.19s + synthesis 0.69s).

### T6 — Chunked TTS Streaming

Producer-consumer threading architecture for sentence-level audio streaming.

**Architecture:**
```
Thread A (Producer): split text → synthesise chunk 1 → queue → synthesise chunk 2 → queue → sentinel
Thread B (Consumer): wait → play chunk 1 → wait → play chunk 2 → stop on sentinel
```

**Key finding:** threading overhead costs more than parallelism saves for single-sentence responses. A sequential fallback was added:

```python
def speak(self, text: str) -> TTSResult:
    sentences = self._split_sentences(text)
    if len(sentences) == 1:
        return self._speak_sequential(sentences[0])  # no overhead
    return self._speak_chunked(sentences)             # true parallelism
```

**T6 result (controlled test, same question types as T5):**
- TTFS: 2.46s (vs T5 baseline 2.52s, -0.06s improvement)
- TTS synthesis: 0.65s (vs 0.69s, -0.04s)

The threading benefit for multi-sentence responses is real but not demonstrated this week — TARA's few-shot prompt consistently produces single sentences. Week 4 tool responses will have longer, structured output that exercises the chunked path.

---

## Challenges Encountered

**1. `keep_alive` parameter placement (T1)**
Silent failure — Ollama ignored the parameter with no warning. Only detectable by waiting 5+ minutes and observing VRAM drop. Always verify configuration changes with observable, time-delayed evidence.

**2. Missing print statements in command branches (T3)**
All `continue` branches called `tts.speak()` but skipped `print()`. Fixed with `_say()` helper that enforces print+speak consistency at the design level, making it architecturally impossible to speak without printing.

**3. `response` variable scope bug (T3)**
The recall branch spoke the correct facts but never assigned them to `response`, then printed the empty default. Fixed alongside the `_say()` refactor.

**4. Threading overhead exceeds parallelism benefit for 1-chunk responses (T6)**
Initial T6 results showed TTFS regression (2.52s → 2.86s). Investigation revealed threading setup cost (~0.20s) exceeded any benefit for single-sentence responses. Sequential fallback restored expected performance. The lesson: always measure threading overhead against the workload before assuming concurrency helps.

**5. Unfair benchmark comparison (T6)**
First T6 comparison used longer responses than T5 baseline (20+ word sentences vs 7-word sentences), inflating synthesis time from 0.69s to 0.88s regardless of threading. Fair comparison requires controlled test conditions — same question types, similar response lengths.

---

## Architecture: Before and After Week 3

**Before:**
```
main.py → TARA class (init + pipeline + commands + stats + UI)
```

**After:**
```
main.py → TARA class (init + audio loop only)
    └── components/orchestrator.py → Orchestrator (pipeline + commands + stats)
    └── components/memory.py → MemoryStore (storage only)
    └── components/tts.py → TextToSpeech (chunked streaming + sequential fallback)
```

---

## Lessons Learned

- **Silent configuration failures need time-delayed verification.** `keep_alive` in the wrong place produced no error, only a behaviour difference 5 minutes later.
- **Architectural helpers prevent entire classes of bugs.** `_say()` makes it structurally impossible to speak without printing. Constraints beat code review.
- **Threading overhead is not free.** Concurrency only pays when there is real work to overlap. Single-chunk responses have nothing to parallelise — sequential is faster.
- **Benchmark conditions must be controlled.** Response length variation between T5 and T6 test sessions invalidated direct comparison. Controlled retests with matched inputs produced valid results.
- **Refactor before the complexity compounds.** The Orchestrator refactor was done before adding chunked TTS threading. Doing it after would have meant untangling pipeline logic and threading simultaneously.
- **Measure what changed, not just what was built.** TTFS as a metric only became meaningful because synthesis and playback were separated into `TTSResult`. You cannot optimise what you cannot measure.

---

## Sprint Outcome

✅ SQLite memory with cross-session recall  
✅ Explicit "remember / recall / clear" voice commands  
✅ Cold start eliminated (keep_alive top-level parameter)  
✅ Orchestrator refactor — command registry + staged pipeline  
✅ TTFS measurement infrastructure (TTSResult dataclass)  
✅ Chunked TTS architecture — producer-consumer threading + sequential fallback  
✅ TTFS baseline: 2.52s (T5) → 2.46s (T6 controlled test)  

---

## Week 4 Preview

**Theme: Agentic Tools**
Intent detection (Stage 2) and tool execution (Stage 3) pipeline stages are ready with placeholder comments. Week 4 fills them in: system monitoring via psutil, basic file operations, and the first structured tool-calling architecture.

The chunked TTS path (multi-sentence streaming) will see its first real workout in Week 4, where tool results produce longer, structured responses.
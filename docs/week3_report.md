# TARA — Week 3 Report
## Memory & Context Sprint

**Sprint duration:** Week 3 of 10  
**Primary goal:** Transform TARA from a stateless voice assistant into a persistent conversational assistant using SQLite  
**Status:** 🔄 In Progress (T5, T6 remaining)

---

## Sprint Summary

Week 3 focused on giving TARA memory — the ability to remember conversations across sessions and store facts the user explicitly provides. Before this sprint, every session started from zero. After it, TARA recalls previous exchanges, addresses the user by name, and maintains context across restarts.

Four components were built or changed this week: a SQLite memory layer, LLM context injection, a cold-start fix that had been unresolved since Week 1, and an Orchestrator class refactor that separated pipeline logic from startup infrastructure.

---

## Performance Baseline

| Metric | Week 2 | Week 3 | Change |
|--------|--------|--------|--------|
| STT avg latency | 0.59s | 0.62s | +0.03s (negligible) |
| LLM avg latency | 1.05s | 1.04s | stable |
| TTS avg latency | 5.42s | 5.74s | +0.32s (memory injection overhead) |
| Total avg latency | 7.06s | 7.35s | +0.29s |
| Cold start (first response) | ~7–80s | eliminated | ✅ fixed |

The +0.29s total increase is the cost of memory context injection — loading recent conversation turns and user facts into the LLM prompt on every request. This is an acceptable trade-off: cross-session memory for under 0.3s additional latency.

---

## What Was Built

### 1. SQLite Memory Layer (`components/memory.py`)

A self-contained memory module with two tables:

**`conversations`** — stores every exchange with session ID, turn index, timestamp, user message, and assistant response. Used to inject recent context into the LLM on each request.

**`user_facts`** — stores permanent user-provided facts (name, preferences, background). Persists across all sessions indefinitely.

Key design decisions:
- `fact_key` normalization before storage prevents duplicate facts from different phrasings
- `ON CONFLICT DO UPDATE` upsert pattern for clean fact management
- WAL journal mode for better concurrent read performance
- Connection-per-operation pattern for thread safety

### 2. LLM Context Injection (`components/llm.py`)

Memory context is injected into the system prompt using the same few-shot principle established in Week 2 — showing TARA past exchanges as examples rather than writing rules about "having access to previous context." Small models (llama3.2:3b) follow demonstrated patterns more reliably than instructions.

### 3. Voice Memory Commands

Three memory-specific voice commands added to the pipeline:

| Command | Behaviour |
|---------|-----------|
| "Remember that [fact]" | Extracts and stores fact permanently |
| "What do you remember about me?" | Recalls all stored facts aloud |
| "Clear memory" | Resets LLM conversation history (facts preserved) |

### 4. Cold Start Fix (`components/llm.py`)

The 80.82s cold start measured in Week 1 was resolved by passing `keep_alive="30m"` as a **top-level parameter** to `ollama.chat()`. Previous attempt placed it inside `options`, where Ollama silently ignores it. The distinction matters: it is an API-level parameter, not a model inference option.

Post-fix behaviour: model stays loaded in VRAM for 30 minutes of inactivity. Confirmed by running a 7.3-minute session with no LLM latency spike.

### 5. Orchestrator Class Refactor (`components/orchestrator.py`)

`main.py` was holding two unrelated concerns — component initialization and pipeline execution logic. As TARA's feature set grows, mixing these would make every addition harder and riskier.

The refactor extracted all pipeline logic into a dedicated `Orchestrator` class:

**`main.py`** now owns only:
- Component initialization
- Audio capture loop
- Banner and startup UI

**`components/orchestrator.py`** now owns:
- Command routing via a registry pattern
- Full pipeline execution (Memory → LLM → TTS → Persistence)
- Session stats tracking
- Stage-structured pipeline with explicit insertion points for future features

Key design decisions in the Orchestrator:

**Command registry pattern** — instead of a chain of `if` statements, commands are registered as `(condition, handler)` pairs. Adding a new command means adding one tuple and two methods. Nothing else changes:

```python
def _build_command_registry(self) -> list[tuple]:
    return [
        (self._is_exit,     self._handle_exit),
        (self._is_clear,    self._handle_clear),
        (self._is_remember, self._handle_remember),
        (self._is_recall,   self._handle_recall),
    ]
```

**Staged pipeline with future insertion points** — `_run_pipeline()` has seven named stages. Stages 2, 3, and 4 are commented placeholders for intent detection, tool execution, and RAG retrieval:

```
Stage 1: Memory Context Retrieval      ← active
Stage 2: Intent Detection              [FUTURE — Week 4]
Stage 3: Tool Execution                [FUTURE — Week 4]
Stage 4: RAG Retrieval                 [FUTURE — Week 5]
Stage 5: LLM Generation               ← active
Stage 6: Response Delivery             [→ Chunked TTS in T6]
Stage 7: Persistence                   ← active
```

**Single Responsibility on MemoryStore** — previously, `MemoryStore.remember_if_requested()` combined intent detection with storage. The Orchestrator now makes the decision of when to remember; `MemoryStore` only stores and retrieves.

---

## Challenges Encountered

**1. `keep_alive` parameter placement**
First fix attempt put `keep_alive` inside the `options` dict. Ollama silently ignored it, and the model still unloaded after 5 minutes. The real cold start was ~7s (RAM→VRAM), not 80s (disk→VRAM) — the original measurement was a one-time disk load cost, not representative of normal operation.

**2. Missing print statements in command branches**
All `continue` branches (remember, recall, clear memory, goodbye) called `tts.speak()` but skipped `print()`. Fixed by introducing a `_say()` helper method that always prints and speaks together, making it architecturally impossible to speak without printing.

**3. `response` variable scope bug**
The recall branch spoke the correct facts but never assigned them to `response`, then printed the empty default. Resolved alongside the `_say()` refactor.

---

## Architecture: Before and After

**Before (Week 2):**
```
main.py
  └── TARA class
        ├── __init__() — component init
        └── run() — audio loop + ALL pipeline logic + command handling + stats
```

**After (Week 3):**
```
main.py
  └── TARA class
        ├── __init__() — component init only
        └── run() — audio loop only

components/orchestrator.py
  └── Orchestrator class
        ├── process_turn() — command routing
        ├── _build_command_registry() — all commands in one place
        ├── _run_pipeline() — staged pipeline execution
        └── _print_baseline_report() — session stats
```

`main.py` shrank from ~130 lines to ~70. The Orchestrator will not require `main.py` changes for any future pipeline feature additions.

---

## Lessons Learned

- **Silent parameter failures are harder to debug than errors.** `keep_alive` being ignored produced no warning — only a behaviour difference visible after a 5-minute wait. Always verify configuration changes with observable evidence.
- **Architectural helpers prevent entire classes of bugs.** The `_say()` method enforces print+speak consistency at the design level. No amount of code review catches what a good constraint prevents automatically.
- **Refactor before it hurts, not after.** The Orchestrator refactor was done before adding chunked TTS. Doing it after would have meant untangling pipeline logic and threading code simultaneously — a much harder problem.
- **Single Responsibility applies to data classes too.** `MemoryStore.remember_if_requested()` was doing intent detection inside a storage class. Catching this before Week 4's tool architecture made the fix easy.
- **Measure what changed.** The +0.29s memory overhead was only visible because a clean Week 2 baseline existed to compare against. Baseline documentation from previous weeks directly enabled this analysis.

---

## Sprint Outcome

✅ SQLite memory layer with conversations and user_facts tables  
✅ Cross-session memory recall working  
✅ Explicit "remember that" and "what do you remember" commands  
✅ Cold start eliminated via `keep_alive` top-level parameter  
✅ Orchestrator refactor — pipeline logic separated from startup  
✅ Command registry pattern — extensible to 20+ commands without structural change  
✅ Staged pipeline with Week 4 and 5 insertion points documented  

---

## Week 4 Preview

**Theme: Agentic Tools**
First tool integrations: system monitoring (psutil), basic file operations, and the first structured tool-calling architecture. TARA will move from answering questions to taking actions.

The Orchestrator's Stage 2 (Intent Detection) and Stage 3 (Tool Execution) placeholders are ready. Week 4 fills them in.
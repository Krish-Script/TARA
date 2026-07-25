# TARA — Week 6 Report
## Error Architecture, File Management, Information Retrieval

**Sprint duration:** Week 6 of 10  
**Primary goal:** Close two open stated requirements (file management, error handling). Build error handling structurally into every new tool.  
**Status:** ✅ Completed (7/7 tasks)

---

## Adjusted Strategy

Three facts from Week 5 shaped Week 6's execution order:

**Error handling was built first, not retrofitted.** The sprint plan listed error handling as T4. It was executed as T1 — every tool built this week inherits structural protections by default. Building T2 before T1 would have meant retrofitting protections onto already-written code, the exact pattern the sprint principle was designed to prevent.

**"Information retrieval" was reframed before building.** The project objective referred to DuckDuckGo web search, which requires internet. This is incompatible with the fully offline constraint. The requirement is reinterpreted as local knowledge retrieval — searching notes, SQLite facts, and local file contents. Documented in `docs/known_limitations.md` before T7 was built.

**qwen2.5:3b warm latency confirmed.** The 9.47s figure from the Week 5 harness was cold-start contamination. Warm inference confirmed at **0.78s** — consistent with the 0.85–1.04s range from the keep_alive session. The model decision stands.

---

## Final Performance Baseline

| Metric | Week 5 | Week 6 | Notes |
|--------|--------|--------|-------|
| STT avg | 0.72s | 0.79s | stable |
| LLM avg (chat) | 1.04s | 1.27s | single data point |
| Tool execution avg | 0.002s | 2.374s | LLM-assisted tools add 1-3s |
| TTS synthesis avg | 0.66s | 0.75s | stable |
| TTFS (chat path) | 2.30s | 2.92s | session variance |
| TTFS (tool path, no LLM) | 1.25s | 1.44s | beats ≤1.50s target |
| TTFS (LLM-assisted tool) | — | 1.28–1.52s | notes create / calculator |
| TTFS (local search) | — | 1.41s | below target |
| qwen2.5:3b warm latency | unconfirmed | **0.78s** ✅ | confirmed |
| Stage 1 on tool path | unconfirmed | **never** ✅ | confirmed |
| Intent accuracy | 22/22 | **37/37** | +15 queries |

**On LLM-assisted tool TTFS:** These paths (notes create, file read, calculator, local search) require one or two LLM calls inside the tool. Tool execution adds 1–3s. TTFS stays near target because STT and TTS synthesis are fast, but this is a distinct latency category from pure tool dispatch and should not be averaged together.

---

## Stage 1 Verification

Debug print restored to `orchestrator.py`. Console evidence from 4-turn regression test:

```
Turn 1: TIME_QUERY    → Stage 1 silent ✅
Turn 2: SYSTEM_QUERY  → Stage 1 silent ✅
Turn 3: NOTES_CREATE  → Stage 1 silent ✅
Turn 4: CHAT          → [Orchestrator] Stage 1: memory context building (CHAT path) ✅
```

---

## What Was Built

### T1 — Three-Tier Error Architecture

**File:** `components/error_manager.py`

Closes the "robust error handling and recovery mechanisms" stated requirement.

| Tier | Trigger | Behaviour |
|------|---------|-----------|
| Tier 1 — Expected | Tool raises `ToolExpectedError` | Spoken naturally, session continues, no log entry |
| Tier 2 — Unexpected | Unhandled tool exception | Full traceback logged to `logs/errors.log`, graceful spoken fallback |
| Tier 3 — Component | STT / TTS / SQLite failure | TTS → terminal print with `[TTS FAULT]` tag. SQLite → `logs/memory_fallback.txt`. Session never dropped |

All three tiers deliberately triggered and confirmed before T2.

---

### T2 — Notes Tool

**File:** `components/tools/notes_tool.py`  
**Storage:** `data/notes/YYYY-MM-DD_HH-MM-SS.txt`

Closes the "file management" stated requirement.

| Operation | Intent | Voice trigger |
|-----------|--------|--------------|
| Create | NOTES_CREATE | "take a note", "note that", "remember to", "add a note" |
| Read last | NOTES_READ | "read my last note", "what was my last note" |
| List | NOTES_LIST | "what notes do I have", "list my notes", "how many notes" |
| Search | NOTES_SEARCH | "find my note about X", "do I have a note about X" |

Critical pattern ordering: "remember to" (NOTES_CREATE) above "remember" (MEMORY) — prevents routing collision. Both raw transcription and extracted content written to file — nothing lost if LLM extraction is imperfect. LLM-assisted TTFS: **1.28s**.

---

### T3 — File Reader Tool

**File:** `components/tools/file_reader.py`

Dynamic OS path resolution via `pathlib.Path.home()` — no hardcoded usernames or YAML config. OneDrive path detection fallback for Windows 11 setups where Desktop/Documents are silently redirected.

- LLM zero-shot filename extraction from natural speech
- Auto-summarisation at >500 chars — secondary LLM call for 1–2 sentence spoken summary
- Security whitelist: Desktop, Documents, Downloads, `data/notes` only
- All error cases (not found, permission denied, binary, oversized) return `ToolExpectedError` — no tracebacks

---

### T4 — Calculator Tool

**File:** `components/tools/calculator_tool.py`

Two-stage pipeline: LLM normalisation ("fifteen percent of two hundred" → "200 * 0.15") → `safe_eval()` with mandatory sanitisation. `eval()` never receives raw user input.

| Query | Response | TTFS |
|-------|----------|------|
| "Calculate 15% of 340" | "That's 51." | 1.80s |
| "What is 847 divided by 7?" | "That's 121." | 1.36s |
| "Calculate the weather." | Graceful error | 1.39s |

False positives fixed: "what is", "what's", "how many is" removed from CALCULATION patterns after benchmark caught all three misrouting conversational queries. Benchmark: 24/24.

---

### T5 — Evaluation Harness: Category A2

**File:** `tests/test_model_eval.py`

Five adversarial prompts added — designed to break the one-sentence constraint via persona requests, multi-part queries, and verbosity-tempting phrasing.

**Category A2 Score: 4/5**

One prompt broke the format constraint — consistent with the Week 5 finding that multi-part or persona-heavy prompts exceed the one-sentence rule on qwen2.5:3b. The score is capability documentation, not a target. The adversarial prompts are not being tuned against.

Appended to `docs/model_evaluation.txt`. Informed the pre-synthesis filtering strategy used in T7 — smaller models given excessive context overshare; constraint must be enforced in Python before the LLM call, not by instruction.

---

### T6 — Intent Extension + Benchmark

**Files:** `components/intent.py`, `tests/test_benchmark.py`

New intents registered: `FILE_LIST`, `LOCAL_SEARCH`. Benchmark expanded to 37 queries across all tool domains. Critical collision test: "Remember to buy milk" → NOTES_CREATE; "Remember that I like chess" → MEMORY.

**Benchmark: 37/37 (100%), 0 false positives, 0.00ms intent latency.**

---

### T7 — Local Information Retrieval

**File:** `components/tools/local_search.py`

Closes the "information retrieval" stated requirement within the offline constraint.

Three-stage pipeline:
1. **Extraction** — LLM isolates core search keyword from natural query ("what do you know about my flight" → "flight")
2. **Retrieval** — Python scans `data/notes/*.txt` and queries SQLite `user_facts` table in parallel
3. **Synthesis** — Only pre-filtered, relevant fragments injected into LLM for 1–2 sentence spoken summary

**Key design decisions:**

**Pre-synthesis Python filtering over LLM instruction:** Initial testing showed qwen2.5:3b overshares when given the full MemoryStore — listing the user's name and favourite language when asked about a flight. Filtering `if target in item.fact.lower()` in Python before context injection is more reliable than instructing the model to ignore unrelated details.

**Possessive triggers only:** Broad patterns like "what do you know about" misrouted general knowledge queries ("What do you know about Einstein?") to LOCAL_SEARCH. Restricted to possessive phrasing ("what do you know about my", "find anything about my") — preserves CHAT path for general knowledge.

**`MemoryStore` path from config:** `MemoryStore(MEMORY_CONFIG["db_path"])` — avoids silent empty-database reads if working directory changes.

**TTFS: 1.41s** — below ≤1.50s target despite two LLM calls.

---

## Open Gaps — Project Objective vs Implementation

| Stated requirement | Status |
|-------------------|--------|
| Real-time voice input | ✅ |
| Offline speech recognition | ✅ |
| Local LLM inference | ✅ |
| Context-aware dialogue management | ✅ |
| Agentic tool execution | ✅ system, time, notes, files, calculator, search |
| File management | ✅ Notes Tool (create/read/list/search) |
| Information retrieval | ✅ File Reader + Local Search |
| Natural voice response | ✅ |
| Modular architecture | ✅ |
| Robust error handling | ✅ Three-tier architecture |
| Thermal-aware operation | ✅ GPU temperature |
| Resource-efficient operation | ✅ |

All stated project objective requirements are now implemented.

---

## Lessons Learned

- **Error handling first is not overhead — it is the foundation.** Every `ToolExpectedError` in T2–T7 works because the dispatcher was designed to handle it before the tools were written.
- **Pre-filtering beats prompt instructions for small models.** qwen2.5:3b overshares when given excessive context. Filtering in Python before LLM injection is more reliable than instructing the model to focus.
- **LLM-assisted tool latency is prompt-length dependent.** 1.28s for note extraction and 1.41s for local search are properties of short prompts. File summarisation on large documents will be slower. These are not a single "LLM-assisted" category.
- **Possessive triggers protect general knowledge routing.** Broad intent patterns capture general knowledge queries as false positives. Restricting local search to possessive phrasing preserves the CHAT path.
- **Adversarial testing reveals honest limits.** Category A2 score of 4/5 is not a failure — it is accurate documentation of where the model constraint holds and where it does not.
- **OS-level abstractions beat hardcoded config.** `pathlib.Path.home()` with OneDrive fallback handled cross-drive Windows setups that a static YAML file would have broken on.
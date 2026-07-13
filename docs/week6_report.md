# TARA — Week 6 Report
## Error Architecture, File Management, Information Retrieval

**Sprint duration:** Week 6 of 10
**Primary goal:** Close two open stated requirements (file management, error handling). Build error handling structurally into every new tool.
**Status:** 🔄 In Progress (T1–T2 complete, T3–T7 pending)

---

## Adjusted Strategy

Three facts from Week 5 shaped Week 6's execution order:

**Error handling was built first, not retrofitted.** The sprint plan originally listed error handling as T4. It was executed as T1 because every tool built this week inherits structural protections by default. Building T2 (Notes Tool) before T1 (Error Architecture) would have meant retrofitting protections onto an already-written tool — the exact pattern the sprint principle was designed to prevent.

**"Information retrieval" was reframed before building.** The project objective referred to DuckDuckGo web search, which requires internet. This is incompatible with the fully offline constraint. The requirement is reinterpreted as local knowledge retrieval — searching notes, SQLite facts, and local file contents. This is documented in `docs/known_limitations.md` and is the basis for T7.

**qwen2.5:3b warm latency confirmed.** The 9.47s figure from the Week 5 harness was cold-start contamination. Warm inference confirmed at **0.78s** via explicit warm-up call — consistent with the 0.85–1.04s range measured during the keep_alive session. The model decision stands.

---

## Performance Baseline — Week 6 T1–T2

| Metric | Week 5 | Week 6 | Change |
|--------|--------|--------|--------|
| STT avg | 0.72s | 0.72s | stable |
| LLM avg (chat) | 1.04s | 1.27s | +0.23s (1 data point) |
| Tool execution avg | 0.002s | 0.305s | +0.303s (notes LLM cost) |
| TTS synthesis avg | 0.66s | 0.75s | stable |
| TTFS (chat path) | 2.30s | 2.92s | session variance — 1 turn |
| TTFS (tool path) | 1.25s | 1.44s | stable, beats ≤1.50s |
| **TTFS (LLM-assisted tool)** | — | **1.28s** | **new category** |
| qwen2.5:3b warm latency | unconfirmed | **0.78s** | ✅ confirmed |
| Stage 1 on tool path | unconfirmed | **never** | ✅ confirmed |

**Note on chat path TTFS (2.92s):** Single data point from one chat turn. The black holes response was 2 sentences (37 words) — longer than the 1-sentence target, which inflated TTS synthesis to 0.91s. Not a regression; session variance.

**Note on LLM-assisted TTFS (1.28s):** This is specific to short extraction tasks (note content extraction prompt → ~10-word response). File summarization on 3000-character documents will be slower. Do not treat 1.28s as a general LLM-assisted tool property.

---

## Stage 1 Verification — 4-Turn Regression Test

Debug print restored to `orchestrator.py`. Console evidence:

```
Turn 1: TIME_QUERY    → [Intent] TIME_QUERY    → Stage 1 silent ✅
Turn 2: SYSTEM_QUERY  → [Intent] SYSTEM_QUERY  → Stage 1 silent ✅
Turn 3: NOTES_CREATE  → [Intent] NOTES_CREATE  → Stage 1 silent ✅
Turn 4: CHAT          → [Orchestrator] Stage 1: memory context building (CHAT path) ✅
```

Stage 1 fires only on CHAT path. All three tool path variants (time, system, notes) confirm the optimisation from Week 5 T2 is intact after the Week 6 changes.

---

## What Was Built

### T1 — Three-Tier Error Architecture

**File:** `components/error_manager.py`

The pipeline's error management was rebuilt from a global catch-all into a tiered classification system, closing the "robust error handling and recovery mechanisms" stated requirement from the project objective.

**Tier 1 — Expected failures:**
Tools raise `ToolExpectedError(message)` for known, predictable edge cases — missing files, empty directories, unavailable sensors. The `ToolRegistry` dispatcher catches this, formats the message as a spoken response, and continues the session. No log entry — these are not errors, they are handled conditions.

**Tier 2 — Unexpected failures:**
Any unhandled exception in a tool is caught by the dispatcher, the full traceback is written to `logs/errors.log` with timestamp and component name, and a graceful spoken fallback is delivered. The user-facing terminal never shows a Python traceback after this version.

**Tier 3 — Component failures:**
STT, TTS, and SQLite each have isolated `try/except` blocks:
- TTS crash → response printed to terminal with `[TTS FAULT - AUDIO FAILED]` tag, session continues
- SQLite failure → turn appended to `logs/memory_fallback.txt`, session continues, no data dropped

**Validation:** All three tiers deliberately triggered and confirmed before proceeding to T2.

---

### T2 — Notes Tool

**File:** `components/tools/notes_tool.py`
**Storage:** `data/notes/YYYY-MM-DD_HH-MM-SS.txt`

Closes the "file management" stated requirement. Four operations:

| Operation | Intent | Voice trigger |
|-----------|--------|--------------|
| Create | NOTES_CREATE | "take a note", "note that", "remember to", "add a note" |
| Read last | NOTES_READ | "read my last note", "what was my last note" |
| List | NOTES_LIST | "what notes do I have", "list my notes", "how many notes" |
| Search | NOTES_SEARCH | "find my note about X", "do I have a note about X" |

**Note content extraction (LLM call on create):**
Zero-shot prompt strips conversational filler ("Take a note, I need to...") and extracts the core content. Both raw transcription and extracted content are written to the file — nothing is lost if extraction is imperfect.

**Critical pattern ordering:** "remember to" (NOTES_CREATE) placed above "remember" (MEMORY) in `IntentDetector` — prevents routing collision. Verified: "Remember to buy milk" → NOTES_CREATE. "Remember that my name is Krishnendu" → MEMORY.

**Error handling (Tier 1 integration):**
- `data/notes/` absent → created automatically
- Empty notes directory on read/list → `ToolExpectedError` spoken naturally
- Search finds nothing → "I don't have any notes about that"
- File write failure → `ToolExpectedError` spoken, raw transcription logged

**LLM-Assisted Tool Path TTFS: 1.28s** — first measurement of this new latency category.

---

### T2 — Time Formatter Fix

The `_format_time()` method in `formatter.py` was prepending `day_str` (e.g. "Sunday") before `date_full` (e.g. "Sunday, July 12, 2026"), producing "Sunday, Sunday, July 12, 2026." Fixed by removing `day_str` from the return string and adding `.strip()` to `date_full`. Result: "It's 05:30 PM on Sunday, July 12, 2026."

---

## Open Gaps — Project Objective vs Implementation

| Stated requirement | Status |
|-------------------|--------|
| Real-time voice input | ✅ |
| Offline speech recognition | ✅ |
| Local LLM inference | ✅ |
| Context-aware dialogue management | ✅ |
| **Agentic tool execution** | ✅ (system, time, notes) |
| **File management** | ✅ (notes create/read/list/search) |
| **Information retrieval** | ⏳ T7 — reframed as local search |
| Natural voice response | ✅ |
| Modular architecture | ✅ |
| **Robust error handling** | ✅ |
| Thermal-aware operation | ✅ (GPU temp) |
| Resource-efficient operation | ✅ |

---

## Pending Tasks

| Task | Description | Priority |
|------|-------------|----------|
| T3 | File Reader Tool | 🔴 Critical |
| T4 | Calculator Tool | 🟡 Medium |
| T5 | Evaluation Harness — Category A2 adversarial | 🟡 High |
| T6 | IntentDetector extension + ≥30 benchmark | 🟡 High |
| T7 | Local information retrieval (notes + facts search) | 🟢 Medium |

---

## Lessons Learned

- **Error handling first is not overhead — it is the foundation.** Building T1 before T2 meant the Notes Tool inherited structural protections by default. Every `ToolExpectedError` in the Notes Tool works correctly because the dispatcher was designed to handle it before the tool was written.
- **LLM-assisted tool latency is prompt-length dependent, not a fixed category.** The 1.28s TTFS for note creation is a property of a short extraction prompt returning a short response. This number will not generalise to file summarization tasks. A TTFS category named "LLM-assisted" without specifying prompt complexity is misleading.
- **Stage 1 evidence requires a debug print.** Removing the debug print in Week 5 left a 10-point scoring gap. Restoring it took 30 seconds. Always maintain observability infrastructure — never remove debug logging without replacing it with equivalent evidence.
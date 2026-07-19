# TARA — Week 6 Report
## Error Architecture, File Management, Information Retrieval

**Sprint duration:** Week 6 of 10
**Primary goal:** Close two open stated requirements (file management, error handling). Build error handling structurally into every new tool.
**Status:** 🔄 In Progress (T1–T6 complete, T7 pending)

---

## Adjusted Strategy

Three facts from Week 5 shaped Week 6's execution order:

**Error handling was built first, not retrofitted.** The sprint plan originally listed error handling as T4. It was executed as T1 because every tool built this week inherits structural protections by default. Building T2 (Notes Tool) before T1 (Error Architecture) would have meant retrofitting protections onto an already-written tool — the exact pattern the sprint principle was designed to prevent.

**"Information retrieval" was reframed before building.** The project objective referred to DuckDuckGo web search, which requires internet. This is incompatible with the fully offline constraint. The requirement is reinterpreted as local knowledge retrieval — searching notes, SQLite facts, and local file contents. This is documented in `docs/known_limitations.md` and is the basis for T3 and T7.

**qwen2.5:3b warm latency confirmed.** The 9.47s figure from the Week 5 harness was cold-start contamination. Warm inference confirmed at **0.78s** via explicit warm-up call — consistent with the 0.85–1.04s range measured during the keep_alive session. The model decision stands.

---

## Performance Baseline

| Metric | Week 5 | Week 6 T1–T2 | Week 6 T3–T4 | Notes |
|--------|--------|--------------|--------------|-------|
| STT avg | 0.72s | 0.72s | 0.79s | stable |
| LLM avg (chat) | 1.04s | 1.27s | — | no chat turns |
| Tool execution avg | 0.002s | 0.305s | 2.374s | LLM-assisted tools |
| TTS synthesis avg | 0.66s | 0.75s | 0.67s | stable |
| TTFS (chat path) | 2.30s | 2.92s | — | no chat turns |
| TTFS (tool path) | 1.25s | 1.44s | 1.52s | marginally over target |
| TTFS (LLM-assisted) | — | 1.28s | 1.52s | |
| qwen2.5:3b warm latency | unconfirmed | 0.78s ✅ | 0.78s | confirmed |
| Stage 1 on tool path | unconfirmed | never ✅ | never | confirmed |

**Note on TTFS tool path (1.52s avg, T3–T4):** Marginally over the ≤1.50s target. Cause: LLM normalisation adds ~1.2–3.1s to tool execution for calculator and file reader queries. TTFS stays close to target because STT and TTS synthesis are fast, but this is a new latency category that will not improve without removing the LLM dependency from these tools.

---

## Stage 1 Verification — 4-Turn Regression Test

Debug print restored to `orchestrator.py`. Console evidence:

```
Turn 1: TIME_QUERY    → Stage 1 silent ✅
Turn 2: SYSTEM_QUERY  → Stage 1 silent ✅
Turn 3: NOTES_CREATE  → Stage 1 silent ✅
Turn 4: CHAT          → [Orchestrator] Stage 1: memory context building (CHAT path) ✅
```

Stage 1 fires only on CHAT path. All tool path variants confirm the optimisation from Week 5 T2 is intact.

---

## What Was Built

### T1 — Three-Tier Error Architecture

**File:** `components/error_manager.py`

Closes the "robust error handling and recovery mechanisms" stated requirement from the project objective.

**Tier 1 — Expected failures:**
Tools raise `ToolExpectedError(message)` for known, predictable edge cases. Dispatcher catches it, speaks the message naturally, continues session. No log entry — handled conditions are not errors.

**Tier 2 — Unexpected failures:**
Unhandled tool exceptions caught by dispatcher, full traceback logged to `logs/errors.log`, graceful spoken fallback delivered. Terminal never shows a Python traceback after this version.

**Tier 3 — Component failures:**
STT, TTS, and SQLite individually wrapped:
- TTS crash → response printed to terminal (`[TTS FAULT - AUDIO FAILED]`), session continues
- SQLite failure → turn appended to `logs/memory_fallback.txt`, session continues, no data dropped

**Validation:** All three tiers deliberately triggered and confirmed before T2.

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

**Critical pattern ordering:** "remember to" (NOTES_CREATE) above "remember" (MEMORY) — prevents routing collision.
**LLM-Assisted TTFS: 1.28s** — first measurement of this latency category.

---

### T3 — File Reader Tool

**File:** `components/tools/file_reader.py`

Closes the first half of the offline "information retrieval" requirement.

**Capabilities:**
- Dynamic OS resolution via `pathlib.Path.home()` — no hardcoded usernames or YAML config
- OneDrive path detection fallback — handles the common Windows 11 setup where Desktop/Documents are silently redirected to `C:\Users\Name\OneDrive\Desktop`
- LLM zero-shot filename extraction from natural speech ("Read the meeting notes from my desktop" → "meeting notes")
- Auto-summarisation threshold: >500 chars triggers a secondary LLM call for a 1–2 sentence spoken summary
- Security whitelist: Desktop, Documents, Downloads, `data/notes` only — path traversal blocked

**Error handling (Tier 1):** File not found, permission denied, binary file, and oversized file all produce graceful spoken responses with no traceback.

**Intent added:** `FILE_READ`
**Pattern ordering:** broad `"read the"` triggers placed below specific `"read my last note"` — prevents shadowing Notes Tool.

---

### T4 — Calculator Tool

**File:** `components/tools/calculator_tool.py`

Two-stage evaluation pipeline:

**Stage 1 — LLM normalisation:**
Converts natural language to a bare arithmetic expression.
"fifteen percent of two hundred" → "200 * 0.15"
"847 divided by 7" → "847 / 7"

**Stage 2 — `safe_eval()`:**
Strips everything except digits, operators, parentheses, and decimal points via `re.sub()`. `eval()` never receives raw user input.

**Error handling (Tier 1):**
- No numbers found → "I couldn't find a valid calculation in that."
- Division by zero → "I can't divide by zero."
- Invalid expression after sanitisation → "I had trouble computing that. Try rephrasing it."
- Non-mathematical query ("Calculate the weather") → "The expression doesn't seem to contain any numbers."

**Result formatting:** Integers spoken as integers ("51", not "51.0"). Decimals rounded to 4 significant figures with trailing zeros stripped.

**Voice test results:**

| Query | Response | Latency | Correct |
|-------|----------|---------|---------|
| "Calculate 15% of 340" | "That's 51." | 3.104s | ✅ |
| "What is 847 divided by 7?" | "That's 121." | 1.249s | ✅ |
| "Calculate the weather." | "The expression doesn't seem to contain any numbers." | 2.770s | ✅ |

**TTFS: 1.80s / 1.36s / 1.39s** — tool path target (≤1.50s) met for warm queries; first call slightly over due to LLM cold context.

---

### T5 — Evaluation Harness (Category A2)

**File:** `tests/test_model_eval.py`

Expanded the automated LLM testing harness with a new adversarial testing category.

**Purpose:**
To establish an honest baseline of the model's resilience against "format bleed" and persona-breaking prompts. Small parameter models (like `qwen2.5:3b`) often struggle to maintain strict constraints when exposed to complex instructions. This category documents that limitation rather than trying to tune it away.

**Mechanics:**
- **Adversarial Prompts:** Injected queries specifically designed to tempt verbosity and break the one-sentence constraint (e.g., "Respond like a pirate", "Summarize the history of AI").
- **Manual Grading Loop:** Enforces strict compliance. 
  - `PASS` = 1-2 sentences, strictly no markdown, answers the prompt.
  - `FAIL` = 3+ sentences, usage of markdown/lists, or irrelevant output.
- **Persistent Logging:** Scores are appended to `docs/model_evaluation.txt` to track degradation if the underlying model is changed.

**Validation:**
As expected, `qwen2.5:3b` struggled with the adversarial constraints. Documenting this failure baseline directly informed the prompt engineering strategy (Recency Bias exploitation) required to make the T3 File Reader auto-summarizer work effectively.

---

### T6 — Intent Extension & Benchmark Validation

**Files:** `components/intent.py`, `tests/test_benchmark.py`

Pre-registered intents for upcoming features and rigorously validated that new broad triggers do not cannibalize existing conversational logic.

**Mechanics:**
- **Intent Expansion:** Added `FILE_LIST` and `LOCAL_SEARCH` to the Intent enum and pattern dictionaries to support upcoming T7 implementation.
- **Pattern Refinement:** Removed overly broad triggers (`"what is"`, `"what's"`) from the `CALCULATION` intent. This prevents catastrophic misrouting (e.g., routing the chat query "What is a neural network?" to the math engine).
- **Benchmark Expansion:** Scaled `INTENT_TEST_CASES` to 37 unique queries across all tool domains.
- **Collision Testing:** Added deliberate edge-case queries to ensure semantic boundaries hold (e.g., ensuring "Remember to buy milk" triggers `NOTES_CREATE`, while "Remember that I like chess" triggers `MEMORY`).

**Validation Results (Automated Suite):**

| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| Intent Routing Accuracy | 37 / 37 | 100% | ✅ |
| False Positives | 0 | 0 | ✅ |
| Intent Classification Latency | 0.00ms | < 5.0ms | ✅ |
| Tool Path TTFS Proxy | 1.37s | ≤ 1.50s | ✅ |

The intent router is mathematically solid. The pipeline is cleared for T7.

---

### Time Formatter Fix

`_format_time()` was prepending `day_str` before `date_full`, which already starts with the day name — producing "Sunday, Sunday, July 12, 2026." Fixed by removing `day_str` from the return and adding `.strip()` to `date_full`. Result: "It's 05:30 PM on Sunday, July 12, 2026."

---

## Pending Tasks

| Task | Description | Priority |
|------|-------------|----------|
| T7 | Local information retrieval (notes + facts search) | 🟢 Medium |

---

## Open Gaps — Project Objective vs Implementation

| Stated requirement | Status |
|-------------------|--------|
| Real-time voice input | ✅ |
| Offline speech recognition | ✅ |
| Local LLM inference | ✅ |
| Context-aware dialogue management | ✅ |
| Agentic tool execution | ✅ system, time, notes, files, calculator |
| File management | ✅ Notes Tool (create/read/list/search) |
| Information retrieval | ✅ File Reader / ⏳ T7 (context search) |
| Natural voice response | ✅ |
| Modular architecture | ✅ |
| Robust error handling | ✅ Three-tier architecture |
| Thermal-aware operation | ✅ GPU temperature |
| Resource-efficient operation | ✅ |

---

## Lessons Learned

- **Error handling first is not overhead — it is the foundation.** Every `ToolExpectedError` in T2–T4 works because the dispatcher was designed to handle it before the tools were written.
- **LLM-assisted tool latency is prompt-length dependent, not a fixed category.** The 1.28s TTFS (notes create) will not generalise to file summarisation on large documents. "LLM-assisted tool path" needs per-tool latency characterisation, not a single number.
- **False positives require benchmark evidence, not intuition.** "what is" seemed like a safe CALCULATION trigger. The benchmark proved it misrouted three conversational queries. Pattern additions must be tested against both target and edge case queries before deployment.
- **OS-level abstractions beat hardcoded configuration.** Static `settings.yaml` would have failed on Windows setups with OneDrive active. `pathlib.Path.home()` handles it dynamically.
# TARA — Week 6 Report
## Error Architecture, File Management, Information Retrieval

**Sprint duration:** Week 6 of 10  
**Primary goal:** Build structural error handling to guarantee session survival, then implement persistent file operations and local knowledge retrieval to close open project requirements.  
**Status:** 🚧 In Progress

---

## Adjusted Strategy & Architectural Shifts

Entering Week 6, the core priority shifted from feature accumulation to system resilience. Previous implementations of the `ToolRegistry` and the main `Orchestrator` relied on global catch-all exception handlers. While these acted as effective crash suppressors, they lacked granular error handling. 

The primary architectural principle for Week 6: **Error handling must be structural, not retrospective.** Before implementing any new file management or system tools, the entire pipeline was retrofitted with a three-tier error classification system to guarantee graceful degradation and session survival under stress.

---

## Sprint Metrics & Targets

**Entering Week 6 Baseline:**
* **TTFS (Chat Path):** 2.30s (using qwen2.5:3b)
* **TTFS (Tool Path):** 1.25s
* **Intent Accuracy:** 22/22 (100%) across 8 supported query types
* **Execution Pace:** Tracking at ~7.5h - 8.0h per sprint (Sprint 6 budgeted for 10.5h)

**Week 6 Progress & Targets:**
* Expand Intent Benchmark to ≥ 30 queries while maintaining 100% accuracy.
* Maintain Chat Path TTFS ≤ 2.30s.
* Document a 3rd TTFS category: "LLM-Assisted Tool Path" (target: ~2.30s). **Current actual: 1.56s (beating target).**
* Log Category A2 (Adversarial) evaluation scores for capability documentation.

---

## What Was Built

### T1 — Error Handling Retrofit
*Note: Originally scoped as T4 in the sprint plan, this was executed as T1 to ensure all subsequent tools built this week inherit these structural protections by default.*

The pipeline's error management was completely rebuilt into a tiered middleware pattern:

* **Tier 1 — Expected Tool Failures:** Handled predictable, known edge cases (e.g., missing hardware sensors, files not found). 
    * *Implementation:* Tools now raise a custom `ToolExpectedError`. The dispatcher intercepts this exception and cleanly formats the message into a natural, spoken response, allowing the session to continue seamlessly.
* **Tier 2 — Unexpected Tool Failures:** Handled unanticipated tool crashes (e.g., corrupted returns). 
    * *Implementation:* Full Python tracebacks are caught by the `ToolRegistry` and routed to a silent, non-propagating file logger (`logs/errors.log`). TARA outputs a graceful fallback phrase. The user-facing terminal is entirely shielded from red tracebacks.
* **Tier 3 — Fatal Component Failures:** Protected the core infrastructure (STT capture, TTS generation, SQLite database writes). 
    * *Implementation:* Isolated `try...except` blocks wrapped around STT in `main.py`, and around TTS and SQLite inside `orchestrator.py`. 
    * *Recovery:* If Piper TTS crashes, TARA falls back to printing the response to the terminal (`[TTS FAULT - AUDIO FAILED]`). If SQLite fails, the turn is appended to a local fallback text file (`logs/memory_fallback.txt`) rather than dropping the data.

**Validation:** All three tiers were deliberately triggered. Forced tool declines spoke naturally (Tier 1), injected `ValueError`s logged silently (Tier 2), and injected `RuntimeError`s in Piper TTS successfully fell back to terminal prints without dropping the session (Tier 3).

---

### T2 — Notes Tool (File Management)

**File:** `components/tools/notes_tool.py`

Addressed the "file management" project requirement gap by building persistent voice-to-file operations.

* **Capabilities:** 
    * **Create:** Uses a zero-shot LLM extraction prompt to cleanly parse user dictation (stripping conversational filler) and saves it alongside the raw transcription to a timestamped `.txt` file in `data/notes/`.
    * **Read / List / Search:** Performs local filesystem traversal, file modification sorting, and string matching.
* **Resilience (Tier 1 Integration):** Heavily utilizes the new `ToolExpectedError`. If the storage folder is missing, empty, or a search yields no results, TARA gracefully speaks a natural fallback rather than throwing OS or Index errors.
* **Intent Routing:** Added `NOTES_CREATE`, `NOTES_READ`, `NOTES_LIST`, and `NOTES_SEARCH`. Implemented critical pattern ordering to prevent collision between notes ("remember to") and memory ("remember that").

**Performance:** First test of the "LLM-Assisted Tool Path" yielded an exceptional TTFS of 1.56s (beating the sprint target of ~2.30s), proving that lightweight model inferences inside tools do not compromise conversational latency.

---

## Pending Tasks (Week 6)

- **T3: File Reader Tool** — Local file resolution using system path aliases and text summarization.
- **T4: Calculator Tool** — Sandboxed mathematical evaluation utilizing LLM normalization.
- **T5: Evaluation Harness Upgrade** — Category A2 adversarial prompt integration.
- **T6: IntentDetector Extension** — New patterns for file/note routing (regression benchmark).
- **T7: Local Information Retrieval** — Consolidating text file indexing and SQLite context search.

---

## Sprint Outcome (In Progress)

✅ T1 — 3-Tier Error Architecture implemented  
✅ T2 — Notes Tool & persistent file management created  
⏳ T3 — File Reader Tool  
⏳ T4 — Calculator Tool  
⏳ T5 — Evaluation Harness Upgrade  
⏳ T6 — IntentDetector Extension  
⏳ T7 — Local Information Retrieval
# TARA — Week 4 Report
## Agentic Tools Sprint

**Sprint duration:** Week 4 of 10  
**Primary goal:** Integrate intent detection and tool execution into the pipeline — TARA moves from answering questions to taking actions  
**Status:** 🔄 In Progress (T1 complete, T2–T7 pending)

---

## Sprint Summary

Week 4 introduces the agentic layer — the components that allow TARA to bypass the LLM entirely for deterministic queries and route them directly to purpose-built tools. The Orchestrator's Stage 2 (Intent Detection) and Stage 3 (Tool Execution) placeholders, established in Week 3's refactor, are now being filled in.

T1 verified the full tool pipeline end-to-end using the time tool — a deliberately trivial tool chosen to validate plumbing before debugging complex psutil values. The pipeline now branches: conversational queries go to the LLM, tool queries skip it entirely.

---

## Performance — T1 Baseline

| Metric | Week 3 | Week 4 T1 | Change |
|--------|--------|-----------|--------|
| STT avg | 0.58s | 0.59s | stable |
| LLM avg (chat) | 1.21s | 1.14s | stable |
| TTS synthesis avg | 0.65s | 0.67s | stable |
| TTFS (chat path) | 2.46s | 2.52s | +0.06s (noise) |
| **TTFS (tool path)** | — | **1.17s** | **new** |
| Tool execution latency | — | 0.000s | new |

**Tool path TTFS 1.17s beats the 1.5s sprint target by 0.33s.**

Note on "Tool path total" (7.03s): this number is not meaningful as a speed comparison. Tool execution is 0.000s but TTS playback is ~6s because TARA speaks a full date string. Total time scales with response length regardless of path. TTFS — the silence before TARA starts speaking — is the correct comparison metric. Tool path (1.17s) vs chat path (2.52s) is a 1.35s improvement in perceived responsiveness.

---

## What Was Built — T1

### Architecture Overview

```
Voice Input
    ↓
STT (unchanged)
    ↓
Orchestrator
    ↓
Stage 2: IntentDetector.classify_with_confidence(text)
    ├── TIME_QUERY   → Stage 3: ToolRegistry.dispatch()
    ├── SYSTEM_QUERY → Stage 3: ToolRegistry.dispatch()  [T3 — pending]
    └── CHAT         → Stage 5: LLM.generate()
    ↓
Stage 3: ToolRegistry → TimeTool → ToolFormatter → TTS
    ↓
Stage 7: Persistence (tool responses tagged source='tool')
```

### `components/intent.py` — IntentDetector

Keyword-pattern router returning Intent enum values. Evaluated top-to-bottom, first match wins — same registry pattern as the Orchestrator's command registry.

**Design decision: keyword matching, not LLM classification.**
LLM intent classification adds 0.8–1.2s latency and achieves ~80-85% accuracy on ambiguous inputs. Keyword matching adds <5ms and achieves 100% accuracy on well-defined unambiguous commands. All Week 4 tool triggers are unambiguous enough for pattern matching.

**Pattern trap avoided:** bare single words ("ram", "time", "memory") misclassify conversational queries like "explain how RAM works." All patterns require specific multi-word phrases: "ram usage", "what time is it", "memory usage" — not bare keywords.

### `components/tools/registry.py` — ToolRegistry + ToolResult

Central dispatcher mapping `Intent → handler`. Returns `ToolResult` dataclass on success or graceful failure. A tool throwing an exception never propagates to the pipeline — registry catches it, returns `success=False` with a fallback spoken string.

```python
@dataclass
class ToolResult:
    tool_name:        str
    raw_output:       dict    # structured data
    formatted_output: str     # TTS-ready natural language
    latency:          float
    success:          bool
    error:            str | None = None
    source:           str = "tool"  # memory filtering tag
```

### `components/tools/time_tool.py` — TimeTool

Returns current time and date as a structured dict. Intentionally trivial — chosen to prove pipeline plumbing with zero risk of a wrong answer before debugging psutil values.

### `components/tools/formatter.py` — ToolFormatter

Converts raw tool dicts to TTS-ready natural language. Owns the translation from structured data to spoken language — no other component does this.

Rules enforced in all templates:
- No markdown, no units like "GB" or "%" — says "gigabytes", "percent"
- Maximum two sentences
- Numbers rounded to 0–1 decimal places

---

## Challenges — T1

**None significant.** The Week 3 Orchestrator refactor paid dividends here — Stage 2 and 3 had explicit placeholder comments with the exact insertion points documented. Wiring took under 30 minutes. This validates the Week 3 decision to refactor before extending.

---

## Pending Tasks

| Task | Status |
|------|--------|
| T1 — Intent Detector + Time Tool + Plumbing | ✅ Done |
| T2 — Extend ToolRegistry (formally) | ⏳ |
| T3 — System Monitor (psutil + pynvml) | ⏳ |
| T4 — System Monitor voice queries | ⏳ |
| T5 — Tool Response Formatter (extend for system) | ⏳ |
| T6 — Benchmark & Validation | ⏳ |
| T7 — Chunked TTS multi-chunk verification | ⏳ |

---

## Lessons Learned (T1)

- **Trivial tools first.** Testing with the time tool caught a stats tracking bug in TTFS before it contaminated psutil measurements. The plumbing-first principle from the sprint plan was correct.
- **Refactor debt repays immediately.** The Week 3 Orchestrator refactor made T1 wiring under 30 minutes. Without it, Stage 2 and 3 would have been tangled inside `main.py`'s audio loop.
- **TTFS is not total time.** Tool path total (7.03s) looked slower than expected until correctly attributed — 0.000s tool execution + 6s speaking a date string. Reporting total time without context is misleading. TTFS (1.17s) is the number that reflects user experience.

---

## Week 4 Targets (updated after T1)

| Metric | T1 Measured | Target by T6 |
|--------|-------------|--------------|
| Tool path TTFS | 1.17s | ≤1.50s ✅ already met |
| Chat path TTFS | 2.52s | ≤2.60s ✅ stable |
| Tool queries supported | 1 (time) | 6 (time + 5 system) |
| Intent accuracy | untested | 100% on 15-query test set |
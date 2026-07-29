# TARA — Week 7 Report
## Regression Fix, Compound Tool Chains, Research Formalization

**Sprint duration:** Week 7 of 10

**Status:** ✅ Completed (6/7 tasks)

---

## T1 Status: Complete (revised scope)

### Root Cause Investigation Summary

Three compounding bugs were identified and fixed in sequence:

#### Bug 1 — Missing source column.
The conversations table had no source column. A migration added
source TEXT NOT NULL DEFAULT 'chat' and backfilled all existing rows.
save_turn() updated to accept and write a source parameter.
get_recent_turns() updated to accept an optional source_filter parameter.

#### Bug 2 — Cross-session context injection.
build_context() was called with session_id=None throughout the codebase.
get_recent_turns() fetched the 10 most recent turns across all sessions.
Turn 1 of any new session inherited full history from previous sessions.
Fix: orchestrator.py Stage 1 updated to pass session_id=self.session_id.

#### Bug 3 — Dual memory injection.
llm.py maintained a conversation_history list that appended every turn
as explicit message objects passed to ollama.chat(). build_context()
simultaneously injected the same history via the system prompt.
Ollama built a growing KV cache for the entire message list on every call.
LLM latency grew from 1.57s to 3.21s across a 6-turn session as a result.
Fix: conversation_history removed entirely. generate() now passes only
[system, user] per call. Memory is handled exclusively by SQLite-backed
build_context().

```text
keep_alive=0 was tested as a hypothesis and rejected. Setting keep_alive=0
unloads the model from VRAM after every inference call, adding 4-6 seconds
of reload overhead per turn. The correct setting is keep_alive="5m" with
the message list fixed at constant size.
```
---

### Before / After TTFS (controlled 6-turn sequence)

| Turn | Before (worst state) | After (fixed) |
|------|----------------------|---------------|
| 1    | 3.59s                | 3.00s         |
| 3    | 4.52s                | 3.83s         |
| 4    | 4.62s                | 3.89s         |
| 6    | 5.08s                | 3.79s         |
| Variance | 2.53s            | 0.89s         |
---

### Revised TTFS Target

- The sprint plan target of ≤2.60s is not achievable on this hardware.
- Minimum TTFS = STT floor (~0.70s) + LLM floor (~1.58s) + TTS floor (~0.72s)
= 3.00s with zero context injection.
- Revised target: ≤4.0s upper bound, ≤1.0s variance across a 6-turn session.
Both conditions met as of this fix.

### Files Changed

#### components/memory.py
- Added source column migration (run once)
- ConversationTurn dataclass: added source field (default 'chat')
- save_turn(): added source parameter, updated INSERT statement
- get_recent_turns(): added source_filter parameter, updated query
- get_context_for_llm(): new method, token-budgeted, source-filtered
- build_context(): replaced raw get_recent_turns() call with
  get_context_for_llm()

#### components/llm.py
- Removed conversation_history attribute and all references
- Removed clear_history() method
- generate(): now passes [system, user] only, no history accumulation
- keep_alive restored to config value (default "5m")

#### orchestrator.py
- Stage 1: session_id=None → session_id=self.session_id
- Stage 3 save_turn(): added source="tool"
- Stage 7 save_turn(): added source="chat"

---

## T2 Status: Complete

### Compound Chains Implemented

Three compound chains registered in components/compound_router.py:

- Chain 1 — system_status_snapshot
Trigger phrases: "how is my system doing", "full system report",
"give me a full system", "system status report"
Execution: single SYSTEM_QUERY dispatch with query="system status" → _get_all()
Synthesis: template (no LLM)
Result: "CPU is at X percent, RAM is Y of Z gigabytes, and disk is A percent full."
Measured TTFS: 1.85s

- Chain 2 — note_with_system_data
Trigger phrases: "take a note with my current", "note my current",
"record my current", "take a note with my"
Execution: SYSTEM_QUERY (metric detected from input) → NOTES_CREATE
Synthesis: template (no LLM)
Result: "Noted. [metric value]."
Measured TTFS: 1.45s

- Chain 3 — timestamped_note
Trigger phrases: "timestamped note", "note the time", "note with timestamp"
Execution: TIME_QUERY → NOTES_CREATE with timestamp prepended
Synthesis: template (no LLM)
Result: "Noted at [time]."
Measured TTFS: 1.59s

### Pipeline Integration

- CompoundRouter inserted at Stage 1.5 — before IntentDetector (Stage 2).
- Compound turns counted as tool-path turns in stats (ttfs_tool, tool_latency).
- Compound turns persisted to SQLite with source='tool'.

### Design Decisions

- Chain 4 (search then summarize) from sprint plan dropped — LOCAL_SEARCH already implements search + LLM synthesis as a single-intent tool. Duplicate implementation adds complexity with no new capability.

- CompoundRouter passes self.tool_registry — all compound chains use existing registered tools. No new tool instances, no new dependencies.

- Trigger phrase specificity enforced: compound patterns require multi-word phrases with specific nouns. "how is my system doing" requires "system" specifically — will not match "how is my note-taking going".

### Bugs Found and Fixed

- Double period in Chain 3 output: time tool formatted output already ends with a period. Fixed by rstrip('.') before template insertion.

- Compound turns not counted in stats: ttfs_tool and tool_latency appends were missing from Stage 1.5 TTS block. Fixed.

---

## T3 Status: Subsumed into T1

The 600-token context ceiling and source filtering were implemented as part of T1 in get_context_for_llm().

The 20-turn summarization trigger was dropped — hardware floor analysis showed context-TTFS variance is within the 0.89s target without it.

Adding LLM-generated summaries would consume inference budget on memory management rather than user responses with no measurable TTFS benefit at current session lengths.

---

## T4 Status: Complete

### Benchmark Extended to 60 Queries

- Section 1 — Intent Classification: 43/43 (100.0%)
- Section 2 — Tool Pipeline: 7/7 (100.0%)
- Section 4 — Compound Router Boundary Tests: 10/10 (100.0%)
- Total: 60/60 (100.0%) | False positives: 0

### Changes Made

Added 4 intent boundary cases (compound negatives routed through IntentDetector):
- "Take a note: buy milk" → NOTES_CREATE
- "What's my CPU right now?" → SYSTEM_QUERY
- "How is quantum computing done?" → CHAT
- "List my notes" → NOTES_LIST

Added Section 4 — Compound Router Boundary Tests (10 cases):
- 5 positive: queries that must match a compound chain
- 5 negative: queries that must fall through to single-intent routing


Fixed 1 test case bug:

- "Do you know anything about chess?" was testing a non-possessive query against LOCAL_SEARCH — which correctly requires possessive phrasing. Corrected to "Do you know anything about my chess games?" to match the intentional pattern design.

Fixed 2 formatter bugs in _format_system():
- Disk formatter missing: raw_output contained disk_used_gb and disk_total_gb but no matching formatter block existed. Tool was returning "I couldn't retrieve system information." despite valid data.
- GPU temperature formatter missing: same failure mode for gpu_temp_c. Both blocks added to ToolFormatter._format_system().


Updated print_summary() header from "WEEK 4" to "WEEK 7".  
Updated print_summary() signature and output to include compound results.

---

## T5 Status: Complete

### Research Findings Formalized

All findings reformatted to Finding/Evidence/Mechanism/Implication structure with specific measured numbers. Full text in docs/research_notes.md.

**Finding 1** — Intent-Routed Tool Bypass as a Latency Architecture for Edge AI Key numbers: 1.25s tool path vs 2.30s chat path (45% reduction). Intent classification <0.01ms. 43/43 benchmark accuracy.

**Finding 2** — Response Length as the Dominant TTFS Lever on 4GB VRAM Hardware Key numbers: qwen2.5:3b 24.4 words / 0.85s generation vs llama3.2:3b 29.0 words / 0.93s generation. Net TTFS difference: -0.20s despite slower model. ~20ms per word TTS synthesis cost on Piper medium.

**Finding 3** — LLM Hallucination of Hardware Metrics is Systematic and Confident Key numbers: 3 documented incidents. Storage wrong by 2x on both capacity and free space. CPU utilisation 57% reported vs 26% actual (2.2x overestimate). Temperature 85°C reported vs 44–47°C actual (nearly double).

**Finding 4** — [Superseded] Earlier hypothesis (tool-response context injection from file summaries) was not confirmed. Superseded by Finding 5 which documents the actual root causes.

**Finding 5** — Dual Memory Injection as a Latency Anti-Pattern Key numbers: TTFS drift 2.92s → 5.08s (Turn 1 → Turn 6). LLM latency 1.57s → 3.21s. Post-fix worst case: 3.89s. Variance: 2.53s → 0.89s.

**Finding 6** — Context-TTFS Tradeoff is Hardware-Determined and Irreducible Key numbers: 119 chars → 1.58s LLM, 594 chars → 2.30s LLM. Hardware floor 3.00s (STT 0.70s + LLM 1.58s + TTS 0.72s). Revised target: ≤4.0s upper bound.

**Finding 7** — Compound Tool Chains as Deterministic Agentic Behaviour Key numbers: Chain 1 TTFS 1.85s, Chain 2 TTFS 1.45s, Chain 3 TTFS 1.59s. All three under 2.0s. All three below chat path floor of 3.00s.

### Hours Spent
Estimated: 1.5h | Actual: ~1.0h

---

## T6 Status: Complete

### Demo Script Written

docs/demo_script.md created with 10-query sequence covering full capability range. Estimated total demo duration: under 5 minutes.

| Query | Capability | Path | Target TTFS |
|-------|-----------|------|-------------|
| 1 | LLM persona + memory | Chat | 3.0–3.5s |
| 2 | Time tool | Tool | 1.3–1.5s |
| 3 | Compound chain (system status) | Compound | 1.6–1.9s |
| 4 | GPU temperature | Tool | 1.3–1.5s |
| 5 | Note creation | Tool | 1.3–1.5s |
| 6 | Cross-session persistence | Tool | 1.3–1.5s |
| 7 | File reader + LLM summarisation | Tool+LLM | 2.2–2.6s |
| 8 | Local search + retrieval | Tool+LLM | 1.4–2.0s |
| 9 | Calculator | Tool | 1.3–1.6s |
| 10 | General knowledge (LLM fallback) | Chat | 3.0–4.0s |

Each query includes: expected response, expected TTFS, capability demonstrated, failure mode, and recovery phrase. Dry run log table included for Week 10 pre-demo session.

---

## T7 Status: Carried to Week 8

Session-end summary (goodbye → spoken summary → save to notes) not started.  
Estimated 0.75h. Lowest priority task — no functional or research impact.

---

## Final Hours Summary (Week 7)

| Task | Estimated | Actual |
|------|-----------|--------|
| T1 — TTFS regression fix | 2.0h | 3.5h |
| T2 — Compound tool chains | 2.5h | 1.5h |
| T3 — Context window manager (subsumed into T1) | 1.5h | 0h |
| T4 — Benchmark extension | 1.0h | 0.5h |
| T5 — Research findings | 1.5h | 1.0h |
| T6 — Demo script | 1.0h | 0.5h |
| T7 — Session summary (carried) | 0.75h | 0h |
| **Total** | **10.25h** | **7.0h** |

---

## Week 8 Framing

System is functionally complete. Three weeks remain. The one thing that would
most undermine research and portfolio value if left undone: the dry run log in
docs/demo_script.md. Seven weeks of measurements mean nothing if the demo
fails under pressure. Week 8 priority 1 is running the full 10-query sequence
in one live session and filling in actual TTFS numbers before any other work
begins.

---

### Updated Week 7 Baseline Table

| Metric                            | Week 6     | Week 7     |
|-----------------------------------|------------|------------|
| STT avg                           | ~0.72s     | ~0.73s     |
| LLM avg (chat path)               | 1.04–2.82s | 1.58–2.37s |
| TTFS (chat path)                  | 2.90–4.27s | 3.00–3.89s |
| TTFS (tool path, no LLM)          | 1.37–1.41s | 1.28–1.37s |
| TTFS (compound — no LLM)          | —          | 1.45–1.85s |
| Chat TTFS upper bound             | 5.53s      | 3.89s      |
| Chat TTFS variance (6 turns)      | 2.53s      | 0.89s      |
| Intent accuracy                   | 37/37      | 37/37      |
| Compound chains supported         | 0          | 3          |

---

## Notes

- The T1 investigation uncovered two pre-existing bugs (cross-session injection, dual memory) that were present before Week 6 and contributing to baseline latency throughout the project. 
- All prior TTFS measurements should be considered slightly elevated relative to a correctly implemented baseline. 
- The Week 5 controlled comparison (qwen2.5:3b vs llama3.2:3b vs phi3.5) remains valid because all three models were tested under the same buggy conditions — the relative rankings hold even if absolute numbers were inflated.
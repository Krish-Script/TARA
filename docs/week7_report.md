# TARA — Week 7 Report
## Regression Fix, Compound Tool Chains, Research Formalization

**Sprint duration:** Week 7 of 10

**Status:** 🔄️ In progress (3/7 tasks completed)

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

## Hours Spent (T1 + T2)

- T1 estimated: 2.0h | Actual: ~3.5h
- T2 estimated: 2.5h | Actual: ~1.5h
- Combined: 5.0h estimated | ~5.0h actual

## T3–T7 Status: Not started

### Week carried forward: 

- T4 (adversarial benchmark extension)
- T5 (research findings)
- T6 (demo script)
- T7 (session summary).


## Hours Spent (T1 only)
```text
Estimated: 2.0h
Actual: ~3.5h (extended by sequential root cause elimination:
source migration → cross-session bug → dual memory bug → keep_alive
false hypothesis → hardware floor confirmation)
```
## Notes

- The T1 investigation uncovered two pre-existing bugs (cross-session injection, dual memory) that were present before Week 6 and contributing to baseline latency throughout the project. 
- All prior TTFS measurements should be considered slightly elevated relative to a correctly implemented baseline. 
- The Week 5 controlled comparison (qwen2.5:3b vs llama3.2:3b vs phi3.5) remains valid because all three models were tested under the same buggy conditions — the relative rankings hold even if absolute numbers were inflated.
# TARA — Adversarial Robustness Test
**Date:** 2026-08-02
**Version:** 0.26.0
**Tester:** Krishnendu

---

## Category 1 — Long Inputs

| ID | STT Output | Intent | TARA Response | TTFS | Verdict |
|----|-----------|--------|--------------|------|---------|
| C1-A | "...what my current CPU usage is before I start my next task." | SYSTEM_QUERY (matched: 'cpu usage') | CPU usage is at 50 percent. | 2.16s | ✅ |
| C1-B | "...take a note that says I need to remember to call my doctor on Thursday morning." | NOTES_CREATE (matched: 'take a note') | Note saved: I need to remember to call my doctor on Thursday morning. | 1.63s | ✅ |
| C1-C | "...what time is it right now on this fine evening?" | TIME_QUERY (matched: 'what time is it') | It's 07:20 PM on Tuesday, August 04, 2026. | 1.68s | ✅ |

## Category 2 — Very Short Inputs

| ID | STT Output | Intent | TARA Response | TTFS | Verdict |
|----|-----------|--------|--------------|------|---------|
| C2-A | "CPU" | CHAT (no pattern match) | A CPU is like the captain of a ship; it's in charge of directing all the operations in a computer. | 2.73s | ✅ |
| C2-B | "time" | CHAT (no pattern match) | Time is like a river that flows continuously, marking moments and cycles through days, weeks, years, and more. | 2.34s | ✅ |
| C2-C | "notes" | CHAT (no pattern match) | Sure, notes can help keep track of important information or tasks. How can you use them effectively for your favorite color blue, Krishnendu? | 2.24s | ✅ (degraded — stored facts bled into ambiguous response) |

**C2 finding:** Single-word inputs consistently fall to CHAT — expected and acceptable. C2-C demonstrates that injected memory context can produce irrelevant responses on ambiguous inputs. This is a known LLM behaviour, not a routing failure. Single-word queries are not a supported interaction pattern for this assistant.

## Category 3 — Ambiguous Queries

| ID | STT Output | Intent | TARA Response | TTFS | Verdict |
|----|-----------|--------|--------------|------|---------|
| C3-A | "What's my memory?" | CHAT (no pattern match) | Your memory likely refers to your personal history and experiences stored in your mind. | 2.54s | ✅ (routing correct — "memory" without "usage" doesn't trigger SYSTEM_QUERY; LLM interpreted human memory) |
| C3-B | "Show me what you know." | CHAT (no pattern match) | Sure, I can demonstrate with a simple Python code snippet or explain a basic concept about neural networks. | 2.86s | ✅ (routing correct — LOCAL_SEARCH requires possessive + topic; LLM response coherent but generic) |
| C3-C | "What time does the file say?" | CHAT (no pattern match) | Could you please clarify which file you are referring to? | 2.02s | ✅ (best response in category — LLM correctly identified ambiguity and asked for clarification) |

**C3 finding:** All three ambiguous inputs fell to CHAT correctly — no false positive tool routing. C3-A exposes a pattern coverage gap: "What's my memory?" does not trigger SYSTEM_QUERY because RAM patterns require explicit "RAM" or "memory usage" phrasing. This is a documented design decision, not a bug — the specificity requirement prevents false positives on "Do you have a good memory?" and similar queries already in the benchmark. C3-C produced the strongest response: the LLM correctly identified an underspecified query and asked for clarification rather than guessing.

## Category 4 — Rapid Succession

| ID | STT Output | Intent | TARA Response | TTFS | Verdict |
|----|-----------|--------|--------------|------|---------|
| C4-A | "What time is it?" | TIME_QUERY | It's 07:34 PM on Tuesday, August 04, 2026. | 1.37s | ✅ |
| C4-B | "What's my CPU usage?" | SYSTEM_QUERY | CPU usage is at 33 percent. | 1.13s | ✅ |
| C4-C | "Calculate 10 plus 20." | CALCULATION | That's 30. | 1.09s | ✅ |

**C4 finding:** TTFS decreased across the sequence (1.37s → 1.13s → 1.09s) under rapid succession — no latency spike, no Ollama reload overhead. keep_alive="5m" maintains model in VRAM between calls as intended. This directly validates the Week 7 decision to reject keep_alive=0, which added 4–6s reload overhead per turn. All three queries remained within tool path target (≤1.50s).

## Category 5 — Empty or Noise Input

| ID | STT Output | Intent | TARA Response | TTFS | Verdict |
|----|-----------|--------|--------------|------|---------|
| C5-A | None — no speech detected | None | [Waiting for speech...] | — | ✅ |
| C5-B | None — desk tap below threshold | None | [Waiting for speech...] | — | ✅ |
| C5-C | None — breath below threshold | None | [Waiting for speech...] | — | ✅ |

---

## Fixes Applied

| Issue | Category | Fix | Status |
|-------|----------|-----|--------|
| None required | — | — | — |

---

## Summary

| Category | Pass | Fail | Notes |
|----------|------|------|-------|
| C1 — Long inputs | 3 | 0 | Buried triggers route correctly regardless of surrounding words |
| C2 — Short inputs | 3 | 0 | All fall to CHAT — expected. C2-C response degraded by memory context bleed |
| C3 — Ambiguous | 3 | 0 | No false positive tool routing. "What's my memory?" exposes RAM pattern gap — documented |
| C4 — Rapid succession | 3 | 0 | TTFS decreased under load — keep_alive working correctly |
| C5 — Empty/noise | 3 | 0 | speaking_started guard blocks all non-speech input cleanly |
| **Total** | **15** | **0** | No fixes required. Two findings documented. |

---

## Research Notes

Two findings from adversarial testing worth adding to research_notes.md:

**Pattern specificity tradeoff (C3-A):** "What's my memory?" does not trigger SYSTEM_QUERY. This is the correct behaviour — the benchmark already includes "Do you have a good memory?" as a confirmed CHAT case. Pattern specificity that prevents false positives also creates coverage gaps on near-miss phrasings. This is an inherent tradeoff in keyword-based routing with no clean resolution.

**keep_alive validation (C4):** Rapid succession tool queries showed decreasing TTFS across the sequence — confirming model stays loaded in VRAM between calls. keep_alive="5m" is validated as the correct setting for demo conditions where queries arrive within seconds of each other.
# TARA — Known Limitations

Documented limitations as of Week 5 of 10. Each entry includes root cause and whether a fix is planned.

---

## Response Length

**Limitation:** Creative, persona, and multi-part list prompts produce responses longer than one sentence despite the one-sentence system prompt constraint.

**Root cause:** qwen2.5:3b cannot hold two conflicting generation modes simultaneously — "respond in character as X" and "maximum one sentence." The persona instruction activates an elaboration mode that overrides the length constraint. Post-processing truncation was evaluated and rejected.

**Decision:** Accept and document (Option B). TARA is a productivity assistant; persona prompts are edge cases.

**Affected queries:** "Explain X like a pirate / medieval knight / child", multi-step questions ("list 3 differences between X and Y")

**Fix planned:** No. Post-processing truncation would degrade response quality without solving the underlying model behaviour.

---

## STT Name Correction Side Effect

**Limitation:** The STT correction `r"\bkrishna\b"` → `"krishnendu"` fires on queries about Krishna the deity or any person named Krishna.

**Root cause:** Substring-level corrections cannot distinguish misrecognitions from valid usage without semantic context.

**Examples that trigger incorrectly:** "Tell me about Krishna", "Who was Krishna in the Mahabharata?"

**Fix planned:** No fix at this level. Future intent-aware correction (Week 7+) could suppress correction when a CHAT intent about a named entity is detected.

---

## CPU Temperature Unavailable on Windows

**Limitation:** CPU temperature is not readable via `psutil.sensors_temperatures()` on Windows without third-party sensor drivers.

**Root cause:** `sensors_temperatures()` is a Linux/macOS API. Windows requires WMI or third-party drivers (OpenHardwareMonitor, HWiNFO) to expose CPU thermal data.

**Current behaviour:** TARA reports "CPU temperature is unavailable on this system" gracefully. GPU temperature via pynvml works correctly.

**Fix planned:** WMI-based CPU temperature query in Week 7+ if prioritised.

---

## File Management — Not Implemented

**Limitation:** File management is listed as a key functional requirement in the project objective. It is not implemented as of Week 5.

**Fix planned:** Week 6, first task.

---

## Information Retrieval — Not Implemented

**Limitation:** Information retrieval is listed as a key functional requirement in the project objective. It is not implemented as of Week 5.

**Fix planned:** Week 6.

---

## TTFS on Chat Path (~2.30s)

**Limitation:** Chat path TTFS of 2.30s means approximately 2.3 seconds of silence between the user finishing speaking and TARA beginning to respond. This is perceptible.

**Root cause:** STT (0.59s) + LLM generation (1.04s) + TTS synthesis (0.66s) are sequential and largely irreducible on this hardware. The LLM cannot generate faster without a larger VRAM budget.

**Fix planned:** Streaming LLM output (Week 7+) would allow TTS synthesis to begin before LLM generation completes, potentially reducing TTFS to ~1.5s on the chat path.

---

## VRAM Misroute on Ambiguous STT

**Limitation:** If Whisper mishears "how much VRAM" as "so much VRAM", the query routes to LLM which fabricates a plausible-sounding but wrong VRAM value.

**Root cause:** "so much" correction was removed (Week 5 T6) because it caused false positives on valid English. The misroute can still occur if the STT output does not match any SYSTEM_QUERY pattern.

**Current behaviour:** LLM will fabricate hardware values. User receives wrong information with no indication it is fabricated.

**Fix planned:** Confidence threshold on intent classification (Week 7+) — if no pattern matches with sufficient specificity, ask for clarification rather than routing to LLM.

---

## Error Handling

**Limitation:** Error handling is listed as a key functional requirement ("robust error handling and recovery mechanisms") in the project objective. The current implementation catches all exceptions in the main loop and speaks "Sorry, something went wrong." This is a crash suppressor, not a recovery mechanism.

**What is missing:** Per-component error classification, graceful degradation (e.g. TTS failure → print response to terminal), retry logic for transient tool failures, session state preservation across errors.

**Fix planned:** Week 6–7. This gap must be closed before the project is presented as production-ready.

---

## Chunked TTS on Single-Sentence Responses

**Limitation:** Chunked TTS streaming (Week 3 T6) provides no benefit for single-sentence responses — threading overhead adds ~0.1–0.2s with zero parallelism gain.

**Current behaviour:** Sequential fallback is used for single-chunk responses. Multi-sentence benefit only materialises for 2+ sentence responses.

**Fix planned:** Streaming LLM output would provide first-word-level chunking regardless of sentence count. Deferred to Week 7+.
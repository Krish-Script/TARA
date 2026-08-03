# TARA — Known Limitations

Documented limitations as of Week 8 of 10. Each entry includes root cause and whether a fix is planned.

---

## VAD Silence Detection Window Excluded from Logged TTFS

**Limitation:** All logged TTFS measurements throughout the project exclude the `silence_duration` window in `record_audio()`. The recorder waits `silence_duration` seconds of silence after the user stops speaking before passing audio to Whisper. This wait is not captured in `stt_latency` because `start = time.time()` is set at the beginning of `transcribe()`, which is called after `record_audio()` returns.

**User-perceived TTFS = logged TTFS + silence_duration.**

| Period | silence_duration | User-perceived overhead |
|--------|-----------------|------------------------|
| Weeks 1–7 | 1.8s | +1.8s on every query |
| Week 8 onward | 0.8s | +0.8s on every query |

**Root cause:** Configuration parameter was set to a conservative default (1.8s) and never calibrated against the actual ambient noise floor. Noise floor measured at Week 8 as mean amplitude ~1.5 against a threshold of 300 — 200× headroom.

**Fix applied (Week 8):** `silence_duration` reduced to 0.8s. Mid-sentence pause test confirmed no clipping. User-perceived TTFS improvement: 1.0s across all paths.

**Residual limitation:** The 0.8s window is still user-perceived latency that does not appear in any logged TTFS number. Research findings annotated accordingly.

**Fix planned:** No further reduction recommended without VAD endpoint detection replacing the fixed-duration silence window. Implementing proper VAD-based endpoint detection (e.g. Silero VAD) would reduce this to ~0.1–0.2s but is out of scope for this project.

---

## Session Summary Skipped on LLM Timeout

**Limitation:** If the LLM call inside `_generate_session_summary()` does not return within 5.0 seconds, the spoken summary and note save are both skipped. TARA exits cleanly after the goodbye phrase with no user-visible indication that the summary was skipped.

**Root cause:** Intentional design — a stalled summary call on exit would be a demo-critical failure. The timeout guard prioritises clean shutdown over summary completeness.

**Current behaviour:** Warning logged to error log. No note saved for that session. The goodbye phrase has already been spoken before the summary attempt begins.

**Fix planned:** No. The 5.0s timeout is generous for a short single-turn LLM call on warm VRAM. A genuine stall at this stage indicates a deeper Ollama issue that a longer timeout would not resolve.

---

## Response Length

**Limitation:** Creative, persona, and multi-part list prompts produce responses longer than one sentence despite the one-sentence system prompt constraint.

**Root cause:** qwen2.5:3b cannot hold two conflicting generation modes simultaneously — "respond in character as X" and "maximum one sentence." The persona instruction activates an elaboration mode that overrides the length constraint.

**Decision:** Accept and document. TARA is a productivity assistant; persona prompts are edge cases. Longer responses on creative prompts are documented in research findings as an accepted trade-off rather than a bug.

**Fix planned:** No.

---

## STT Name Correction Side Effect

**Limitation:** The STT correction `r"\bkrishna\b"` → `"krishnendu"` fires on queries about Krishna the deity or any person named Krishna.

**Root cause:** Substring-level corrections cannot distinguish misrecognitions from valid usage without semantic context. The same constraint applies to all entries in `_STT_CORRECTIONS`.

**Examples that trigger incorrectly:** "Tell me about Krishna", "Who was Krishna in the Mahabharata?"

**Fix planned:** No fix at this level. Intent-aware correction would require semantic context unavailable at the STT correction stage.

---

## "Tara" Casing in Note Content

**Limitation:** When the user says "TARA" in a dictated note, Whisper transcribes it as "Tara" (title case) rather than "TARA" (all caps). Notes are saved and retrieved correctly — only the visual casing is affected.

**Root cause:** Whisper treats "TARA" as a proper noun and applies standard title-case capitalization. The "Tharal" misrecognition is corrected; "Tara" is phonetically correct and not correctable without false-positive risk on legitimate uses of the word.

**Fix planned:** No. Functionally correct; cosmetically imperfect.

---

## CPU Temperature Unavailable on Windows

**Limitation:** CPU temperature is not readable via `psutil.sensors_temperatures()` on Windows without third-party sensor drivers.

**Root cause:** `sensors_temperatures()` is a Linux/macOS API. Windows requires WMI or third-party drivers to expose CPU thermal data.

**Current behaviour:** TARA reports "CPU temperature is unavailable on this system" gracefully. GPU temperature via pynvml works correctly.

**Fix planned:** No. WMI-based CPU temperature query is out of scope for remaining weeks.

---

## TTFS on Chat Path (~3.00s hardware floor)

**Limitation:** Chat path logged TTFS of 3.00s minimum means approximately 3.80s of user-perceived silence (3.00s + 0.8s VAD window) between the user finishing speaking and TARA beginning to respond. This is perceptible.

**Root cause:** STT (~0.70s) + LLM generation (~1.58s) + TTS synthesis (~0.72s) are sequential and irreducible on this hardware. The 3.00s floor was confirmed post-fix in Week 7 after dual memory injection was removed.

**Prior documentation:** This limitation was previously documented as "~2.30s" — that number was measured under dual-injection conditions (Week 5) and is no longer the correct floor. The correct post-fix floor is 3.00s logged / ~3.80s user-perceived.

**Fix planned:** Streaming LLM output would allow TTS synthesis to begin before LLM generation completes, potentially reducing logged TTFS to ~1.5s on the chat path. Out of scope for remaining weeks.

---

## LOCAL_SEARCH: Two LLM Calls Per Query

**Limitation:** LOCAL_SEARCH uses two sequential LLM calls: one for keyword extraction and one for answer synthesis. This produces TTFS of 1.4–2.0s on the tool path — higher than single-tool no-LLM paths (1.17–1.53s).

**Root cause:** Architectural choice. Keyword extraction via LLM allows flexible natural language matching rather than fixed pattern triggers. Synthesis via LLM allows multi-source answer generation from notes and facts.

**Current behaviour:** Acceptable within target range. Two-call latency is consistent and does not grow with session length (no conversation history injected).

**Fix planned:** No. The two-call architecture is intentional. Keyword extraction could be replaced with regex stripping of possessive patterns, but this would reduce flexibility. Out of scope.

---

## VRAM Misroute on Ambiguous STT

**Limitation:** If Whisper mishears a SYSTEM_QUERY trigger phrase, the query routes to CHAT and the LLM fabricates a plausible-sounding but wrong hardware value.

**Root cause:** No confidence threshold on intent classification. If no pattern matches, the query falls through to CHAT regardless of whether the original intent was deterministic.

**Current behaviour:** LLM will fabricate hardware values with no uncertainty signal. This is documented as Finding 3 in research_notes.md.

**Fix planned:** No for this project. A confidence threshold or clarification request on ambiguous inputs would require architectural changes out of scope for remaining weeks.

---

## Chunked TTS on Single-Sentence Responses

**Limitation:** Chunked TTS streaming provides no benefit for single-sentence responses. Threading overhead adds ~0.1–0.2s with zero parallelism gain.

**Current behaviour:** Sequential fallback used for single-chunk responses. Multi-sentence benefit only materialises for 2+ sentence responses.

**Fix planned:** Streaming LLM output would provide first-word-level chunking regardless of sentence count. Out of scope.

---

## ~~File Management — Not Implemented~~ ✅ Resolved (Week 6)

File reader tool implemented in Week 6.

---

## ~~Information Retrieval — Not Implemented~~ ✅ Resolved (Week 6)

LOCAL_SEARCH tool implemented in Week 6 with SQLite facts store and filesystem note retrieval.

---

## ~~Error Handling — Crash Suppressor Only~~ ✅ Resolved (Week 6)

Three-tier error handling implemented in Week 6: component crash isolation, graceful degradation per component, session state preservation across errors.
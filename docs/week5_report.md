# TARA — Week 5 Report
## Model Evaluation, Prompt Engineering, Pipeline Polish

**Sprint duration:** Week 5 of 10  
**Primary goal:** Evaluation harness before model upgrade. Fix known bugs before adding complexity.  
**Status:** ✅ Completed

---

## Uncomfortable truth first

The project objective lists "file management" as a key functional requirement under agentic tool execution. At the halfway point of the 10-week sprint, zero file management capability exists. This is not a stretch goal that slipped — it is a stated requirement. Week 6 must open with it.

---

## Sprint Summary

Week 5 established the first quantitative quality baseline for TARA and made the first evidence-based model upgrade decision in the project. Every previous quality assessment was based on impression. T3 changed that. The model upgrade (llama3.2:3b → qwen2.5:3b) was decided entirely from harness scores, not from subjective impressions during testing.

T5 surfaced a model capability ceiling: qwen2.5:3b cannot reliably hold two conflicting instructions simultaneously — "respond in character as X" and "maximum one sentence." The decision was made to accept this as a documented limitation rather than apply post-processing truncation. The reasoning: TARA is a productivity assistant, not a creative writing tool. Persona prompts are edge cases. Creativity should not be killed for rigid standardisation.

---

## Final Performance Baseline

| Metric | Week 4 | Week 5 | Change |
|--------|--------|--------|--------|
| STT avg | 0.69s | 0.72s | stable |
| LLM avg (chat, normal queries) | 0.94s | 1.04s | +0.10s |
| TTS synthesis avg | 0.72s | 0.78s | stable |
| TTFS (chat path, normal queries) | 2.50s | 2.30s | **-0.20s** |
| TTFS (tool path) | 1.37s | 1.25s | **-0.12s** |
| Intent accuracy | 22/22 | 22/22 | stable |
| Model | llama3.2:3b | qwen2.5:3b | upgraded |

---

## What Was Built

### T1 — Bug Fixes

**TTS pronunciation preprocessing** — `_preprocess_for_tts()` in `components/tts.py`. VRAM replaced before RAM to prevent partial-match corruption. CPU/GPU omitted — letter-by-letter is correct pronunciation for those.

**`_cap_first()` replacing `.capitalize()`** — `str.capitalize()` lowercases all characters after the first. "VRAM is..." → "Vram is...". `_cap_first()` uppercases index 0 only.

**Intent pattern extensions** — Three LLM hallucination incidents identified missing patterns (storage, CPU utilisation variants). Benchmark extended to 22 cases, 22/22 (100%).

---

### T2 — Context Injection Optimisation

Stage 2 (intent detection, 0ms) moved before Stage 1 (memory retrieval) in `_run_pipeline()`. Memory context now only built for CHAT intent.

Result: Chat TTFS 2.49s → 2.26s. Tool TTFS 1.59s → 1.17s. Cross-path memory integrity confirmed — chat recall unaffected by intervening tool turns.

---

### T3 — Model Evaluation Harness

`tests/test_model_eval.py` — 15-query harness, three categories. Identified scorer bug (digit "2" vs word "two") and semantic failure (model arguing with injected VRAM fact). Both corrected before T4.

**llama3.2:3b baseline (corrected):**

| Category | Score |
|----------|-------|
| A — Format compliance | 5/5 |
| B — Context recall | 5/5 |
| C — Avg word count | 29.0 words |
| LLM warm latency | 0.93s |

---

### T4 — Model Upgrade Evaluation

| Metric | llama3.2:3b | phi3.5 | qwen2.5:3b |
|--------|-------------|--------|------------|
| Category A | 5/5 | **2/5** | 5/5 |
| Category B | 5/5 | 4/5 | 5/5 |
| Category C avg | 29.0w | 34.0w | **24.4w** |
| Warm LLM latency | 0.93s | 2.80s | 0.85s |
| Chat TTFS | 2.50s | rejected | **2.30s** |

phi3.5 eliminated on two independent grounds: Category A 2/5 (fails upgrade rule); self-commentary appended to responses would be spoken aloud by Piper ("Note: The above response meets the criteria..."). qwen2.5:3b selected — 16% shorter responses, same quality scores, keep_alive confirmed over 7.5-minute idle test, 22/22 intent benchmark unaffected.

---

### T5 — Prompt Engineering

**System prompt restructured.** Closing instruction ("Always respond exactly like these examples") was placed before the three new few-shot examples added during testing, causing the model to read them as outside the rule. Instruction moved to the end of the example block.

**Formatter tool framing fix.** CPU tool framing example ("Your CPU is running at 51 percent right now") was added to the system prompt — which is injected only on CHAT turns. Tool path queries never reach the LLM. Fix applied correctly in `components/tools/formatter.py` instead: "CPU is at" → "your CPU is at".

**Creative length — documented limitation (Option B).** Persona and "explain like" prompts consistently produced 40-80 word multi-sentence responses despite the one-sentence constraint. Two additional few-shot examples were added demonstrating short persona responses. Effect: marginal.

Root cause: qwen2.5:3b cannot hold "respond in character as X" and "maximum one sentence" simultaneously. The creative persona instruction activates an elaboration mode that overrides the length constraint. Post-processing truncation (Option A) was considered and rejected — creativity should not be killed for rigid standardisation on a productivity assistant where persona prompts are edge cases.

**Documented limitation:** Creative, persona, and multi-part list prompts may produce responses longer than one sentence. All factual, system monitoring, memory, and time queries behave within the one-sentence constraint.

---

## Hallucination Log — T1

| Query | Routed to | LLM response | Actual | Error |
|-------|-----------|-------------|--------|-------|
| "How much storage is left?" | LLM | 83.5GB free / 1TB | 41GB / 512GB | Both figures fabricated |
| "For the CPU utilization" | LLM | 57% | 26% | 2.2× wrong |
| "What's the CPU used?" | LLM | 57% | 26% | 2.2× wrong |

---

## Open Gap — Project Objective vs Implementation

| Stated requirement | Status |
|-------------------|--------|
| Real-time voice input | ✅ |
| Offline speech recognition | ✅ |
| Local LLM inference | ✅ |
| Context-aware dialogue management | ✅ |
| System monitoring | ✅ |
| **File management** | **❌ Not built** |
| **Information retrieval** | **❌ Not built** |
| Natural voice response | ✅ |
| Modular architecture | ✅ |
| Thermal-aware operation | ✅ (GPU temp) |
| Resource-efficient operation | ✅ |

File management and information retrieval are Week 6 priorities, not optional features.

---

## Lessons Learned

- **Evaluation before upgrade is not bureaucracy.** phi3.5 would have been a regression — self-commentary spoken aloud by Piper, 2/5 format compliance. Without the harness, that wouldn't have been known until Week 6.
- **System prompt placement matters.** The closing instruction appearing before the final few-shot examples caused those examples to be read as outside the rule. Order is semantics, not just style.
- **Tool response formatting belongs in the formatter, not the system prompt.** Tool path queries never reach the LLM. Putting tool framing examples in the system prompt has zero effect.
- **Shorter output beats faster generation on constrained hardware.** qwen2.5:3b's LLM latency is +0.11s slower but TTFS improved -0.20s because 4.6 fewer words per response reduces TTS synthesis time more than the generation cost increase.

---

## T6 — STT Post-Recognition Correction Layer

**File:** `components/stt.py`

Added `_apply_corrections()` method with whole-word regex matching. Called inside `transcribe()` before return.

**Final dictionary — two entries removed, one retained:**

| Pattern | Replacement | Status | Reason |
|---------|-------------|--------|--------|
| `r"\bkrishna\b"` | `"krishnendu"` | ✅ Kept | Consistent misrecognition observed Week 5 |
| `"so much"` | `"how much"` | ❌ Removed | Fires on valid English ("so much pollution") — ambiguity unfixable |
| `"so many"` | `"how many"` | ❌ Removed | Same reason |

**Two bugs found and fixed during T6:**

Bug 1 — substring replacement: `str.replace("krishna", "krishnendu")` on input "krishnendu" produced "krishnendundu". Fixed with `re.sub` + `\b` word boundary — matches standalone word only.

Bug 2 — "so much pollution" → "how much pollution": Correction fired on grammatically correct English with no way to distinguish from the intended misrecognition case. Removed permanently. This is a fundamental limitation: substring-level corrections cannot distinguish misrecognitions from valid usage without semantic context.

**Rule enforced going forward:** Every entry in `_STT_CORRECTIONS` must be an observed misrecognition, not a predicted one. Each entry overrides Whisper output — wrong corrections produce silent misroutes harder to debug than the original error.

**Known caveat:** `r"\bkrishna\b"` will fire on queries about Krishna the deity. Documented in `docs/known_limitations.md` (T7).

---

## T7 — Midpoint Documentation

Three files created and committed:

**`README.md`** — full project overview including capability table, 7-stage pipeline diagram, Week 5 performance baseline, hardware requirements, setup instructions, and known limitations summary.

**`docs/known_limitations.md`** — eight documented limitations with root cause, current behaviour, and fix status for each. Key entries: creative length accepted as documented behaviour; CPU temperature unavailable on Windows; file management and information retrieval not implemented; error handling gap explicitly documented.

**`docs/research_notes.md`** — two sections:

*What has been measured that is worth reporting:*
- Tool-path vs chat-path TTFS: 45% reduction (1.25s vs 2.30s) by bypassing LLM for deterministic queries — with supporting hallucination log showing LLM fabricates hardware values when queries misroute
- Response length as the primary TTFS lever: qwen2.5:3b is +0.11s slower than llama3.2:3b but -0.20s faster TTFS because 4.6 fewer words per response reduces TTS synthesis cost more than generation cost increased
- LLM hardware hallucination is systematic — three incidents, all producing plausible-sounding but wrong values with no uncertainty signal

*What has not been measured that would be worth measuring:*
- Pareto frontier between VRAM and format compliance across model sizes
- Memory injection overhead growth at scale (50+ facts, 200+ turns)
- STT error rate on domain-specific vocabulary

**Gap identified during T7:** The project objective states "robust error handling and recovery mechanisms" as a key functional requirement. The current implementation catches all exceptions in the main loop and speaks "Sorry, something went wrong." This is a crash suppressor, not a recovery mechanism. No per-component error classification, graceful degradation, or retry logic has been built. This is documented in `known_limitations.md` and is a Week 6–7 priority.

---

## Sprint Outcome

✅ T1 — TTS pronunciation, capitalisation fix, 22 intent patterns  
✅ T2 — Stage 2 before Stage 1, memory skipped on tool path  
✅ T3 — Model evaluation harness, corrected llama3.2:3b baseline  
✅ T4 — qwen2.5:3b selected: 5/5 A, 5/5 B, 24.4w avg, 2.30s TTFS  
✅ T5 — Prompt restructured, tool framing in formatter, creative length documented  
✅ T6 — STT correction layer with regex word boundaries  
✅ T7 — README, known_limitations.md, research_notes.md  

**Two stated requirements remain unimplemented:** file management, information retrieval. Both are Week 6 first priorities.
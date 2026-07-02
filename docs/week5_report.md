# TARA — Week 5 Report
## Model Evaluation, Prompt Engineering, Pipeline Polish

**Sprint duration:** Week 5 of 10  
**Primary goal:** Evaluation harness before model upgrade. Fix known bugs before adding complexity.  
**Status:** 🔄 In Progress (T1–T4 complete, T5–T7 pending)

---

## Sprint Summary

Week 5 established the first quantitative quality baseline for TARA and made the first evidence-based model upgrade decision in the project. Every previous quality assessment — including "few-shot prompting works" from Week 2 — was based on impression rather than measurement. T3 changed that.

The model upgrade decision (llama3.2:3b → qwen2.5:3b) was made entirely from harness data, not from subjective impressions during testing. The decision rule was set before running T4: upgrade only if Category A score matches baseline AND chat TTFS stays under 2.80s. qwen2.5:3b met both criteria. phi3.5 was eliminated on two independent grounds.

---

## Final Performance Baseline — T4

| Metric | Week 4 | Week 5 (qwen2.5:3b) | Change |
|--------|--------|---------------------|--------|
| STT avg | 0.69s | 0.59s | -0.10s |
| LLM avg (chat) | 0.94s | 1.04s | +0.10s |
| TTS synthesis avg | 0.72s | 0.66s | -0.06s |
| TTFS (chat path) | 2.50s | **2.30s** | **-0.20s** |
| TTFS (tool path) | 1.37s | 1.37s | stable |
| keep_alive confirmed | ✅ | ✅ | 7.5 min idle test |
| Intent accuracy | 22/22 | 22/22 | unaffected by model swap |

LLM latency increased +0.10s but TTFS improved -0.20s. The improvement comes from qwen2.5:3b's shorter average responses (24.4 vs 29.0 words) reducing TTS synthesis time — same compounding effect observed in Week 2 when prompt engineering cut response length.

---

## What Was Built

### T1 — Bug Fixes

**TTS pronunciation preprocessing** — `_preprocess_for_tts()` in `components/tts.py`. "RAM" → "Ram", "VRAM" → "V Ram". CPU/GPU intentionally omitted — letter-by-letter is correct for those. VRAM replaced before RAM to prevent partial-match corruption.

**`_cap_first()` replacing `.capitalize()`** — Python's `.capitalize()` lowercases all characters after the first. "VRAM is..." → "Vram is...". `_cap_first()` uppercases index 0 only.

**Intent pattern extensions** — Three LLM hallucination incidents identified missing patterns. Storage queries and CPU utilisation variants added. Benchmark extended to 22 test cases, score: 22/22.

### T2 — Context Injection Optimisation

Stage 2 (intent detection, 0ms) moved before Stage 1 (memory retrieval) in `_run_pipeline()`. Memory context now only built for CHAT intent.

Result: Chat TTFS 2.49s → 2.26s (-0.23s). Tool TTFS 1.59s → 1.17s (-0.42s). Regression test confirmed cross-path memory integrity — chat recall unaffected by intervening tool turns.

### T3 — Model Evaluation Harness

`tests/test_model_eval.py` — 15-query harness across three categories. Identified a scorer bug (digit "2" vs word "two") and a semantic failure (model overriding injected VRAM fact with its own prior). Both corrected before T4.

**Corrected llama3.2:3b baseline:**

| Category | Score | Notes |
|----------|-------|-------|
| A — Format compliance | 5/5 | All responses 1 sentence, no markdown |
| B — Context recall | 5/5 | After scorer bug fix |
| C — Avg word count | 29.0 words | Well under 35-word target |
| LLM latency | 0.93s | Warm inference |

### T4 — Model Upgrade Evaluation

**Decision table:**

| Metric | llama3.2:3b | phi3.5 | qwen2.5:3b |
|--------|-------------|--------|------------|
| Category A | 5/5 | **2/5** | 5/5 |
| Category B | 5/5 | 4/5 | 5/5 |
| Category C avg | 29.0w | 34.0w | **24.4w** |
| Warm LLM latency | 0.93s | 2.80s | 0.85s |
| Chat TTFS | 2.50s | — | **2.30s** |
| Decision | baseline | **REJECT** | **UPGRADE** |

**phi3.5 eliminated on two independent grounds:**
1. Category A 2/5 — fails the upgrade rule outright
2. Self-commentary appended to responses ("Note: The above response meets the criteria...") — would be spoken aloud by Piper, making it a TTS compatibility failure

**qwen2.5:3b upgrade justified:**
- Matches llama3.2:3b on every quality metric
- 24.4 avg words (16% shorter — directly reduces TTS latency)
- keep_alive confirmed working across 7.5-minute idle test
- 22/22 intent benchmark unaffected after model swap

---

## Hallucination Log — T1

| Query | Routed to | LLM Response | Actual | Error |
|-------|-----------|-------------|--------|-------|
| "How much storage is left?" | LLM | 83.5GB free / 1TB | 41GB / 512GB | Both figures fabricated |
| "For the CPU utilization" | LLM | 57% | 26% | 2.2× wrong |
| "What's the CPU used?" | LLM | 57% | 26% | 2.2× wrong |

---

## Pending Tasks

| Task | Description |
|------|-------------|
| T5 | Prompt engineering overhaul — verify format compliance holds on qwen2.5:3b |
| T6 | STT post-recognition correction layer |
| T7 | Midpoint documentation — README + research notes |

---

## Lessons Learned

- **Evaluation before upgrade is not bureaucracy — it's how you avoid regressing.** phi3.5 failed on format compliance and would have been a clear regression from llama3.2:3b. Without the harness, that wouldn't have been known until Week 6 when responses started coming back with self-commentary spoken aloud.
- **Scorer bugs invalidate baseline data.** Category B[4] produced a false FAIL (digit "2" vs word "two") and B[5] produced a false PASS (model argued with injected fact but "4" appeared). Both required manual identification. Automatic scorers need edge case testing.
- **Shorter responses improve TTFS more reliably than faster models.** qwen2.5:3b's LLM latency is +0.10s slower than llama3.2:3b but TTFS improved -0.20s because 4.6 fewer words per response reduces TTS synthesis time. Output length is a more reliable latency lever than model speed on this hardware.
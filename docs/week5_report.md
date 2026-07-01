# TARA — Week 5 Report
## Model Evaluation, Prompt Engineering, Pipeline Polish

**Sprint duration:** Week 5 of 10  
**Primary goal:** Evaluation harness before model upgrade. Fix known bugs before adding complexity.  
**Status:** 🔄 In Progress (T1–T2 complete, T3–T7 pending)

---

## Sprint Summary

Week 5 opened with three known bugs from Week 4 and surfaced two more during T1 testing. All five were fixed before new features were added. T2 restructured the pipeline stage order — intent detection now runs before memory retrieval, eliminating SQLite overhead on the tool path.

The recurring finding this week: LLM hardware hallucination is systematic, not occasional. Storage, CPU utilisation, and temperature all produced fabricated values when queries fell through to the LLM. Pattern coverage is a correctness constraint, not a quality-of-life improvement.

---

## Performance Baseline

| Metric | Week 4 | Week 5 T1 | Week 5 T2 | Change |
|--------|--------|-----------|-----------|--------|
| STT avg | 0.69s | 0.79s | 0.66s | stable |
| LLM avg (chat) | 0.94s | 1.02s | 0.98s | stable |
| Tool execution avg | 25.3ms | 0.002s | 0.101s | stable |
| TTS synthesis avg | 0.72s | 0.73s | 0.58s | -0.14s |
| TTFS (chat path) | 2.50s | 2.49s | **2.26s** | **-0.24s** |
| TTFS (tool path) | 1.37s | 1.59s | **1.17s** | **back on target** |
| Intent accuracy | 19/19 | 22/22 | 22/22 | stable |

Chat path TTFS improved 0.24s from T1 to T2 — direct result of skipping Stage 1 memory retrieval on non-CHAT turns.

---

## What Was Built

### T1 — Bug Fixes (three issues)

**1. TTS pronunciation preprocessing**
Piper reads ALL CAPS as individual letters. "RAM" → "R-A-M", "VRAM" → "V-R-A-M". Added `_preprocess_for_tts()` in `components/tts.py`:

```python
_TTS_REPLACEMENTS = [
    ("VRAM", "V Ram"),   # spoken naturally as "V-Ram"
    ("RAM",  "Ram"),     # spoken as a word, not R-A-M
]
```

VRAM replaced before RAM — order prevents partial-match corruption. CPU/GPU intentionally omitted — letter-by-letter is correct for those.

**2. `.capitalize()` → `_cap_first()`**
`str.capitalize()` lowercases all characters after the first — "VRAM is..." → "Vram is...". Replaced throughout `formatter.py` with `_cap_first()` which uppercases only index 0.

**3. Intent pattern extensions**
Two LLM hallucination incidents during testing identified missing patterns:

| Missing query | LLM fabricated | Actual |
|---------------|---------------|--------|
| "How much storage is left?" | 83.5GB free / 1TB | 41GB free / 512GB |
| "For the CPU utilization" | 57% | 26% |
| "What's the CPU used?" | 57% | 26% |

Added to SYSTEM_QUERY patterns: "storage", "how much storage", "storage left", "storage space", "free space", "cpu utilization", "cpu load", "what's my cpu", "processor usage".

Benchmark extended from 19 to 22 test cases. Score: 22/22 (100%).

---

### T2 — Context Injection Optimisation

**Problem:** Stage 1 (memory retrieval) ran before Stage 2 (intent detection). Every tool query paid SQLite read overhead that contributed nothing to the response — tool handlers never use LLM context.

**Fix:** Reordered `_run_pipeline()` in `orchestrator.py`:

```
Before: Stage 1 (memory) → Stage 2 (intent) → Stage 3 or Stage 5
After:  Stage 2 (intent, 0ms) → Stage 1 (memory, CHAT only) → Stage 3 or Stage 5
```

**Regression test (4 turns):**

| Turn | Query | Path | Stage 1 fired | TARA response |
|------|-------|------|---------------|---------------|
| 1 | "My name is Krishna and you." | CHAT | ✅ Yes | Introduced as TARA, addressed Krishna |
| 2 | "What's my CPU usage?" | SYSTEM_QUERY | ❌ No | CPU is at 51 percent (tool) |
| 3 | "What do you remember about me?" | command registry | ❌ No | Recalled stored facts correctly |
| 4 | "What's my name?" | CHAT | ✅ Yes | "Your name is Krishna" — correct recall |

Turn 4 confirmed memory integrity: chat-path context injection works correctly after a tool-path turn that skipped Stage 1.

**Observed benefit:**
- Chat path TTFS: 2.49s → 2.26s (-0.23s)
- Tool path TTFS: 1.59s → 1.17s (-0.42s)

---

## Known Limitation — STT Name Recognition

Whisper base model consistently mishears "Krishnendu" as "Krishna". Root cause: South Asian names are underrepresented in the base model's training data. T6 (STT correction layer) addresses this directly:

```python
_STT_CORRECTIONS = {
    "so much":  "how much",
    "so many":  "how many",
    "krishna":  "krishnendu",   # STT consistently mishears
}
```

Documented caveat: "Krishna" is also a standalone proper noun (deity, common name). This correction will silently corrupt queries containing "Krishna" in a non-name context. Acceptable risk for personal assistant use; flagged for documentation.

---

## Pending Tasks

| Task | Description | Est. |
|------|-------------|------|
| T3 | Model evaluation harness — baseline llama3.2:3b | 2.0h |
| T4 | Model upgrade evaluation — phi3.5 and qwen2.5:3b | 2.0h |
| T5 | Prompt engineering overhaul — format compliance | 2.0h |
| T6 | STT post-recognition correction layer | 1.0h |
| T7 | Midpoint documentation — README + research notes | 1.0h |

**Non-negotiable:** T3 before T4. Baseline scores for llama3.2:3b must exist before evaluating candidates. Evidence first, decision second.

---

## Lessons Learned

- **LLM hardware hallucination is systematic.** Storage, CPU, and temperature all fabricated values when patterns were missing. The LLM produces plausible-sounding numbers with zero uncertainty signal. Pattern coverage is a correctness constraint.
- **Stage ordering has measurable impact.** Moving intent detection before memory retrieval cost zero new code and reduced chat path TTFS by 0.23s. Pipeline stage order is an architectural decision, not an implementation detail.
- **Test with real queries.** "How much storage is left?" and "What's the CPU used?" are natural phrasings never covered by designed test cases. Benchmark accuracy means nothing if the test set doesn't include real usage patterns.
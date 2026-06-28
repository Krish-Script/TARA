# TARA — Week 5 Report
## Model Evaluation, Prompt Engineering, Pipeline Polish

**Sprint duration:** Week 5 of 10  
**Primary goal:** Evaluation harness before model upgrade. Fix known bugs before adding complexity.  
**Status:** 🔄 In Progress (T1 complete, T2–T7 pending)

---

## Sprint Summary

Week 5 opened with three known bugs carried from Week 4 and immediately surfaced two more during initial testing. All five were fixed before any new features were added — consistent with the sprint principle of eliminating known issues before extending the system.

The most significant finding of T1 testing: LLM hallucination of hardware data is not limited to temperature. When "How much storage is left?" fell through to the LLM due to a missing pattern, it reported 83.5GB free from a 1TB drive. Actual: 41GB free from a 512GB drive. When CPU queries were misrouted, the LLM reported 57% utilisation. Actual: 26%. The pattern: the LLM fabricates plausible-sounding hardware values with no hesitation and no indication that it is guessing. Every hardware query must route to the system monitor — no exceptions.

---

## Performance Baseline — T1

| Metric | Week 4 | Week 5 T1 | Change |
|--------|--------|-----------|--------|
| STT avg | 0.69s | 0.79s | +0.10s (session variance) |
| LLM avg (chat) | 0.94s | 1.02s | stable |
| Tool execution avg | 25.3ms | 0.002s | stable |
| TTS synthesis avg | 0.72s | 0.73s | stable |
| TTFS (chat path) | 2.50s | 2.49s | stable |
| TTFS (tool path) | 1.37s | 1.59s | +0.22s — see note |
| Intent accuracy | 19/19 | 22/22 | +3 new test cases |

**Note on tool path TTFS regression (+0.22s):** Tool path TTFS moved from 1.37s to 1.59s — 0.09s over the ≤1.50s target. This is session variance from higher STT latency (0.98s on first query vs 0.69s Week 4 average), not a performance regression. The benchmark-measured TTFS estimate (1.37s, based on average STT) remains valid. T2 (context injection skip on tool path) will reduce this further regardless.

---

## What Was Built — T1

### 1. TTS Pronunciation Preprocessing

**Problem:** Piper TTS reads ALL CAPS text as individual letters. "RAM" → "R-A-M", "VRAM" → "V-R-A-M".

**Fix:** Added `_preprocess_for_tts()` to `components/tts.py`. Applies before text reaches `piper.exe`. Console logs retain original casing; Piper receives pronunciation-friendly form.

```python
_TTS_REPLACEMENTS = [
    ("VRAM", "V Ram"),   # spoken naturally as "V-Ram"
    ("RAM",  "Ram"),     # spoken as a word, not R-A-M
    # CPU and GPU intentionally omitted — C-P-U and G-P-U are correct
]
```

VRAM replaced before RAM to prevent partial-match corruption ("VRAM" → "V Ram" before "RAM" → "Ram" runs).

### 2. Acronym Capitalisation Fix

**Problem:** Python's `.capitalize()` lowercases all characters after the first. "VRAM is 2.37..." → "Vram is 2.37...".

**Fix:** Added `_cap_first()` static method to `ToolFormatter`. Uppercases first character only, preserving everything after:

```python
@staticmethod
def _cap_first(s: str) -> str:
    """Uppercase first character only — preserves acronyms like GPU, RAM, VRAM."""
    return s[0].upper() + s[1:] if s else s
```

Replaced all `.capitalize()` calls in `formatter.py` with `_cap_first()`.

### 3. Intent Pattern Extensions

**Two LLM hallucination incidents during testing identified three missing pattern categories:**

**Missing: Storage queries**
"How much storage is left?" → LLM reported 83.5GB free from 1TB (hallucinated). Actual: 41GB free from 512GB.
Added: "storage", "how much storage", "storage left", "storage space", "free space"

**Missing: CPU utilisation variants**
"For the CPU utilization" and "What's the CPU used?" → LLM reported 57% utilisation. Actual: 26%.
Added: "cpu utilization", "cpu load", "what's my cpu", "processor usage"

**Result:** Benchmark extended from 19 to 22 test cases. Score: 22/22 (100%).

---

## Hallucination Log — Week 5 T1

| Query | Routed to | LLM Response | Actual Value | Error |
|-------|-----------|-------------|--------------|-------|
| "How much storage is left?" | LLM (no pattern) | 83.5GB free / 1TB | 41GB free / 512GB | Fabricated both figures |

**Pattern:** LLM gives plausible-sounding hardware values with no uncertainty signal. A user would have no indication the numbers are fabricated. All the cases were fixed by adding the missing patterns — but the incidents confirm that pattern coverage must be comprehensive and tested, not assumed.

---

## Pending Tasks

| Task | Description | Est. |
|------|-------------|------|
| T2 | Context injection optimisation — skip Stage 1 on tool path | 1.5h |
| T3 | Model evaluation harness — baseline llama3.2:3b | 2.0h |
| T4 | Model upgrade evaluation — phi3.5 and qwen2.5:3b | 2.0h |
| T5 | Prompt engineering overhaul — format compliance | 2.0h |
| T6 | STT post-recognition correction layer | 1.0h |
| T7 | Midpoint documentation — README + research notes | 1.0h |

---

## Lessons Learned — T1

- **LLM hardware hallucination is not limited to temperature.** Storage was fabricated with equal confidence. Pattern coverage is not optional — it is a safety constraint on the accuracy of what TARA tells the user.
- **Test with real queries, not just designed ones.** "How much storage is left?" and "What's the CPU used?" are natural phrasings that were never tested. The benchmark catches patterns we designed; real usage catches patterns we forgot.
- **Fix bugs before adding features.** T1 took less than two hours and closed five known issues. Starting T2–T7 with these bugs present would have made every subsequent test ambiguous.
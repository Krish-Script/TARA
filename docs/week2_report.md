# TARA — Week 2 Report
## Voice Quality & Latency Sprint

**Sprint duration:** Week 2 of 10  
**Primary goal:** Replace pyttsx3 with Piper TTS and reduce total pipeline latency below 8s  
**Status:** ✅ Completed

---

## Sprint Summary

Week 2 had one primary objective: replace the robotic Windows SAPI5 voice (pyttsx3) with a neural offline TTS engine that sounds more human. A secondary objective emerged from Week 1's end-to-end data — TARA's responses were consistently 30–40 words long, making TTS the dominant latency cost. Both objectives were addressed: Piper replaced pyttsx3, and few-shot prompt engineering cut response length by roughly half.

Final result: **47% reduction in total pipeline latency** (13.27s → 7.06s) without changing any models.

---

## Software Stack Changes

| Component | Week 1 | Week 2 | Reason |
|-----------|--------|--------|--------|
| TTS Engine | pyttsx3 (SAPI5) | Piper TTS (neural) | Voice quality + speed |
| TTS Voice | Microsoft Zira | en_US-hfc_female-medium | More natural, female voice |
| System Prompt | Rule-based | Few-shot examples | Better instruction following on small models |

---

## Performance Comparison

| Component | Week 1 | Week 2 | Change |
|-----------|--------|--------|--------|
| STT avg | 0.62s | 0.59s | -0.03s |
| LLM avg | 1.41s | 1.05s | -0.36s |
| TTS avg | 11.23s | 5.42s | **-5.81s** |
| **Total avg** | **13.27s** | **7.06s** | **-6.21s (47%)** |

The TTS improvement (-5.81s) came from two independent sources: Piper generating audio faster than pyttsx3 spoke it, and shorter responses (from prompt engineering) reducing the audio length itself.

---

## Piper TTS Migration

### The problem with pip-based Piper on Windows

The migration was not straightforward. Two versions of `piper-tts` exist on PyPI under the same package name:

| Package | Maintainer | API | Outcome |
|---------|------------|-----|---------|
| piper-tts 1.4.2 | OHF / Home Assistant | Different, incompatible API | ❌ Failed — `sentence_silence` TypeError |
| piper-tts 1.1.x | Rhasspy (original) | Correct API | ❌ Failed — `piper-phonemize` has no Windows wheels |

Both pip-based approaches failed. The working solution was the **piper standalone binary**:
- Downloaded `piper_windows_amd64.zip` from the rhasspy GitHub releases
- Called `piper.exe` via Python `subprocess`, piping text as stdin and receiving raw PCM audio on stdout
- Played raw audio using PyAudio (already installed and confirmed working)

This approach bypasses all Python package compatibility issues entirely and is more stable than any pip-based integration.

### Voice selection

Three female voices were evaluated:

| Voice | Avg latency (short phrases) | Pipeline avg (full responses) | Decision |
|-------|----------------------------|-------------------------------|----------|
| lessac-medium (male) | 4.69s | 7.19s | Reference |
| hfc_female-medium | 4.42s | 9.84s | Selected |
| (amy-medium) | not tested | — | Skipped |

hfc_female-medium is 2.65s slower than lessac-medium per response. This was a **conscious trade-off**: character and voice quality were prioritised over those 2.65s. TARA is designed to be a persistent assistant with a consistent identity — voice character is part of that identity.

---

## Prompt Engineering

### The verbosity problem

Week 1's end-to-end data showed TARA consistently producing 30–40 word responses despite a system prompt rule saying "maximum 2–3 sentences." Example:

> *"I'm here to assist you with any questions or tasks you'd like help with, since I'm running offline on your device, I don't have access to external information or internet connectivity."* — 32 words

Rule-based prompts fail on small models. llama3.2:3b has weak instruction-following for length constraints.

### The fix: few-shot examples

Replacing rules with demonstrated examples produced immediate results:

```
Examples of correct responses:
User: How are you? TARA: I'm doing well and ready to help.
User: Why is the sky blue? TARA: Light scatters more at short wavelengths, making the sky appear blue.
User: Tell me a joke. TARA: Why don't scientists trust atoms? Because they make up everything.
```

Results after few-shot prompt:

| Before | After |
|--------|-------|
| TTS avg 9.19s | TTS avg 5.42s |
| Total avg 11.04s | Total avg 7.06s |
| 30–40 word responses | 10–15 word responses |

The model pattern-matched to the examples rather than interpreting the rules. First response after the change was word-for-word identical to the example: *"I'm doing well and ready to help."*

---

## Key Architectural Decisions

**Piper binary over pip package:** The subprocess approach adds ~50–100ms overhead per call compared to a native Python API, but eliminates all Windows-specific package compatibility issues permanently. Reliability over theoretical performance.

**Few-shot over rule-based prompting:** Established as a project-wide principle this week. Every future prompt for small-model behaviour will use demonstrated examples, not written rules. The evidence is clear: rules are interpreted, examples are imitated.

**Voice character over speed:** The 2.65s cost of hfc_female over lessac-medium was documented and accepted. TARA's identity consistency across 10 weeks matters more than those seconds.

---

## Challenges Encountered

### 1. Piper package incompatibility
Both available versions of `piper-tts` on PyPI failed for different reasons. Recognising that the binary approach was the correct solution (rather than debugging pip compatibility further) saved significant time.

### 2. Sample rate mismatch risk
Different Piper voice models output at different sample rates (16000 Hz or 22050 Hz). Playing 22050 Hz audio as 16000 Hz causes distorted, slowed speech. Verified hfc_female-medium's sample rate from its `.onnx.json` config file before finalising the configuration.

### 3. Prompt engineering iteration
Three prompt versions were tested before finding an effective one — rule-only, tightened-rules, and few-shot. Only the few-shot version produced consistent short responses. The lesson: don't iterate on rules when a fundamentally different approach (examples) is available.

---

## Lessons Learned

- **Few-shot prompting outperforms rule-based prompting for small models.** This is now a project-wide principle. Show the model what correct behaviour looks like — don't describe it.
- **TTS latency is proportional to response length, not just engine speed.** Cutting response length from 35 words to 15 words saved more latency than switching TTS engines did. Prompt engineering and TTS are not independent variables.
- **"Reliability over theoretical performance" is the right default on constrained hardware.** The piper binary subprocess approach is slightly slower in theory but works unconditionally. On a project with a 4GB VRAM ceiling and Windows-specific dependencies, reliability is more valuable than marginal speed gains.
- **Conscious trade-offs should be documented.** The decision to use hfc_female over lessac-medium (character > speed) is in the log. Future weeks can revisit it with evidence if priorities change.

---

## Sprint Outcome

✅ Piper TTS integrated via binary approach — fully offline, no pip compatibility issues  
✅ hfc_female-medium voice selected — more natural than SAPI5  
✅ Few-shot prompting reduces response length by ~55%  
✅ Total pipeline latency reduced from 13.27s to 7.06s (47% improvement)  
✅ VRAM budget unchanged — all Piper processing on CPU  

---

## Week 3 Preview

**Theme: Memory & Context**  
Implement SQLite-backed persistent memory so TARA remembers conversations across sessions. Resolve the cold-start issue permanently. Introduce TTFS (time-to-first-syllable) as the new primary latency metric.
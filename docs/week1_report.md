# TARA — Week 1 Report
## Foundation Sprint

**Sprint duration:** Week 1 of 10  
**Primary goal:** Build a working end-to-end offline voice pipeline from scratch  
**Status:** ✅ Completed

---

## Sprint Summary

Week 1 established the entire technical foundation of TARA. Starting from zero — no code, no environment, no prior data — the goal was to get three independent AI components working in isolation, then connect them into a single voice loop. By Day 5, TARA could hear speech, understand it, reason about it, and speak a response back, entirely offline.

The non-negotiable deliverable: `main.py` hears you speak, transcribes it, sends it to the LLM, and speaks the answer back before the week closes. Everything else was secondary to that.

---

## Hardware

| Component | Specification |
|-----------|---------------|
| GPU | NVIDIA GeForce RTX 3050 Laptop (4GB VRAM) |
| RAM | 16GB |
| OS | Windows 11 |
| Python | 3.11.7 |

The 4GB VRAM constraint was the defining hardware decision of the entire project. Every model selection, every component split, every architecture choice this week was made under that constraint.

---

## Software Stack

| Component | Technology | Runs On | Reason |
|-----------|------------|---------|--------|
| Speech-to-Text | faster-whisper (base, int8) | CPU | Reserves full GPU for LLM |
| Language Model | Ollama + llama3.2:3b | GPU | Fits in 4GB VRAM with headroom |
| Text-to-Speech | pyttsx3 (Windows SAPI5) | CPU | Zero setup, fully offline |
| Audio I/O | PyAudio | CPU | Microphone capture and playback |

The CPU/GPU split was a deliberate architectural decision, not a compromise. Running Whisper on CPU at int8 quantisation costs ~0.7s per transcription — an acceptable trade for keeping the full 4GB VRAM available to the LLM.

---

## Performance Baseline

### STT (Whisper base, CPU, int8)

| Round | Latency |
|-------|---------|
| 1 | 0.89s |
| 2 | 0.66s |
| 3 | 0.56s |
| **Average** | **0.70s** |

### LLM (llama3.2:3b, Ollama, GPU)

| Metric | Value | Notes |
|--------|-------|-------|
| Cold start (disk → VRAM) | 80.82s | One-time per session |
| Cold start (RAM → VRAM) | 7.30s | After first load, model cached in RAM |
| Warm inference avg | 0.68s | Stable after first load |
| VRAM steady-state | 2.2–2.5GB | 1.5–1.8GB headroom remaining |

### TTS (pyttsx3, Zira voice)

| Phrase | Latency |
|--------|---------|
| 1 (9 words) | 5.66s |
| 2 (9 words) | 5.00s |
| 3 (9 words) | 4.19s |
| **Average** | **4.95s** |

### End-to-End Pipeline

| Metric | Value |
|--------|-------|
| STT avg | 0.62s |
| LLM avg | 1.41s |
| TTS avg | 11.23s |
| **Total avg** | **13.27s** |
| Time-to-first-response (STT+LLM) | ~2.0s |
| VRAM steady-state | 2.2GB |
| Session length | 1.2 min / 3 turns |

The 11.23s TTS average reflects full 30–40 word responses. TTS duration scales linearly with response length — it is speech playback time, not processing time. The actionable latency metric is time-to-first-response (~2.0s), not total pipeline time.

---

## Challenges Encountered

### 1. PyAudio installation on Windows
`pip install pyaudio` fails on Windows — no prebuilt wheels available through the standard path. Resolved using `pip install pyaudio` after attempting `pipwin install pyaudio` (pipwin itself errored first). Documented for future environment setups.

### 2. pyttsx3 engine singleton bug
pyttsx3 only produced audio for the first `speak()` call in a session. Every subsequent call returned immediately with no audio output. Root cause: pyttsx3 maintains an internal engine cache (`_activeEngines`) and returns the same broken COM object on subsequent `init()` calls rather than creating a new one. Fix: call `pyttsx3._activeEngines.clear()` before each `init()` to force a genuinely fresh engine instance. This adds ~0.1–0.2s overhead per call but is fully reliable.

### 3. Assistant identity (ARIA → TARA)
TARA initially introduced herself as "ARIA" — a name with strong associations in AI assistant training data (Opera's browser AI is called Aria). Root cause: the system prompt said "You are ARIA" because a find-and-replace during project renaming missed the system prompt string. Fixed by manually correcting `config.py`. Documented as a small-model behaviour: llama3.2:3b has weak instruction-following for identity constraints, which influenced Week 2's prompt engineering approach.

### 4. LLM cold start (80.82s)
The first LLM response in any session took 80+ seconds due to Ollama loading the model from disk into VRAM. Subsequent responses were 0.68s (warm). Mitigated in Week 1 by documenting it as a known issue; resolved properly in Week 3 with `keep_alive` parameter.

---

## Key Architectural Decisions

**Whisper on CPU, Ollama on GPU:** The only split that makes the 4GB budget work. Whisper at int8 on CPU runs at ~0.7s — fast enough for conversational use. Any attempt to run both on GPU would exhaust VRAM.

**llama3.2:3b over larger models:** The sprint principle was "working small model beats crashing large model." 3b fits comfortably at 2.2GB steady-state. Model upgrade path (5b, 7b) deferred to Week 5 after architecture is stable.

**Isolation before integration:** Each component (STT, LLM, TTS) was tested via its own isolated test script before being connected. This discipline caught all three major bugs before they compounded in the full pipeline.

---

## Lessons Learned

- **The CPU/GPU split is not a compromise — it's a design.** Explicit resource allocation per component produces predictable, stable VRAM usage.
- **"Total pipeline latency" is a misleading metric.** TTS playback is not processing latency — it is the sound of TARA speaking. The metric that matters for responsiveness is time-to-first-response (~2.0s), established this week as the primary benchmark.
- **Isolate before integrating.** Every bug found this week (pyttsx3, identity, PyAudio) was caught in an isolated test script. If all three components had been integrated first, the same bugs would have taken three times longer to diagnose.
- **Document baseline numbers immediately.** Week 2 and 3 optimizations are only meaningful because Week 1 numbers exist to compare against.

---

## Sprint Outcome

✅ End-to-end offline voice pipeline working  
✅ All three components tested independently before integration  
✅ VRAM budget held at 2.2GB steady-state (1.8GB headroom)  
✅ Baseline performance documented  
✅ Git repository initialized with milestone commits  

---

## Week 2 Preview

**Theme: Voice Quality & Latency Reduction**  
Replace pyttsx3 with Piper TTS (neural, offline) and address TARA's response verbosity through prompt engineering. Target: reduce total latency below 8s without changing any models.
# TARA — Research Notes
## Midpoint Analysis

---

## Measurement Integrity Note

Weeks 1–6 measurements were collected under two pre-existing bugs: cross-session context injection (`session_id=None` in `build_context()`) and dual memory injection (SQLite-backed context via `build_context()` plus explicit `conversation_history` list
in `llm.py`). These inflated absolute TTFS measurements across all chat-path sessions. Bug fix applied in Week 7. Findings citing TTFS from Weeks 1–6 are annotated accordingly. Post-fix measurements use the corrected pipeline. Hardware floor confirmed at 3.00s (STT 0.70s + LLM 1.58s + TTS 0.72s).

Additionally: all logged TTFS measurements across all weeks exclude the VAD silence-detection window (`silence_duration=0.8s` post-Week-8 calibration, `1.8s` in all prior weeks). User-perceived TTFS equals logged TTFS plus the silence window duration. All relative comparisons between paths and conditions remain valid — the silence window is constant across all measurements. Absolute TTFS numbers should be interpreted as logged (pipeline-only) values, not user-perceived values.

---

## What Has Been Measured That Is Worth Reporting

## Finding 1 — Intent-Routed Tool Bypass as a Latency Architecture for Edge AI

**Finding:** For deterministic queries on constrained hardware, keyword-based intent routing produces lower TTFS and higher answer accuracy than LLM-based generation, making tool routing a correctness requirement rather than a performance optimisation.

**Evidence:** Tool path TTFS measured at 1.25s vs post-fix chat path floor of 3.00s — a 58% reduction. Pre-fix chat path TTFS was 2.30s (Week 5 baseline under dual-injection conditions); post-fix floor is 3.00s, making the tool path advantage larger than initially measured. LLM generation (1.58s minimum post-fix) is the dominant latency cost on the chat path. Tool execution (0.002–0.101s) is negligible by comparison. Intent classification latency measured at <0.01ms across 20 repeated calls. Three documented hallucination incidents confirmed LLM-generated hardware values were wrong by factors of 2–10 with no uncertainty signal.

**Mechanism:** Deterministic queries — system monitoring, time/date, arithmetic — bypass LLM inference entirely. Keyword routing matches on specific multi-word phrases in <0.01ms. Tool execution calls psutil, datetime, or safe_eval directly. The LLM forward pass, which accounts for 1.58–2.37s of chat path latency post-fix, is never
invoked. Intent accuracy measured at 60/60 (100%) on the full benchmark suite.

**Implication:** For voice assistants on resource-constrained hardware, separating deterministic tool queries from generative chat queries is not an optimisation — it is the architecture. The TTFS difference (58%, well above the 300ms perceptible lag threshold) is user-visible on every query. The tool routing advantage is not merely a latency benefit: it also entirely bypasses the dual-injection failure mode that caused chat TTFS to grow with session length (Finding 5). The accuracy difference is a correctness guarantee: tools return measured values; LLMs return statistically plausible completions.

*Note: The 45% figure cited in earlier versions of this finding used pre-fix chat TTFS (2.30s). The correct post-fix figure is 58% (1.25s vs 3.00s). The conclusion is stronger, not weaker, under corrected numbers.*

---

## Finding 2 — Response Length as the Dominant TTFS Lever on 4GB VRAM Hardware

**Finding:** When selecting LLMs for voice assistant deployment on constrained hardware, average response length is a more predictive metric than generation latency alone — a slower model producing shorter responses can outperform a faster model on TTFS.

**Evidence:** Controlled model comparison (Week 5): qwen2.5:3b produced 24.4-word average responses with 0.85s generation latency. llama3.2:3b produced 29.0-word average responses with 0.93s generation latency — 0.08s faster generation but 4.6 more words. Net TTFS result: qwen2.5:3b achieved -0.20s lower TTFS despite being the slower generator. TTS synthesis on Piper medium model measured at approximately 20ms per word at this response length range.

*Measurement note: These absolute TTFS numbers were collected under pre-fix dual-injection conditions (Week 5). Both models were tested under identical conditions, so the relative comparison (qwen2.5:3b faster on TTFS due to shorter responses) is valid. Absolute values are elevated relative to post-fix baselines. The mechanism (TTS synthesis cost scaling linearly with word count) is unaffected by the dual-injection bug and holds under post-fix conditions.*

**Mechanism:** TTS synthesis time scales linearly with word count. The 4.6-word reduction from qwen2.5:3b saves approximately 92ms in synthesis time. The 0.08s generation cost increase is more than offset by the synthesis saving. The crossover point — where model slowness would dominate output length reduction — was not reached in this comparison.

**Implication:** Model selection benchmarks for voice assistants should report average response word count alongside generation latency. Standard benchmarks reporting tokens-per-second do not capture this trade-off. On hardware where TTS synthesis is a significant TTFS component, optimising for brevity in model output is equivalent to optimising for generation speed.

---

## Finding 3 — LLM Hallucination of Hardware Metrics is Systematic and Confident

**Finding:** LLMs generate plausible but incorrect hardware values with high confidence and no uncertainty signal when queried about system state — making tool routing for deterministic facts a correctness requirement, not a fallback.

**Evidence:** Three documented incidents (Weeks 4–5). Storage: LLM reported 83.5GB free on a 1TB drive; actual was 41GB free on a 512GB drive — wrong on both total capacity and free space. CPU utilisation: LLM reported 57%; psutil measured 26% — a 2.2x overestimate. Temperature: LLM reported 85°C CPU and 78°C GPU; actual GPU temperature via pynvml was 44–47°C — nearly double the actual reading. In all three cases the model expressed no uncertainty and produced values within plausible real-world ranges.

**Mechanism:** LLMs generate statistically likely continuations of their input. Common hardware values appear frequently in training data — benchmark reports, forum posts, documentation. When asked about system state, the model completes from this prior distribution rather than indicating it lacks access to real-time sensor data. The values are plausible by construction but are uncorrelated with actual system state.

**Implication:** Any voice assistant architecture that routes hardware queries to an LLM — even as a fallback — will produce confident wrong answers. This extends beyond hardware metrics: any query with a deterministic correct answer that differs from the model's statistical prior is a hallucination risk. Tool routing for deterministic facts is a correctness guarantee that cannot be approximated by prompt engineering or confidence thresholds.

---

## Finding 4 — [Superseded]

An earlier hypothesis attributed TTFS regression to tool-response context injection from large file summaries. Week 7 investigation identified three separate root causes: cross-session context injection (`session_id=None`), dual memory injection (`conversation_history` accumulation in `llm.py` alongside SQLite-backed `build_context()`), and missing `source` column preventing tool-turn filtering. The tool-response injection hypothesis was not confirmed before the actual causes were identified. See Finding 5 for the accurate documented finding.

---

## Finding 5 — Dual Memory Injection as a Latency Anti-Pattern in Local LLM Assistants

**Finding:** Running two simultaneous memory systems against the same LLM inference call produces compounding context growth that masquerades as model instability.

**Evidence:** Chat path TTFS drifted from 2.92s (Turn 1) to 5.08s (Turn 6) in a controlled 6-turn session under pre-fix conditions. LLM latency grew from 1.57s to 3.21s across the same session. After removing the redundant system, worst-case TTFS dropped from 5.53s to 3.89s and variance collapsed from 2.53s to 0.89s.

| Turn | Pre-fix TTFS | Post-fix TTFS |
|------|-------------|--------------|
| 1 | 3.59s | 3.00s |
| 3 | 4.52s | 3.83s |
| 4 | 4.62s | 3.89s |
| 6 | 5.08s | 3.79s |
| Variance | 2.53s | 0.89s |

**Mechanism:** TARA had two independent memory systems feeding the same `ollama.chat()` call. The SQLite-backed `build_context()` injected history via the system prompt. The in-process `conversation_history` list appended every turn as explicit message objects. Ollama built a KV cache for the entire growing message list on every call. By Turn 6, the model was processing 12 message objects plus the system prompt context block — the same history represented twice. Removing `conversation_history` and passing only `[system, user]` per call reduced the KV cache to a fixed size.

**Implication:** When building a voice assistant with both a persistent memory store and an LLM client library, verify that the client library does not maintain its own conversation state. Many Ollama and OpenAI client wrappers accumulate history internally by default. On constrained hardware, this accumulation is the dominant TTFS growth factor and is indistinguishable from model instability without per-stage latency instrumentation.

---

## Finding 6 — Context-TTFS Tradeoff is Hardware-Determined and Irreducible

**Finding:** On a 4GB VRAM GPU running a 3B parameter quantized model, injected context tokens impose a fixed latency cost that cannot be optimized away in software.

**Evidence:** With `conversation_history` removed and `session_id` correctly scoped, LLM latency tracked context size: 119 chars (Turn 1) → 1.58s, 252 chars (Turn 3) → 2.37s, 407 chars (Turn 4) → 2.36s, 594 chars (Turn 6) → 2.30s. Memory build time was <10ms at all turns. The minimum achievable logged TTFS with zero context is STT (~0.70s) + LLM (~1.58s) + TTS synthesis (~0.72s) = 3.00s. This is the hardware floor. These measurements are post-fix (Week 7) and reflect the corrected pipeline.

**Mechanism:** qwen2.5:3b on RTX 3050 costs approximately 1ms per additional context token during prefill. A 600-token context ceiling adds ~0.60s to LLM latency versus a zero-context baseline. This cost is paid on every chat-path turn regardless of software optimizations.

**Implication:** TTFS targets for voice assistants on edge hardware must be derived from measured hardware floors, not aspirational benchmarks. A ≤4.0s logged TTFS target with ≤1.0s session variance is achievable on this hardware. A ≤2.60s target is not, given the STT + LLM + TTS component minimums.

*All logged TTFS measurements exclude the VAD silence-detection window (`silence_duration=0.8s` post-Week-8 calibration, `1.8s` in all prior weeks). User-perceived TTFS equals logged TTFS plus the silence window duration.*

---

## Finding 7 — Compound Tool Chains as Deterministic Agentic Behaviour

**Finding:** Multi-step tool execution on constrained hardware achieves lower TTFS than single LLM-assisted tool calls by eliminating generative inference from the synthesis step entirely.

**Evidence:** Three compound chains measured in a controlled session:
- System status snapshot (3 psutil calls + template synthesis): TTFS 1.85s
- Note with live system data (1 psutil call + 1 note write): TTFS 1.45s
- Timestamped note (1 datetime call + 1 note write): TTFS 1.59s

All three outperform the chat path floor of 3.00s and match or beat the single-tool no-LLM path target of ≤1.60s (Chain 1 at 1.85s is the sole exception, within the compound target of ≤2.0s). Week 8 dry run confirmed Chain 1 at 1.67–1.68s under real demo conditions.

**Mechanism:** Compound chains execute as a predefined sequence of deterministic tool calls with template-based output synthesis. No LLM planning, no LLM synthesis for Chains 1 and 3. The CompoundRouter runs before IntentDetector in the pipeline, matching specific multi-word phrases before single-intent routing fires.

**Implication:** Agentic multi-step behaviour on edge hardware does not require LLM orchestration. For a well-defined set of compound queries, keyword-triggered deterministic chains produce lower latency, higher reliability, and predictable output compared to LLM-planned execution. The design tradeoff is expressiveness: deterministic chains only handle anticipated compound patterns, not arbitrary multi-step requests. This is acceptable for a voice assistant with a defined capability set.

---

## What Has Not Been Measured That Would Be Worth Measuring

### 1. The Pareto Frontier Between VRAM and Format Compliance

The project operates under a hard 4GB VRAM constraint. The model swap evaluation tested two candidates at the same parameter count (3B). The unanswered question: is there a model at 1.5B–2B parameters that fits more comfortably within 2GB VRAM while maintaining acceptable format compliance? Or does format compliance degrade sharply below 3B parameters on this task? A structured experiment plotting format compliance and TTFS across model sizes would make model selection principled rather than hardware-constrained.

### 2. Memory Injection Overhead vs Recall Quality at Scale

The +0.29s memory overhead measured in Week 3 was from a near-empty database. The overhead at 50 stored facts, 200 stored turns, and 1000 stored turns has not been measured. The relevant question: does memory injection overhead grow linearly with context size, and at what context size does the TTFS budget absorb the full headroom?

### 3. STT Error Rate on Domain-Specific Vocabulary

The STT correction layer currently has four entries based on observed misrecognitions from one speaker. The base model's error rate on technical vocabulary (VRAM, psutil, Ollama, Whisper, qwen) and South Asian names has not been systematically measured. A structured test reading 50 domain-specific terms and comparing Whisper output to ground truth would identify whether the correction dictionary is near-complete or represents a small fraction of actual error cases.
# TARA — Research Notes
## Midpoint Analysis

---

## What Has Been Measured That Is Worth Reporting

### 1. Tool-Path vs Chat-Path TTFS on Constrained Hardware

The most concrete finding of this project so far: bypassing LLM generation for deterministic queries reduces TTFS by 45% on a 4GB VRAM system (2.30s chat path vs 1.25s tool path). This is not a novel architectural idea — intent-based routing is standard in production voice assistants — but the measurement on consumer-grade hardware with a fully offline stack is concrete data.

The mechanism is straightforward: LLM generation (1.04s) is the dominant latency cost on the chat path. Tool execution (0.002–0.101s) is negligible by comparison. The 1.05s difference is directly attributable to the presence or absence of one forward pass through a 3B parameter model.

This creates a testable hypothesis worth formalising: for a given class of user queries (system monitoring, time/date, arithmetic), keyword-based intent routing on constrained hardware produces lower TTFS than LLM-based routing, with identical or higher answer accuracy. The accuracy claim is supported by the hallucination log — the LLM fabricated storage, CPU utilisation, and temperature values when queries fell through to it. Tool routing is not just faster; it is more accurate for deterministic queries.

**The gap in this finding:** intent classification accuracy was measured at 22/22 on a designed test set. Real-world accuracy on natural speech variations is unknown. The benchmark is a lower bound on failure rate, not an upper bound on reliability.

---

### 2. Response Length as the Primary TTFS Lever on This Hardware

The model upgrade from llama3.2:3b to qwen2.5:3b increased LLM latency by +0.11s but reduced TTFS by -0.20s. The mechanism: qwen2.5:3b produces 24.4-word average responses vs 29.0 words, reducing TTS synthesis time more than the generation cost increase.

This suggests a counterintuitive optimisation principle for constrained TTS pipelines: a slower model that produces shorter output can reduce end-to-end TTFS compared to a faster model with longer output. This holds when TTS synthesis time scales with output length faster than LLM generation time scales with model size — which appears to be true for Piper TTS on this hardware.

**What this does not establish:** whether this relationship generalises beyond the two specific models tested, or whether there is a crossover point where model slowness dominates output length reduction. A controlled experiment varying model size and measuring both output length and TTFS would answer this.

---

### 3. LLM Hallucination of Hardware Metrics — Systematic, Not Occasional

Three separate incidents across Weeks 4–5 documented the LLM fabricating hardware values with high confidence and no uncertainty signal: storage (83.5GB free / 1TB vs actual 41GB / 512GB), CPU utilisation (57% vs 26%), and temperature (85°C CPU, 78°C GPU vs actual sensor readings). In each case, the values were plausible — within realistic ranges for the hardware class — but wrong by factors of 2–10.

This is consistent with known LLM behaviour: models generate statistically likely continuations, and common hardware values from training data (typical CPU loads, typical VRAM figures) are statistically likely completions for "your CPU is at X percent." The model is not retrieving data; it is completing a pattern.

The practical implication for offline assistants: any query with a deterministic correct answer that differs from the model's statistical prior is a hallucination risk. For hardware metrics this is visible and verifiable. For less observable domains (personal calendar, local files, user preferences), the same mechanism produces wrong answers that are harder to catch.

---

### 4. Stabilising Multi-Turn Latency via Context Injection Constraints

The latency regression observed across extended conversational sessions has been successfully resolved. Empirical measurements now show Turn 1 TTFS at 2.92s and Turn 6 at 3.19s. This 0.27s variance sits comfortably within the established ≤0.30s target threshold for multi-turn degradation.

The root cause of the previous degradation was identified as unbounded tool-response context injection. When raw, unoptimised tool outputs (such as large file summaries or unstructured data dumps) were continuously appended to the LLM's short-term conversational memory, the rapidly expanding context window degraded generation speed non-linearly.

The practical implication here reinforces the architectural decisions made in Week 6: stable multi-turn latency on constrained hardware requires aggressive curation of what tools are allowed to inject into persistent context. Keeping large tool data isolated to a temporary synthesis prompt—rather than appending it to the ongoing chat history—is mandatory to prevent TTFS from ballooning over a long session.

---

## Finding 5 — Dual Memory Injection as a Latency Anti-Pattern in Local LLM Assistants

Finding: Running two simultaneous memory systems against the same LLM inference call
produces compounding context growth that masquerades as model instability.

Evidence: Chat path TTFS drifted from 2.92s (Turn 1) to 5.08s (Turn 6) in a
controlled 6-turn session. LLM latency grew from 1.57s to 3.21s across the same
session. After removing the redundant system, worst-case TTFS dropped from 5.53s
to 3.89s and variance collapsed from 2.53s to 0.89s.

Mechanism: TARA had two independent memory systems feeding the same ollama.chat()
call. The SQLite-backed build_context() injected history via the system prompt.
The in-process conversation_history list appended every turn as explicit message
objects. Ollama built a KV cache for the entire growing message list on every call.
By Turn 6, the model was processing 12 message objects plus the system prompt
context block — the same history represented twice. Removing conversation_history
and passing only [system, user] per call reduced the KV cache to a fixed size.

Implication: When building a voice assistant with both a persistent memory store
and an LLM client library, verify that the client library does not maintain its
own conversation state. Many Ollama and OpenAI client wrappers accumulate history
internally by default. On constrained hardware, this accumulation is the dominant
TTFS growth factor and is indistinguishable from model instability without
per-stage latency instrumentation.

---

## Finding 6 — Context-TTFS Tradeoff is Hardware-Determined and Irreducible

Finding: On a 4GB VRAM GPU running a 3B parameter quantized model, injected context
tokens impose a fixed latency cost that cannot be optimized away in software.

Evidence: With conversation_history removed and session_id correctly scoped,
LLM latency tracked context size linearly: 119 chars (Turn 1) → 1.58s,
252 chars (Turn 3) → 2.37s, 407 chars (Turn 4) → 2.36s, 594 chars (Turn 6) →
2.30s. Memory build time was <10ms at all turns — SQLite is not the bottleneck.
The minimum achievable TTFS with zero context is STT (~0.70s) + LLM (~1.58s) +
TTS synthesis (~0.72s) = 3.00s. This is the hardware floor.

Mechanism: qwen2.5:3b on RTX 3050 costs approximately 1ms per additional context
token during prefill. A 600-token context ceiling adds ~0.60s to LLM latency
versus a zero-context baseline. This cost is paid on every chat-path turn
regardless of software optimizations.

Implication: TTFS targets for voice assistants on edge hardware must be derived
from measured hardware floors, not aspirational benchmarks. The correct design
response is not to reduce context injection aggressively — which degrades memory
coherence — but to set user-facing latency expectations against the measured
floor. A ≤4.0s TTFS target with ≤1.0s session variance is achievable on this
hardware. A ≤2.60s target is not, given the STT + LLM + TTS component minimums.

---

## What Has Not Been Measured That Would Be Worth Measuring

### 1. The Pareto Frontier Between VRAM and Format Compliance

The project operates under a hard 4GB VRAM constraint. Within that constraint, the model swap evaluation tested two candidates at the same parameter count (3B). The unanswered question: is there a model at 1.5B–2B parameters that fits more comfortably within 2GB VRAM (freeing headroom for future components) while maintaining acceptable format compliance? Or does format compliance degrade sharply below 3B parameters on this task?

A structured experiment: evaluate format compliance (Category A score) and TTFS across a range of model sizes (1B, 1.5B, 3B, 7B — the last requiring a VRAM upgrade), plot the Pareto frontier. This would make the model selection principled rather than constrained to "what fits in 4GB."

### 2. Memory Injection Overhead vs Recall Quality at Scale

The current memory context injects the last 6 conversation turns and up to 10 user facts. As stored facts accumulate over weeks of use, the injected context grows. The +0.29s memory overhead measured in Week 3 was from a near-empty database. The overhead at 50 stored facts, 200 stored turns, and 1000 stored turns has not been measured.

The relevant question: does memory injection overhead grow linearly with context size, and at what context size does the TTFS budget absorb the full headroom? A longitudinal measurement (log memory context size and TTFS across sessions over 4+ weeks) would characterise this.

### 3. STT Error Rate on Domain-Specific Vocabulary

The STT correction layer currently has one entry based on observed misrecognition. The base model's error rate on technical vocabulary (VRAM, psutil, Ollama, Whisper, qwen) and South Asian names has not been systematically measured. A structured test reading 50 domain-specific terms and comparing Whisper output to ground truth would identify whether the correction dictionary is near-complete or represents a small fraction of actual error cases.
# TARA — Research Notes
## Midpoint Analysis — Week 5 of 10

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

## What Has Not Been Measured That Would Be Worth Measuring

### 1. The Pareto Frontier Between VRAM and Format Compliance

The project operates under a hard 4GB VRAM constraint. Within that constraint, the model swap evaluation tested two candidates at the same parameter count (3B). The unanswered question: is there a model at 1.5B–2B parameters that fits more comfortably within 2GB VRAM (freeing headroom for future components) while maintaining acceptable format compliance? Or does format compliance degrade sharply below 3B parameters on this task?

A structured experiment: evaluate format compliance (Category A score) and TTFS across a range of model sizes (1B, 1.5B, 3B, 7B — the last requiring a VRAM upgrade), plot the Pareto frontier. This would make the model selection principled rather than constrained to "what fits in 4GB."

### 2. Memory Injection Overhead vs Recall Quality at Scale

The current memory context injects the last 6 conversation turns and up to 10 user facts. As stored facts accumulate over weeks of use, the injected context grows. The +0.29s memory overhead measured in Week 3 was from a near-empty database. The overhead at 50 stored facts, 200 stored turns, and 1000 stored turns has not been measured.

The relevant question: does memory injection overhead grow linearly with context size, and at what context size does the TTFS budget absorb the full headroom? A longitudinal measurement (log memory context size and TTFS across sessions over 4+ weeks) would characterise this.

### 3. STT Error Rate on Domain-Specific Vocabulary

The STT correction layer currently has one entry based on observed misrecognition. The base model's error rate on technical vocabulary (VRAM, psutil, Ollama, Whisper, qwen) and South Asian names has not been systematically measured. A structured test reading 50 domain-specific terms and comparing Whisper output to ground truth would identify whether the correction dictionary is near-complete or represents a small fraction of actual error cases.
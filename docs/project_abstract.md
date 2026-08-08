# TARA — Project Abstract

**Totally Autonomous Responsive Assistant**  
Krishnendu Mandal · 10-Week Portfolio Project · 2026

---

## Problem Statement

Cloud-based voice assistants transmit every spoken query to remote servers for processing. This creates three compounding problems: every interaction is logged by a third party, functionality fails without network connectivity, and the user has no control over what data is retained or how it is used. For users in sensitive environments — healthcare, legal, research, or simply private — these are not edge cases but architectural guarantees of exposure. This project asks whether a voice assistant with comparable capability can be built to run entirely on consumer hardware, with zero external dependencies and no data leaving the device.

---

## What Was Built

TARA (Totally Autonomous Responsive Assistant) is a fully offline, voice-controlled AI assistant built on a Windows 11 laptop with an NVIDIA RTX 3050 GPU (4GB VRAM). The system implements a 7-stage pipeline: voice input via PyAudio, speech recognition via Faster-Whisper (base, int8, CPU), STT post-correction, a CompoundRouter for multi-step deterministic chains at Stage 1.5, keyword-based intent classification routing to nine tool types, LLM generation via qwen2.5:3b on Ollama, and Piper TTS synthesis. The capability set includes system monitoring via psutil and pynvml, arithmetic via safe_eval, note management, file reading with LLM summarisation, hybrid local information retrieval across SQLite and filesystem, persistent cross-session memory, session-end summarisation, and conversational fallback. A 70-query benchmark suite validates intent, tool, and compound routing at 100% accuracy. All processing runs locally. No query leaves the device.

---

## What Was Found

**Finding 1 — Tool routing reduces TTFS by 58%.**
Keyword-based intent routing achieves a 1.25s tool path TTFS versus a 3.00s chat path floor on the same hardware — a 58% reduction. Intent classification runs in under 0.01ms with 100% accuracy across 70 benchmark queries, outperforming LLM-based classification on both latency and correctness.

**Finding 2 — Response length predicts TTFS better than generation speed.**
qwen2.5:3b produced 24.4-word average responses at 0.85s generation versus llama3.2:3b's 29.0 words at 0.93s — the 4.6-word reduction saved approximately 92ms in TTS synthesis, producing lower end-to-end TTFS despite slower generation. Standard tokens-per-second benchmarks do not capture this tradeoff.

**Finding 3 — LLM hardware hallucination is systematic and confident.**
In three documented incidents, LLM-reported hardware values were wrong by factors of 2–10 while remaining within real-world plausible ranges — CPU utilisation reported at 57% versus 26% actual, GPU temperature at 78°C versus 44–47°C actual. No uncertainty signal was produced in any case.

**Finding 5 — Dual memory injection masquerades as model instability.**
Running two concurrent memory systems against the same LLM inference call caused chat TTFS to drift from 2.92s to 5.08s across a six-turn session — a 74% increase indistinguishable from hardware degradation without per-stage instrumentation. Removing the redundant system collapsed session variance from 2.53s to 0.89s.

---

## Implications

This project demonstrates that a capable, privacy-preserving voice assistant is deployable on widely available consumer hardware within a 4GB VRAM budget — but only with specific architectural choices. Deterministic tool routing is not an optimisation layered onto LLM reasoning; it is a prerequisite for both latency and correctness on hardware-query tasks. Response length is a first-class model selection criterion that standard benchmarks do not capture. And latency targets for voice interfaces on edge hardware must be derived from measured hardware floors — the 3.00s component minimum on this platform is irreducible in software, making aspirational sub-2s targets meaningless without streaming output or significantly larger VRAM. All three conclusions are supported by specific measurements from a reproducible local deployment on consumer hardware.
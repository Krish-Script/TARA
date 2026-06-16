# TARA - Week 1 Report

## Sprint Goal

Build a complete offline voice pipeline consisting of:

- Speech-to-Text (Whisper)
- Local LLM (Ollama + Llama 3.2:3B)
- Text-to-Speech
- End-to-End conversation loop

---

# Hardware

| Component | Specification |
|-----------|---------------|
| CPU | Intel CPU |
| GPU | RTX 3050 Laptop 4GB |
| RAM | 16 GB |
| OS | Windows 11 |

---

# Software Stack

| Component | Technology |
|-----------|------------|
| STT | Faster-Whisper |
| LLM | Ollama + llama3.2:3b |
| TTS | pyttsx3 |
| Language | Python 3.11.7 |

---

# Performance Baseline

## STT

| Test | Time |
|------|------|
| Round 1 | 0.89 s |
| Round 2 | 0.66 s |
| Round 3 | 0.56 s |
| **Average** | **0.70 s** |

---

## LLM

| Metric | Value |
|---------|-------|
| Cold Start (Disk → VRAM) | 80.82 s |
| Cold Run (RAM → VRAM) | 7.30 s |
| Warm Inference | **0.68 s** |
| VRAM Usage | 2.2–2.5 GB |

---

## TTS

| Phrase | Time |
|---------|------|
| 1 | 5.66 s |
| 2 | 5.00 s |
| 3 | 4.19 s |
| **Average** | **4.95 s** |

---

## End-to-End

| Metric | Value |
|---------|-------|
| Session Length | 1.2 min |
| Conversation Turns | 3 |
| STT Avg | 0.62 s |
| LLM Avg | 1.41 s |
| TTS Avg | 11.23 s |
| Time To First Response | ~2.0 s |
| VRAM | 2.2 GB |

---

# Problems Encountered

- pyttsx3 only spoke the first sentence.
- Fixed by recreating the engine for every speech request.
- Assistant initially identified itself as ARIA instead of TARA.
- Cold-start latency from Ollama was expected due to model loading.

---

# Sprint Outcome

✅ Offline voice pipeline completed

✅ Stable GPU memory usage

✅ Voice conversation working

---

# Next Sprint

- Replace pyttsx3 with Piper
- Improve response quality
- Reduce TTS latency
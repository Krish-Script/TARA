# TARA - Week 2 Report

## Sprint Goal

Improve voice quality and overall responsiveness.

---

# Improvements

- Migrated from pyttsx3 to Piper TTS
- Tuned prompt engineering
- Reduced total response latency

---

# Performance

| Component | Week 1 | Week 2 |
|-----------|---------|---------|
| STT | 0.62 s | 0.59 s |
| LLM | 1.41 s | 1.05 s |
| TTS | 11.23 s | 5.42 s |
| Total | 13.26 s | **7.06 s** |

---

# Voice

- Model: en_US-hfc_female-medium

---

# Lessons Learned

- Few-shot prompting performs better than instruction-only prompts.
- Piper produces significantly faster speech synthesis than pyttsx3.
- GPU memory remained stable throughout testing.

---

# Sprint Outcome

✅ 47% reduction in total latency

✅ Better sounding voice

✅ More natural responses

---

# Next Sprint

- SQLite memory
- Persistent conversations
- User profile storage
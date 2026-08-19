# TARA — Week 10 Checklist

## Week 10 Deliverable

**Primary:** On-camera demo recording (~3 minutes), uploaded to LinkedIn and linked in README under a "Demo" section.

**Secondary:** Final demo run (Run 5) performed from cold boot as the recording take. Shot list rehearsed minimum 3 times before the real take.

**Definition of done:** Recording shows voice input → tool execution → TTS response across at least 5 distinct capabilities. Wi-Fi disabled on camera for at least one query. Session summary spoken at exit. Video linked in README before the repository is considered submission-ready.

---

## Pre-Demo Verification Steps

Run these in order before the Week 10 recording take. Do not skip any step.

- [ ] Cold-boot system — kill all Ollama and Python processes
- [ ] Run `nvidia-smi` — confirm VRAM at 0MiB before starting TARA
- [ ] Run `python tests/test_benchmark.py` — confirm 70/70
- [ ] Run demo script queries 1–10 in sequence — confirm all within TTFS targets
- [ ] Verify `data/notes/` contains only the one retained demo note (note 6: "I demonstrated TARA today")
- [ ] Verify `data/tara_memory.db` facts table contains expected demo facts
- [ ] Confirm Ollama model is qwen2.5:3b and keep_alive="5m" in config
- [ ] Run a test exit — confirm session summary speaks content, not stats
- [ ] Test OBS audio mix — confirm both your voice and Piper TTS are audible at -12dB to -6dB peak
- [ ] Test NVENC + Ollama VRAM contention — throwaway recording take while TARA is running; confirm no dropped frames

---

## Recording Shot List

Ten beats in order. Rehearse until transitions feel natural — not until words are memorised.

| Beat | Action | Expected |
|------|--------|----------|
| 1 | Camera: introduce yourself + one sentence on what TARA is | — |
| 2 | Voice: "What time is it TARA?" | Instant response — shows responsiveness |
| 3 | Voice: "What is my CPU and RAM usage?" | Local system data — visually obvious |
| 4 | Voice: "Take a note: I need to review the project report before Thursday" | Note saved confirmation |
| 5 | Voice: "Read me that note back" | Memory across session demonstrated |
| 6 | Camera: "Now I'll turn off Wi-Fi" → disable on screen | Offline proof moment |
| 7 | Voice: "What is machine learning?" | Offline LLM response |
| 8 | Voice: compound query | Showpiece — two tools in one query |
| 9 | Voice: "Goodbye TARA" | Session summary spoken aloud |
| 10 | Cut to spec slide | Stack: Faster-Whisper → qwen2.5:3b → Piper TTS, 70/70, RTX 3050 4GB |

**Pause after every TARA response.** Half a second of silence reads as confidence. Rushing to the next query reads as nerves.

---

## OBS Configuration

- Scene: TARA Demo
- Source 1: Screen capture (full display, fills canvas)
- Source 2: Webcam overlay (280×160px, bottom-right corner)
- Source 3: Mic input — target -12dB to -6dB peak
- Source 4: Desktop audio (Piper TTS) — target -12dB to -6dB peak
- Encoder: NVENC H.264 (switch to x264 if frame drops detected)
- Rate control: CQP 20
- Resolution: 1920×1080 @ 30fps
- Format: MP4

---

## Final Documentation Checklist

Complete before recording. Every item must pass before the take.

- [ ] `README.md`: Demo section added with LinkedIn video link placeholder
- [ ] `README.md`: current version shows Week 9 cold-boot benchmark numbers
- [ ] `docs/research_notes.md`: 10 findings (9 active, 1 superseded), 3 unmeasured gaps with rationale
- [ ] `docs/known_limitations.md`: 8 limitations with current status
- [ ] `docs/project_abstract.md`: under 600 words, four findings with specific numbers, both logged and user-perceived TTFS values
- [ ] `CHANGELOG.md`: v1.0.0 entry present, [Unreleased] cleared
- [ ] `docs/demo_script.md`: Run 4 cold-boot numbers filled in
- [ ] `docs/week9_report.md`: all 7 tasks marked complete

---

## Portfolio Submission Checklist

- [ ] GitHub repository is public and accessible
- [ ] README renders correctly on GitHub — no broken links, correct paths
- [ ] `docs/` folder is clean — no draft files, no stale development notes
- [ ] `data/` is gitignored — no personal session data in version control
- [ ] LinkedIn post drafted — hook in first line, video attached, GitHub link included
- [ ] Demo video linked in README under "Demo" section
- [ ] v1.0.0 tag visible on GitHub releases page
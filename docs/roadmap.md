# TARA Development Roadmap

## ✅ Week 1 (Completed)

- Test microphone + transcription
- Test the AI model
- Test voice output
- Full voice loop

---

## ✅ Week 2 (Completed)

- Install Piper + sounddevice, download voice model
- Write isolated tests/test_piper.py and verify audio
- Rewrite components/tts.py to use Piper
- Test full pipeline with Piper, record new baseline
- Tighten system prompt — force shorter responses
- Add model warm-up call at startup to kill 80s cold start
- Try 3 different Piper voice models, pick the best

---

## 🚧 Week 3 (In Progress)

- keep_alive cold start fix
- SQLite memory schema + storage
- Cross-session context injection
- Explicit user fact memory
- Orchestrator class refactor
- TTFS measurement
- Chunked TTS streaming

---

## Week 5

- Tool Calling
- File Management
- Browser Control

---

## Week 6

- Local Automation
- App Launcher
- System Commands

---

## Week 7

- Vision
- OCR
- Screen Understanding

---

## Week 8

- GUI
- Packaging
- Installer
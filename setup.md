# TARA Week 1 Setup Guide
## Plain-English Instructions, Day by Day

---

## What You're Building

```
Your Voice → Whisper (CPU) → Text → LLaMA via Ollama (GPU) → Response → pyttsx3 → You Hear It
```

| Component        | Tool           | Runs On | Why                          |
|------------------|----------------|---------|------------------------------|
| Speech → Text    | faster-whisper | CPU     | Saves VRAM entirely for LLM  |
| Language Model   | Ollama + LLaMA | GPU     | The "brain" of the assistant |
| Text → Speech    | pyttsx3        | CPU     | Zero setup, fully offline    |

---

## DAY 1 — Environment Setup (~2.5 hours)

### 1. Install Python 3.11
- Download from: https://www.python.org/downloads/
- During installation: ✅ CHECK "Add Python to PATH"
- Verify by opening Command Prompt and typing:
  ```
  python --version
  ```
  You should see: `Python 3.11.x`

### 2. Install Ollama (the LLM engine)
- Download from: https://ollama.com/download
- Run the installer — it will run as a background service automatically
- Verify by opening Command Prompt and typing:
  ```
  ollama list
  ```
  You should see an empty table (no models yet).

### 3. Download the AI Model (takes 5–10 min)
In Command Prompt:
```
ollama pull llama3.2:3b
```
This downloads ~2 GB. Wait for it to finish before continuing.

### 4. Create the Project Folder
```
mkdir D:\TARA
cd D:\TARA
```

### 5. Copy Your Project Files
Copy ALL the files you received into `D:\TARA\` so the structure looks like:
```
D:\TARA\
├── main.py
├── config.py
├── requirements.txt
├── .gitignore
├── components\
│   ├── __init__.py
│   ├── stt.py
│   ├── llm.py
│   └── tts.py
└── tests\
    ├── test_stt.py
    ├── test_llm.py
    └── test_tts.py
```

### 6. Create a Virtual Environment
A virtual environment keeps this project's packages separate from everything else on your PC.
```
cd D:\TARA
python -m venv .venv
.venv\Scripts\activate
```
You'll see `(.venv)` at the start of your command prompt. This means it's active.
**You must activate it every time you open a new terminal.**

### 7. Install PyAudio (the tricky one)
PyAudio handles your microphone. It doesn't install via plain `pip` on Windows.

**Option A (try this first):**
```
pip install pipwin
pipwin install pyaudio
```

**Option B (if Option A fails):**
1. Go to: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
2. Download `PyAudio‑0.2.14‑cp311‑cp311‑win_amd64.whl`
3. Run: `pip install C:\Users\YourName\Downloads\PyAudio-0.2.14-cp311-cp311-win_amd64.whl`

**Option C (if both fail):**
```
conda install pyaudio
```
(requires Anaconda to be installed)

### 8. Install Remaining Packages
```
pip install -r requirements.txt
```

### 9. Verify Everything
```
python -c "import faster_whisper; print('Whisper OK')"
python -c "import ollama; print('Ollama OK')"
python -c "import pyttsx3; print('TTS OK')"
python -c "import pyaudio; print('PyAudio OK')"
```
All four should print "OK".

### ✅ Day 1 Git Commit
```
git init
git add .
git commit -m "Week1 Day1: environment setup complete, all packages installed"
```

---

## DAY 2 — Test STT (~2 hours)

Make sure your microphone is working (test in Windows Settings first).

With `.venv` active, run:
```
python tests/test_stt.py
```

You'll get 3 rounds. After each "🎤 Listening...", speak a sentence.
You should see your words appear on screen.

**Write down the average latency number printed at the end.**

**Microphone not working?**
- In `config.py`, try lowering `silence_threshold` from 300 to 150
- Try increasing `silence_duration` from 1.8 to 2.5

### ✅ Day 2 Git Commit
```
git add .
git commit -m "Week1 Day2: STT working, avg latency Xs"
```
(Replace X with your actual number)

---

## DAY 3 — Test LLM (~2 hours)

Make sure Ollama is running (it usually starts automatically, but you can
open the Ollama desktop app to confirm, or run `ollama serve` in a terminal).

With `.venv` active, run:
```
python tests/test_llm.py
```

You should see 3 questions answered by TARA in text.
Also open **Task Manager → Performance → GPU** and check VRAM usage (~2 GB).

**Write down the average LLM latency printed at the end.**

**Errors?**
- "Connection refused" → Open the Ollama app, or run `ollama serve`
- "Model not found"   → Run `ollama pull llama3.2:3b`

### ✅ Day 3 Git Commit
```
git add .
git commit -m "Week1 Day3: LLM working, avg latency Xs, VRAM ~2GB"
```

---

## DAY 4 — Test TTS (~1 hour)

Make sure speakers or headphones are plugged in.

With `.venv` active, run:
```
python tests/test_tts.py
```

You should **hear** 3 phrases spoken aloud.
The script also lists all available Windows voices — pick one you like
and set `voice_index` in `config.py`.

### ✅ Day 4 Git Commit
```
git add .
git commit -m "Week1 Day4: TTS working, voice selected"
```

---

## DAY 5 — End-to-End Pipeline (~3 hours)

This is the main goal of Week 1.

With `.venv` active and Ollama running, run:
```
python main.py
```

Wait for:  `✅ All components loaded. TARA is ready!`

Then **speak to it**. You should hear a voice reply.

**Voice commands:**
- Say "quit" or "goodbye" to stop
- Say "clear memory" to reset the conversation

When you stop, a **baseline performance table** will print.
**Screenshot it** — this is your Week 1 deliverable.

### ✅ Day 5 Git Commit
```
git add .
git commit -m "Week1 Day5: end-to-end voice pipeline working"
git push origin main
```

---

## Hardware Safety — Always Check Before Running main.py

- [ ] Ollama is running (GPU) — model should show in `ollama list`
- [ ] config.py: `device = "cpu"` for Whisper (NEVER "cuda")
- [ ] Using `llama3.2:3b` — NOT a 7b model
- [ ] No other GPU-heavy apps open (games, video rendering, etc.)

Expected peak VRAM: **~2.2 GB / 4 GB** — you have 1.8 GB headroom ✅

---

## Common Errors Quick Reference

| Error | Cause | Fix |
|-------|-------|-----|
| `PyAudio not found` | PyAudio not installed | See Day 1 Step 7 |
| `No speech detected` | silence_threshold too high | Lower to 150 in config.py |
| `Connection refused (Ollama)` | Ollama not running | Open Ollama app or `ollama serve` |
| `Model not found` | Model not downloaded | `ollama pull llama3.2:3b` |
| `CUDA out of memory` | Another GPU app running | Close other apps, restart Ollama |
| `No audio output` | Wrong audio device | Check Windows sound settings |

---

## What to Record for Week 1 Review (Friday)

- [ ] Average STT latency: _______s
- [ ] Average LLM latency: _______s
- [ ] Average TTS latency: _______s
- [ ] Peak VRAM usage: _______GB
- [ ] Any error patterns you noticed
- [ ] Screenshot of the baseline report from main.py
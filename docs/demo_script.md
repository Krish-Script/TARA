# TARA — Demo Script
**Target duration:** Under 5 minutes  
**Tested:** Week 7  
**Hardware:** RTX 3050 Laptop GPU, 4GB VRAM, Windows 11

---

## Pre-Demo Checklist

- [x] TARA is running and has spoken the startup greeting
- [x] Microphone is positioned close — within 30cm
- [x] No background noise (fans, music, notifications)
- [x] Ollama is running — confirm with `ollama list` in a separate terminal
- [x] `data/notes/` has at least one existing note from a previous session
- [x] README file exists at D:\TARA\README.md

Speak slowly and clearly. Pause one full second after TARA finishes speaking before the next query. Do not rush — the pipeline needs the silence to detect end of speech.

---

## Query Sequence

---

### Query 1 — Memory Recall
**Say:** "What is your name?"  
**Expected:** TARA introduces herself by name and purpose  
**Expected TTFS:** 3.0–3.5s (chat path, minimal context)  
**Demonstrates:** LLM persona, system is live and responsive  

**What could go wrong:**  
STT mishears "name" — TARA gives an unrelated response.  
**Recovery:** Say "Who are you?" — simpler phrasing, same intent.

---

### Query 2 — Instant Tool Path
**Say:** "What time is it?"  
**Expected:** "It's [time] on [day], [date]."  
**Expected TTFS:** 1.3–1.6s  
**Demonstrates:** Tool path, low latency, deterministic answer  

**What could go wrong:**  
Nothing. This is the most reliable query in the suite. If it fails, Ollama has crashed — restart and restart TARA before continuing.

---

### Query 3 — Compound Chain
**Say:** "How is my system doing?"  
**Expected:** "CPU is at X percent, RAM is Y of Z gigabytes, and disk is A percent full."  
**Expected TTFS:** 1.6–1.9s  
**Demonstrates:** Compound router, multi-step tool execution, no LLM call, live hardware data  

**What could go wrong:**  
STT mishears "system" as "sister" or similar.  
**Recovery:** Say "Give me a full system report" — alternate trigger phrase for the same compound chain.

---

### Query 4 — Thermal Awareness
**Say:** "What's the GPU temperature?"  
**Expected:** "GPU temperature is [X] degrees Celsius."  
**Expected TTFS:** 1.3–1.5s  
**Demonstrates:** pynvml integration, thermal-aware operation claim, live sensor data (not LLM-generated)  

**What could go wrong:**  
STT mishears "GPU" — routes to CHAT and LLM guesses a temperature.  
**Recovery:** Say "What's the GPU temp?" — shorter phrase, easier to pronounce clearly. If it still hallucinates, note aloud: "This is exactly why tool routing exists — the LLM would guess here." That's a research point, not a failure.

---

### Query 5 — Note Creation
**Say:** "Take a note: I demonstrated TARA today."  
**Expected:** "Got it, I've saved your note." (or similar)  
**Expected TTFS:** 1.3–1.5s  
**Demonstrates:** Notes tool, file persistence, agentic task execution  

**What could go wrong:**  
STT adds extra words or drops "TARA" — note saves with garbled content.  
**Recovery:** Check aloud by moving to Query 6 — if the note reads back incorrectly, say "The STT added noise there — the note still saved, which is what matters."

---

### Query 6 — Cross-Session Persistence
**Say:** "What was my last note?"  
**Expected:** Reads back the note just saved in Query 5  
**Expected TTFS:** 1.3–1.5s  
**Demonstrates:** File persistence survives within-session, notes tool reading back correctly  

**What could go wrong:**  
Reads a different note if Query 5 failed to save.  
**Recovery:** "Read my notes" — lists all notes including dates, shows the file system is populated from previous sessions going back to July 11.

---

### Query 7 — File Reader with LLM Summarisation
**Say:** "Summarize the README file."  
**Expected:** 2–3 sentence spoken summary of TARA's README content  
**Expected TTFS:** 2.2–2.6s  
**Demonstrates:** File reader tool, LLM-assisted summarisation, longest tool path in the suite  

**What could go wrong:**  
STT mishears "README" as "read me" and TARA responds conversationally.  
**Recovery:** Say "Summarize the README file" — alternate FILE_READ trigger phrase.  
LLM summary is vague or wrong — say: "The summarisation quality is model-dependent. On a 3B parameter model, this is the expected tradeoff between VRAM usage and output quality."

---

### Query 8 — Local Information Retrieval
**Say:** "What do you know about my demonstration?"  
**Expected:** Synthesised response drawing from notes and stored facts  
**Expected TTFS:** 1.4–2.0s  
**Demonstrates:** LOCAL_SEARCH tool, hybrid retrieval across SQLite and filesystem, possessive query routing  

**What could go wrong:**  
No stored facts about "project" — TARA says nothing found.  
**Recovery:** Say "What do you know about my flight?" — a note from July 11 contains flight information from earlier testing. Pivot naturally: "Let me try a query with data I know exists."

---

### Query 9 — Calculator
**Say:** "Calculate 15 percent of 340."  
**Expected:** "15 percent of 340 is 51."  
**Expected TTFS:** 1.3–1.6s  
**Demonstrates:** Calculator tool, safe_eval, arithmetic without LLM  

**What could go wrong:**  
STT mishears "340" as a different number — answer is wrong but confidently spoken.  
**Recovery:** Repeat with slower pronunciation. If it happens twice, note: "STT accuracy on numbers is hardware-dependent — this is a known edge case for non-native speakers and is documented."

---

### Query 10 — Conversational LLM Fallback
**Say:** "What is a large language model?"  
**Expected:** 1–2 sentence natural explanation  
**Expected TTFS:** 3.0–4.0s  
**Demonstrates:** Chat path, LLM inference, natural conversation, full pipeline end-to-end  

**What could go wrong:**  
Response is too long — TTFS exceeds 4.5s.  
**Recovery:** None needed — note the latency aloud and explain: "Chat path on 4GB VRAM has a 3.0s hardware floor. That's the cost of running a 3B parameter model fully offline with no cloud dependency."

---

## Capability Coverage Summary

| Query | Capability | Path | Target TTFS |
|-------|-----------|------|-------------|
| 1 | LLM persona + memory | Chat | 3.0–3.5s |
| 2 | Time tool | Tool | 1.3–1.6s |
| 3 | Compound chain | Compound | 1.6–1.9s |
| 4 | GPU temperature | Tool | 1.3–1.5s |
| 5 | Note creation | Tool | 1.3–1.5s |
| 6 | Cross-session persistence | Tool | 1.3–1.5s |
| 7 | File reader + summarisation | Tool+LLM | 2.2–2.6s |
| 8 | Local search + retrieval | Tool+LLM | 1.4–2.0s |
| 9 | Calculator | Tool | 1.3–1.6s |
| 10 | General knowledge | Chat | 3.0–4.0s |

---

## Dry Run Log — Run 1 (pre-fix)

Complete this table once before Week 10 demo:

| Query | Actual TTFS | Notes |
|-------|------------|-------|
| 1 | 3.04s | |
| 2 | 1.58s | |
| 3 | 1.69s | |
| 4 | 1.28s | |
| 5 | 1.38s | Misheard "TARA" as "Tharal" |
| 6 | 1.35s | |
| 7 | 2.29s | Misheard "README" as "Redmi" |
| 8 | 1.25s | Intent recognized from saved notes. Replied: "Your project midpoint review is on Friday."  Recovery: "flight" misheard as "slide" |
| 9 | 1.18s | |
| 10 | 3.78s | |

Run the full sequence in one live session. Do not skip queries.
Fill in actual TTFS from console output. Note any STT misheard
phrases and their corrected alternates for your accent specifically.

## Dry Run Log — Run 2 (post-fix: STT corrections + notes cleaned)
| Query | Actual TTFS | STT Output | Notes |
|-------|------------|------------|-------|
| 1 | 3.21s | My name is TARA. How can I assist you today? | |
| 2 | 1.33s | It's 07:00 PM on Sunday, August 02, 2026. | |
| 3 | 1.67s | CPU is at 67.1 percent, RAM is 11.0 of 15.7 gigabytes, and disk is 71.9 percent full. | |
| 4 | 1.17s | GPU temperature is 45 degrees Celsius. | |
| 5 | 1.53s | Note saved: I demonstrated Tara today. | |
| 6 | 1.36s | Your last note says: I demonstrated Tara today. | |
| 7 | 1.89s | The file README.md is quite long, so here is a summary: This is about an AI assistant that works offline without needing internet and can do things like remembering what you said earlier and calculating numbers. It's built on a specific hardware setup. | |
| 8 | 1.21s | I couldn't find any saved notes or facts about project. | |
| 9 | 1.20s | That's 51. | |
| 10 | 3.10s |  A large language model is a type of artificial intelligence that has been trained on vast amounts of text data to generate human-like responses and produce coherent text across various topics. | |

## Dry Run Log — Run 3
| Query | Actual TTFS | STT Output | Notes |
|-------|------------|------------|-------|
| 1 | 2.14s | My name is TARA. How can I assist you today? | |
| 2 | 1.29s | It's 07:47 PM on Sunday, August 02, 2026. | |
| 3 | 1.68s | CPU is at 61.1 percent, RAM is 11.8 of 15.7 gigabytes, and disk is 71.9 percent full. | |
| 4 | 1.50s | GPU temperature is 46 degrees Celsius. | |
| 5 | 1.34s | Take a note, I demonstrated Tara today. | |
| 6 | 1.42s | Your last note says: I demonstrated Tara today. | |
| 7 | 2.27s | The file README.md is quite long, so here is a summary: This is about an AI assistant named TARA that runs locally and doesn't need internet, has various useful features like voice input and fact recall, and uses hardware components like a specific laptop model. | |
| 8 | 1.26s | You saved notes that state you demonstrated TARA today. | |
| 9 | 1.22s | That's 51. | |
| 10 | 3.08s | A large language model is a type of artificial intelligence designed to understand and generate human-like text, typically trained on vast amounts of text data. | |

## Dry Run Log — Run 4
| Query | Actual TTFS | STT Output | Notes |
|-------|------------|------------|-------|
| 1 | 3.63s | My name is TARA. | |
| 2 | 1.53s | It's 08:58 PM on Monday, August 17, 2026. | |
| 3 | 1.78s | CPU is at 56.0 percent, RAM is 10.8 of 15.7 gigabytes, and disk is 72.7 percent full. | |
| 4 | 1.26s | GPU temperature is 40 degrees Celsius. | |
| 5 | 1.52s | Take a note, I demonstrated TARA today. | |
| 6 | 1.41s | Your last note says: I demonstrated TARA today. | |
| 7 | 2.09s | The file README.md is quite long, so here is a summary: This is about an AI assistant named TARA that works offline without needing internet and has various functions like remembering things you say, answering questions about tech stuff, checking system stats and more. | |
| 8 | 1.32s | You saved notes that state you demonstrated TARA today. | |
| 9 | 1.17s | That's 51. | |
| 10 | 3.43s | A large language model is an AI designed to understand and generate human-like text, trained extensively on massive datasets. | |
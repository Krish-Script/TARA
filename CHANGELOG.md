# Changelog

All notable changes to **TARA (Totally Autonomous Responsive Assistant)** will be documented in this file.

The format is based on **Keep a Changelog** and the project follows **Semantic Versioning (SemVer)**.

---

## [Unreleased]

### Planned

* Integrate SQLite memory with conversation pipeline
* Automatic long-term memory extraction
* Context-aware prompt injection
* Semantic memory retrieval
* Vector database integration
* Tool calling framework
* Vision module
* GUI application

---

## [0.3.0] - 2026-06-16

### Added

* Introduced SQLite-based persistent memory system.
* Created dedicated `MemoryStore` class.
* Automatic database initialization.
* Conversation history storage.
* User fact storage.
* Session ID generation utilities.
* Prompt context builder.
* Helper methods for memory extraction.
* Database reset and cleanup utilities.

### Database

* Added `tara_memory.db`.
* Added `conversations` table.
* Added `user_facts` table.
* Added indexes for optimized lookups.

### Testing

* Verified database creation.
* Verified conversation storage.
* Verified conversation retrieval.
* Verified persistent fact storage.
* Verified fact retrieval.

### Documentation

* Added Week 3 development report.
* Added project roadmap.
* Improved project documentation structure.

---

## [0.2.0] - 2026-06-12

### Added

* Migrated Text-to-Speech engine from pyttsx3 to Piper.
* Integrated `en_US-hfc_female-medium` voice.
* Improved prompt engineering using few-shot prompting.

### Improved

* Reduced speech synthesis latency.
* Improved response naturalness.
* Reduced total end-to-end latency by approximately **47%**.

### Performance

| Component | Before  | After  |
| --------- | ------- | ------ |
| STT       | 0.62 s  | 0.59 s |
| LLM       | 1.41 s  | 1.05 s |
| TTS       | 11.23 s | 5.42 s |
| Total     | 13.26 s | 7.06 s |

### Documentation

* Added Week 2 report.

---

## [0.1.0] - 2026-06-04

### Added

* Initial project structure.
* Offline Speech-to-Text using Faster-Whisper.
* Local LLM using Ollama with Llama 3.2:3B.
* Offline Text-to-Speech using pyttsx3.
* Wake-free conversational pipeline.
* Modular component architecture.
* Configuration management.
* End-to-end voice interaction.

### Performance

#### Speech-to-Text

* Average transcription latency: **0.70 s**

#### Large Language Model

* Warm inference: **0.68 s**
* GPU VRAM usage: **2.2–2.5 GB**

#### Text-to-Speech

* Average synthesis time: **4.95 s**

#### End-to-End

* Average STT: **0.62 s**
* Average LLM: **1.41 s**
* Average TTS: **11.23 s**
* Time-to-first-response: **~2.0 s**

### Fixed

* Resolved pyttsx3 speech interruption issue.
* Fixed assistant identity consistency (TARA).
* Improved application stability during long conversations.

---

## Version History

| Version    | Description                                    | Status      |
| ---------- | ---------------------------------------------- | ----------- |
| 0.1.0      | Initial offline assistant                      | Released    |
| 0.2.0      | Piper integration and performance improvements | Released    |
| 0.3.0      | SQLite memory system                           | Released    |
| Unreleased | Memory integration, RAG, automation, vision    | In Progress |

---

## Project Statistics

Current Features

* Offline Speech Recognition
* Local Large Language Model
* Offline Speech Synthesis
* Modular Architecture
* SQLite Memory Backend
* Persistent User Facts
* Conversation History
* Session Management

Current Technology Stack

* Python
* Faster-Whisper
* Ollama
* Llama 3.2:3B
* Piper TTS
* SQLite
* Git
* GitHub

---

Maintained by **Krishnendu Mandal** as part of the **TARA** project.

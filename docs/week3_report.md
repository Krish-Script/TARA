# TARA - Week 3 Report

## Sprint Goal

Implement persistent memory using SQLite.

---

# Features

- SQLite database
- Conversation history
- User fact storage
- Session management
- Automatic database creation

---

# Database

```
tara_memory.db
```

Tables:

- conversations
- user_facts

---

# Completed

- [x] Memory schema
- [x] Database initialization
- [x] Save conversations
- [x] Load conversations
- [x] Save user facts
- [x] Read user facts

---

# Testing

| Test | Status |
|------|--------|
| Database creation | ✅ |
| conversations table | ✅ |
| user_facts table | ✅ |
| save_turn() | ✅ |
| get_recent_turns() | ✅ |
| save_fact() | ✅ |
| get_facts() | ✅ |

---

# Current Status

The memory layer works independently.

Next step is integrating it with:

- main.py
- llm.py

so TARA automatically remembers previous conversations.

---

# Next Sprint

- Long-term memory retrieval
- Automatic memory extraction
- Better prompt construction
- Semantic search
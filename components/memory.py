"""
SQLite-backed memory layer for TARA.

Stores:
- conversation turns for short-term context
- user facts for long-term recall

This module is intentionally self-contained so it can be wired into
llm.py and main.py without pulling in extra dependencies.
"""

from __future__ import annotations

import re
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, List, Optional, Sequence
MAX_CONTEXT_TOKENS = 600  # approximate ceiling for injected history

def _utc_now_iso() -> str:
    """Return a UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalize_fact(fact: str) -> str:
    """Normalize a fact so duplicates can be detected reliably."""
    return re.sub(r"\s+", " ", fact.strip().lower())


def create_session_id(prefix: str = "session") -> str:
    """Create a human-readable session id."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{stamp}-{uuid.uuid4().hex[:8]}"


@dataclass(frozen=True)
class ConversationTurn:
    session_id: str
    turn_index: int
    timestamp: str
    user_message: str
    assistant_response: str
    source: str = "chat"


@dataclass(frozen=True)
class UserFact:
    fact: str
    created_at: str
    updated_at: str


class MemoryStore:
    """
    SQLite memory store for TARA.
    Default database file:
        D:\\TARA\\tara_memory.db
    """

    def __init__(self, db_path: str | Path = "tara_memory.db") -> None:
        self.db_path = Path(db_path)
        parent = self.db_path.parent
        if str(parent) not in (".", ""):
            parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        try:
            yield conn
        finally:
            conn.close()

    def _initialize(self) -> None:
        """Create tables and indexes if they do not already exist."""
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    turn_index INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    assistant_response TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS user_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fact_key TEXT NOT NULL UNIQUE,
                    fact TEXT NOT NULL,
                    source_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_conversations_session_turn
                ON conversations(session_id, turn_index);

                CREATE INDEX IF NOT EXISTS idx_conversations_timestamp
                ON conversations(timestamp);

                CREATE INDEX IF NOT EXISTS idx_user_facts_updated_at
                ON user_facts(updated_at);
                """
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Conversation storage
    # ------------------------------------------------------------------
    def next_turn_index(self, session_id: str) -> int:
        """Return the next turn number for the given session."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(turn_index), 0) + 1 AS next_index "
                "FROM conversations WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            return int(row["next_index"]) if row else 1

    def save_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str,
        timestamp: Optional[str] = None,
        source: str = "chat",
    ) -> int:
        """
        Save one user/assistant exchange and return the inserted row id.
        source: 'chat' for LLM-generated responses, 'tool' for tool-path responses.
        """
        user_message = (user_message or "").strip()
        assistant_response = (assistant_response or "").strip()
        if not user_message and not assistant_response:
            raise ValueError("Cannot save an empty conversation turn.")

        if source not in ("chat", "tool"):
            raise ValueError(f"Invalid source tag: {source!r}. Must be 'chat' or 'tool'.")

        ts = timestamp or _utc_now_iso()
        turn_index = self.next_turn_index(session_id)

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO conversations (
                    session_id, turn_index, timestamp,
                    user_message, assistant_response, source
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, turn_index, ts, user_message, assistant_response, source),
            )
            conn.commit()
            return int(cursor.lastrowid)  # type: ignore

    def get_recent_turns(
        self,
        session_id: Optional[str] = None,
        limit: int = 6,
        source_filter: Optional[str] = None,  # None = all, 'chat' = chat only, 'tool' = tool only
    ) -> List[ConversationTurn]:
        """
        Fetch the most recent conversation turns.
        If session_id is provided, only that session is queried.
        If source_filter is provided, only turns matching that source are returned.
        """
        limit = max(1, int(limit))

        conditions = []
        params: list[object] = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)

        if source_filter is not None:
            conditions.append("source = ?")
            params.append(source_filter)

        query = """
            SELECT session_id, turn_index, timestamp,
                user_message, assistant_response, source
            FROM conversations
        """
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            ConversationTurn(
                session_id=row["session_id"],
                turn_index=int(row["turn_index"]),
                timestamp=row["timestamp"],
                user_message=row["user_message"],
                assistant_response=row["assistant_response"],
                source=row["source"],
            )
            for row in reversed(rows)
        ]


    def get_context_for_llm(self, session_id: Optional[str] = None) -> str:
        """
        Return a token-budgeted context string for LLM injection.
        Only chat-path turns are included — tool responses are excluded.
        Oldest turns are dropped first when the budget is exceeded.
        Token count is approximated as word_count * 1.3.
        """
        turns = self.get_recent_turns(
            session_id=session_id,
            limit=10,
            source_filter="chat",
        )

        context_parts: list[str] = []
        running_tokens = 0.0

        for turn in reversed(turns):  # most recent first, then trim oldest
            candidate = f"User: {turn.user_message}\nTARA: {turn.assistant_response}\n"
            token_estimate = len(candidate.split()) * 1.3
            if running_tokens + token_estimate > MAX_CONTEXT_TOKENS:
                break
            context_parts.append(candidate)
            running_tokens += token_estimate

        context_parts.reverse()  # restore chronological order for LLM
        return "".join(context_parts)

    def clear_session_turns(self, session_id: str) -> int:
        """Delete all turns for a session and return the count removed."""
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM conversations WHERE session_id = ?",
                (session_id,),
            )
            conn.commit()
            return int(cursor.rowcount)

    def clear_all_turns(self) -> int:
        """Delete all conversation turns."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM conversations")
            conn.commit()
            return int(cursor.rowcount)

    # ------------------------------------------------------------------
    # Persistent user facts
    # ------------------------------------------------------------------
    def save_fact(self, fact: str, source_message: Optional[str] = None) -> bool:
        """
        Store a user fact permanently.

        Returns True when a new row is inserted or an existing one is updated.
        """
        cleaned = " ".join((fact or "").split()).strip()
        if not cleaned:
            return False

        fact_key = _normalize_fact(cleaned)
        now = _utc_now_iso()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_facts (fact_key, fact, source_message, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(fact_key) DO UPDATE SET
                    fact = excluded.fact,
                    source_message = COALESCE(excluded.source_message, user_facts.source_message),
                    updated_at = excluded.updated_at
                """,
                (fact_key, cleaned, source_message, now, now),
            )
            conn.commit()
        return True

    def get_facts(self, limit: Optional[int] = None) -> List[UserFact]:
        """Return stored user facts ordered from newest to oldest."""
        query = """
            SELECT fact, created_at, updated_at
            FROM user_facts
            ORDER BY updated_at DESC, id DESC
        """
        params: Sequence[object] = ()
        if limit is not None:
            query += " LIMIT ?"
            params = (max(1, int(limit)),)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            UserFact(
                fact=row["fact"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def clear_facts(self) -> int:
        """Delete all stored user facts."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM user_facts")
            conn.commit()
            return int(cursor.rowcount)
        

    # ------------------------------------------------------------------
    # Prompt-building helpers
    # ------------------------------------------------------------------
    def build_context(self, session_id=None, recent_turns=6, fact_limit=10):
        """
        Build a prompt-ready memory block.
        The returned text is meant to be injected into the LLM context as
        a system/developer-style memory note or as a prefixed context block.
        """
        facts = self.get_facts(limit=fact_limit)
        turns_context = self.get_context_for_llm(session_id=session_id)

        print(f"[MEMORY DEBUG] facts={len(facts)} | context_chars={len(turns_context)} | context_tokens_est={len(turns_context.split())*1.3:.0f}")
        print(f"[MEMORY DEBUG] context preview: {turns_context[:200]!r}")

        sections = []

        if facts:
            fact_lines = "\n".join(f"- {item.fact}" for item in facts)
            sections.append(f"Known user facts:\n{fact_lines}")

        if turns_context:
            sections.append("Recent conversation:\n" + turns_context)

        return "\n\n".join(sections).strip()

    def build_few_shot_memory(
        self,
        session_id: Optional[str] = None,
        recent_turns: int = 6,
        fact_limit: int = 10,
    ) -> str:
        """Alias for build_context() kept for readability in llm.py."""
        return self.build_context(
            session_id=session_id,
            recent_turns=recent_turns,
            fact_limit=fact_limit,
        )

    # ------------------------------------------------------------------
    # Convenience utilities
    # ------------------------------------------------------------------
    @staticmethod
    def extract_fact_from_text(text: str) -> Optional[str]:
        """
        Extract a likely memory fact from a 'remember ...' style request.
        """
        if not text:
            return None

        cleaned = " ".join(text.strip().split())

        patterns = [
            r"^remember that (.+)$",
            r"^remember (.+)$",
            r"^please remember that (.+)$",
            r"^please remember (.+)$",
            r"^keep in mind that (.+)$",
        ]

        for pattern in patterns:
            match = re.match(pattern, cleaned, flags=re.IGNORECASE)
            if match:
                captured = match.group(1).strip(" .!?")
                if captured:
                    if len(captured) == 1:
                        return captured.upper()
                    return captured[0].upper() + captured[1:]

        return None

    def remember_if_requested(self, user_text: str) -> bool:
        """
        Convenience helper: store a fact if the user's message looks like a
        memory request. Returns True if something was stored.
        """
        fact = self.extract_fact_from_text(user_text)
        if not fact:
            return False
        return self.save_fact(fact, source_message=user_text)

    def reset_all(self) -> None:
        """Wipe all stored memory."""
        self.clear_all_turns()
        self.clear_facts()

    def print_stats(self) -> None:
        """Print summary stats about stored conversations and facts."""
        with self._connect() as conn:
            convo_count = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
            fact_count = conn.execute("SELECT COUNT(*) FROM user_facts").fetchone()[0]

        print(f"[MemoryStore] {convo_count} conversation turns, {fact_count} user facts stored.")


__all__ = [
    "ConversationTurn",
    "MemoryStore",
    "UserFact",
    "create_session_id",
]
"""
components/llm.py — Language Model Component
=============================================
Uses Ollama to run LLaMA 3.2 locally on your GPU.
"""

import time

import ollama


class LanguageModel:
    def __init__(self, config: dict):
        self.config             = config
        self.conversation_history: list[dict] = []
        self._test_connection()
        self.warm_up()  # Preload the model to reduce first-response latency

    # ── Startup Check ────────────────────────────────────────

    def _test_connection(self):
        """Verify Ollama is running and the model exists."""
        try:
            models      = ollama.list()
            model_names = [m.model for m in models.models]
            target      = self.config["model"]

            # Check if our model is in the list
            if any(target in name for name in model_names):
                print(f"[LLM] Model '{target}' ready ✓")
            else:
                print(f"[LLM] ⚠  Model '{target}' not found locally.")
                print(f"[LLM]    Run this in a terminal: ollama pull {target}")
                print(f"[LLM]    Available models: {model_names}")

        except Exception as e:
            print(f"[LLM] ❌ Cannot connect to Ollama: {e}")
            print("[LLM]    Fix: open the Ollama app, or run 'ollama serve' in a terminal.")

    # ── Response Generation ──────────────────────────────────

    def generate(self, user_message: str) -> tuple[str, float]:
        """
        Send a message to the LLM and get a response.
        Automatically keeps track of conversation history so
        the assistant remembers what was said earlier.

        Returns (response_text, latency_seconds).
        """
        # Add the user's message to memory
        self.conversation_history.append({
            "role":    "user",
            "content": user_message,
        })

        # Build the full message list:
        #   [system prompt]  ← sets the TARA persona
        #   [user turn 1]
        #   [assistant turn 1]
        #   [user turn 2]     ← current message
        messages = [
            {"role": "system", "content": self.config["system_prompt"]}
        ] + self.conversation_history

        start = time.time()

        response = ollama.chat(
            model=self.config["model"],
            messages=messages,
            keep_alive=self.config.get("keep_alive", "30m"),
            options={
                "temperature": self.config.get("temperature", 0.7),
                "num_ctx":     self.config.get("num_ctx",     2048),
            },
        )

        latency = time.time() - start

        # Extract the text from the response object
        assistant_text = response.message.content.strip() # type: ignore

        # Save the assistant's reply to memory
        self.conversation_history.append({
            "role":    "assistant",
            "content": assistant_text,
        })

        # Trim old history to prevent memory bloat
        # Each conversation turn = 2 entries (user + assistant)
        max_entries = self.config.get("max_history", 10) * 2
        if len(self.conversation_history) > max_entries:
            self.conversation_history = self.conversation_history[-max_entries:]

        return assistant_text, latency

    # ── Utility ──────────────────────────────────────────────

    def clear_history(self):
        """Wipe conversation memory. Call when starting a new topic."""
        self.conversation_history = []
        print("[LLM] Conversation history cleared.")

    def warm_up(self):
        """
        Send a throwaway request so Ollama loads the model
        before the user speaks their first real message.
        """
        print("[LLM] Warming up model...")
        start = time.time()
        ollama.chat(
            model=self.config["model"],
            messages=[{"role": "user", "content": "hi"}],
            options={"num_ctx": self.config.get("num_ctx", 2048)}
        )
        print(f"[LLM] Model warm ✓  ({time.time() - start:.1f}s load time)")
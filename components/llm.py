"""
components/llm.py — Language Model Component
=============================================
Uses Ollama to run LLaMA 3.2 locally on your GPU.

How Ollama works:
  - Ollama is a separate app/server running in the background.
  - This Python file sends text to it over localhost (no internet).
  - Ollama loads the model onto your GPU and sends back a response.
  - Think of Ollama as the engine; this file is the steering wheel.
"""

import time

import ollama


class LanguageModel:
    def __init__(self, config: dict):
        self.config             = config
        self.conversation_history: list[dict] = []
        self._test_connection()

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
            options={
                "temperature": self.config.get("temperature", 0.7),
                "num_ctx":     self.config.get("num_ctx",     2048),
            },
        )

        latency = time.time() - start

        # Extract the text from the response object
        assistant_text = response.message.content.strip()

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
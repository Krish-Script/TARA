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

    def generate(self, user_message: str, memory_context: str = "") -> tuple[str, float]:
        """
        Send a message to the LLM and get a response.
        Memory is handled externally via memory_context (SQLite-backed).
        Returns (response_text, latency_seconds).
        """
        system_content = self.config["system_prompt"]
        if memory_context:
            system_content = system_content + "\n\n" + memory_context

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user",   "content": user_message},
        ]

        start = time.time()

        response = ollama.chat(
            model=self.config["model"],
            messages=messages,
            keep_alive=self.config.get("keep_alive", "5m"),  # discard KV cache after each call — prevents latency drift
            options={
                "temperature": self.config.get("temperature", 0.7),
                "num_ctx":     self.config.get("num_ctx", 2048),
                "num_predict": self.config.get("num_predict", 80),
            },
        )

        latency = time.time() - start
        return response.message.content.strip(), latency  # type: ignore

    # ── Utility ──────────────────────────────────────────────

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
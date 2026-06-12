"""
tests/test_llm.py — Isolated LLM Test
This test checks if the local LLM component is working correctly by sending a few simple prompts and measuring the response time.
==============================================
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.llm import LanguageModel
from config import LLM_CONFIG


def test_llm():
    print("=" * 55)
    print("  LLM COMPONENT TEST — Day 3")
    print("=" * 55)
    print("Sending 3 test prompts to the local LLM...")
    print("(No voice, just text in → text out)")
    print()

    llm = LanguageModel(LLM_CONFIG)

    test_prompts = [
        "Introduce yourself in one sentence.",
        "What is the capital of Japan?",
        "Tell me one very short joke.",
    ]

    latencies = []

    for i, prompt in enumerate(test_prompts, 1):
        print(f"─── Test {i} ───")
        print(f"  You:  {prompt}")

        response, latency = llm.generate(prompt)

        print(f"  TARA: {response}")
        print(f"  ⏱  Latency: {latency:.2f}s")
        latencies.append(latency)
        print()

    # Summary
    print("=" * 55)
    if latencies:
        avg = sum(latencies) / len(latencies)
        print(f"  ✅ LLM TEST PASSED")
        print(f"  📊 Average latency: {avg:.2f}s")
        print()
        print(f"  ⭐ SAVE THIS NUMBER → avg LLM latency = {avg:.2f}s")
        print("     You'll need it for your Week 1 baseline report.")
    print("=" * 55)

    print()
    print("Also check: open Task Manager → Performance → GPU")
    print("Your VRAM usage should be around 2.0-3.0 GB while the model is loaded.")


if __name__ == "__main__":
    test_llm()
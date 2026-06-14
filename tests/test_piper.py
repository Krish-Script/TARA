"""
tests/test_piper.py — Isolated Piper TTS Test (Week 2, Day 2)
=============================================================
Run this ALONE before touching main.py.
Goal: confirm Piper generates audio and sounds better than pyttsx3.

Usage:
    cd D:\TARA
    .venv\Scripts\activate
    python tests/test_piper.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.tts import TextToSpeech
from config import PIPER_CONFIG          # ← uses PIPER_CONFIG, not TTS_CONFIG


def test_piper():
    print("=" * 55)
    print("  PIPER TTS TEST — Week 2")
    print("=" * 55)
    print("You should hear a noticeably more natural voice.")
    print()

    tts = TextToSpeech(PIPER_CONFIG)

    test_phrases = [
        "Hello! I am TARA, your offline AI assistant.",
        "All of my processing happens on your local device.",
        "No internet connection is required for me to work.",
    ]

    latencies = []

    for i, phrase in enumerate(test_phrases, 1):
        print(f"─── Phrase {i} ───")
        print(f"  Text: {phrase}")
        latency = tts.speak(phrase)
        print(f"  ⏱  TTS time: {latency:.2f}s")
        latencies.append(latency)
        print()

    avg = sum(latencies) / len(latencies)
    print("=" * 55)
    print(f"  📊 Piper avg latency: {avg:.2f}s")
    print(f"  📊 pyttsx3 baseline:  4.95s (Day 4)")
    print(f"  📊 Improvement:       {4.95 - avg:+.2f}s")
    print()

    if avg < 4.95:
        print("  ✅ Piper is FASTER than pyttsx3")
    else:
        print("  ⚠  Piper is slower — try en_US-lessac-low model instead")

    print("=" * 55)


if __name__ == "__main__":
    test_piper()
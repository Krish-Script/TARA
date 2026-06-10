"""
tests/test_stt.py — Isolated STT Test (Day 2)
==============================================
Run this ALONE before touching LLM or TTS.
Goal: confirm your microphone works and Whisper transcribes correctly.

Usage:
    cd D:\\TARA
    .venv\\Scripts\\activate
    python tests/test_stt.py
"""

import sys
import os

# Allow imports from the parent folder (the project root)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.stt import SpeechToText
from config import STT_CONFIG, AUDIO_CONFIG


def test_stt():
    print("=" * 55)
    print("  STT COMPONENT TEST — Day 2")
    print("=" * 55)
    print("You will have 3 recording rounds.")
    print("Speak clearly after you see 🎤 Listening...")
    print()

    # Merge the two config dicts so SpeechToText gets everything it needs
    config = {**STT_CONFIG, **AUDIO_CONFIG}
    stt = SpeechToText(config)

    latencies = []

    for round_num in range(1, 4):
        print(f"─── Round {round_num} of 3 ───")
        text, latency = stt.listen_and_transcribe()

        if text:
            print(f"  ✅ Heard:   '{text}'")
            print(f"  ⏱  Latency: {latency:.2f}s")
            latencies.append(latency)
        else:
            print("  ❌ Nothing heard.")
            print("     Try: speak louder, or lower 'silence_threshold' in config.py")
        print()

    # Summary
    print("=" * 55)
    if latencies:
        avg = sum(latencies) / len(latencies)
        print(f"  ✅ STT TEST PASSED")
        print(f"  📊 Average latency: {avg:.2f}s")
        print()
        print(f"  ⭐ SAVE THIS NUMBER → avg STT latency = {avg:.2f}s")
        print("     You'll need it for your Week 1 baseline report.")
    else:
        print("  ❌ STT TEST FAILED — nothing was transcribed.")
        print()
        print("  Troubleshooting:")
        print("  1. Is your microphone plugged in and set as default in Windows?")
        print("  2. Try lowering 'silence_threshold' in config.py (e.g. 150)")
        print("  3. Try increasing 'silence_duration' to 2.5")
    print("=" * 55)


if __name__ == "__main__":
    test_stt()